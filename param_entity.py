
from collections import OrderedDict

class Property:
  def __init__(self, pretty_name, attribute_name, num_bits):
    self.pretty_name = pretty_name
    self.attribute_name = attribute_name
    self.num_bits = num_bits

class ParamEntity:
  def __init__(self):
    self.property_params = OrderedDict()
    self.properties = OrderedDict()
    
    # Used to keep track of the entity's position in the GUI for entities that do not have an actual position.
    self._dummy_x = 0
    self._dummy_y = 0
  
  def update_params(self):
    self.reset_params()
    
    # This function should be overwritten by child classes to add their own params.
  
  def reset_params(self):
    # First delete any properties that are params.
    for param_name, param_data in self.property_params.items():
      del self.properties[param_name]
    
    # Then clear the params themselves.
    self.property_params.clear()
  
  def add_property(self, attribute_name, num_bits, pretty_name=None):
    if pretty_name is None:
      pretty_name = attribute_name.replace("_", " ")
      pretty_name_words = pretty_name.split()
      pretty_name_words = [
        word[0].upper() + word[1:] # Capitalize first letter of each word
        for word in pretty_name_words
      ]
      pretty_name = " ".join(pretty_name_words)
    
    property = Property(pretty_name, attribute_name, num_bits)
    self.properties[attribute_name] = property
  
  def add_param(self, param_name, params_bitfield_name, bit_mask, pretty_param_name=None):
    for other_param_name, (other_bitfield_name, other_bit_mask) in self.property_params.items():
      if params_bitfield_name == other_bitfield_name and bit_mask & other_bit_mask != 0:
        print("Warning: Param %s overlaps existing param %s" % (param_name, other_param_name))
    
    self.property_params[param_name] = (params_bitfield_name, bit_mask)
    
    _, num_bits = self.get_first_bit_index_and_num_bits(bit_mask)
    
    self.add_property(param_name, num_bits, pretty_name=pretty_param_name)
  
  def add_missing_params_for_bitfields(self, params_bitfields_to_check):
    # Adds parameters that are non-zero yet are not mentioned in the docs.
    unk_param_index = 1
    for params_bitfield_name, num_bits in params_bitfields_to_check:
      unfound_bits = ((1 << num_bits) - 1)
      
      for param_name, (other_params_bitfield_name, bit_mask) in self.property_params.items():
        if params_bitfield_name == other_params_bitfield_name:
          unfound_bits &= ~bit_mask
      if getattr(self, params_bitfield_name) & unfound_bits != 0:
        num_hex_digits = (num_bits+3)//4
        format_string = "%0" + str(num_hex_digits) + "X"
        
        #print("Found unknown parameter:")
        #print(
        #  "  Room: %02X-%02X, type %02X" % (
        #    self.room.area.area_index,
        #    self.room.room_index,
        #    self.type
        #  ))
        #print(
        #  "  %s %s %s" % (
        #    params_bitfield_name,
        #    format_string % unfound_bits,
        #    format_string % getattr(self, params_bitfield_name)
        #  ))
        
        unknown_param_masks = self.split_bit_mask_into_multiple_contiguous_masks(unfound_bits)
        #print("%08X %d %s" % (unfound_bits, len(unknown_param_masks), ["%08X" % unknown_param_mask for unknown_param_mask in unknown_param_masks]))
        for unknown_param_mask in unknown_param_masks:
          if getattr(self, params_bitfield_name) & unknown_param_mask != 0:
            self.add_param("unknown_param_%d" % unk_param_index, params_bitfield_name, unknown_param_mask)
            unk_param_index += 1
  
  def __getattr__(self, attr_name):
    if attr_name in ["property_params", "properties"]:
      return super(self.__class__, self).__getattribute__(attr_name)
    
    if attr_name in self.property_params:
      params_field_name, bit_mask = self.property_params[attr_name]
      params = self.__getattribute__(params_field_name)
      amount_to_shift, _ = self.get_first_bit_index_and_num_bits(bit_mask)
      return ((params & bit_mask) >> amount_to_shift)
    else:
      return super(self.__class__, self).__getattribute__(attr_name)
  
  def __setattr__(self, attr_name, value):
    if attr_name in ["property_params", "properties"]:
      super().__setattr__(attr_name, value)
      return
      
    if attr_name in self.property_params:
      params_field_name, bit_mask = self.property_params[attr_name]
      params = self.__getattribute__(params_field_name)
      amount_to_shift, _ = self.get_first_bit_index_and_num_bits(bit_mask)
      params = (params & (~bit_mask)) | ((value << amount_to_shift) & bit_mask)
      super().__setattr__(params_field_name, params)
    elif attr_name in self.properties:
      prop = self.properties[attr_name]
      value = value & ((1 << prop.num_bits) - 1)
      super().__setattr__(attr_name, value)
    else:
      super().__setattr__(attr_name, value)
  
  @property
  def x(self):
    if "x_pos" in self.properties:
      prop = self.properties["x_pos"]
      return ParamEntity.sign_extend(self.x_pos, prop.num_bits)
    elif "tile_x" in self.properties:
      return self.tile_x*0x10
    elif "center_x" in self.properties:
      prop = self.properties["center_x"]
      return ParamEntity.sign_extend(self.center_x, prop.num_bits)
    else:
      return self._dummy_x
  
  @x.setter
  def x(self, value):
    if "x_pos" in self.properties:
      prop = self.properties["x_pos"]
      value = value & ((1 << prop.num_bits) - 1)
      self.x_pos = value
    elif "tile_x" in self.properties:
      if value < 0:
        value = 0
      if value > 0x3FF:
        value = 0x3FF
      self.tile_x = value//0x10
    elif "center_x" in self.properties:
      prop = self.properties["center_x"]
      value = value & ((1 << prop.num_bits) - 1)
      self.center_x = value
    else:
      self._dummy_x = value
  
  @property
  def y(self):
    if "y_pos" in self.properties:
      prop = self.properties["y_pos"]
      return ParamEntity.sign_extend(self.y_pos, prop.num_bits)
    elif "tile_y" in self.properties:
      return self.tile_y*0x10
    elif "center_y" in self.properties:
      prop = self.properties["center_y"]
      return ParamEntity.sign_extend(self.center_y, prop.num_bits)
    else:
      return self._dummy_y
  
  @y.setter
  def y(self, value):
    if "y_pos" in self.properties:
      prop = self.properties["y_pos"]
      value = value & ((1 << prop.num_bits) - 1)
      self.y_pos = value
    elif "tile_y" in self.properties:
      if value < 0:
        value = 0
      if value > 0x3FF:
        value = 0x3FF
      self.tile_y = value//0x10
    elif "center_y" in self.properties:
      prop = self.properties["center_y"]
      value = value & ((1 << prop.num_bits) - 1)
      self.center_y = value
    else:
      self._dummy_y = value
  
  @staticmethod
  def sign_extend(value, num_bits):
    sign_bit = 1 << (num_bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)
  
  @staticmethod
  def get_first_bit_index_and_num_bits(bit_mask):
    first_bit_index = None
    last_bit_index = None
    for bit_index in range(32):
      bit_is_set = (bit_mask & (1 << bit_index) != 0)
      if first_bit_index is None:
        if bit_is_set:
          first_bit_index = bit_index
      elif last_bit_index is None:
        if not bit_is_set:
          last_bit_index = bit_index-1
      else:
        if bit_is_set:
          raise Exception("Bit mask is not contiguous")
    if first_bit_index is None:
      raise Exception("Invalid bit mask: %08X" % bit_mask)
    if last_bit_index is None:
      last_bit_index = 31
    num_bits = last_bit_index - first_bit_index + 1
    return (first_bit_index, num_bits)
  
  @staticmethod
  def split_bit_mask_into_multiple_contiguous_masks(bit_mask):
    contiguous_bit_masks = []
    
    first_bit_index = None
    num_bits = 0
    for bit_index in range(32):
      bit_is_set = (bit_mask & (1 << bit_index) != 0)
      if bit_is_set:
        num_bits += 1
        if first_bit_index is None:
          first_bit_index = bit_index
      elif first_bit_index is not None:
        contiguous_bit_mask = ((1 << num_bits) - 1) << first_bit_index
        contiguous_bit_masks.append(contiguous_bit_mask)
        first_bit_index = None
        num_bits = 0
    
    if first_bit_index is not None:
      contiguous_bit_mask = ((1 << num_bits) - 1) << first_bit_index
      contiguous_bit_masks.append(contiguous_bit_mask)
    
    return contiguous_bit_masks
