
class VisualZone:
  def __init__(self, zone_ptr, rom):
    self.zone_ptr = zone_ptr
    self.rom = rom
    
    self.read()
  
  @staticmethod
  def read_list_of_zones(zone_list_ptr, rom):
    zones = []
    
    zone_ptr = zone_list_ptr
    while rom.read_u16(zone_ptr) != 0x00FF:
      zone = VisualZone(zone_ptr, rom)
      zones.append(zone)
      
      zone_ptr += 0xA
    
    return zones
  
  def read(self):
    self.zone_id = self.rom.read_u16(self.zone_ptr + 0)
    self.x = self.rom.read_u16(self.zone_ptr + 2)
    self.y = self.rom.read_u16(self.zone_ptr + 4)
    self.w = self.rom.read_u16(self.zone_ptr + 6)
    self.h = self.rom.read_u16(self.zone_ptr + 8)
