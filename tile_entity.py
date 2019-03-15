
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
    
    bitfield = self.rom.read_u16(self.entity_ptr + 4)
    self.x_pos = bitfield & 0x003F
    self.y_pos = (bitfield & 0x0FC0) >> 6
    self.unknown_3 = (bitfield & 0xF000) >> 12 # Might be unused?
    
    self.message_id = self.rom.read_u16(self.entity_ptr + 6)
