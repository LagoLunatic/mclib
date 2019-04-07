
from mclib.param_entity import ParamEntity

class Exit(ParamEntity):
  def __init__(self, exit_ptr, room, rom):
    super().__init__()
    
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
    self.unknown_4 = self.rom.read_u8(self.exit_ptr + 0xF)
    self.unknown_5 = self.rom.read_u16(self.exit_ptr + 0x10)
    self.padding_1 = self.rom.read_u16(self.exit_ptr + 0x12)
    
    self.add_property("exit_ptr", 32, pretty_name="ROM Location")
    self.add_property("transition_type", 16)
    self.add_property("x_pos", 16)
    self.add_property("y_pos", 16)
    self.add_property("dest_x", 16)
    self.add_property("dest_y", 16)
    self.add_property("screen_edge", 8)
    self.add_property("dest_area", 8)
    self.add_property("dest_room", 8)
    self.add_property("unknown_2", 8)
    self.add_property("unknown_3", 8)
    self.add_property("unknown_4", 8)
    self.add_property("unknown_5", 16)
    self.add_property("padding_1", 16)
