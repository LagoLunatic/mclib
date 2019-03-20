
class VisualZone:
  # 240x160 is the GBA's screen resolution.
  # We search within half the size of the screen (since Link is in the middle).
  # We also add 32 pixels of leeway on all sides.
  X_SEARCH_RANGE = 240//2 + 32
  Y_SEARCH_RANGE = 160//2 + 32
  
  def __init__(self, zone_ptr, rom):
    self.zone_ptr = zone_ptr
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.zone_id = self.rom.read_u16(self.zone_ptr + 0)
    self.x = self.rom.read_u16(self.zone_ptr + 2)
    self.y = self.rom.read_u16(self.zone_ptr + 4)
    self.w = self.rom.read_u16(self.zone_ptr + 6)
    self.h = self.rom.read_u16(self.zone_ptr + 8)
  
  @staticmethod
  def read_list_of_zones(zone_list_ptr, rom):
    zones = []
    
    zone_ptr = zone_list_ptr
    while rom.read_u16(zone_ptr) != 0x00FF:
      zone = VisualZone(zone_ptr, rom)
      zones.append(zone)
      
      zone_ptr += 0xA
    
    return zones
  
  @staticmethod
  def get_zone_lists_for_area(tileset_swapper_entity_subtype, area_index, rom):
    if tileset_swapper_entity_subtype == 7:
      # Minish Village
      return [
        VisualZone.read_list_of_zones(0x08108050, rom),
      ]
    elif tileset_swapper_entity_subtype == 0x12:
      # Hyrule Town
      if area_index == 0x15:
        # Hyrule Town (Prologue)
        return [
          VisualZone.read_list_of_zones(0x081083DA, rom),
          VisualZone.read_list_of_zones(0x081083F2, rom),
        ]
      else:
        # Hyrule Town (Normal)
        return [
          VisualZone.read_list_of_zones(0x08108398, rom),
          VisualZone.read_list_of_zones(0x081083AE, rom),
          VisualZone.read_list_of_zones(0x081083C4, rom),
        ]
    
    return []
  
  @staticmethod
  def get_zone_ids_overlapping_point(zone_lists, x, y):
    zone_ids = []
    
    for zone_list in zone_lists:
      for zone in zone_list:
        if x+15 < zone.x - VisualZone.X_SEARCH_RANGE:
          continue
        if x-15 >= zone.x + zone.w + VisualZone.X_SEARCH_RANGE:
          continue
        if y+15 < zone.y - VisualZone.Y_SEARCH_RANGE:
          continue
        if y-15 >= zone.y + zone.h + VisualZone.Y_SEARCH_RANGE:
          continue
        zone_ids.append(zone.zone_id)
        break
    
    return zone_ids

class VisualZoneData:
  def __init__(self, tileset_swapper_entity_subtype, area_index, zone_id, rom):
    self.tileset_swapper_entity_subtype = tileset_swapper_entity_subtype
    self.area_index = area_index
    self.zone_id = zone_id
    self.rom = rom
    
    self.read()
  
  def read(self):
    if self.tileset_swapper_entity_subtype == 7:
      # Minish Village
      self.palette_group_index = self.rom.read_u8(0x081081E4 + self.zone_id)
      
      self.gfx_load_datas = []
      first_zone_gfx_info_ptr = 0x081080A4
      for i in range(8):
        zone_gfx_info_ptr = first_zone_gfx_info_ptr + 0x40*self.zone_id + i*8
        
        zone_gfx_data_ptr = self.rom.read_u32(zone_gfx_info_ptr) + 0x085A2E80
        zone_gfx_load_offset = self.rom.read_u32(zone_gfx_info_ptr+4) - 0x06000000
        
        self.gfx_load_datas.append((zone_gfx_data_ptr, zone_gfx_load_offset))
    elif self.tileset_swapper_entity_subtype == 0x12:
      # Hyrule Town
      if self.area_index == 0x15:
        # Hyrule Town (Prologue)
        first_zone_gfx_info_ptr = 0x08108468
      else:
        # Hyrule Town (Normal)
        first_zone_gfx_info_ptr = 0x08108408
      
      self.palette_group_index = None
      
      self.gfx_load_datas = []
      for i in range(2):
        zone_gfx_info_ptr = first_zone_gfx_info_ptr + 0x10*self.zone_id + i*8
        
        zone_gfx_data_ptr = self.rom.read_u32(zone_gfx_info_ptr) + 0x085A2E80
        zone_gfx_load_offset = self.rom.read_u32(zone_gfx_info_ptr+4) - 0x06000000
          
        self.gfx_load_datas.append((zone_gfx_data_ptr, zone_gfx_load_offset))
