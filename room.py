
import traceback
from collections import OrderedDict

from mclib.entity import Entity, TileEntity
from mclib.exit import Exit
from mclib.assets import AssetList

class Room:
  def __init__(self, room_index, area, rom):
    self.room_index = room_index
    self.area = area
    self.rom = rom
    
    self.read()
  
  def read(self):
    self.gfx_metadata_ptr = self.area.room_gfx_metadatas_list + self.room_index*0xA
    
    if self.area.room_property_lists_pointer == 0:
      self.property_list_ptr = 0
    else:
      self.property_list_ptr = self.rom.read_u32(self.area.room_property_lists_pointer + self.room_index*4)
    
    self.exit_list_ptr = self.rom.read_u32(self.area.room_exit_lists_pointer + self.room_index*4)
    self.layer_list_ptr = self.rom.read_u32(self.area.room_layers_lists_pointer + self.room_index*4)
    
    self.x_pos = self.rom.read_u16(self.gfx_metadata_ptr)
    self.y_pos = self.rom.read_u16(self.gfx_metadata_ptr + 2)
    self.width = self.rom.read_u16(self.gfx_metadata_ptr + 4)
    self.height = self.rom.read_u16(self.gfx_metadata_ptr + 6)
    self.gfx_index = self.rom.read_u16(self.gfx_metadata_ptr + 8)
    
    self._layers_asset_list = None # Lazy load
    
    self.read_entities()
    
    self.read_exits()
  
  @property
  def layers_asset_list(self):
    if not self._layers_asset_list:
      self._layers_asset_list = AssetList(self.layer_list_ptr, self.rom)
    return self._layers_asset_list
  
  def read_entities(self):
    self.entity_lists = []
    self.tile_entities = []
    self.exits = []
    
    if self.property_list_ptr == 0:
      return
    
    self.entity_list_ptr_1 = self.rom.read_u32(self.property_list_ptr + 0)
    self.entity_list_ptr_2 = self.rom.read_u32(self.property_list_ptr + 4)
    self.enemy_list_ptr = self.rom.read_u32(self.property_list_ptr + 8)
    self.tile_entity_list_ptr = self.rom.read_u32(self.property_list_ptr + 0xC)
    self.state_changing_func_ptr = self.rom.read_u32(self.property_list_ptr + 0x1C)
    
    if self.entity_list_ptr_1 != 0:
      self.read_one_entity_list(self.entity_list_ptr_1)
    
    if self.entity_list_ptr_2 != 0:
      self.read_one_entity_list(self.entity_list_ptr_2)
    
    if self.enemy_list_ptr != 0:
      self.read_one_entity_list(self.enemy_list_ptr)
    
    self.extract_hardcoded_state_entity_list_pointers()
    for entity_list_ptr in self.hardcoded_state_entity_list_pointers:
      self.read_one_entity_list(entity_list_ptr)
    
    if self.tile_entity_list_ptr != 0:
      entity_ptr = self.tile_entity_list_ptr
      while True:
        possible_end_marker = self.rom.read_u8(entity_ptr)
        if possible_end_marker == 0x00:
          break
        
        entity = TileEntity(entity_ptr, self, self.rom)
        self.tile_entities.append(entity)
        
        entity_ptr += 8
  
  def read_one_entity_list(self, entity_list_ptr):
    entity_list = []
    self.entity_lists.append(entity_list)
    
    entity_ptr = entity_list_ptr
    while True:
      possible_end_marker = self.rom.read_u8(entity_ptr)
      if possible_end_marker == 0xFF:
        break
      
      entity = Entity(entity_ptr, self, self.rom)
      entity_list.append(entity)
      
      entity_ptr += 0x10
  
  def read_exits(self):
    if not self.rom.is_pointer(self.exit_list_ptr):
      # Invalid exit list pointer (e.g. for room 8A-02)
      return
    
    exit_ptr = self.exit_list_ptr
    while True:
      possible_end_marker = self.rom.read_u16(exit_ptr)
      if possible_end_marker == 0xFFFF:
        break
      
      ext = Exit(exit_ptr, self, self.rom)
      self.exits.append(ext)
      
      exit_ptr += 0x14
  
  def extract_hardcoded_state_entity_list_pointers(self):
    # Rooms can have a function that hardcodes various conditional checks and then loads different entity lists.
    # This function extracts those hardcoded entity list pointers automatically.
    
    #print("Room %02X:" % self.room_index)
    
    self.hardcoded_state_entity_list_pointers = []
    
    func_start_ptr = self.state_changing_func_ptr
    func_start_ptr &= 0xFFFFFFFE # Lowest bit being set only means that it's a THUMB function instead of ARM
    
    ptr = func_start_ptr
    on_first = True
    is_push_r14_start = False
    minimum_address_that_may_be_func_end = func_start_ptr
    all_branch_destinations = []
    constants_loaded = OrderedDict()
    while True:
      bytecode = self.rom.read_u16(ptr)
      ptr += 2
      if   bytecode & 0b11111111_00000000 == 0b10110101_00000000:
        # Push registers including r14 (start a function)
        if on_first:
          is_push_r14_start = True
      elif bytecode & 0b11111111_00000000 == 0b10111101_00000000:
        # Pop registers including r15 (return)
        if is_push_r14_start and ptr >= minimum_address_that_may_be_func_end:
          break
      elif bytecode == 0x4770:
        # bx r14 (return)
        if ptr >= minimum_address_that_may_be_func_end:
          break
      elif bytecode & 0b11111000_00000000 == 0b01001000_00000000:
        # ldr, =(some constant)
        offset = bytecode & 0b00000000_11111111
        offset <<= 2
        
        # ptr is ahead by 2 bytes, and offset is behind by 4 bytes, so add an extra 2.
        fixed_ptr = ptr + 2
        
        ptr_word_aligned = (fixed_ptr & 0xFFFFFFFC)
        constant_address = ptr_word_aligned + offset
        constant = self.rom.read_u32(constant_address)
        
        constants_loaded[ptr-2] = constant
      elif bytecode & 0b11110000_00000000 == 0b11110000_00000000:
        # Long branch with link (function call)
        bytecode2 = self.rom.read_u16(ptr)
        ptr += 2
        assert bytecode  & 0b11111000_00000000 == 0b11110000_00000000
        assert bytecode2 & 0b11111000_00000000 == 0b11111000_00000000
        
        offset_high = bytecode & 0b00000111_11111111
        offset_low = bytecode2 & 0b00000111_11111111
        offset = (offset_high << 11) | offset_low
        offset <<= 1
        
        if offset & 0x00400000 != 0:
          # Negative, take the 23-bit two's complement
          offset = -((~offset & 0x007FFFFF) + 1)
        
        # Note that ptr is ahead by 4 bytes, but offset is behind by 4 bytes, so it cancels out.
        dest_func = ptr + offset
        
        if dest_func == 0x0804ADDC: # LoadRoomEntityList
          last_line_ptr = ptr-6
          if last_line_ptr in constants_loaded:
            self.hardcoded_state_entity_list_pointers.append(constants_loaded[last_line_ptr])
            #print("Found entity list %08X" % (constants_loaded[last_line_ptr]))
          elif ptr == 0x0804E412:
            # This room (44-00) is the only one in the entire game that doesn't put the entity list pointer conveniently on the line right before.
            # Instead of an error for this room, just hardcode where to read the entity list pointers from.
            list_of_entity_lists_ptr = constants_loaded[ptr-16]
            for i in range(8):
              entity_list_ptr = self.rom.read_u32(list_of_entity_lists_ptr+i*4)
              self.hardcoded_state_entity_list_pointers.append(entity_list_ptr)
          else:
            raise Exception("Found function call to LoadRoomEntityList at %08X, but no constant on the line before" % (ptr-4))
      elif bytecode & 0b11111000_00000000 == 0b11100000_00000000 or bytecode & 0b11110000_00000000 == 0b11010000_00000000:
        # Branch
        if bytecode & 0b11111000_00000000 == 0b11100000_00000000:
          # Unconditional branch
          offset = bytecode & 0b00000111_11111111
          offset <<= 1
          
          if offset & 0b00001000_00000000 != 0:
            # Negative, take the 12-bit two's complement
            offset = -((~offset & 0xFFF) + 1)
          
          unconditional = True
        elif bytecode & 0b11110000_00000000 == 0b11010000_00000000:
          # Conditional branch
          offset = bytecode & 0b00000000_11111111
          offset <<= 1
          
          if offset & 0b00000001_00000000 != 0:
            # Negative, take the 9-bit two's complement
            offset = -((~offset & 0x1FF) + 1)
          
          unconditional = False
        
        # ptr is ahead by 2 bytes, and offset is behind by 4 bytes, so add an extra 2.
        dest_ptr = ptr + offset + 2
        
        #print("%08X -> %08X" % (ptr-2, dest_ptr))
        
        all_branch_destinations.append(dest_ptr)
        
        if unconditional:
          # Unconditional branches can be used to jump over a region of memory that is used for storing constants.
          # We need to detect these and also skip this region so we don't try to read data as code.
          #print("Possible skip region: %08X-%08X" % (ptr, dest_ptr-1))
          branch_dests_in_possible_skip_region = [
            x for x in all_branch_destinations
            if x >= ptr and x < dest_ptr
          ]
          if branch_dests_in_possible_skip_region:
            # If we've seen any other branches that go inside the region we're considering skipping, then that means only part of the region is data that should be skipped.
            earliest_branch_dest_in_possible_skip_region = min(branch_dests_in_possible_skip_region)
            if earliest_branch_dest_in_possible_skip_region > ptr:
              ptr = earliest_branch_dest_in_possible_skip_region
              #print("Skipped to %08X" % earliest_branch_dest_in_possible_skip_region)
          else:
            ptr = dest_ptr
            #print("Skipped to %08X" % dest_ptr)
        
        if dest_ptr > minimum_address_that_may_be_func_end:
          # If a line within the function branches somewhere, we know that destination must also be within the function.
          # So don't stop reading the function until at least this address, even if something that looks like a return is encountered.
          minimum_address_that_may_be_func_end = dest_ptr
        elif dest_ptr < func_start_ptr:
          raise Exception("Branch destination of %08X is before the function started at %08X" % (dest_ptr, func_start_ptr))
      elif bytecode == 0x4687:
        # mov r15, r0 (switch statement)
        assert self.rom.read_u16(ptr-4) == 0x6800 # Make sure previous line was ldr r0, [r0]
        assert self.rom.read_u16(ptr-6) == 0x1840 # Make sure previous line was add r0, r0, r1
        
        # TODO there are some rare exceptions to this rule
        # regex to help search for them:
        # add     r0,r.+\r?\n.+ldr     r0,\[r0\]\r?\n.+mov     r15,r0
        
        # Read all the switch cases.
        location_of_cases_list = constants_loaded[ptr-8]
        next_case_ptr = location_of_cases_list
        while True:
          case_dest_ptr = self.rom.read_u32(next_case_ptr)
          all_branch_destinations.append(case_dest_ptr)
          #print("Found case: %08X" % case_dest_ptr)
          
          next_case_ptr += 4
          
          lowest_unpassed_branch_dest = min([
            x for x in all_branch_destinations
            if x >= ptr
          ])
          if next_case_ptr >= lowest_unpassed_branch_dest:
            # We know to stop reading cases once we reach something we know is code.
            break
        
        # And skip over the whole case list of case pointers so we don't try to read them as if they were code.
        #print("Skipped from %08X to %08X due to switch statement" % (ptr, next_case_ptr))
        ptr = next_case_ptr
      
      on_first = False
    
    #func_end_ptr = ptr-2
    #print("State function ranges from %08X-%08X" % (func_start_ptr, func_end_ptr))
