
from collections import OrderedDict

import os
import re

from mclib.entity import Entity

DATA_PATH = "./mclib/data" # TODO

with open(os.path.join(DATA_PATH, "entity_types.txt")) as f:
  type_doc_str = f.read()

ENTITY_TYPE_DOCS = OrderedDict()

last_seen_type_doc = None
last_seen_subtype_doc = None
found_forms_header_for_subtype = False
for line_index, line in enumerate(type_doc_str.split("\n")):
  if len(line) == 0:
    continue
  if line[0] == "#":
    continue
  
  type_match = re.search(r"^([0-9A-F]{2}) (.+)$", line, re.IGNORECASE)
  subtype_match = re.search(r"^  ([0-9A-F]{2}) (.+)$", line, re.IGNORECASE)
  forms_header_match = re.search(r"^    Forms:$", line, re.IGNORECASE)
  form_match = re.search(r"^      ([0-9A-F]+) (.+)$", line, re.IGNORECASE)
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
  elif forms_header_match:
    if last_seen_subtype_doc is None:
      raise Exception("Found forms list doc not under a subtype on line %d" % (line_index+1))
    
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
  else:
    continue

# TODO: implement best sprite frame into new doc format

class EntityTypeDocs:
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
    
    return pretty_value
  
  @staticmethod
  def get_best_sprite_frame(entity):
    if entity.type in ENTITY_TYPE_DOCS:
      type_data = ENTITY_TYPE_DOCS[entity.type]
      if entity.subtype in type_data["subtypes"]:
        subtype_data = type_data["subtypes"][entity.subtype]
        if "best_frame" in subtype_data:
          return subtype_data["best_frame"]
    
    return 0
