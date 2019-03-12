
class Dungeon:
  def __init__(self, dungeon_index, rom):
    self.rom = rom
    self.dungeon_index = dungeon_index
    
    self.read()
  
  def read(self):
    self.dungeon_ptr = self.rom.read_u32(0x080C9C50 + self.dungeon_index*4)
    self.dungeon_floor_metadata_ptr = 0x080C9C6C + self.dungeon_index*4
    
    self.num_floors = self.rom.read_u8(self.dungeon_floor_metadata_ptr+0)
    self.topmost_floor_number = self.rom.read_u8(self.dungeon_floor_metadata_ptr+1)
    
    self.floors = []
    
    curr_ptr = self.dungeon_ptr
    for floor_index in range(self.num_floors):
      floor_ptr = self.rom.read_u32(curr_ptr)
      
      floor = []
      self.floors.append(floor)
      
      room_ptr = floor_ptr
      while True:
        possible_end_marker = self.rom.read_u8(room_ptr+0)
        if possible_end_marker == 0x00:
          break
        
        room = DungeonRoom(room_ptr, self.rom)
        floor.append(room)
        
        room_ptr += 8
      
      curr_ptr += 4

class DungeonRoom:
  def __init__(self, room_ptr, rom):
    self.rom = rom
    self.room_ptr = room_ptr
    
    self.read()
  
  def read(self):
    self.area_index = self.rom.read_u8(self.room_ptr+0)
    self.room_index = self.rom.read_u8(self.room_ptr+1)
    self.unknown_1 = self.rom.read_u8(self.room_ptr+2)
    self.unknown_2 = self.rom.read_u8(self.room_ptr+3)
    self.room_map_data_offset = self.rom.read_u32(self.room_ptr+4)
    
    self.room_map_data_ptr = 0x08324AE4 + self.room_map_data_offset
