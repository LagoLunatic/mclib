
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

class Entity:
  def __init__(self, entity_ptr, room, rom):
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
    self.form = self.rom.read_u8(self.entity_ptr + 3)
    
    self.unknown_4 = self.rom.read_u8(self.entity_ptr + 4)
    self.unknown_5 = self.rom.read_u8(self.entity_ptr + 5)
    self.unknown_6 = self.rom.read_u8(self.entity_ptr + 6)
    self.unknown_7 = self.rom.read_u8(self.entity_ptr + 7)
    
    self.x_pos = self.rom.read_u16(self.entity_ptr + 8)
    self.y_pos = self.rom.read_u16(self.entity_ptr + 0xA)
    
    self.params = self.rom.read_u32(self.entity_ptr + 0xC)

class DelayedLoadEntityList(EntityList):
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
    self.entity_ptr = entity_ptr
    self.type = type
    self.room = room
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.subtype = self.rom.read_u8(self.entity_ptr + 0)
    self.form = self.rom.read_u8(self.entity_ptr + 1)
    self.unknown_4 = self.rom.read_u8(self.entity_ptr + 2)
    unk = self.rom.read_u8(self.entity_ptr + 3) # TODO
    self.x_pos = self.rom.read_u16(self.entity_ptr + 4)
    self.y_pos = self.rom.read_u16(self.entity_ptr + 6)
    self.params = self.rom.read_u32(self.entity_ptr + 8)
    self.unknown_5 = self.rom.read_u16(self.entity_ptr + 0xC)
    unk2 = self.rom.read_u16(self.entity_ptr + 0xE) # TODO
    
    # TODO
    self.unknown_1 = 0
    self.unknown_2 = 0
    self.unknown_3 = 0
    self.unknown_6 = 0
    self.unknown_7 = 0
