
class SpriteLoadingData:
  def __init__(self, entity_type, entity_subtype, entity_form, rom, area_index=0):
    self.entity_type = entity_type
    self.entity_subtype = entity_subtype
    self.entity_form = entity_form
    self.area_index = area_index
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.has_no_sprite = False
    
    if self.entity_type == 1:
      # The player, Link.
      # Always uses swap type GFX.
      self.gfx_type = 1
      self.sprite_index = 0x001
      self.object_palette_id = 0x16
    elif self.entity_type == 3:
      sprite_loading_datas_list = 0x080D2C58
      self.read_format_a(sprite_loading_datas_list)
    elif self.entity_type == 4:
      sprite_loading_datas_list = 0x0813210C
      self.read_format_a(sprite_loading_datas_list)
    elif self.entity_type == 6:
      sprite_loading_datas_list = 0x08126798
      self.read_format_b(sprite_loading_datas_list)
    elif self.entity_type == 7:
      sprite_loading_datas_list = 0x08114AE4
      self.read_format_b(sprite_loading_datas_list)
    elif self.entity_type == 8:
      sprite_loading_datas_list = 0x08126DA8
      self.read_format_c(sprite_loading_datas_list)
    else:
      self.has_no_sprite = True
  
  def read_format_a(self, sprite_loading_datas_list):
    sprite_loading_data_ptr = sprite_loading_datas_list + self.entity_subtype*0x10
    bitfield = self.rom.read_u16(sprite_loading_data_ptr + 0)
    
    if bitfield == 0xFFFF:
      # Multiple forms
      sprite_loading_data_ptr = self.rom.read_u32(sprite_loading_data_ptr + 4) + self.entity_form*0x10
      bitfield = self.rom.read_u16(sprite_loading_data_ptr + 0)
    else:
      # Single form
      sprite_loading_data_ptr = sprite_loading_data_ptr
    
    if bitfield == 0:
      self.has_no_sprite = True
    else:
      self.gfx_type = (bitfield & 0xC000) >> 14
      if self.gfx_type == 0:
        self.fixed_gfx_index = bitfield
      elif self.gfx_type == 1:
        self.swap_gfx_slots_needed = (bitfield & 0x0FF0) >> 4
      elif self.gfx_type == 2:
        self.common_gfx_tile_index = bitfield & 0x03FF
    
    self.object_palette_id = self.rom.read_u16(sprite_loading_data_ptr + 2)
    self.sprite_index = self.rom.read_u16(sprite_loading_data_ptr + 8)
    
    if self.entity_type == 3 and self.entity_subtype == 0x17:
      # Rupee Like. Change the sprite index to be the Rupee Like sprite instead of an item sprite.
      self.sprite_index = 0xD1
  
  def read_format_b(self, sprite_loading_datas_list):
    sprite_loading_data_ptr = sprite_loading_datas_list + self.entity_subtype*8
    self.sprite_data_type = self.rom.read_u8(sprite_loading_data_ptr + 0) & 0x03
    
    if self.sprite_data_type == 0:
      self.has_no_sprite = True
      return
    elif self.sprite_data_type == 1:
      # Single form
      sprite_loading_data_ptr = sprite_loading_data_ptr
    elif self.sprite_data_type == 2:
      # Multiple forms
      sprite_loading_data_ptr = self.rom.read_u32(sprite_loading_data_ptr + 4) + self.entity_form*8
    else:
      raise Exception("Unknown sprite loading data type")
    
    bitfield = self.rom.read_u16(sprite_loading_data_ptr + 2)
    self.gfx_type = (bitfield & 0x0C00) >> 10
    if self.gfx_type == 0:
      self.fixed_gfx_index = bitfield & 0x03FF
    elif self.gfx_type == 1:
      self.swap_gfx_slots_needed = (bitfield & 0x0FF0) >> 4
    elif self.gfx_type == 2:
      self.common_gfx_tile_index = bitfield & 0x03FF
    self.object_palette_id = self.rom.read_u16(sprite_loading_data_ptr + 4) & 0x03FF
    self.sprite_index = self.rom.read_u16(sprite_loading_data_ptr + 6) & 0x03FF
    
    if self.entity_type == 6 and self.entity_subtype in [8, 0x6C]:
      # Door
      if self.area_index == 0x25:
        self.fixed_gfx_index = 0x1E7
      elif self.area_index == 0x35:
        self.fixed_gfx_index = 0x1C3
      elif self.area_index >= 0x40:
        self.fixed_gfx_index = self.rom.read_u16(0x0811F690 + (self.area_index-0x40)*2)
      else:
        self.fixed_gfx_index = 0xA
      
      if self.area_index == 0x68:
        self.object_palette_id = 0
      elif self.area_index == 0x88:
        self.object_palette_id = 1
    elif self.entity_type == 6 and self.entity_subtype == 0x27:
      # Pushable statue
      if self.area_index >= 0x40:
        self.fixed_gfx_index = self.rom.read_u16(0x08120CCC + (self.area_index-0x40)*2)
      else:
        self.fixed_gfx_index = 0xE9
  
  def read_format_c(self, sprite_loading_datas_list):
    sprite_loading_data_ptr = sprite_loading_datas_list + self.entity_subtype*8
    bitfield = self.rom.read_u8(sprite_loading_data_ptr + 0)
    
    if bitfield == 0xFF:
      # Multiple forms
      index = self.rom.read_u8(sprite_loading_data_ptr + 1)
      #first_item_id = self.rom.read_u8(sprite_loading_data_ptr + 2)
      list_ptr = self.rom.read_u32(0x08126ED8 + index*4)
      #sprite_loading_data_ptr = list_ptr + (item_id - first_item_id)*8
      sprite_loading_data_ptr = list_ptr + self.entity_form*8 # TODO: form is not really the index, the index is item_id-first_item_id
    else:
      # Single form
      sprite_loading_data_ptr = sprite_loading_data_ptr
    
    bitfield = self.rom.read_u8(sprite_loading_data_ptr + 0)
    self.object_palette_id = bitfield & 0x0F
    
    self.sprite_index = self.rom.read_u8(sprite_loading_data_ptr + 5)
    
    gfx_load_bitfield = self.rom.read_u16(sprite_loading_data_ptr + 6)
    if gfx_load_bitfield == 0:
      # Use Link's GFX, which is swap type
      self.gfx_type = 1
    else:
      # Use common GFX
      self.gfx_type = 2
      self.common_gfx_tile_index = gfx_load_bitfield & 0x03FF
