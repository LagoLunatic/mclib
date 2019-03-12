
class PaletteGroup:
  def __init__(self, palette_group_index, rom):
    self.rom = rom
    self.palette_group_index = palette_group_index
    
    self.read()
  
  def read(self):
    palette_set_pointer = self.rom.read_u32(0x080FF850+self.palette_group_index*4)
    
    self.palette_sets = []
    while True:
      palette_set = PaletteSet(palette_set_pointer, self.rom)
      self.palette_sets.append(palette_set)
      
      if not palette_set.continue_loading_palette_sets:
        break
      
      palette_set_pointer += 4

class PaletteSet:
  def __init__(self, palette_set_pointer, rom):
    self.rom = rom
    self.palette_set_pointer = palette_set_pointer
    
    self.read()
  
  def read(self):
    self.global_palette_index = self.rom.read_u16(self.palette_set_pointer+0)
    self.palette_load_offset = self.rom.read_u8(self.palette_set_pointer+2)
    bitfield = self.rom.read_u8(self.palette_set_pointer+3)
    
    self.num_palettes = bitfield & 0x0F
    if self.num_palettes == 0:
      self.num_palettes = 0x10
    self.continue_loading_palette_sets = (bitfield & 0x80 == 0x80)
    
    self.first_palette_pointer = 0x085A2E80 + self.global_palette_index*0x20
