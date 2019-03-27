
class Cutscene:
  def __init__(self, cutscene_ptr, rom):
    self.rom = rom
    self.cutscene_ptr = cutscene_ptr
    
    self.read()
  
  def read(self):
    self.commands = []
    all_checked_command_ptrs = []
    path_starts_to_check = [self.cutscene_ptr]
    while path_starts_to_check:
      command_ptr = path_starts_to_check.pop(0)
      while True:
        possible_end_marker = self.rom.read_u16(command_ptr)
        if possible_end_marker == 0xFFFF:
          break
        if possible_end_marker == 0x0000:
          break
        
        if command_ptr in all_checked_command_ptrs:
          # We looped back to something we already checked, so no need to check it again.
          break
        
        command = Command(command_ptr, self.rom)
        self.commands.append(command)
        all_checked_command_ptrs.append(command_ptr)
        
        #print("%08X: command type %02X, args: " % (command_ptr, command.type) + (", ".join(["%04X" % arg for arg in command.arguments])))
        
        if command.type in [3, 4, 5, 6]:
          offset = command.arguments[0]
          if offset & 0x8000 != 0:
            # Negative, take the 16-bit two's complement
            offset = -((~offset & 0xFFFF) + 1)
          
          if offset == 0:
            raise Exception("Branch offset of zero for command at %08X" % command_ptr)
          
          # The offset is relative to the location of the first argument, not the command itself.
          # So add 2 for the command header, then the offset to get the desired address.
          dest_offset = command_ptr + 2 + offset
          path_starts_to_check.append(dest_offset)
          
          if command.type == 3:
            # 3 is unconditional, so don't keep checking this path.
            break
        elif command.type == 0x47:
          player_script_ptr = command.arguments[0] | (command.arguments[1] << 16)
          path_starts_to_check.append(player_script_ptr)
        
        command_ptr += command.length*2

class Command:
  def __init__(self, command_ptr, rom):
    self.rom = rom
    self.command_ptr = command_ptr
    
    self.read()
  
  def read(self):
    bitfield = self.rom.read_u16(self.command_ptr)
    self.type = bitfield & 0x03FF
    # Command length is in terms of halfwords, and includes this first halfword we just read.
    self.length = (bitfield & 0xFC00) >> 10
    if self.length == 0:
      raise Exception("Found command with length 0 at %08X" % self.command_ptr)
    
    self.arguments = []
    for i in range(1, self.length):
      arg = self.rom.read_u16(self.command_ptr + i*2)
      self.arguments.append(arg)
