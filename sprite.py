
class Sprite:
  def __init__(self, sprite_index, rom):
    self.sprite_index = sprite_index
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.sprite_ptr = 0x080029B4 + self.sprite_index*0x10
    self.frame_list_ptr = self.rom.read_u32(self.sprite_ptr + 4)
    self.gfx_pointer = self.rom.read_u32(self.sprite_ptr + 8)
    
    self.frames = []
    
    if self.frame_list_ptr == 0:
      # Invalid sprite
      return
    
    # Guess how many frames there are by looking at the next sprite's frame list pointer.
    # TODO: Try to find a proper way of detecting the number of frames.
    all_frame_list_ptrs = []
    for i in range(0x149):
      ptr = 0x080029B4 + i*0x10
      frame_list_ptr = self.rom.read_u32(ptr + 4)
      if frame_list_ptr > 0:
        all_frame_list_ptrs.append(frame_list_ptr)
    if self.sprite_index == 0x148:
      num_frames = 0x13
    elif self.sprite_index == 0x17:
      num_frames = 0xB4
    else:
      next_frame_list_ptr = min([x for x in all_frame_list_ptrs if x > self.frame_list_ptr])
      num_frames = (next_frame_list_ptr - self.frame_list_ptr) // 4
    
    offset_1 = self.rom.read_u32(0x082F3D74 + self.sprite_index*4)
    for frame_index in range(num_frames):
      offset_2 = self.rom.read_u32(0x082F3D74 + offset_1 + frame_index*4)
      frame_obj_data_ptr = 0x082F3D74 + offset_2
      
      frame_data_ptr = self.frame_list_ptr + frame_index*4
      
      frame = Frame(frame_data_ptr, frame_obj_data_ptr, self.rom)
      self.frames.append(frame)

class Frame:
  def __init__(self, frame_data_ptr, frame_obj_data_ptr, rom):
    self.frame_data_ptr = frame_data_ptr
    self.frame_obj_data_ptr = frame_obj_data_ptr
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.num_gfx_tiles = self.rom.read_u8(self.frame_data_ptr)
    self.first_gfx_tile_index = self.rom.read_u16(self.frame_data_ptr + 2)
    
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
    
    self.override_palette = (bitfield & 0x01) != 0
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
