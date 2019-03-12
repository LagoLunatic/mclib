
class Entity:
  def __init__(self, entity_ptr, room, rom):
    self.entity_ptr = entity_ptr
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    type_and_unknowns = self.rom.read_u8(self.entity_ptr + 0)
    self.type = type_and_unknowns & 0x0F
    self.unknown_1 = (type_and_unknowns & 0xF0) >> 4
    self.unknown_2 = self.rom.read_u8(self.entity_ptr + 1)
    self.subtype = self.rom.read_u8(self.entity_ptr + 2)
    self.unknown_3 = self.rom.read_u8(self.entity_ptr + 3)
    
    self.unknown_4 = self.rom.read_u32(self.entity_ptr + 4)
    
    self.x_pos = self.rom.read_u16(self.entity_ptr + 8)
    self.y_pos = self.rom.read_u16(self.entity_ptr + 0xA)
    
    self.params = self.rom.read_u32(self.entity_ptr + 0xC)

class TileEntity:
  def __init__(self, entity_ptr, room, rom):
    self.entity_ptr = entity_ptr
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.type = self.rom.read_u8(self.entity_ptr + 0)
    self.unknown_1 = self.rom.read_u8(self.entity_ptr + 1)
    self.item_id = self.rom.read_u8(self.entity_ptr + 2)
    self.unknown_2 = self.rom.read_u8(self.entity_ptr + 3)
    
    pos = self.rom.read_u16(self.entity_ptr + 4)
    self.x_pos = pos & 0x003F
    self.y_pos = (pos & 0x0FC0) >> 6
    
    self.message_id = self.rom.read_u16(self.entity_ptr + 6)
