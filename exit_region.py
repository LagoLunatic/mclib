
from mclib.exit import Exit
from mclib.param_entity import ParamEntity

class ExitRegion(ParamEntity):
  def __init__(self, region_ptr, rom):
    super().__init__()
    
    self.region_ptr = region_ptr
    self.rom = rom
    
    self.read()
  
  @staticmethod
  def read_list_of_exit_regions(region_list_ptr, room):
    regions = []
    
    region_ptr = region_list_ptr
    while room.rom.read_u16(region_ptr) != 0xFFFF:
      region = ExitRegion(region_ptr, room.rom)
      regions.append(region)
      
      exit_ptr = room.rom.read_u32(room.property_list_ptr + region.exit_pointer_property_index*4)
      region.exit = Exit(exit_ptr, room, room.rom)
      
      region_ptr += 8
    
    return regions
  
  def read(self):
    self.center_x = self.rom.read_u16(self.region_ptr + 0)
    self.center_y = self.rom.read_u16(self.region_ptr + 2)
    self.half_width = self.rom.read_u8(self.region_ptr + 4)
    self.half_height = self.rom.read_u8(self.region_ptr + 5)
    self.exit_pointer_property_index = self.rom.read_u8(self.region_ptr + 6)
    self.unknown_1 = self.rom.read_u8(self.region_ptr + 7) # TODO figure this out, it's a bitfield
    
    self.add_property("region_ptr", 32, pretty_name="ROM Location")
    self.add_property("center_x", 16)
    self.add_property("center_y", 16)
    self.add_property("half_width", 8)
    self.add_property("half_height", 8)
    self.add_property("exit_pointer_property_index", 8, pretty_name="Which Exit")
    self.add_property("unknown_1", 8)
    
    # TODO: need to somehow display the exit as a child property
