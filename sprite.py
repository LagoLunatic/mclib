
class Sprite:
  def __init__(self, sprite_index, rom):
    self.sprite_index = sprite_index
    self.rom = rom
    
    self.read()
  
  def read(self):
    if self.sprite_index >= 0x149:
      self.animation_list_ptr = 0
      self.frame_gfx_data_list_ptr = 0
      self.gfx_pointer = 0
    else:
      self.sprite_ptr = 0x080029B4 + self.sprite_index*0x10
      self.animation_list_ptr = self.rom.read_u32(self.sprite_ptr + 0)
      self.frame_gfx_data_list_ptr = self.rom.read_u32(self.sprite_ptr + 4)
      self.gfx_pointer = self.rom.read_u32(self.sprite_ptr + 8)
  
  def get_frame_obj_list(self, frame_index):
    offset_1 = self.rom.read_u32(0x082F3D74 + self.sprite_index*4)
    offset_2 = self.rom.read_u32(0x082F3D74 + offset_1 + frame_index*4)
    frame_obj_data_ptr = 0x082F3D74 + offset_2
    
    frame_obj_list = FrameObjList(frame_obj_data_ptr, self.rom)
    return frame_obj_list
  
  def get_extra_frame_offsets_by_main_frame(self, frame_index, subentry_index):
    offset_1 = self.rom.read_u16(0x089FB780 + self.sprite_index*2)
    unk_index = self.rom.read_u8(0x089FB770 + offset_1 + frame_index)
    offset_data_ptr = 0x089FB770 + unk_index*4 + 0xD00
    if subentry_index == 0:
      pass
    elif subentry_index == 1:
      offset_data_ptr += 2
    else:
      raise Exception("Given a sprite subentry index other than 0 or 1")
    extra_x_off = self.rom.read_s8(offset_data_ptr+0)
    extra_y_off = self.rom.read_s8(offset_data_ptr+1)
    return (extra_x_off, extra_y_off)
  
  def get_animation(self, anim_index):
    if self.animation_list_ptr == 0:
      return None
    
    animation_ptr = self.rom.read_u32(self.animation_list_ptr + anim_index*4)
    animation = Animation(animation_ptr, self.rom)
    return animation
  
  def get_frame_gfx_data(self, frame_index):
    if self.frame_gfx_data_list_ptr == 0:
      return None
    
    frame_gfx_data_ptr = self.frame_gfx_data_list_ptr + frame_index*4
    frame_gfx_data = FrameGfxData(frame_gfx_data_ptr, self.rom)
    return frame_gfx_data

class Animation:
  def __init__(self, animation_ptr,rom):
    self.animation_ptr = animation_ptr
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.keyframes = []
    keyframe_ptr = self.animation_ptr
    while True:
      keyframe = Keyframe(keyframe_ptr, self.rom)
      self.keyframes.append(keyframe)
      
      if keyframe.end_of_animation:
        break
      
      keyframe_ptr += 5

class Keyframe:
  def __init__(self, keyframe_ptr, rom):
    self.keyframe_ptr = keyframe_ptr
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.frame_index = self.rom.read_u8(self.keyframe_ptr+0)
    self.keyframe_duration = self.rom.read_u8(self.keyframe_ptr+1)
    bitfield = self.rom.read_u8(self.keyframe_ptr+2)
    self.h_flip = (bitfield & 0x40) != 0
    self.v_flip = (bitfield & 0x80) != 0
    bitfield = self.rom.read_u8(self.keyframe_ptr+3)
    self.end_of_animation = (bitfield & 0x80) != 0
    self.extra_frame_index = bitfield & 0x3F

class FrameGfxData:
  def __init__(self, frame_gfx_data_ptr, rom):
    self.frame_gfx_data_ptr = frame_gfx_data_ptr
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.num_gfx_tiles = self.rom.read_u8(self.frame_gfx_data_ptr)
    self.first_gfx_tile_index = self.rom.read_u16(self.frame_gfx_data_ptr + 2)

class FrameObjList:
  def __init__(self, frame_obj_data_ptr, rom):
    self.frame_obj_data_ptr = frame_obj_data_ptr
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.num_objs = self.rom.read_u8(self.frame_obj_data_ptr)
    
    obj_ptr = self.frame_obj_data_ptr + 1
    self.objs = []
    for i in range(self.num_objs):
      obj = Obj(obj_ptr, self.rom)
      self.objs.append(obj)
      obj_ptr += 5

class Obj:
  OBJ_SIZES = {
    0: {
      0: (8, 8),
      1: (16, 16),
      2: (32, 32),
      3: (64, 64),
    },
    1: {
      0: (16, 8),
      1: (32, 8),
      2: (32, 16),
      3: (64, 32),
    },
    2: {
      0: (8, 16),
      1: (8, 32),
      2: (16, 32),
      3: (32, 64),
    },
  }
  
  def __init__(self, obj_ptr, rom):
    self.obj_ptr = obj_ptr
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.x_off = self.rom.read_s8(self.obj_ptr + 0)
    self.y_off = self.rom.read_s8(self.obj_ptr + 1)
    bitfield = self.rom.read_u8(self.obj_ptr + 2)
    bitfield2 = self.rom.read_u16(self.obj_ptr + 3)
    
    self.override_entity_palette_index = (bitfield & 0x01) != 0
    # Bit 02 seems unused.
    self.h_flip = (bitfield & 0x04) != 0
    self.v_flip = (bitfield & 0x08) != 0
    self.size = (bitfield & 0x30) >> 4
    self.shape = (bitfield & 0xC0) >> 6
    if self.shape == 3:
      raise Exception("Invalid OBJ shape")
    
    self.width, self.height = self.OBJ_SIZES[self.shape][self.size]
    
    self.first_gfx_tile_offset = bitfield2 & 0x03FF
    self.priority = (bitfield2 & 0x0C00) >> 10
    self.palette_index = (bitfield2 & 0xF000) >> 12
