
import os
import re

from mclib.data_interface import RomInterface
from mclib.area import Area
from mclib.map import Dungeon
from mclib.cutscene import Cutscene
from mclib.docs import ITEM_ID_TO_NAME

class Game:
  def __init__(self, input_rom_path):
    self.input_rom_path = input_rom_path
    
    self.rom = RomInterface(self.input_rom_path)
    
    self.read()
  
  def read(self):
    self.areas = []
    for area_index in range(0x90):
      area = Area(area_index, self.rom)
      self.areas.append(area)
    
    self.dungeons = []
    for dungeon_index in range(7):
      dungeon = Dungeon(dungeon_index, self.rom)
      self.dungeons.append(dungeon)
  
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
        all_cutscenes_for_room = []
        for entity_list in room.entity_lists:
          for entity in entity_list.entities:
            if entity.unknown_3 == 4 or entity.type == 7:
              if entity.params != 0:
                cutscene = Cutscene(entity.params, self.rom)
                all_cutscenes_for_room.append(cutscene)
            if entity.type == 7 and entity.subtype == 3: # Minish
              cutscene_ptr = self.rom.read_u32(0x08109D18 + entity.unknown_4*4)
              cutscene = Cutscene(cutscene_ptr, self.rom)
              all_cutscenes_for_room.append(cutscene)
        
        for cutscene in all_cutscenes_for_room:
          for command in cutscene.commands:
            if command.type in [0x82, 0x85]:
              item_id = command.arguments[0]
              if item_id == 0x3F and len(command.arguments) > 1:
                item_param = command.arguments[1]
              else:
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
