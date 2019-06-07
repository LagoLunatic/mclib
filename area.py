
import traceback
from collections import OrderedDict

from mclib.room import Room
from mclib.assets import AssetList
from mclib.palette_group import PaletteGroup

class Area:
  def __init__(self, area_index, rom):
    self.area_index = area_index
    self.rom = rom
    
    self.read()
  
  def read(self):
    area_metadata_pointer = 0x08127D30 + self.area_index*4
    bitfield = self.rom.read_u8(area_metadata_pointer + 0)
    self.area_id = self.rom.read_u8(area_metadata_pointer + 1)
    self.local_flag_offset_index = self.rom.read_u8(area_metadata_pointer + 2)
    self.is_dungeon = (bitfield & 0x08) == 0x08
    self.is_overworld = bitfield == 0x81
    if self.is_dungeon:
      self.dungeon_index = self.area_id - 0x17
    
    if self.area_index in [0x20, 0x2D]:
      self.uses_256_color_bg1s = True
    else:
      self.uses_256_color_bg1s = False
    
    self.room_gfx_metadatas_list = self.rom.read_u32(0x0811E214 + self.area_index*4)
    self.room_property_lists_pointer = self.rom.read_u32(0x080D50FC + self.area_index*4)
    self.room_exit_lists_pointer = self.rom.read_u32(0x0813A7F0 + self.area_index*4)
    
    self.gfx_and_palettes_list_pointer = self.rom.read_u32(0x0810246C + self.area_index*4)
    self.tilesets_pointer = self.rom.read_u32(0x0810309C + self.area_index*4)
    self.room_layers_lists_pointer = self.rom.read_u32(0x08107988 + self.area_index*4)
    
    self._tilesets_asset_list = None # Lazy load
    
    self.rooms = []
    if self.room_gfx_metadatas_list == 0 and self.room_property_lists_pointer == 0:
      # Invalid area
      return
    
    room_index = 0
    while True:
      room_gfx_metadata_ptr = self.room_gfx_metadatas_list + room_index*0xA
      
      possible_end_marker = self.rom.read_u16(room_gfx_metadata_ptr+0)
      if possible_end_marker == 0xFFFF:
        break
      possible_skip_marker = self.rom.read_u16(room_gfx_metadata_ptr+8)
      if possible_skip_marker == 0xFFFF:
        self.rooms.append(None)
        room_index += 1
        continue
      
      try:
        room = Room(room_index, self, self.rom)
      except Exception as e:
        # TODO: handle these errors properly
        stack_trace = traceback.format_exc()
        error_message = ("Error reading room %02X-%02X:\n" % (self.area_index, room_index)) + str(e) + "\n\n" + stack_trace
        print(error_message)
        room = None
      
      self.rooms.append(room)
      room_index += 1
    
    self.cached_gfx_asset_lists = OrderedDict()
    self.cached_palette_groups = OrderedDict()
  
  @property
  def tilesets_asset_list(self):
    if not self._tilesets_asset_list:
      self._tilesets_asset_list = AssetList(self.tilesets_pointer, self.rom)
    return self._tilesets_asset_list
  
  def get_gfx_asset_list(self, gfx_index):
    if gfx_index in self.cached_gfx_asset_lists:
      return self.cached_gfx_asset_lists[gfx_index]
    else:
      gfx_and_palettes_pointer = self.rom.read_u32(self.gfx_and_palettes_list_pointer + gfx_index*4)
      gfx_asset_list = AssetList(gfx_and_palettes_pointer, self.rom)
      
      self.cached_gfx_asset_lists[gfx_index] = gfx_asset_list
      return gfx_asset_list
  
  def get_palette_group(self, gfx_index):
    if gfx_index in self.cached_palette_groups:
      return self.cached_palette_groups[gfx_index]
    else:
      gfx_asset_list = self.get_gfx_asset_list(gfx_index)
      palette_group = PaletteGroup(gfx_asset_list.palette_group_index, self.rom)
      
      self.cached_palette_groups[gfx_index] = palette_group
      return palette_group
