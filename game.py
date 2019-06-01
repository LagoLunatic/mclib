
import os
import re
from collections import OrderedDict

from mclib.data_interface import RomInterface
from mclib.area import Area
from mclib.map import Dungeon
from mclib.cutscene import Cutscene
from mclib.docs import ITEM_ID_TO_NAME

import yaml
try:
  from yaml import CDumper as Dumper
except ImportError:
  from yaml import Dumper

# Allow yaml to load and dump OrderedDicts.
yaml.SafeLoader.add_constructor(
  yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
  lambda loader, node: OrderedDict(loader.construct_pairs(node))
)
yaml.Dumper.add_representer(
  OrderedDict,
  lambda dumper, data: dumper.represent_dict(data.items())
)

from paths import ASM_PATH
from paths import DATA_PATH

class Game:
  def __init__(self, input_rom_path):
    self.input_rom_path = input_rom_path
    
    with open(self.input_rom_path, "rb") as file:
      self.rom = RomInterface(file.read())
    
    self.read()
    
    self.read_custom_symbols()
  
  def read(self):
    self.areas = []
    for area_index in range(0x90):
      area = Area(area_index, self.rom)
      self.areas.append(area)
    
    self.dungeons = []
    for dungeon_index in range(7):
      dungeon = Dungeon(dungeon_index, self.rom)
      self.dungeons.append(dungeon)
  
  def print_all_entity_cutscene_scripts(self):
    vanilla_symbols_path = os.path.join(DATA_PATH, "symbol_map.sym")
    
    with open(vanilla_symbols_path, "r") as f:
      matches = re.findall(r"^[0-9a-f]{8} ScriptCommand([0-9a-f]{2})(\S*)$", f.read(), re.IGNORECASE | re.MULTILINE)
    script_command_names = {}
    for command_index, command_name in matches:
      command_index = int(command_index, 16)
      script_command_names[command_index] = command_name
    
    for area in self.areas:
      for room in area.rooms:
        if room is None:
          continue
        for entity_list in room.entity_lists:
          for entity in entity_list.entities:
            if entity.has_cutscene:
              filename = "%02X-%02X %02X-%02X-%02X %08X" % (
                area.area_index, room.room_index,
                entity.type, entity.subtype, entity.form,
                entity.cutscene_pointer
              )
              with open("./logs/all entity cutscenes/%s.txt" % filename, "w") as f:
                cutscene = Cutscene(entity.cutscene_pointer, self.rom)
                for command in cutscene.commands:
                  line = "%08X: " % command.command_ptr
                  command_name = script_command_names[command.type]
                  line += "ScriptCommand%02X%s(" % (command.type, command_name)
                  line += (", ".join(["%04X" % arg for arg in command.arguments]))
                  line += ")\n"
                  f.write(line)
                  
                  #f.write("%08X: command type %02X, args: " % (command.command_ptr, command.type) + (", ".join(["%04X" % arg for arg in command.arguments])) + "\n")
  
  def apply_patch(self, patch_name, rom=None):
    if rom is None:
      rom = self.rom
    
    with open(os.path.join(ASM_PATH, patch_name + "_diff.txt")) as f:
      diffs = yaml.safe_load(f)
      
      for org_address, new_bytes in diffs.items():
        rom.write(org_address, new_bytes, "B"*len(new_bytes))
  
  def read_custom_symbols(self):
    self.custom_symbols = {}
    
    custom_symbols_path = os.path.join(ASM_PATH, "custom_symbols.txt")
    if not os.path.isfile(custom_symbols_path):
      return
    
    with open(custom_symbols_path, "r") as f:
      matches = re.findall(r"^([0-9a-f]{8}) (\S+)", f.read(), re.IGNORECASE | re.MULTILINE)
    for symbol_address, symbol_name in matches:
      self.custom_symbols[symbol_name] = int(symbol_address, 16)
  
  def print_item_locations(self):
    output = []
    for area in self.areas:
      area_index = area.area_index
      #print("Area %02X:" % area_index)
      for room in area.rooms:
        if room is None:
          continue
        room_index = room.room_index
        #print("On room %02X-%02X:" % (area_index, room_index))
        
        for tile_entity in room.tile_entities:
          if tile_entity.type in [2, 3]:
            # Small chest or big chest
            item_id = tile_entity.item_id
            item_name = ITEM_ID_TO_NAME[item_id]
            item_param = tile_entity.unknown_2
            output.append(
              "Room %02X-%02X:   Chest at %08X gives item %02X (%02X) - %s" % (
                area_index, room_index, tile_entity.entity_ptr, item_id, item_param, item_name
              ))
        
        for entity_list in room.entity_lists:
          for entity in entity_list.entities:
            if entity.type == 6 and entity.subtype in [0, 2, 5, 0x40, 0xAC]:
              item_id = entity.form
              if item_id == 0 and entity.subtype == 5:
                # For pots, item ID 0 means random item
                continue
              item_name = ITEM_ID_TO_NAME[item_id]
              if entity.subtype in [0, 2]:
                item_param = entity.unknown_4
              elif entity.subtype == 5:
                item_param = entity.unknown_5
              else:
                item_param = 0
              output.append(
                "Room %02X-%02X:  Entity at %08X gives item %02X (%02X) - %s" % (
                  area_index, room_index, entity.entity_ptr, item_id, item_param, item_name
                ))
        
        # Items given by cutscenes
        all_cutscene_ptrs_for_room = []
        for entity_list in room.entity_lists:
          for entity in entity_list.entities:
            if entity.unknown_3 == 4 or entity.type == 7:
              if entity.cutscene_pointer != 0:
                all_cutscene_ptrs_for_room.append(entity.cutscene_pointer)
            if entity.type == 7 and entity.subtype == 3: # Minish
              cutscene_ptr = self.rom.read_u32(0x08109D18 + entity.unknown_4*4)
              all_cutscene_ptrs_for_room.append(cutscene_ptr)
            elif entity.type == 7 and entity.subtype == 0x37: # Rem
              cutscene_ptr = 0x08012F0C
              all_cutscene_ptrs_for_room.append(cutscene_ptr)
        
        for cutscene_ptr in all_cutscene_ptrs_for_room:
          cutscene = Cutscene(cutscene_ptr, self.rom)
          for command in cutscene.commands:
            if command.type == 0x82:
              item_id = command.arguments[0]
              item_param = 0
              if item_id == 0x3F and len(command.arguments) > 1:
                item_param = command.arguments[1]
            elif command.type == 0x85:
              item_id = command.arguments[0]
              item_param = 0
            elif command.type == 0x83:
              item_id = 0x5C
              item_param = command.arguments[0]
            else:
              continue
            item_name = ITEM_ID_TO_NAME[item_id]
            output.append(
              "Room %02X-%02X: Command at %08X gives item %02X (%02X) - %s" % (
                area_index, room_index, command.command_ptr, item_id, item_param, item_name
              ))
    
    with open("item_locations.txt", "w") as f:
      for line in output:
        f.write(line + "\n")
