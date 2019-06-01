
from collections import OrderedDict

import os
import re

from mclib.entity import Entity
from mclib.tile_entity import TileEntity

from paths import DATA_PATH

import string

ALLOWED_ATTR_NAME_CHARS = string.ascii_letters + string.digits + "_"

def parse_doc(doc_str):
  doc_dict = OrderedDict()
  doc_dict["name"] = "ROOT"
  doc_dict["children"] = OrderedDict()
  doc_dict["properties"] = OrderedDict()
  last_entry_by_indent = OrderedDict()
  last_entry_by_indent[-1] = doc_dict
  for line_index, line in enumerate(doc_str.split("\n")):
    line_num = line_index + 1
    
    if not line.strip():
      continue
    
    index_value_match = re.search(r"^( *)([0-9A-F]+) (.*)$", line, re.IGNORECASE)
    property_match = re.search(r"^( *)(.+?)(?: - |: )(.+)$$", line, re.IGNORECASE)
    value_list_start_match = re.search(r"^( *)([^:]+):$", line, re.IGNORECASE)
    if index_value_match:
      indent_spaces = index_value_match.group(1)
      key = int(index_value_match.group(2), 16)
      value = index_value_match.group(3)
      is_property = False
    elif property_match:
      indent_spaces = property_match.group(1)
      key = property_match.group(2)
      value = property_match.group(3)
      is_property = True
    elif value_list_start_match:
      indent_spaces = value_list_start_match.group(1)
      key = value_list_start_match.group(2)
      value = None
      is_property = True
    else:
      #print(line_num)
      #print("??? TODO")
      continue
    
    indent_level = (len(indent_spaces) + 1) // 2
    
    parent_indent_level = indent_level - 1
    if parent_indent_level not in last_entry_by_indent:
      continue
    parent = last_entry_by_indent[parent_indent_level]
    
    new_entry = OrderedDict()
    if is_property:
      parent["properties"][key] = new_entry
    else:
      parent["children"][key] = new_entry
    new_entry["name"] = value
    new_entry["children"] = OrderedDict()
    new_entry["properties"] = OrderedDict()
    last_entry_by_indent[indent_level] = new_entry
  
  return doc_dict


AREA_INDEX_TO_NAME = {}
with open(os.path.join(DATA_PATH, "area_names.txt"), "r") as f:
  matches = re.findall(r"^([0-9a-f]{2}) (.*)$", f.read(), re.IGNORECASE | re.MULTILINE)
for area_index, area_name in matches:
  area_index = int(area_index, 16)
  AREA_INDEX_TO_NAME[area_index] = area_name


ITEM_ID_TO_NAME = {}
ITEM_NAME_TO_ID = {}
with open(os.path.join(DATA_PATH, "item_names.txt"), "r") as f:
  matches = re.findall(r"^([0-9a-f]{2}) (.+)$", f.read(), re.IGNORECASE | re.MULTILINE)
for item_id, item_name in matches:
  if item_name:
    item_id = int(item_id, 16)
    ITEM_ID_TO_NAME[item_id] = item_name
    if item_name in ITEM_NAME_TO_ID:
      raise Exception("Duplicate item name: " + item_name)
    ITEM_NAME_TO_ID[item_name] = item_id


with open(os.path.join(DATA_PATH, "entity_types.txt")) as f:
  entity_doc_str = f.read()
ENTITY_TYPE_DOCS = parse_doc(entity_doc_str)

with open(os.path.join(DATA_PATH, "tile_entity_types.txt")) as f:
  tile_entity_doc_str = f.read()
TILE_ENTITY_TYPE_DOCS = parse_doc(tile_entity_doc_str)

class Docs:
  @staticmethod
  def prettify_prop_value(prop, value, entity):
    num_hex_digits = (prop.num_bits+3)//4
    format_string = "%0" + str(num_hex_digits) + "X"
    pretty_value = format_string % value
    
    if isinstance(entity, Entity):
      type_list = ENTITY_TYPE_DOCS["children"]
      if prop.attribute_name == "type" and value in type_list:
        type_data = type_list[value]
        pretty_value += ": " + type_data["name"]
      elif prop.attribute_name == "subtype" and entity.type in type_list:
        type_data = type_list[entity.type]
        if value in type_data["children"]:
          subtype_data = type_data["children"][value]
          pretty_value += ": " + subtype_data["name"]
      elif prop.attribute_name == "form" and entity.type in type_list:
        type_data = type_list[entity.type]
        if entity.subtype in type_data["children"]:
          subtype_data = type_data["children"][entity.subtype]
          if "Forms" in subtype_data["properties"] and value in subtype_data["properties"]["Forms"]["children"]:
            pretty_value += ": " + subtype_data["properties"]["Forms"]["children"][value]["name"]
          elif subtype_data["properties"].get("Form", {}).get("name") == "The item ID." and value in ITEM_ID_TO_NAME:
            pretty_value += ": " + ITEM_ID_TO_NAME[value]
          elif subtype_data["properties"].get("Form", {}).get("name") == "A room property index." and value in entity.room.property_pointers:
            pretty_value += ": %08X" % entity.room.property_pointers[value]
    elif isinstance(entity, TileEntity):
      type_list = TILE_ENTITY_TYPE_DOCS["children"]
      if prop.attribute_name == "type" and value in type_list:
        type_data = type_list[value]
        pretty_value += ": " + type_data["name"]
      elif prop.attribute_name == "item_id" and value in ITEM_ID_TO_NAME:
        pretty_value += ": " + ITEM_ID_TO_NAME[value]
    
    return pretty_value
  
  @staticmethod
  def get_name_for_entity(entity):
    name = ""
    
    if isinstance(entity, Entity):
      type_list = ENTITY_TYPE_DOCS["children"]
      if entity.type in type_list:
        type_data = type_list[entity.type]
        if entity.subtype in type_data["children"]:
          subtype_data = type_data["children"][entity.subtype]
          name += subtype_data["name"]
          if "Forms" in subtype_data["properties"] and entity.form in subtype_data["properties"]["Forms"]["children"]:
            name += " " + subtype_data["properties"]["Forms"]["children"][entity.form]["name"]
    
    return name
  
  @staticmethod
  def get_entity_param_properties(entity):
    properties = []
    
    if isinstance(entity, Entity):
      type_list = ENTITY_TYPE_DOCS["children"]
      if entity.type in type_list:
        type_data = type_list[entity.type]
        properties += Docs.extract_param_properties_from_doc_list(type_data["properties"])
        if entity.subtype in type_data["children"]:
          subtype_data = type_data["children"][entity.subtype]
          properties += Docs.extract_param_properties_from_doc_list(subtype_data["properties"])
          if "Forms" in subtype_data["properties"] and entity.form in subtype_data["properties"]["Forms"]["children"]:
            form_data = subtype_data["properties"]["Forms"]["children"][entity.form]
            properties += Docs.extract_param_properties_from_doc_list(form_data["properties"])
    elif isinstance(entity, TileEntity):
      type_list = TILE_ENTITY_TYPE_DOCS["children"]
      if entity.type in type_list:
        type_data = type_list[entity.type]
        properties += Docs.extract_param_properties_from_doc_list(type_data["properties"])
    
    return properties
  
  @staticmethod
  def extract_param_properties_from_doc_list(properties_doc_list):
    properties = []
    
    for prop_str, prop_data in properties_doc_list.items():
      match = re.search(r"^([a-z_][a-z0-9_]*) *& *([0-9a-f]{1,8})$", prop_str, re.IGNORECASE)
      if match:
        bitfield_name = match.group(1).lower()
        bitmask = int(match.group(2), 16)
        
        prop_name = prop_data["name"]
        if prop_name is None:
          continue
        prop_name = prop_name.replace(" ", "_").lower()
        prop_name = "".join(
          char for char in prop_name
          if char in ALLOWED_ATTR_NAME_CHARS
        )
        if len(prop_name) == 0:
          continue
        if prop_name[0] in string.digits:
          continue
        
        pretty_name = prop_data["name"]
        pretty_name = pretty_name.replace(".", "")
        pretty_name_words = pretty_name.split()
        pretty_name_words = [
          word[0].upper() + word[1:] # Capitalize first letter of each word
          for word in pretty_name_words
        ]
        pretty_name = " ".join(pretty_name_words)
        
        properties.append((prop_name, bitfield_name, bitmask, pretty_name))
    
    return properties
  
  @staticmethod
  def get_best_sprite_frame(entity):
    if entity.type == 6 and entity.subtype in [8, 0x6C]:
      # Door
      frame_index = entity.form & 0x03
      if ((entity.form & 0x0C) >> 2) == 2:
        # Small key door
        frame_index |= 4
      return frame_index
    elif entity.type == 6 and entity.subtype == 0x2D:
      return 0x1A
    elif entity.type == 6 and entity.subtype == 0x16:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x46:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x6D and entity.form <= 5:
      return [0, 2, 4, 3, 7, 5][entity.form]
    elif entity.type == 6 and entity.subtype == 0x4F:
      return entity.unknown_4
    elif entity.type == 6 and entity.subtype == 0x6F:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x4E:
      return entity.unknown_4
    elif entity.type == 6 and entity.subtype == 0x5D:
      if entity.form <= 5:
        frame_index = [0xFF, 0xFF, 0, 0, 2, 2][entity.form]
        if frame_index != 0xFF:
          return frame_index
      return entity.unknown_4
    elif entity.type == 3 and entity.subtype == 6:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0xBC:
      return None
    elif entity.type == 6 and entity.subtype == 0xA1:
      return entity.unknown_4
    elif entity.type == 6 and entity.subtype == 0x60:
      return entity.form
    elif entity.type == 7 and entity.subtype == 0x13:
      if entity.form <= 5:
        return [
          0x00,
          0x00,
          0x00,
          0x01,
          0x01,
          0x00,
        ][entity.form]
    elif entity.type == 7 and entity.subtype == 0x0B:
      # TODO: correct behavior is to grab the current animation's current frame index and add 0x10
      return 0x10
    elif entity.type == 6 and entity.subtype == 0x9D and entity.form == 1:
      return 3
    elif entity.type == 6 and entity.subtype == 0x71:
      return entity.form
    
    if entity.type in ENTITY_TYPE_DOCS:
      type_data = ENTITY_TYPE_DOCS[entity.type]
      if entity.subtype in type_data["subtypes"]:
        subtype_data = type_data["subtypes"][entity.subtype]
        if "best_frame" in subtype_data:
          return subtype_data["best_frame"]
    
    return 0
  
  @staticmethod
  def get_best_sprite_head_frame(entity):
    if entity.type != 7:
      return None
    
    if entity.subtype == 7:
      if entity.form <= 8:
        return [
          0x19,
          0x25,
          0x2E,
          0x37,
          0x40,
          0x48,
          0x78,
          0x83,
          0x8B
        ][entity.form] + 4
    elif entity.subtype == 6:
      if entity.form <= 0x14:
        return [
          0x00,
          0x08,
          0x80,
          0x88,
          0x18,
          0x20,
          0x90,
          0x98,
          0x40,
          0x48,
          0x68,
          0x70,
          0xA0,
          0x50,
          0x78,
          0x10,
          0x28,
          0x30,
          0x38,
          0x58,
          0x60
        ][entity.form] + 4
    elif entity.subtype == 3:
      return 0x1C
    elif entity.subtype == 0x34:
      return 0xF
    elif entity.subtype in [8, 0x15]:
      return 0x46
    elif entity.subtype == 0x38:
      return 0x1C
    elif entity.subtype == 0x49:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index
      return 7
    elif entity.subtype == 0x48:
      return 3
    elif entity.subtype == 0x13:
      if entity.form <= 5:
        return [
          0x04,
          0x0C,
          0x14,
          0x1C,
          0x24,
          0x2C,
        ][entity.form] + 5
    elif entity.subtype == 0x46:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index
      return 0xB
    elif entity.subtype == 0x53:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index and add 8
      return 8
    elif entity.subtype == 0x0B:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index&7F and add 1A (or if that value is 0, don't add anything)
      return 0x1B
    elif entity.subtype == 0x16:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index&7F and add A (or if that value is 0, don't add anything)
      return 0xB
    elif entity.subtype == 0x11:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index&3F
      return 8
    elif entity.subtype == 0x2D:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index&1F and add 4
      return 4
    elif entity.subtype == 0x2F:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index&1F
      return 0xA
    elif entity.subtype == 0x1D:
      # TODO: correct behavior is to grab the current keyframe's extra_frame_index&7 and add B
      return 0xB
    
    return None
  
  @staticmethod
  def get_best_sprite_accessory_frame(entity):
    if entity.type != 7:
      return None
    
    if entity.subtype == 0x48:
      return 6
    elif entity.subtype == 0x15:
      return 0x1F
    
    return None
  
  @staticmethod
  def get_best_extra_sprite_frames_for_entity(entity):
    if entity.type != 7:
      return None
    
    frames = [
      Docs.get_best_sprite_head_frame(entity),
      Docs.get_best_sprite_accessory_frame(entity),
    ]
    frames = [frame for frame in frames if frame is not None]
    
    return frames
  
  @staticmethod
  def get_best_sprite_animation(entity):
    if entity.type == 6 and entity.subtype in [0, 2, 0x40, 0xAC]:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x47:
      return 0x62
    elif entity.type == 4 and entity.subtype == 0x15:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x25:
      return None
    elif entity.type == 6 and entity.subtype == 5:
      return 5
    elif entity.type == 6 and entity.subtype == 0x6B and entity.form == 3:
      return 0xC
    elif entity.type == 6 and entity.subtype == 0x41:
      return 0xA
    elif entity.type == 6 and entity.subtype == 0x6A and entity.form == 7:
      return 0x5B
    elif entity.type == 6 and entity.subtype == 0x6A and entity.form == 0x12:
      return 0x5C
    elif entity.type == 6 and entity.subtype == 0x6A and entity.form == 8:
      return 2
    elif entity.type == 6 and entity.subtype == 0x14:
      return 9
    elif entity.type == 6 and entity.subtype == 0x39:
      return entity.form & 0x1F
    elif entity.type == 3 and entity.subtype == 1:
      return 2
    elif entity.type == 6 and entity.subtype == 0x55:
      anim_index = 4
      if entity.unknown_5 <= 3:
        anim_index += [1, 2, 0, 0][entity.unknown_5]
        anim_index += [4, 0, 4, 0][entity.unknown_5]
      return anim_index
    elif entity.type == 6 and entity.subtype == 0x38:
      if entity.unknown_4 == 0:
        return 0
      else:
        return 1
    elif entity.type == 6 and entity.subtype == 0x8C:
      return entity.form + 0x39
    elif entity.type == 3 and entity.subtype == 0x3A:
      return 5
    elif entity.type == 3 and entity.subtype == 0x35:
      return 3
    elif entity.type == 3 and entity.subtype == 9:
      return entity.form & 0x03
    elif entity.type == 3 and entity.subtype == 0x14:
      return 1
    elif entity.type == 3 and entity.subtype == 0x4E:
      if entity.form == 0:
        return 1
      else:
        return 9
    elif entity.type == 3 and entity.subtype == 2:
      return 2
    elif entity.type == 6 and entity.subtype == 0xC0:
      return entity.unknown_5
    elif entity.type == 7 and entity.subtype == 0x31:
      return entity.unknown_4
    elif entity.type == 3 and entity.subtype == 0x2E:
      return 1
    elif entity.type == 7 and entity.subtype == 7:
      return None
    elif entity.type == 7 and entity.subtype == 6:
      return None
    elif entity.type == 6 and entity.subtype == 0xF:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x9F:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x7F:
      anim_index = entity.unknown_4
      if entity.form <= 5:
        anim_index += [
          3,
          0,
          3,
          3,
          3,
          3,
        ][entity.form]
      return anim_index
    elif entity.type == 7 and entity.subtype == 3:
      return 2
    elif entity.type == 7 and entity.subtype == 0x15:
      return 2
    elif entity.type == 7 and entity.subtype == 0x49:
      return 2
    elif entity.type == 7 and entity.subtype == 0x13:
      return None
    elif entity.type == 7 and entity.subtype == 0x0B:
      return None
    elif entity.type == 7 and entity.subtype == 0x16:
      return 2
    elif entity.type == 7 and entity.subtype == 0x45:
      return 2
    elif entity.type == 7 and entity.subtype == 0x52:
      return 2
    elif entity.type == 7 and entity.subtype == 0x25:
      return 2
    elif entity.type == 7 and entity.subtype == 0x22:
      return 2
    elif entity.type == 7 and entity.subtype == 0x2D:
      return 2
    elif entity.type == 7 and entity.subtype == 0x1D:
      return 2
    elif entity.type == 7 and entity.subtype == 0x2B and entity.form == 1:
      return 4
    
    return 0
  
  @staticmethod
  def get_best_sprite_offset(entity):
    if entity.type == 6 and entity.subtype == 5:
      return (0, 3)
    elif entity.type == 3 and entity.subtype == 0x3A:
      return (0, 3)
    
    return (0, 0)
