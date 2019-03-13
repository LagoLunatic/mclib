
from collections import OrderedDict

import os

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

DATA_PATH = "./mclib/data" # TODO

with open(os.path.join(DATA_PATH, "entity_types.txt")) as f:
  ENTITY_TYPE_DOCS = yaml.safe_load(f)

class EntityTypeDocs:
  @staticmethod
  def prettify_prop_value(prop, value, entity):
    num_hex_digits = (prop.num_bits+3)//4
    format_string = "%0" + str(num_hex_digits) + "X"
    pretty_value = format_string % value
    
    if prop.attribute_name == "type" and value in ENTITY_TYPE_DOCS:
      type_data = ENTITY_TYPE_DOCS[value]
      pretty_value += ": " + type_data["name"]
    elif prop.attribute_name == "subtype" and entity.type in ENTITY_TYPE_DOCS:
      type_data = ENTITY_TYPE_DOCS[entity.type]
      if value in type_data["subtypes"]:
        subtype_data = type_data["subtypes"][value]
        pretty_value += ": " + subtype_data["name"]
    
    return pretty_value
