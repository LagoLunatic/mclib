
from mclib import docs
from mclib.param_entity import ParamEntity

class EntityList:
  def __init__(self, entity_list_ptr, name, room, rom):
    self.entity_list_ptr = entity_list_ptr
    self.name = name
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.entities = []
    
    entity_ptr = self.entity_list_ptr
    while True:
      possible_end_marker = self.rom.read_u8(entity_ptr)
      if possible_end_marker == 0xFF:
        break
      
      entity = Entity(entity_ptr, self.room, self.rom)
      self.entities.append(entity)
      
      entity_ptr += 0x10

class Entity(ParamEntity):
  def __init__(self, entity_ptr, room, rom):
    super().__init__()
    
    self.entity_ptr = entity_ptr
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    type_and_unknowns = self.rom.read_u8(self.entity_ptr + 0)
    self.type = type_and_unknowns & 0x0F
    self.unknown_1 = (type_and_unknowns & 0xF0) >> 4
    unknowns = self.rom.read_u8(self.entity_ptr + 1)
    self.unknown_2 = unknowns & 0x0F
    self.unknown_3 = (unknowns & 0xF0) >> 4
    self.subtype = self.rom.read_u8(self.entity_ptr + 2)
    
    self.params_a = self.rom.read_u8(self.entity_ptr + 3)
    self.params_b = self.rom.read_u32(self.entity_ptr + 4)
    self.params_c = self.rom.read_u32(self.entity_ptr + 8)
    self.params_d = self.rom.read_u32(self.entity_ptr + 0xC)
    
    self.add_property("entity_ptr", 32, pretty_name="ROM Location")
    self.add_property("type", 4)
    self.add_property("unknown_1", 4)
    self.add_property("unknown_2", 4)
    self.add_property("unknown_3", 4)
    self.add_property("subtype", 8)
    
    self.update_params()
  
  def save(self):
    type_and_unknowns = (self.type & 0x0F) | ((self.unknown_1 << 4) & 0xF0)
    self.rom.write_u8(self.entity_ptr + 0, type_and_unknowns)
    unknowns = (self.unknown_2 & 0x0F) | ((self.unknown_3 << 4) & 0xF0)
    self.rom.write_u8(self.entity_ptr + 1, unknowns)
    self.rom.write_u8(self.entity_ptr + 2, self.subtype)
    
    self.rom.write_u8(self.entity_ptr + 3, self.params_a)
    self.rom.write_u32(self.entity_ptr + 4, self.params_b)
    self.rom.write_u32(self.entity_ptr + 8, self.params_c)
    self.rom.write_u32(self.entity_ptr + 0xC, self.params_d)
  
  def update_params(self):
    self.reset_params()
    
    self.add_param("form", "params_a", 0xFF)
    
    self.add_param("unknown_4", "params_b", 0x000000FF)
    self.add_param("unknown_5", "params_b", 0x0000FF00)
    self.add_param("unknown_6", "params_b", 0x00FF0000)
    self.add_param("unknown_7", "params_b", 0xFF000000)
    
    self.add_param("x_pos", "params_c", 0x0000FFFF)
    self.add_param("y_pos", "params_c", 0xFFFF0000)
    
    self.add_param("params", "params_d", 0xFFFFFFFF)

class DelayedLoadEntityList:
  def __init__(self, entity_list_ptr, listed_entities_type, name, room, rom):
    self.entity_list_ptr = entity_list_ptr
    self.listed_entities_type = listed_entities_type
    self.name = name
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.entities = []
    
    entity_ptr = self.entity_list_ptr
    while True:
      possible_end_marker = self.rom.read_u8(entity_ptr)
      if possible_end_marker == 0xFF:
        break
      
      entity = DelayedLoadEntity(entity_ptr, self.listed_entities_type, self.room, self.rom)
      self.entities.append(entity)
      
      entity_ptr += 0x10

class DelayedLoadEntity(Entity):
  def __init__(self, entity_ptr, type, room, rom):
    ParamEntity.__init__(self)
    
    self.entity_ptr = entity_ptr
    self.type = type
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.subtype = self.rom.read_u8(self.entity_ptr + 0)
    
    self.params_a = self.rom.read_u8(self.entity_ptr + 1)
    self.params_b = self.rom.read_u8(self.entity_ptr + 2)
    self.layer_index = self.rom.read_u8(self.entity_ptr + 3)
    self.params_c = self.rom.read_u32(self.entity_ptr + 4)
    self.params_d = self.rom.read_u32(self.entity_ptr + 8)
    self.params_e = self.rom.read_u16(self.entity_ptr + 0xC)
    self.condition_bitfield = self.rom.read_u16(self.entity_ptr + 0xE) # TODO
    
    self.add_property("entity_ptr", 32, pretty_name="ROM Location")
     # TODO make type non-editable, disable the dropdown somehow.
    self.add_property("type", 4)
    self.add_property("subtype", 8)
    self.add_property("layer_index", 8)
    self.add_property("condition_bitfield", 16, pretty_name="Conditions")
    
    self.update_params()
  
  def save(self):
    self.rom.write_u8(self.entity_ptr + 0, self.subtype)
    self.rom.write_u8(self.entity_ptr + 1, self.params_a)
    self.rom.write_u8(self.entity_ptr + 2, self.params_b)
    self.rom.write_u8(self.entity_ptr + 3, self.layer_index)
    self.rom.write_u32(self.entity_ptr + 4, self.params_c)
    self.rom.write_u32(self.entity_ptr + 8, self.params_d)
    self.rom.write_u16(self.entity_ptr + 0xC, self.params_e)
    self.rom.write_u16(self.entity_ptr + 0xE, self.condition_bitfield)
  
  def update_params(self):
    self.reset_params()
    
    self.add_param("form", "params_a", 0xFF)
    
    self.add_param("unknown_4", "params_b", 0xFF)
    
    self.add_param("x_pos", "params_c", 0x0000FFFF)
    self.add_param("y_pos", "params_c", 0xFFFF0000)
    
    self.add_param("params", "params_d", 0xFFFFFFFF)
    
    self.add_param("unknown_5", "params_e", 0x00FF)
    self.add_param("padding_1", "params_e", 0xFF00)
