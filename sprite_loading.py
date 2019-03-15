
class SpriteLoadingData:
  def __init__(self, entity, rom):
    self.entity_type = entity.type
    self.entity_subtype = entity.subtype
    self.entity_form = entity.form
    self.area = entity.room.area
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.has_no_sprite = False
    
    if self.entity_type == 3:
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
  
  def read_format_a(self, sprite_loading_datas_list):
    sprite_loading_data_ptr = sprite_loading_datas_list + self.entity_subtype*0x10
    bitfield = self.rom.read_u16(sprite_loading_data_ptr + 0)
    
    if bitfield == 0xFFFF:
      sprite_loading_data_ptr = self.rom.read_u32(sprite_loading_data_ptr + 4) + self.entity_form*0x10
      bitfield = self.rom.read_u16(sprite_loading_data_ptr + 0)
    else:
      sprite_loading_data_ptr = sprite_loading_data_ptr
    
    if bitfield == 0:
      self.has_no_sprite = True
    else:
      self.gfx_type = (bitfield & 0x4000) >> 14
      if self.gfx_type == 0:
        self.fixed_gfx_index = bitfield
      elif self.gfx_type == 1:
        pass # TODO
      elif self.gfx_type == 2:
        self.common_gfx_tile_index = bitfield & 0x03FF
    
    self.object_palette_id = self.rom.read_u16(sprite_loading_data_ptr + 2)
    self.sprite_index = self.rom.read_u16(sprite_loading_data_ptr + 8)
  
  def read_format_b(self, sprite_loading_datas_list):
    sprite_loading_data_ptr = sprite_loading_datas_list + self.entity_subtype*8
    self.sprite_data_type = self.rom.read_u8(sprite_loading_data_ptr + 0) & 0x03
    
    if self.sprite_data_type == 0:
      self.has_no_sprite = True
      return
    elif self.sprite_data_type == 1:
      sprite_loading_data_ptr = sprite_loading_data_ptr
    elif self.sprite_data_type == 2:
      sprite_loading_data_ptr = self.rom.read_u32(sprite_loading_data_ptr + 4) + self.entity_form*8
    else:
      raise Exception("Unknown sprite loading data type")
    
    bitfield = self.rom.read_u16(sprite_loading_data_ptr + 2)
    self.gfx_type = (bitfield & 0x0C00) >> 10
    if self.gfx_type == 0:
      self.fixed_gfx_index = bitfield & 0x03FF
    elif self.gfx_type == 1:
      pass # TODO
    elif self.gfx_type == 2:
      self.common_gfx_tile_index = bitfield & 0x03FF
    self.object_palette_id = self.rom.read_u16(sprite_loading_data_ptr + 4) & 0x03FF
    self.sprite_index = self.rom.read_u16(sprite_loading_data_ptr + 6) & 0x03FF
    
    if self.entity_type == 6 and self.entity_subtype == 8:
      # Door
      if self.area.area_index == 0x25:
        self.fixed_gfx_index = 0x1E7
      elif self.area.area_index == 0x35:
        self.fixed_gfx_index = 0x1C3
      elif self.area.area_index >= 0x40:
        self.fixed_gfx_index = self.rom.read_u16(0x0811F690 + (self.area.area_index-0x40)*2)
      else:
        self.fixed_gfx_index = 0xA
      
      if self.area.area_index == 0x68:
        self.object_palette_id = 0
      elif self.area.area_index == 0x88:
        self.object_palette_id = 1
    elif self.entity_type == 6 and self.entity_subtype == 0x27:
      # Pushable statue
      if self.area.area_index >= 0x40:
        self.fixed_gfx_index = self.rom.read_u16(0x08120CCC + (self.area.area_index-0x40)*2)
      else:
        self.fixed_gfx_index = 0xE9
