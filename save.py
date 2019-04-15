
class Save:
  def __init__(self, raw_data):
    if len(raw_data) != 0x2000:
      raise Exception("Not a valid Minish Cap save.")
    if raw_data.read_str(0) != "AGBZELDA:THE MINISH CAP:ZELDA 5":
      raise Exception("Not a valid Minish Cap save.")
    
    self.data = raw_data
    
    self.slots = [
      SaveSlot(0x080, self.data),
      SaveSlot(0x580, self.data),
      SaveSlot(0xA80, self.data),
    ]
    
    self.read()
  
  def read(self):
    for slot in self.slots:
      slot.read()
  
  def write(self):
    for slot_index, slot in enumerate(self.slots):
      slot.write()
      
      slot_str = self.data.read_raw(0x34 + 0x10*slot_index, 4)
      slot_str_checksum = self.calculate_checksum(slot_str)
      slot_data = self.data.read_raw(0x80 + 0x500*slot_index, 0x500)
      slot_data_checksum = self.calculate_checksum(slot_data)
      
      slot_checksum = (slot_str_checksum + slot_data_checksum) & 0xFFFF
      self.data.write_u16(0x30 + 0x10*slot_index, slot_checksum)
      self.data.write_u16(0x32 + 0x10*slot_index, 0x10000-slot_checksum)
    
    first_redundant_data = self.data.read_bytes(0, 0x1000)
    self.data.write_bytes(0x1000, first_redundant_data)
  
  @staticmethod
  def calculate_checksum(data):
    checksum = 0
    data_len_remaining = len(data)
    offset = 0
    
    while offset < len(data):
      checksum += (data.read_u16(offset) ^ data_len_remaining)
      offset += 2
      data_len_remaining -= 2
    
    return checksum
  
  
  def to_raw_format(self):
    return self.data.copy()
  
  def to_vba_mgba_format(self):
    if len(self.data) % 8 != 0:
      raise Exception("Save data length is invalid.")
    
    new_data = self.data.copy()
    
    offset = 0
    while offset < len(self.data):
      for i in range(8):
        byte = self.data.read_u8(offset + i)
        new_data.write_u8(offset + 7 - i, byte)
      offset += 8
    
    return new_data
  
  def to_gameshark_format(self):
    raise NotImplementedError() # TODO
  
  @staticmethod
  def from_raw_format(raw_data):
    return Save(raw_data)
  
  @staticmethod
  def from_vba_mgba_format(data):
    if len(data) != 0x2000:
      raise Exception("Not a valid Minish Cap save.")
    
    raw_data = data.copy()
    
    offset = 0
    while offset < len(data):
      for i in range(8):
        byte = data.read_u8(offset + i)
        raw_data.write_u8(offset + 7 - i, byte)
      offset += 8
    
    return Save.from_raw_format(raw_data)
  
  @staticmethod
  def from_gameshark_format(data):
    if len(data) != 0x2067:
      raise Exception("Not a GameShark save.")
    if data.read_str(4) != "SharkPortSave":
      raise Exception("Not a GameShark save.")
    
    raw_data = data.read_raw(0x63, 0x2000)
    
    return Save.from_raw_format(raw_data)

class SaveSlot:
  NUM_FIGURINES = 0x120
  NUM_ITEMS = 0x88
  NUM_FLAGS = 0x1000
  
  def __init__(self, offset, data):
    self.offset = offset
    self.data = data
  
  def read(self):
    self.area_index = self.data.read_u8(self.offset + 0x88)
    self.room_index = self.data.read_u8(self.offset + 0x89)
    self.button_a_equip = self.data.read_u8(self.offset + 0xB4)
    self.button_b_equip = self.data.read_u8(self.offset + 0xB5)
    
    self.owned_figurines = []
    for i in range(self.NUM_FIGURINES):
      byte = self.data.read_u8(self.offset + 0xCE + i//8)
      bit_offset = (i % 8)
      figurine_is_owned = byte & (1 << bit_offset) != 0
      self.owned_figurines.append(figurine_is_owned)
    
    self.owned_item_info = []
    for i in range(self.NUM_ITEMS):
      byte = self.data.read_u8(self.offset + 0xF2 + i//4)
      bits_offset = (i % 4)*2
      item_value = (byte >> bits_offset) & 0x03
      self.owned_item_info.append(item_value)
    
    self.flags = []
    for i in range(self.NUM_FLAGS):
      byte = self.data.read_u8(self.offset + 0x25C + i//8)
      bit_offset = (i % 8)
      flag_is_set = byte & (1 << bit_offset) != 0
      self.flags.append(flag_is_set)
  
  def write(self):
    for i in range(self.NUM_ITEMS):
      byte = self.data.read_u8(self.offset + 0xF2 + i//4)
      bits_offset = (i % 4)*2
      byte = byte & ~(0x03 << bits_offset)
      byte = byte | (self.owned_item_info[i] & 0x03) << bits_offset
      byte = self.data.write_u8(self.offset + 0xF2 + i//4, byte)
