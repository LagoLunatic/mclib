
from PIL import Image
import traceback
import os

from mclib.palette_group import PaletteGroup
from mclib.sprite import Sprite
from mclib.sprite_loading import SpriteLoadingData
from mclib.docs import Docs

class Renderer:
  MAX_8x8_TILES_PER_ROW = 32
  DUMMY_PALETTE = [(255, 0, 0, 255)]*16
  
  def __init__(self, game):
    self.game = game
    self.rom = self.game.rom
    
    self.common_palettes = self.generate_palettes_from_palette_group_by_index(0xB)
    
    self.curr_room_bg_palettes = None
    self.curr_room_tileset_images = [None]*4
  
  def update_curr_room_palettes_and_tilesets(self, room):
    if room is None:
      self.curr_room_bg_palettes = None
      self.curr_room_tileset_images = [None]*4
      return
    
    area = room.area
    
    if room.layers_asset_list is None:
      gfx_index = 0
    else:
      gfx_index = room.gfx_index
    self.curr_room_bg_palettes = self.generate_palettes_for_area_by_gfx_index(area, gfx_index)
    
    self.curr_room_tileset_images = [None]*4
    if area.uses_256_color_bg1s:
      return
    for layer_index in range(1, 3+1):
      try:
        tileset_image = self.render_tileset(area, room.gfx_index, self.curr_room_bg_palettes, layer_index)
        self.curr_room_tileset_images[layer_index] = tileset_image
      except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = "Error rendering tileset:\n" + str(e) + "\n\n" + stack_trace
        print(error_message)
  
  def render_tileset(self, area, gfx_index, palettes, layer_index):
    rom = self.rom
    
    gfx_asset_list = area.get_gfx_asset_list(gfx_index)
    gfx_data = gfx_asset_list.gfx_data
    tileset_datas = area.tilesets_asset_list.tileset_datas
    
    tileset_image = self.render_tileset_by_assets(gfx_data, palettes, tileset_datas, layer_index)
    
    #if tileset_image is not None:
    #  tileset_image.save("../tileset_renders/area%02X-layer%02X-gfxindex%02X-tileset.png" % (area.area_index, layer_index, gfx_index))
    
    return tileset_image
  
  def render_tileset_by_assets(self, gfx_data, palettes, tileset_datas, layer_index):
    if layer_index in [1, 3]:
      gfx_data = gfx_data.read_raw(0x4000, len(gfx_data)-0x4000)
    
    tileset_data = tileset_datas[layer_index]
    
    if tileset_data is None:
      return None
    
    tileset_height = (len(tileset_data)+3)//4
    tileset_image = Image.new("RGBA", (16*16, tileset_height), (255, 255, 255, 0))
    
    cached_tile_images_by_tile_attrs = {}
    for tile_index_16x16 in range(len(tileset_data)//4):
      tile_x = tile_index_16x16 % 16
      tile_y = tile_index_16x16 // 16
      
      for tile_8x8_i in range(4):
        tile_attrs = tileset_data[tile_index_16x16*4 + tile_8x8_i]
        
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
    
    return tileset_image
  
  def render_room(self, room, palettes):
    area = room.area
    
    room_image = Image.new("RGBA", (room.width, room.height), (255, 255, 255, 0))
    
    for layer_index in range(1, 3+1):
      layer_image = self.render_layer(room, palettes, layer_index)
      
      room_image.alpha_composite(layer_image)
    
    room_image.save("../room_renders/area%02X-room%02X.png" % (area.area_index, room.room_index))
    
    return room_image
  
  def render_layer(self, room, tileset_image, palettes, layer_index):
    if room.area.uses_256_color_bg1s:
      if layer_index == 2:
        return self.render_layer_mapped(room, palettes, layer_index, color_mode=256)
      else:
        # Their BG1s may be unused? They seem to error out when trying to render them. TODO figure them out
        return Image.new("RGBA", (room.width, room.height), (255, 255, 255, 0))
    else:
      return self.render_layer_16_color(room, tileset_image, layer_index)
  
  def render_layer_16_color(self, room, tileset_image, layer_index):
    rom = self.rom
    area = room.area
    
    layer_image = Image.new("RGBA", (room.width, room.height), (255, 255, 255, 0))
    
    if room.layers_asset_list is None:
      return layer_image
    
    # TODO: figure out what these are
    if len(room.layers_asset_list.gfx_data) != 0:
      print("room.layers_asset_list.gfx_data: ", room.layers_asset_list.gfx_data)
    if room.layers_asset_list.palette_metadata_index is not None:
      print("room.layers_asset_list.palette_metadata_index: ", room.layers_asset_list.palette_metadata_index)
    
    layer_data = room.layers_asset_list.layer_datas[layer_index]
    if layer_data is None:
      raise Exception("Layer BG%d has no layer data" % layer_index)
    
    room_width_in_16x16_tiles = room.width//16
    
    cached_tile_images_by_16x16_index = {}
    for i in range(len(layer_data)):
      tile_index_16x16 = layer_data[i]
      
      if tile_index_16x16 in cached_tile_images_by_16x16_index:
        tile_image = cached_tile_images_by_16x16_index[tile_index_16x16]
      else:
        tile_image = self.get_16x16_tile_by_index(tileset_image, tile_index_16x16)
        cached_tile_images_by_16x16_index[tile_index_16x16] = tile_image
      
      x_in_room = i % room_width_in_16x16_tiles
      y_in_room = i // room_width_in_16x16_tiles
      layer_image.paste(tile_image, (x_in_room*16, y_in_room*16))
    
    return layer_image
  
  def render_layer_mapped(self, room, palettes, layer_index, color_mode=256):
    rom = self.rom
    area = room.area
    
    layer_image = Image.new("RGBA", (room.width, room.height), (255, 255, 255, 0))
    
    gfx_asset_list = area.get_gfx_asset_list(room.gfx_index)
    gfx_data = gfx_asset_list.gfx_data
    palette_metadata_index = gfx_asset_list.palette_metadata_index
    
    if layer_index in [1, 3]:
      gfx_data = gfx_data.read_raw(0x4000, len(gfx_data)-0x4000)
    
    if layer_index == 3:
      tile_mapping_8x8_data = area.get_gfx_asset_list(room.gfx_index).tile_mappings_8x8[layer_index]
    else:
      tile_mapping_8x8_data = room.layers_asset_list.tile_mappings_8x8[layer_index]
    if tile_mapping_8x8_data is None:
      raise Exception("Layer BG%d has no 8x8 tile mapping" % layer_index)
    
    layer_image_in_chunks = self.render_gfx_mapped(gfx_data, tile_mapping_8x8_data, palettes, color_mode=color_mode)
    
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
  
  def get_16x16_tile_by_index(self, tileset_image, tile_index_16x16):
    x_on_tileset = tile_index_16x16 % 16
    y_on_tileset = tile_index_16x16 // 16
    tile_image = tileset_image.crop((x_on_tileset*16, y_on_tileset*16, x_on_tileset*16+16, y_on_tileset*16+16))
    return tile_image
  
  def render_gfx_mapped(self, gfx_data, tile_mapping_8x8_data, palettes, color_mode=16):
    self.MAX_8x8_TILES_PER_ROW = 32
    
    image_height = (len(tile_mapping_8x8_data)+3)//4
    image = Image.new("RGBA", (self.MAX_8x8_TILES_PER_ROW*8, image_height), (255, 255, 255, 0))
    
    for tile_i in range(len(tile_mapping_8x8_data)):
      tile_attrs = tile_mapping_8x8_data[tile_i]
      
      tile_image = self.render_tile_by_tile_attrs(tile_attrs, gfx_data, palettes, color_mode=color_mode)
      
      tile_x = tile_i % self.MAX_8x8_TILES_PER_ROW
      tile_y = tile_i // self.MAX_8x8_TILES_PER_ROW
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
        palette = palettes[i]
        if palette is None:
          full_palette += self.DUMMY_PALETTE
        else:
          full_palette += palette
      
      tile_image = self.render_tile_256_colors(gfx_data, tile_number, full_palette)
    
    if horizontal_flip:
      tile_image = tile_image.transpose(Image.FLIP_LEFT_RIGHT)
    if vertical_flip:
      tile_image = tile_image.transpose(Image.FLIP_TOP_BOTTOM)
    
    return tile_image
  
  def render_gfx_raw(self, gfx_data, palette, color_mode=16, tiles_wide_8x8=MAX_8x8_TILES_PER_ROW):
    if color_mode == 16:
      bytes_per_8x8_tile = 0x20
    else:
      bytes_per_8x8_tile = 0x40
    
    num_bytes_per_row = (bytes_per_8x8_tile*tiles_wide_8x8)
    image_height_in_8x8_tiles = (len(gfx_data)+num_bytes_per_row-1)//num_bytes_per_row
    image_width_in_8x8_tiles = min(len(gfx_data), num_bytes_per_row)//bytes_per_8x8_tile
    image = Image.new("RGBA", (image_width_in_8x8_tiles*8, image_height_in_8x8_tiles*8), (255, 255, 255, 0))
    
    for tile_i in range(len(gfx_data)//bytes_per_8x8_tile):
      if color_mode == 16:
        tile_image = self.render_tile(gfx_data, tile_i, palette)
      else:
        tile_image = self.render_tile_256_colors(gfx_data, tile_i, palette)
      
      tile_x = tile_i % tiles_wide_8x8
      tile_y = tile_i // tiles_wide_8x8
      x = tile_x*8
      y = tile_y*8
      
      image.paste(tile_image, (x, y))
    
    return image
  
  def render_tile(self, gfx_data, tile_index, palette):
    tile_image = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    pixels = tile_image.load()
    
    if palette is None:
      palette = self.DUMMY_PALETTE
    
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
    
    if palette is None:
      palette = self.DUMMY_PALETTE
    
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
  
  def render_entity_pretty_sprite(self, entity):
    if entity.type == 6 and entity.subtype == 0xC and entity.form in [0, 1]:
      # Small chest spawner
      chest_tile_image = self.get_16x16_tile_by_index(self.curr_room_tileset_images[2], 0x10)
      return (chest_tile_image, -8, -8)
    
    loading_data = SpriteLoadingData(entity, self.rom)
    
    if loading_data.has_no_sprite:
      return (None, None, None)
    
    print(
      "Entity %02X-%02X (form %02X): pal %02X, sprite %03X" % (
        entity.type, entity.subtype, entity.form,
        loading_data.object_palette_id, loading_data.sprite_index
      ))
    
    palettes, entity_palette_index = self.generate_object_palettes(loading_data.object_palette_id)
    
    sprite = Sprite(loading_data.sprite_index, self.rom)
    
    best_anim_index = None
    keyframe = None
    if sprite.animation_list_ptr != 0:
      best_anim_index = Docs.get_best_sprite_animation(entity)
    
    frame_index = 0xFF
    if best_anim_index is not None:
      keyframe = sprite.get_animation(best_anim_index).keyframes[0]
      frame_index = keyframe.frame_index
      print("Has animations, using anim %02X, which has frame %02X for its first keyframe" % (best_anim_index, frame_index))
    
    if frame_index == 0xFF:
      frame_index = Docs.get_best_sprite_frame(entity)
      if frame_index is None:
        return (None, None, None)
    
    gfx_data = self.get_sprite_gfx_data_for_frame(loading_data, sprite, frame_index)
    if gfx_data is None:
      return (None, None, None)
    
    frame_obj_list = sprite.get_frame_obj_list(frame_index)
    
    frame_image, min_x, min_y = self.render_sprite_frame_by_assets(frame_obj_list, gfx_data, palettes, entity_palette_index)
    
    if keyframe:
      if keyframe.h_flip:
        frame_image = frame_image.transpose(Image.FLIP_LEFT_RIGHT)
      if keyframe.v_flip:
        frame_image = frame_image.transpose(Image.FLIP_TOP_BOTTOM)
    
    
    extra_frame_indexes = Docs.get_best_extra_sprite_frames_for_entity(entity)
    if extra_frame_indexes:
      body_sprite = sprite
      body_frame_index = frame_index
      body_frame_image = frame_image
      body_min_x = min_x
      body_min_y = min_y
      
      images_and_offsets = [
        (body_frame_image, body_min_x, body_min_y),
      ]
      for subentry_index, extra_frame_index in enumerate(extra_frame_indexes):
        extra_sprite = sprite
        if entity.subtype == 6:
          # Hyrule Townspeople have a different sprite for their head and body.
          # TODO: don't hardcode this
          extra_sprite = Sprite(0x3A, self.rom)
        
        extra_palettes = palettes
        extra_entity_palette_index = entity_palette_index
        if entity.subtype == 0x13:
          # Some sitting people have different palettes for their head??
          # TODO: don't hardcode this
          if entity.form in [1, 5]:
            extra_palettes, extra_entity_palette_index = self.generate_object_palettes(0x3E)
          elif entity.form in [2, 3, 4]:
            extra_palettes, extra_entity_palette_index = self.generate_object_palettes(0x40)
          # TODO: the main body sprite for sitting people can also be a different palette from the one specified in the main sprite loading data
        
        extra_x_off, extra_y_off = body_sprite.get_extra_frame_offsets_by_main_frame(body_frame_index, subentry_index)
        
        gfx_data = self.get_sprite_gfx_data_for_frame(loading_data, extra_sprite, extra_frame_index)
        
        extra_frame_obj_list = extra_sprite.get_frame_obj_list(extra_frame_index)
        extra_frame_image, extra_min_x, extra_min_y = self.render_sprite_frame_by_assets(
          extra_frame_obj_list, gfx_data, extra_palettes, extra_entity_palette_index
        )
        
        images_and_offsets.append(
          (extra_frame_image, extra_min_x + extra_x_off, extra_min_y + extra_y_off),
        )
      
      # TODO: the z-indexing order of the sprites can be different for each entity.
      # for example, guard with spear has his spear below his body. dina on the other hand has her pointing stick above her body.
      
      frame_image, min_x, min_y = self.combine_multiple_images_with_offsets(images_and_offsets)
    
    
    x_off, y_off = Docs.get_best_sprite_offset(entity)
    x_off += min_x
    y_off += min_y
    
    return (frame_image, x_off, y_off)
  
  def combine_multiple_images_with_offsets(self, images_and_offsets):
    final_image_min_x = 9999
    final_image_min_y = 9999
    final_image_max_x = -9999
    final_image_max_y = -9999
    for image, min_x, min_y in images_and_offsets:
      max_x = min_x + image.width
      max_y = min_y + image.height
      if min_x < final_image_min_x:
        final_image_min_x = min_x
      if min_y < final_image_min_y:
        final_image_min_y = min_y
      if max_x > final_image_max_x:
        final_image_max_x = max_x
      if max_y > final_image_max_y:
        final_image_max_y = max_y
    
    final_image_width = final_image_max_x - final_image_min_x
    final_image_height = final_image_max_y - final_image_min_y
    final_image = Image.new("RGBA", (final_image_width, final_image_height), (255, 255, 255, 0))
    
    for image, min_x, min_y in images_and_offsets:
      x_off = min_x - final_image_min_x
      y_off = min_y - final_image_min_y
      final_image.paste(image, (x_off, y_off), image)
    
    return final_image, final_image_min_x, final_image_min_y 
  
  def render_all_figurines(self):
    for i in range(1, 136+1):
      image = self.render_figurine(i)[0]
      if image is None:
        continue
      image.save("./logs/figurine renders/figurine %d.png" % i)
  
  def render_figurine(self, figurine_id):
    if figurine_id == 0:
      return (None, None, None)
    
    sprite_index = 0x1F8
    sprite = Sprite(sprite_index, self.rom)
    
    frame_index = figurine_id - 1
    
    frame_obj_list = sprite.get_frame_obj_list(frame_index)
    
    palette_data_ptr = self.rom.read_u32(0x081281A8 + figurine_id*0x10 + 0)
    gfx_data_ptr = self.rom.read_u32(0x081281A8 + figurine_id*0x10 + 4)
    gfx_data_len = self.rom.read_u32(0x081281A8 + figurine_id*0x10 + 8)
    
    final_palettes = self.common_palettes.copy()
    final_palettes = self.generate_palettes_from_palette_group_by_index(0xCE, existing_palettes=final_palettes)
    palettes = self.generate_palettes(palette_data_ptr, 9)
    final_palettes[0x16:0x16+9] = palettes
    
    if gfx_data_len == 0 or gfx_data_len >= 0x80000000:
      raise Exception("Compressed figurine GFX not yet implemented")
    else:
      gfx_data = self.rom.read_raw(gfx_data_ptr, gfx_data_len)
    
    entity_palette_index = 6
    
    return self.render_sprite_frame_by_assets(frame_obj_list, gfx_data, final_palettes, entity_palette_index)
  
  def get_sprite_gfx_data_for_frame(self, loading_data, sprite, frame_index):
    if loading_data.gfx_type == 0:
      return self.get_sprite_fixed_type_gfx_data(loading_data)
    elif loading_data.gfx_type == 1:
      return self.get_sprite_swap_type_gfx_data_for_frame(sprite, frame_index)
    elif loading_data.gfx_type == 2:
      return self.get_sprite_common_type_gfx_data(loading_data)
    else:
      raise Exception("Don't know how to render this sprite (GFX type %X)" % loading_data.gfx_type)
  
  def get_sprite_swap_type_gfx_data_for_frame(self, sprite, frame_index):
    frame_gfx_data = sprite.get_frame_gfx_data(frame_index)
    gfx_data_ptr = sprite.gfx_pointer + frame_gfx_data.first_gfx_tile_index*0x20
    gfx_data_len = frame_gfx_data.num_gfx_tiles*0x20
    if gfx_data_len == 0:
      raise Exception("GFX data length is 0")
    gfx_data = self.rom.read_raw(gfx_data_ptr, gfx_data_len)
    
    return gfx_data
  
  def get_sprite_fixed_type_gfx_data(self, loading_data):
    if loading_data.fixed_gfx_index == 0:
      return None
    
    bitfield = self.rom.read_u32(0x08132B30 + loading_data.fixed_gfx_index*4)
    gfx_data_ptr = 0x085A2E80 + (bitfield & 0x00FFFFFC)
    if bitfield & 0x00000001 == 1:
      raise Exception("Compressed entity GFX not yet implemented")
    else:
      gfx_data_len = ((bitfield & 0x7F000000)>>24) * 0x200
      if gfx_data_len == 0:
        raise Exception("GFX data length is 0")
      gfx_data = self.rom.read_raw(gfx_data_ptr, gfx_data_len)
    
    return gfx_data
  
  def get_sprite_common_type_gfx_data(self, loading_data):
    # TODO: implement this properly as a separate class.
    # asset with index 0x17 in list 0x08100AA8
    
    gfx_data_ptr = 0x085A2E80 + 0x01D7E0
    tile_offset = loading_data.common_gfx_tile_index*0x20
    gfx_data = self.rom.read_raw(gfx_data_ptr+tile_offset, 0x2000-tile_offset)
    return gfx_data
  
  def render_sprite_frame_by_assets(self, frame_obj_list, gfx_data, palettes, entity_palette_index):
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
    
    obj_i = len(frame_obj_list.objs)-1
    for obj in reversed(frame_obj_list.objs):
      if obj.override_entity_palette_index:
        palette_index = obj.palette_index + 0x10
      else:
        palette_index = obj.palette_index + 0x10 + entity_palette_index
      
      #print("%08X %02X %02X %02X" % (obj.obj_ptr, obj.palette_index, entity_palette_index, palette_index))
      
      num_gfx_tiles_needed = (obj.width//8) * (obj.height//8)
      gfx_data_for_obj = gfx_data.read_raw(obj.first_gfx_tile_offset*0x20, num_gfx_tiles_needed*0x20)
      obj_image = self.render_gfx_raw(gfx_data_for_obj, palettes[palette_index], tiles_wide_8x8=obj.width//8)
      
      if obj.h_flip:
        obj_image = obj_image.transpose(Image.FLIP_LEFT_RIGHT)
      if obj.v_flip:
        obj_image = obj_image.transpose(Image.FLIP_TOP_BOTTOM)
      
      #obj_image.save("./logs/%08X.png" % obj.obj_ptr)
      
      frame_image.paste(obj_image, (obj.x_off - min_x, obj.y_off - min_y), obj_image)
      
      obj_i -= 1
    
    return (frame_image, min_x, min_y)
  
  def generate_palettes_for_area_by_gfx_index(self, area, gfx_index):
    palette_group = area.get_palette_group(gfx_index)
    final_palettes = self.common_palettes.copy()
    
    # First fill all the palettes with None, which will be rendered as bright red.
    # This is so that any palettes not loaded in will be obviously wrong visually making it easier to notice problems.
    for i in range(0x20):
      final_palettes.append(None)
    
    for palette_set in palette_group.palette_sets:
      if palette_set.palette_load_offset < 0 or palette_set.palette_load_offset >= 0x20:
        raise Exception("Palette set has an invalid palette load offset: %02X" % palette_set.palette_load_offset)
      if palette_set.palette_load_offset + palette_set.num_palettes > 0x20 or palette_set.num_palettes == 0:
        raise Exception("Palette set tried to load an invalid number of palettes: %02X" % palette_set.num_palettes)
      
      palettes = self.generate_palettes(palette_set.first_palette_pointer, palette_set.num_palettes)
      
      final_palettes[palette_set.palette_load_offset:palette_set.palette_load_offset+palette_set.num_palettes] = palettes
    
    return final_palettes
  
  def generate_palettes_from_palette_group_by_index(self, palette_group_index, existing_palettes=None):
    palette_group = PaletteGroup(palette_group_index, self.rom)
    
    if existing_palettes is None:
      # First fill all the palettes with None, which will be rendered as bright red.
      # This is so that any palettes not loaded in will be obviously wrong visually making it easier to notice problems.
      final_palettes = []
      for i in range(0x20):
        final_palettes.append(None)
    else:
      final_palettes = existing_palettes.copy()
    
    for palette_set in palette_group.palette_sets:
      if palette_set.palette_load_offset < 0 or palette_set.palette_load_offset >= 0x20:
        raise Exception("Palette set has an invalid palette load offset: %02X" % palette_set.palette_load_offset)
      if palette_set.palette_load_offset + palette_set.num_palettes > 0x20 or palette_set.num_palettes == 0:
        raise Exception("Palette set tried to load an invalid number of palettes: %02X" % palette_set.num_palettes)
      
      palettes = self.generate_palettes(palette_set.first_palette_pointer, palette_set.num_palettes)
      
      final_palettes[palette_set.palette_load_offset:palette_set.palette_load_offset+palette_set.num_palettes] = palettes
    
    return final_palettes
  
  def generate_object_palettes(self, object_palette_id, existing_palettes=None):
    if existing_palettes is None:
      final_palettes = self.common_palettes.copy()
      final_palettes[0x15] = self.curr_room_bg_palettes[3]
    else:
      final_palettes = existing_palettes.copy()
    
    entity_palette_index = None
    for i in range(0x16, 0x20):
      if final_palettes[i] is None:
        entity_palette_index = i - 0x10
        break
    if entity_palette_index is None:
      raise Exception("Failed to find any empty object palette slots")
    
    if 0 <= object_palette_id <= 5:
      entity_palette_index = object_palette_id
    elif 6 <= object_palette_id <= 0x14:
      background_palette_index = object_palette_id - 6
      background_palette = self.curr_room_bg_palettes[background_palette_index]
      final_palettes[0x10 + entity_palette_index] = background_palette
    elif object_palette_id == 0x15:
      color = self.curr_room_bg_palettes[3][0xC]
      final_palettes[0x10 + entity_palette_index] = [color]*0x10
    else:
      object_palette_index = object_palette_id - 0x16
      bitfield = self.rom.read_u32(0x08133368 + object_palette_index*4)
      palette_ptr = 0x085A2E80 + (bitfield & 0x00FFFFFF)
      num_palettes = (bitfield & 0x0F000000) >> 24
      
      first_obj_pal_index = 0x10 + entity_palette_index
      if 0x20 - first_obj_pal_index < num_palettes:
        raise Exception("Failed to find enough empty object palette slots")
      
      palettes = self.generate_palettes(palette_ptr, num_palettes)
      final_palettes[first_obj_pal_index:first_obj_pal_index+num_palettes] = palettes
    
    return (final_palettes, entity_palette_index)
  
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
        red   = (red_bits   << 3) | (red_bits   >> 2)
        green = (green_bits << 3) | (green_bits >> 2)
        blue  = (blue_bits  << 3) | (blue_bits  >> 2)
        
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
      
      if palette is None:
        palette = self.DUMMY_PALETTE
      
      for color_index in range(0x10):
        color = palette[color_index]
        
        x = color_index*8
        y = palette_index*8
        palettes_image.paste(color, (x, y, x+8, y+8))
    
    palettes_image.save("palette.png")
  
  def render_world_map(self):
    gfx_data = self.rom.read_raw(0x08934FE0, 0x4000)
    tile_mapping_8x8_data = self.rom.read_raw(0x08938FE0, 0x500).read_all_u16s()
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
    
    if palette is None:
      palette = self.DUMMY_PALETTE
    
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
