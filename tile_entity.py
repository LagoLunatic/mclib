
from mclib.param_entity import ParamEntity
from mclib import docs

class TileEntity(ParamEntity):
  def __init__(self, entity_ptr, room, rom):
    super().__init__()
    
    self.entity_ptr = entity_ptr
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.type = self.rom.read_u8(self.entity_ptr + 0)
    
    self.params_a = self.rom.read_u8(self.entity_ptr + 1)
    self.params_b = self.rom.read_u16(self.entity_ptr + 2)
    self.params_c = self.rom.read_u16(self.entity_ptr + 4)
    self.params_d = self.rom.read_u16(self.entity_ptr + 6)
    
    self.add_property("entity_ptr", 32, pretty_name="ROM Location")
    self.add_property("type", 8)
    
    self.update_params()
  
  def save(self):
    self.rom.write_u8(self.entity_ptr + 0, self.type)
    self.rom.write_u8(self.entity_ptr + 1, self.params_a)
    self.rom.write_u16(self.entity_ptr + 2, self.params_b)
    self.rom.write_u16(self.entity_ptr + 4, self.params_c)
    self.rom.write_u16(self.entity_ptr + 6, self.params_d)
  
  def update_params(self):
    self.reset_params()
    
    for prop_name, bitfield_name, bitmask, pretty_param_name in docs.Docs.get_entity_param_properties(self):
      self.add_param(prop_name, bitfield_name, bitmask, pretty_param_name=pretty_param_name)
