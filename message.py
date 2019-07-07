
class MessageGroup:
  def __init__(self, group_index, rom):
    self.group_index = group_index
    self.rom = rom
    
    self.read()
  
  def read(self):
    # We can determine the number of messages in this message group by reading the offset of the first message string in this group relative to the start of the group, and dividing by 4.
    # The reason this works is that the start of each group is a list of each message's offset (each is 4 bytes), and the first message's string comes right after the last offset.
    group_offset = self.rom.read_u32(0x089B1D90 + self.group_index*4)
    first_message_offset = self.rom.read_u32(0x089B1D90 + group_offset)
    self.num_messages = first_message_offset//4

class Message:
  def __init__(self, message_id, rom):
    self.message_id = message_id
    self.rom = rom
    
    self.read()
  
  def read(self):
    group_index = (self.message_id & 0xFF00) >> 8
    msg_index = (self.message_id & 0x00FF)
    group_offset = self.rom.read_u32(0x089B1D90 + group_index*4)
    message_offset = self.rom.read_u32(0x089B1D90 + group_offset + msg_index*4)
    self.string_ptr = 0x089B1D90 + group_offset + message_offset
    
    self.read_string()
  
  def read_string(self):
    #print("%04X %s" % (self.message_id, self.string))
    
    self.string = ""
    curr_char_ptr = self.string_ptr
    max_address = self.rom.max_offset()
    while curr_char_ptr < max_address:
      byte = self.rom.read_u8(curr_char_ptr)
      curr_char_ptr += 1
      if byte == 0x00:
        break
      elif byte == 0x01:
        arg = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[%02X %02X]" % (byte, arg)
      elif byte == 0x02:
        color_index = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        self.string += "[Color %01X]" % color_index
      elif byte == 0x03:
        sfx_id = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        sfx_id <<= 8
        sfx_id |= self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        self.string += "[Sound %04X]" % sfx_id
      elif byte == 0x04:
        arg = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        if arg == 0x10:
          arg2 = self.rom.read_u8(curr_char_ptr)
          curr_char_ptr += 1
          
          self.string + "[%02X %02X %02X]" % (byte, arg, arg2)
        else:
          self.string + "[%02X %02X]" % (byte, arg)
      elif byte == 0x05:
        other_message_id = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        if other_message_id == 0xFF:
          self.string += "[Choice %02X]" % other_message_id
        else:
          other_message_id <<= 8
          other_message_id |= self.rom.read_u8(curr_char_ptr)
          curr_char_ptr += 1
          self.string += "[Choice %04X]" % other_message_id
      elif byte == 0x06:
        variable_type = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        if variable_type == 0:
          self.string += "[Player]"
        elif variable_type == 5:
          other_message_id = self.rom.read_u8(curr_char_ptr)
          curr_char_ptr += 1
          other_message_id <<= 8
          
          other_message_id |= self.rom.read_u8(curr_char_ptr)
          curr_char_ptr += 1
          
          self.string += "[Variable %02X %04X]" % (variable_type, other_message_id)
        else:
          self.string += "[Variable %02X]" % variable_type
      elif byte == 0x07:
        other_message_id = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        other_message_id <<= 8
        
        other_message_id |= self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[Message %04X]" % other_message_id
      elif byte == 0x08:
        arg = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[%02X %02X]" % (byte, arg)
      elif byte == 0x09:
        arg = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[%02X %02X]" % (byte, arg)
      elif byte == 0x0A:
        self.string += "\\n\n"
      elif byte == 0x0B:
        arg = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[%02X %02X]" % (byte, arg)
      elif byte == 0x0C:
        arg = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[Button %01X]" % arg
      elif byte == 0x0D:
        arg = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[%02X %02X]" % (byte, arg)
      elif byte == 0x0E:
        arg = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[%02X %02X]" % (byte, arg)
      elif byte == 0x0F:
        symbol_index = self.rom.read_u8(curr_char_ptr)
        curr_char_ptr += 1
        
        self.string += "[Symbol %02X]" % symbol_index
      else:
        char = chr(byte)
        if char == "[":
          char = "\\["
        if char == "]":
          char = "\\]"
        self.string += char
