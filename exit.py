
class Exit:
  def __init__(self, exit_ptr, room, rom):
    self.exit_ptr = exit_ptr
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.transition_type = self.rom.read_u16(self.exit_ptr + 0)
    self.x_pos = self.rom.read_u16(self.exit_ptr + 2)
    self.y_pos = self.rom.read_u16(self.exit_ptr + 4)
    self.dest_x = self.rom.read_u16(self.exit_ptr + 6)
    self.dest_y = self.rom.read_u16(self.exit_ptr + 8)
    self.screen_edge = self.rom.read_u8(self.exit_ptr + 0xA)
    self.dest_area = self.rom.read_u8(self.exit_ptr + 0xB)
    self.dest_room = self.rom.read_u8(self.exit_ptr + 0xC)
    self.unknown_2 = self.rom.read_u8(self.exit_ptr + 0xD)
    self.unknown_3 = self.rom.read_u8(self.exit_ptr + 0xE)
    self.unknown_3 = self.rom.read_u8(self.exit_ptr + 0xF)
    self.unknown_4 = self.rom.read_u16(self.exit_ptr + 0x10)
    self.padding = self.rom.read_u16(self.exit_ptr + 0x12)
    if self.padding != 0x0000:
      print("Found an exit with nonzero padding! %08X" % self.exit_ptr)
