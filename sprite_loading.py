
class SpriteLoadingData:
  def __init__(self, entity_type, entity_subtype, entity_form, rom):
    self.entity_type = entity_type
    self.entity_subtype = entity_subtype
    self.entity_form = entity_form
    self.rom = rom
    
    self.read()
  
  def read(self):
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
    unknown_1 = self.rom.read_u16(sprite_loading_data_ptr + 0)
    
    if unknown_1 == 0xFFFF:
      sprite_loading_data_ptr = self.rom.read_u32(sprite_loading_data_ptr + 4) + self.entity_form*0x10
      unknown_1 = self.rom.read_u16(sprite_loading_data_ptr + 0)
    else:
      sprite_loading_data_ptr = sprite_loading_data_ptr
    
    if unknown_1 & 0x8000 != 0:
      pass # TODO
    elif unknown_1 & 0x4000 != 0:
      pass # TODO
    else:
      self.fixed_gfx_index = unknown_1
    
    self.object_palette_id = self.rom.read_u16(sprite_loading_data_ptr + 2)
    self.sprite_index = self.rom.read_u16(sprite_loading_data_ptr + 8)
  
  def read_format_b(self, sprite_loading_datas_list):
    sprite_loading_data_ptr = sprite_loading_datas_list + self.entity_subtype*8
    self.sprite_data_type = self.rom.read_u8(sprite_loading_data_ptr + 0) & 0x03
    
    if self.sprite_data_type == 0:
      return
    elif self.sprite_data_type == 1:
      sprite_loading_data_ptr = sprite_loading_data_ptr
    elif self.sprite_data_type == 2:
      sprite_loading_data_ptr = self.rom.read_u32(sprite_loading_data_ptr + 4) + self.entity_form*8
    else:
      raise Exception("Unknown sprite loading data type")
    
    self.object_palette_id = self.rom.read_u16(sprite_loading_data_ptr + 4) & 0x03FF
    self.sprite_index = self.rom.read_u16(sprite_loading_data_ptr + 6) & 0x03FF
