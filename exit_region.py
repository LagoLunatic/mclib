
from mclib.exit import Exit

class ExitRegion:
  def __init__(self, region_ptr, rom):
    self.region_ptr = region_ptr
    self.rom = rom
    
    self.read()
  
  @staticmethod
  def read_list_of_entrances(region_list_ptr, room):
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
    self.unknown_bitfield = self.rom.read_u8(self.region_ptr + 7) # TODO
