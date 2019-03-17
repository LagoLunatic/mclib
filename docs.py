
from collections import OrderedDict

import os
import re

from mclib.entity import Entity

DATA_PATH = "./mclib/data" # TODO


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
  type_doc_str = f.read()

ENTITY_TYPE_DOCS = OrderedDict()

last_seen_type_doc = None
last_seen_subtype_doc = None
found_forms_header_for_subtype = False
found_form_is_item_id_for_subtype = False
for line_index, line in enumerate(type_doc_str.split("\n")):
  if len(line) == 0:
    continue
  if line[0] == "#":
    continue
  
  type_match = re.search(r"^([0-9A-F]{2}) (.+)$", line, re.IGNORECASE)
  subtype_match = re.search(r"^  ([0-9A-F]{2}) (.+)$", line, re.IGNORECASE)
  forms_header_match = re.search(r"^    Forms:$", line, re.IGNORECASE)
  form_match = re.search(r"^      ([0-9A-F]+) (.+)$", line, re.IGNORECASE)
  form_is_item_id_match = re.search(r"^    Form: The item ID.$", line, re.IGNORECASE)
  if type_match:
    type = int(type_match.group(1), 16)
    type_name = type_match.group(2)
    
    if type in ENTITY_TYPE_DOCS:
      raise Exception("Duplicate doc for entity type %X on line %d" % (type, line_index+1))
    
    type_doc = OrderedDict()
    type_doc["name"] = type_name
    type_doc["subtypes"] = OrderedDict()
    ENTITY_TYPE_DOCS[type] = type_doc
    
    last_seen_type_doc = type_doc
    last_seen_subtype_doc = None
    found_forms_header_for_subtype = False
    found_form_is_item_id_for_subtype = False
  elif subtype_match:
    subtype = int(subtype_match.group(1), 16)
    subtype_name = subtype_match.group(2)
    
    if last_seen_type_doc is None:
      raise Exception("Found subtype doc not under a type on line %d" % (line_index+1))
    if subtype in last_seen_type_doc["subtypes"]:
      raise Exception("Duplicate doc for entity subtype %X on line %d" % (subtype, line_index+1))
    
    subtype_doc = OrderedDict()
    last_seen_type_doc["subtypes"][subtype] = subtype_doc
    subtype_doc["name"] = subtype_name
    subtype_doc["forms"] = OrderedDict()
    
    last_seen_subtype_doc = subtype_doc
    found_forms_header_for_subtype = False
    found_form_is_item_id_for_subtype = False
  elif forms_header_match:
    if last_seen_subtype_doc is None:
      raise Exception("Found forms list doc not under a subtype on line %d" % (line_index+1))
    if found_form_is_item_id_for_subtype:
      raise Exception("Cannot list forms and also have form be the item ID")
    
    found_forms_header_for_subtype = True
  elif form_match:
    form = int(form_match.group(1), 16)
    form_name = form_match.group(2)
    
    if last_seen_subtype_doc is None:
      raise Exception("Found forms list doc not under a subtype on line %d" % (line_index+1))
    if not found_forms_header_for_subtype:
      continue
    if form in last_seen_subtype_doc["forms"]:
      raise Exception("Duplicate doc for entity form %X on line %d" % (form, line_index+1))
    
    form_doc = OrderedDict()
    last_seen_subtype_doc["forms"][form] = form_doc
    form_doc["name"] = form_name
  elif form_is_item_id_match:
    if last_seen_subtype_doc is None:
      raise Exception("Found form is item ID not under a subtype on line %d" % (line_index+1))
    if found_forms_header_for_subtype:
      raise Exception("Cannot list forms and also have form be the item ID")
    
    last_seen_subtype_doc["form_is_item_id"] = True
  else:
    continue

# TODO: implement best sprite frame into new doc format

class Docs:
  @staticmethod
  def prettify_prop_value(prop, value, entity):
    num_hex_digits = (prop.num_bits+3)//4
    format_string = "%0" + str(num_hex_digits) + "X"
    pretty_value = format_string % value
    
    if entity.__class__ == Entity:
      if prop.attribute_name == "type" and value in ENTITY_TYPE_DOCS:
        type_data = ENTITY_TYPE_DOCS[value]
        pretty_value += ": " + type_data["name"]
      elif prop.attribute_name == "subtype" and entity.type in ENTITY_TYPE_DOCS:
        type_data = ENTITY_TYPE_DOCS[entity.type]
        if value in type_data["subtypes"]:
          subtype_data = type_data["subtypes"][value]
          pretty_value += ": " + subtype_data["name"]
      elif prop.attribute_name == "form" and entity.type in ENTITY_TYPE_DOCS:
        type_data = ENTITY_TYPE_DOCS[entity.type]
        if entity.subtype in type_data["subtypes"]:
          subtype_data = type_data["subtypes"][entity.subtype]
          if value in subtype_data["forms"]:
            pretty_value += ": " + subtype_data["forms"][value]["name"]
          elif subtype_data.get("form_is_item_id", False) and value in ITEM_ID_TO_NAME:
            pretty_value += ": " + ITEM_ID_TO_NAME[value]
    
    return pretty_value
  
  @staticmethod
  def get_name_for_entity(entity):
    name = ""
    
    if entity.type in ENTITY_TYPE_DOCS:
      type_data = ENTITY_TYPE_DOCS[entity.type]
      if entity.subtype in type_data["subtypes"]:
        subtype_data = type_data["subtypes"][entity.subtype]
        name += subtype_data["name"]
        if entity.form in subtype_data["forms"]:
          name += " " + subtype_data["forms"][entity.form]["name"]
    
    return name
  
  @staticmethod
  def get_best_sprite_frame(entity):
    if entity.type == 6 and entity.subtype == 8:
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
    
    if entity.type in ENTITY_TYPE_DOCS:
      type_data = ENTITY_TYPE_DOCS[entity.type]
      if entity.subtype in type_data["subtypes"]:
        subtype_data = type_data["subtypes"][entity.subtype]
        if "best_frame" in subtype_data:
          return subtype_data["best_frame"]
    
    return 0
  
  def get_best_sprite_animation(entity):
    if entity.type == 6 and entity.subtype in [0, 2]:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x47:
      return 0x62
    elif entity.type == 4 and entity.subtype == 0x15:
      return entity.form
    elif entity.type == 6 and entity.subtype == 0x25:
      return None
    
    return 0
