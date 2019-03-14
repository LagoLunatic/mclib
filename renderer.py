
from PIL import Image
import traceback
import os

from mclib.palette_group import PaletteGroup
from mclib.sprite import Sprite
from mclib.sprite_loading import SpriteLoadingData

class Renderer:
  def __init__(self, game):
    self.game = game
    self.rom = self.game.rom
  
  def render_tileset(self, area, gfx_index, palettes, layer_index):
    rom = self.rom
    
    gfx_asset_list = area.get_gfx_asset_list(gfx_index)
    gfx_data = gfx_asset_list.gfx_data
    #palette_metadata_index = gfx_asset_list.palette_metadata_index
    tile_mappings_8x8 = area.tilesets_asset_list.tile_mappings
    
    # TODO: figure out what these are
    if [x for x in gfx_asset_list.tile_mappings if x is not None]:
      print("gfx_asset_list.tile_mappings: ", gfx_asset_list.tile_mappings)
    if len(area.tilesets_asset_list.gfx_data) != 0:
      print("area.tilesets_asset_list.gfx_data: ", area.tilesets_asset_list.gfx_data)
    if area.tilesets_asset_list.palette_metadata_index is not None:
      print("area.tilesets_asset_list.palette_metadata_index: ", area.tilesets_asset_list.palette_metadata_index)
    
    if layer_index >= 1:
      gfx_data = gfx_data.read_raw(0x4000, len(gfx_data)-0x4000)
    
    tile_mapping_8x8_data = tile_mappings_8x8[layer_index]
    
    tileset_height = (len(tile_mapping_8x8_data)+7)//8
    tileset_image = Image.new("RGBA", (16*16, tileset_height), (255, 255, 255, 0))
    
    cached_tile_images_by_tile_attrs = {}
    for tile_index_16x16 in range(len(tile_mapping_8x8_data)//8):
      tile_x = tile_index_16x16 % 16
      tile_y = tile_index_16x16 // 16
      
      for tile_8x8_i in range(4):
        tile_attrs = tile_mapping_8x8_data.read_u16(tile_index_16x16*8 + tile_8x8_i*2)
        
        if tile_attrs in cached_tile_images_by_tile_attrs:
          tile_image = cached_tile_images_by_tile_attrs[tile_attrs]
        else:
          tile_image = self.render_tile_by_tile_attrs(tile_attrs, gfx_data, palettes)
          cached_tile_images_by_tile_attrs[tile_attrs] = tile_image
        
        x_on_16x16_tile = tile_8x8_i % 2
        y_on_16x16_tile = tile_8x8_i // 2
        x = tile_x*16 + x_on_16x16_tile*8
        y = tile_y*16 + y_on_16x16_tile*8
        
        tileset_image.paste(tile_image, (x, y))
    
    #tileset_image.save("../tileset_renders/area%02X-layer%02X-gfxindex%02X-tileset.png" % (area.area_index, layer_index, gfx_index))
    return tileset_image
  
  def render_room(self, room, palettes):
    area = room.area
    
    room_image = Image.new("RGBA", (room.width, room.height), (255, 255, 255, 0))
    
    for layer_index in range(len(room.layers_asset_list.tile_mappings)):
      layer_image = self.render_layer(room, palettes, layer_index)
      
      room_image.alpha_composite(layer_image)
    
    room_image.save("../room_renders/area%02X-room%02X.png" % (area.area_index, room.room_index))
    
    return room_image
  
  def render_layer(self, room, palettes, layer_index):
    if room.area.area_index in [0x20, 0x2D]:
      if layer_index == 1:
        # Areas 20 and 2D use 256 color on BG2.
        return self.render_layer_256_color(room, palettes, layer_index)
      else:
        # Their BG1s may be unused? They seem to error out when trying to render them. TODO figure them out
        return Image.new("RGBA", (room.width, room.height), (255, 255, 255, 0))
    else:
      return self.render_layer_16_color(room, palettes, layer_index)
  
  def render_layer_16_color(self, room, palettes, layer_index):
    rom = self.rom
    area = room.area
    
    # TODO: figure out what these are
    if len(room.layers_asset_list.gfx_data) != 0:
      print("room.layers_asset_list.gfx_data: ", room.layers_asset_list.gfx_data)
    if room.layers_asset_list.palette_metadata_index is not None:
      print("room.layers_asset_list.palette_metadata_index: ", room.layers_asset_list.palette_metadata_index)
    
    tileset_image = self.render_tileset(area, room.gfx_index, palettes, layer_index)
    
    layer_image = Image.new("RGBA", (room.width, room.height), (255, 255, 255, 0))
    
    tile_mapping_16x16_data = room.layers_asset_list.tile_mappings[layer_index]
    if tile_mapping_16x16_data is None:
      raise Exception("Layer BG%d has no 16x16 tile mapping" % (layer_index+1))
    
    room_width_in_16x16_tiles = room.width//16
    
    cached_tile_images_by_16x16_index = {}
    for i in range(len(tile_mapping_16x16_data)//2):
      tile_map_16x16_offset = i*2
      tile_index_16x16 = tile_mapping_16x16_data.read_u16(tile_map_16x16_offset)
      
      if tile_index_16x16 in cached_tile_images_by_16x16_index:
        tile_image = cached_tile_images_by_16x16_index[tile_index_16x16]
      else:
        x_on_tileset = tile_index_16x16 % 16
        y_on_tileset = tile_index_16x16 // 16
        tile_image = tileset_image.crop((x_on_tileset*16, y_on_tileset*16, x_on_tileset*16+16, y_on_tileset*16+16))
        cached_tile_images_by_16x16_index[tile_index_16x16] = tile_image
      
      x_in_room = i % room_width_in_16x16_tiles
      y_in_room = i // room_width_in_16x16_tiles
      layer_image.paste(tile_image, (x_in_room*16, y_in_room*16))
    
    return layer_image
  
  def render_layer_256_color(self, room, palettes, layer_index):
    rom = self.rom
    area = room.area
    
    layer_image = Image.new("RGBA", (room.width, room.height), (255, 255, 255, 0))
    
    gfx_asset_list = area.get_gfx_asset_list(room.gfx_index)
    gfx_data = gfx_asset_list.gfx_data
    palette_metadata_index = gfx_asset_list.palette_metadata_index
    
    if [x for x in gfx_asset_list.tile_mappings if x is not None]:
      print("1: ", gfx_asset_list.tile_mappings)
    if len(area.tilesets_asset_list.gfx_data) != 0:
      print("2: ", area.tilesets_asset_list.gfx_data)
    if area.tilesets_asset_list.palette_metadata_index is not None:
      print("3: ", area.tilesets_asset_list.palette_metadata_index)
    if len(room.layers_asset_list.gfx_data) != 0:
      print("4: ", room.layers_asset_list.gfx_data)
    if room.layers_asset_list.palette_metadata_index is not None:
      print("5: ", room.layers_asset_list.palette_metadata_index)
    
    tile_mapping_8x8_data = room.layers_asset_list.tile_mappings[layer_index]
    if tile_mapping_8x8_data is None:
      raise Exception("Layer BG%d has no 8x8 tile mapping" % (layer_index+1))
    
    layer_image_in_chunks = self.render_gfx_mapped(gfx_data, tile_mapping_8x8_data, palettes, color_mode=256)
    
    # Reassemble the layer out of the 256x256 chunks.
    dst_y = 0
    src_y = 0
    while dst_y < room.height:
      dst_x = 0
      while dst_x < room.width:
        layer_chunk = layer_image_in_chunks.crop((0, src_y, 256, src_y+256))
        layer_image.paste(layer_chunk, (dst_x, dst_y))
        dst_x += 256
        src_y += 256
      dst_y += 256
    
    return layer_image
  
  def render_gfx_mapped(self, gfx_data, tile_mapping_8x8_data, palettes, color_mode=16):
    #with open("gfx.bin", "wb") as f:
    #  f.write(gfx_data)
    #with open("map.bin", "wb") as f:
    #  f.write(tile_mapping_8x8_data)
    #self.export_palettes(palettes)
    
    image_width_in_8x8_tiles = 32
    
    image_height = (len(tile_mapping_8x8_data)+7)//8
    image = Image.new("RGBA", (image_width_in_8x8_tiles*8, image_height), (255, 255, 255, 0))
    
    for tile_i in range(len(tile_mapping_8x8_data)//2):
      tile_attrs = tile_mapping_8x8_data.read_u16(tile_i*2)
      
      tile_image = self.render_tile_by_tile_attrs(tile_attrs, gfx_data, palettes, color_mode=color_mode)
      
      tile_x = tile_i % image_width_in_8x8_tiles
      tile_y = tile_i // image_width_in_8x8_tiles
      x = tile_x*8
      y = tile_y*8
      
      image.paste(tile_image, (x, y))
    
    return image
  
  def render_tile_by_tile_attrs(self, tile_attrs, gfx_data, palettes, color_mode=16):
    palette_index   = (tile_attrs & 0xF000) >> 0xC
    horizontal_flip = (tile_attrs & 0x0400) > 0
    vertical_flip   = (tile_attrs & 0x0800) > 0
    tile_number     = (tile_attrs & 0x03FF)
    
    if color_mode == 16:
      palette = palettes[palette_index]
      
      tile_image = self.render_tile(gfx_data, tile_number, palette)
    else:
      full_palette = []
      for i in range(0x10):
        full_palette += palettes[i]
      
      tile_image = self.render_tile_256_colors(gfx_data, tile_number, full_palette)
    
    if horizontal_flip:
      tile_image = tile_image.transpose(Image.FLIP_LEFT_RIGHT)
    if vertical_flip:
      tile_image = tile_image.transpose(Image.FLIP_TOP_BOTTOM)
    
    return tile_image
  
  def render_gfx_raw(self, gfx_data, palette, color_mode=16):
    if color_mode == 16:
      bytes_per_8x8_tile = 0x20
    else:
      bytes_per_8x8_tile = 0x40
    
    max_image_width_in_8x8_tiles = 32
    num_bytes_per_row = (bytes_per_8x8_tile*max_image_width_in_8x8_tiles)
    image_height_in_8x8_tiles = (len(gfx_data)+num_bytes_per_row-1)//num_bytes_per_row
    image_width_in_8x8_tiles = min(len(gfx_data), num_bytes_per_row)//bytes_per_8x8_tile
    image = Image.new("RGBA", (image_width_in_8x8_tiles*8, image_height_in_8x8_tiles*8), (255, 255, 255, 0))
    
    for tile_i in range(len(gfx_data)//bytes_per_8x8_tile):
      if color_mode == 16:
        tile_image = self.render_tile(gfx_data, tile_i, palette)
      else:
        tile_image = self.render_tile_256_colors(gfx_data, tile_i, palette)
      
      tile_x = tile_i % max_image_width_in_8x8_tiles
      tile_y = tile_i // max_image_width_in_8x8_tiles
      x = tile_x*8
      y = tile_y*8
      
      image.paste(tile_image, (x, y))
    
    return image
  
  def render_tile(self, gfx_data, tile_index, palette):
    tile_image = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    pixels = tile_image.load()
    
    tile_gfx_offset = tile_index*0x20
    x_in_tile = 0
    y_in_tile = 0
    while True:
      byte = gfx_data.read_u8(tile_gfx_offset)
      
      if byte != 0:
        low_nibble = byte & 0xF
        if low_nibble != 0:
          pixels[x_in_tile,y_in_tile] = palette[low_nibble]
        
        high_nibble = byte >> 4
        if high_nibble != 0:
          pixels[x_in_tile+1,y_in_tile] = palette[high_nibble]
      
      x_in_tile += 2
      if x_in_tile == 8:
        x_in_tile = 0
        y_in_tile += 1
        if y_in_tile == 8:
          break
      
      tile_gfx_offset += 1
    
    return tile_image
  
  def render_tile_256_colors(self, gfx_data, tile_index, palette):
    tile_image = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    pixels = tile_image.load()
    
    tile_gfx_offset = tile_index*0x40
    x_in_tile = 0
    y_in_tile = 0
    while True:
      byte = gfx_data.read_u8(tile_gfx_offset)
      
      pixels[x_in_tile,y_in_tile] = palette[byte]
      
      x_in_tile += 1
      if x_in_tile == 8:
        x_in_tile = 0
        y_in_tile += 1
        if y_in_tile == 8:
          break
      
      tile_gfx_offset += 1
    
    return tile_image
  
  def render_all_sprites(self):
    for i in range(0x149):
      try:
        if not os.path.exists("../sprite_renders/%03d_0x%03X" % (i, i)):
          os.makedirs("../sprite_renders/%03d_0x%03X" % (i, i))
        
        sprite = Sprite(i, self.rom)
        
        self.render_all_sprite_frames(sprite)
      except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = "Error loading map:\n" + str(e) + "\n\n" + stack_trace
        print(error_message)
        return
  
  def render_all_sprite_frames(self, sprite):
    palettes = self.generate_palettes_from_palette_group_by_index(0xB)
    palettes[0x16] = self.generate_palettes(0x085A3040, 1)[0] # Link palette
    for frame_index, frame in enumerate(sprite.frames):
      frame_image = self.render_sprite_frame_swap_type_gfx(sprite, frame, palettes)
      frame_image.save("../sprite_renders/%03d_0x%03X/frame%03d_0x%02X.png" % (sprite.sprite_index, sprite.sprite_index, frame_index, frame_index))
  
  def render_entity_sprite_frame(self, entity, frame_index):
    # TODO: if image is entirely blank, don't just return a blank image!
    
    loading_data = SpriteLoadingData(entity.type, entity.subtype, entity.form, self.rom)
    
    #print(
    #  "Entity %02X-%02X (form %02X): pal %02X, sprite %03X" % (
    #    entity.type, entity.subtype, entity.form, loading_data.object_palette_id, loading_data.sprite_index
    #  )
    #)
    
    palettes = self.generate_object_palettes(loading_data.object_palette_id)
    
    sprite = Sprite(loading_data.sprite_index, self.rom)
    #print("%08X" % sprite.frame_list_ptr)
    
    #if not sprite.frames:
    #  # TODO: why do some have no frames?
    #  # example is entity type 06 subtype 2C in room 03-00
    #  return Image.new("RGBA", (16, 16), (255, 0, 0, 255))
    
    if entity.type in [6, 7]:
      return self.render_sprite_frame_swap_type_gfx(sprite, frame_index, palettes)
    else:
      return self.render_sprite_frame_fixed_type_gfx(sprite, frame_index, loading_data, palettes)
  
  def render_sprite_frame_swap_type_gfx(self, sprite, frame_index, palettes):
    frame_gfx_data = sprite.frame_gfx_datas[frame_index]
    gfx_data_ptr = sprite.gfx_pointer + frame_gfx_data.first_gfx_tile_index*0x20
    gfx_data_len = frame_gfx_data.num_gfx_tiles*0x20
    if gfx_data_len == 0:
      raise Exception("GFX data length is 0")
    gfx_data = self.rom.read_raw(gfx_data_ptr, gfx_data_len)
    
    frame_obj_list = sprite.frame_obj_lists[frame_index]
    
    return self.render_sprite_frame(frame_obj_list, gfx_data, palettes)
  
  def render_sprite_frame_fixed_type_gfx(self, sprite, frame_index, loading_data, palettes):
    bitfield = self.rom.read_u32(0x08132B30 + loading_data.unknown_1*4)
    gfx_data_ptr = 0x085A2E80 + (bitfield & 0x00FFFFFC)
    gfx_data_len = ((bitfield & 0x7F000000)>>24) * 0x200
    if gfx_data_len == 0:
      raise Exception("GFX data length is 0")
    gfx_data = self.rom.read_raw(gfx_data_ptr, gfx_data_len)
    
    frame_obj_list = sprite.frame_obj_lists[frame_index]
    
    return self.render_sprite_frame(frame_obj_list, gfx_data, palettes)
  
  def render_sprite_frame(self, frame_obj_list, gfx_data, palettes):
    if not frame_obj_list.objs:
      raise Exception("Frame has no objs")
    
    min_x = 9999
    min_y = 9999
    max_x = -9999
    max_y = -9999
    for obj in frame_obj_list.objs:
      if obj.x_off < min_x:
        min_x = obj.x_off
      if obj.y_off < min_y:
        min_y = obj.y_off
      if obj.x_off + obj.width > max_x:
        max_x = obj.x_off + obj.width
      if obj.y_off + obj.height > max_y:
        max_y = obj.y_off + obj.height
    
    image_width = max_x - min_x
    image_height = max_y - min_y
    frame_image = Image.new("RGBA", (image_width, image_height), (255, 255, 255, 0))
    
    tiles_image_for_palette = {}
    
    src_y = 0
    for obj in frame_obj_list.objs:
      if obj.palette_index in tiles_image_for_palette:
        tiles_image = tiles_image_for_palette[obj.palette_index]
      else:
        tiles_image = self.render_gfx_raw(gfx_data, palettes[obj.palette_index+0x10])
      
      rows_needed_for_obj = obj.height//8
      
      src_x = obj.first_gfx_tile_offset*8
      dst_x = obj.x_off - min_x
      dst_y = obj.y_off - min_y
      for _ in range(rows_needed_for_obj):
        obj_row_image = tiles_image.crop((src_x, src_y, src_x+obj.width, src_y+8))
        src_x += obj.width
        
        if obj.h_flip:
          obj_row_image = obj_row_image.transpose(Image.FLIP_LEFT_RIGHT)
        if obj.v_flip:
          obj_row_image = obj_row_image.transpose(Image.FLIP_TOP_BOTTOM)
        
        frame_image.paste(obj_row_image, (dst_x, dst_y), obj_row_image)
        dst_y += 8
    
    return frame_image
  
  def generate_palettes_for_area_by_gfx_index(self, area, gfx_index):
    common_palettes = self.generate_palettes(0x085A2E80, 5)
    
    palette_group = area.get_palette_group(gfx_index)
    final_palettes = []
    
    # First fill all the palettes with bright red.
    # This is so that any palettes not loaded in will be obviously wrong visually making it easier to notice problems.
    dummy_palette = [(255, 0, 0, 255)]*16
    for i in range(0x20):
      final_palettes.append(dummy_palette)
    
    # Load in the common palettes shared by all areas.
    final_palettes[0:len(common_palettes)] = common_palettes
    
    for palette_set in palette_group.palette_sets:
      if palette_set.palette_load_offset < 0 or palette_set.palette_load_offset >= 0x20:
        raise Exception("Palette set has an invalid palette load offset: %02X" % palette_set.palette_load_offset)
      if palette_set.palette_load_offset + palette_set.num_palettes > 0x20 or palette_set.num_palettes == 0:
        raise Exception("Palette set tried to load an invalid number of palettes: %02X" % palette_set.num_palettes)
      
      palettes = self.generate_palettes(palette_set.first_palette_pointer, palette_set.num_palettes)
      
      final_palettes[palette_set.palette_load_offset:palette_set.palette_load_offset+palette_set.num_palettes] = palettes
    
    return final_palettes
  
  def generate_palettes_from_palette_group_by_index(self, palette_group_index):
    palette_group = PaletteGroup(palette_group_index, self.rom)
    
    final_palettes = []
    
    # First fill all the palettes with bright red.
    # This is so that any palettes not loaded in will be obviously wrong visually making it easier to notice problems.
    dummy_palette = [(255, 0, 0, 255)]*16
    for i in range(0x20):
      final_palettes.append(dummy_palette)
    
    for palette_set in palette_group.palette_sets:
      if palette_set.palette_load_offset < 0 or palette_set.palette_load_offset >= 0x20:
        raise Exception("Palette set has an invalid palette load offset: %02X" % palette_set.palette_load_offset)
      if palette_set.palette_load_offset + palette_set.num_palettes > 0x20 or palette_set.num_palettes == 0:
        raise Exception("Palette set tried to load an invalid number of palettes: %02X" % palette_set.num_palettes)
      
      palettes = self.generate_palettes(palette_set.first_palette_pointer, palette_set.num_palettes)
      
      final_palettes[palette_set.palette_load_offset:palette_set.palette_load_offset+palette_set.num_palettes] = palettes
    
    return final_palettes
  
  def generate_object_palettes(self, object_palette_id):
    if object_palette_id >= 0 and object_palette_id <= 5:
      return self.generate_palettes_from_palette_group_by_index(0xB)
    
    assert object_palette_id >= 0x16
    object_palette_index = object_palette_id - 0x16
    bitfield = self.rom.read_u32(0x08133368 + object_palette_index*4)
    palette_ptr = 0x085A2E80 + (bitfield & 0x00FFFFFF)
    num_palettes = (bitfield & 0xFF000000) >> 24
    
    final_palettes = []
    
    for i in range(0x10):
      # Fill up with dummy background palettes.
      final_palettes.append(None)
    
    final_palettes += self.generate_palettes(palette_ptr, num_palettes)
    
    dummy_palette = [(255, 0, 0, 255)]*16
    for i in range(0x10-num_palettes):
      final_palettes.append(dummy_palette)
    
    return final_palettes
  
  def generate_palettes(self, palette_pointer, num_palettes):
    palettes = []
    
    palette_index = 0
    while palette_index < num_palettes:
      palette = []
      color_index = 0
      while color_index < 16:
        pointer = palette_pointer + color_index*2
        color_data = self.rom.read_u16(pointer)
        blue_bits  = (color_data & 0b0111_1100_0000_0000) >> 10
        green_bits = (color_data & 0b0000_0011_1110_0000) >> 5
        red_bits   =  color_data & 0b0000_0000_0001_1111
        red = red_bits << 3
        green = green_bits << 3
        blue = blue_bits << 3
        
        color = (red, green, blue, 0xFF)
        palette.append(color)
        color_index += 1
      
      palettes.append(palette)
      palette_index += 1
      palette_pointer += 0x20
    
    return palettes
  
  def export_palettes(self, palettes):
    palettes_image = Image.new("RGBA", (0x10*8, 0x20*8), (255, 255, 255, 0))
    
    for palette_index in range(0x20):
      palette = palettes[palette_index]
      
      for color_index in range(0x10):
        color = palette[color_index]
        
        x = color_index*8
        y = palette_index*8
        palettes_image.paste(color, (x, y, x+8, y+8))
    
    palettes_image.save("palette.png")
  
  def render_world_map(self):
    gfx_data = self.rom.read_raw(0x08934FE0, 0x4000)
    tile_mapping_8x8_data = self.rom.read_raw(0x08938FE0, 0x500)
    palettes = self.generate_palettes_from_palette_group_by_index(0xB9)
    
    map_image = self.render_gfx_mapped(gfx_data, tile_mapping_8x8_data, palettes)
    map_image = map_image.crop((40, 8, 200, 136))
    
    return map_image
  
  def render_dungeon_map(self, dungeon):
    image_width  = 128
    image_height = 128*len(dungeon.floors)
    dungeon_image = Image.new("RGBA", (image_width, image_height), (255, 255, 255, 0))
    
    palettes = self.generate_palettes_from_palette_group_by_index(0xB8)
    palette = palettes[0xC]
    
    for floor in dungeon.floors:
      for dungeon_room in floor:
        if dungeon_room.area_index >= len(self.game.areas):
          print("Invalid room on dungeon map: %02X-%02X" % (dungeon_room.area_index, dungeon_room.room_index))
          continue
        area = self.game.areas[dungeon_room.area_index]
        if dungeon_room.room_index >= len(area.rooms):
          print("Invalid room on dungeon map: %02X-%02X" % (dungeon_room.area_index, dungeon_room.room_index))
          continue
        room = area.rooms[dungeon_room.room_index]
        
        if room is None:
          print("Tried to render an invalid room onto the dungeon map, area %02X room %02X" % (dungeon_room.area_index, dungeon_room.room_index))
          continue
        
        room_image = self.render_dungeon_map_room(dungeon_room.room_map_data_ptr, room, palette)
        
        room_x = room.x_pos//16
        room_y = room.y_pos//16
        dungeon_image.paste(room_image, (room_x, room_y), mask=room_image)
    
    return dungeon_image
  
  def render_dungeon_map_room(self, room_map_data_pointer, room, palette):
    # Each pixel on the map is equivalent to one 16x16 tile in the room.
    # Also, the width needs to be rounded up to the nearest 4 16x16 tiles because of the format of the map data.
    image_width = room.width//16
    bytes_per_row = (image_width+3)//4
    image_width = bytes_per_row*4
    image_height = room.height//16
    
    room_image = Image.new("RGBA", (image_width, image_height), (255, 255, 255, 0))
    pixels = room_image.load()
    
    for y in range(image_height):
      for x in range(0, image_width, 4):
        offset = y*bytes_per_row + x//4
        byte = self.rom.read_u8(room_map_data_pointer + offset)
        
        for i in range(4):
          color_type = (byte >> (6 - i*2)) & 0x03
          if color_type == 2:
            color_type = 3
          elif color_type == 3:
            color_type = 7
          
          if color_type != 0:
            color = palette[color_type]
            pixels[x,y] = color
          
          x += 1
    
    return room_image
  
  def render_dummy_map(self, area):
    width = 128
    height = 128
    
    for room in area.rooms:
      if room is None:
        continue
      room_x = room.x_pos // 0x10
      room_y = room.y_pos // 0x10
      room_w = room.width // 0x10
      room_h = room.height // 0x10
      if room_x + room_w > width:
        width = room_x + room_w
      if room_y + room_h > height:
        height = room_y + room_h
    
    map_image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    
    for room in area.rooms:
      if room is None:
        continue
      room_x = room.x_pos // 0x10
      room_y = room.y_pos // 0x10
      room_w = room.width // 0x10
      room_h = room.height // 0x10
      
      map_image.paste((210, 120, 210, 255), (room_x, room_y, room_x+room_w, room_y+room_h))
    
    return map_image
