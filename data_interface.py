
import struct
from io import BytesIO

from mclib.gba_lz77 import GBALZ77

class DataInterface:
  def __init__(self, data):
    self.data = BytesIO(data)
  
  def __len__(self):
    data_length = self.data.seek(0, 2)
    return data_length
  
  def read(self, offset, length, format_string):
    self.data.seek(offset)
    requested_data = self.data.read(length)
    unpacked_data = struct.unpack(format_string, requested_data)
    return unpacked_data
  
  def read_raw(self, offset, length):
    self.data.seek(offset)
    requested_data = self.data.read(length)
    requested_data_interface = DataInterface(requested_data)
    return requested_data_interface
  
  def decompress_read(self, offset):
    self.data.seek(offset)
    # Read everything that remains in the data since we don't yet know how much is compressed
    compressed_data = self.data.read()
    decompressed_data = GBALZ77.decompress(compressed_data)
    decompressed_data_interface = DataInterface(decompressed_data)
    return decompressed_data_interface
  
  def write_raw(self, offset, new_data):
    self.data.seek(offset)
    new_data.data.seek(0)
    self.data.write(new_data.data.read())
  
  
  def read_u8(self, offset):
    return self.read(offset, 1, "B")[0]
  
  def read_u16(self, offset):
    return self.read(offset, 2, "H")[0]
  
  def read_u32(self, offset):
    return self.read(offset, 4, "I")[0]
  
  def read_float(self, offset):
    return self.read(offset, 4, "f")[0]
  
  
  def read_s8(self, offset):
    return self.read(offset, 1, "b")[0]
  
  def read_s16(self, offset):
    return self.read(offset, 2, "h")[0]
  
  def read_s32(self, offset):
    return self.read(offset, 4, "i")[0]

class InvalidAddressError(Exception):
  pass

class RomInterface(DataInterface):
  def __init__(self, rom_path):
    self.rom_path = rom_path
    
    with open(rom_path, "rb") as file:
      self.data = BytesIO(file.read())
  
  def read(self, address, length, format_string):
    if not self.is_pointer(address):
      raise InvalidAddressError("%08X is not a valid ROM address." % address)
    offset = address-0x08000000
    return super().read(offset, length, format_string)
  
  def read_raw(self, address, length):
    if not self.is_pointer(address):
      raise InvalidAddressError("%08X is not a valid ROM address." % address)
    offset = address-0x08000000
    return super().read_raw(offset, length)
  
  def decompress_read(self, address):
    offset = address-0x08000000
    return super().decompress_read(offset)
  
  def is_pointer(self, address):
    if address >= 0x08000000 and address <= 0x08FFFFFF:
      return True
    else:
      return False
