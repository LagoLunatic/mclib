
import struct
import array
from io import BytesIO

from mclib.gba_lz77 import GBALZ77

class DataInterface:
  def __init__(self, data):
    self.data = BytesIO(data)
    
    # TODO orig compressed lengths should be saved with the project
    self.orig_compressed_lengths_by_offset = {}
  
  def __len__(self):
    data_length = self.data.seek(0, 2)
    return data_length
  
  def max_offset(self):
    return len(self)
  
  def copy(self):
    self.data.seek(0)
    copy_data = self.data.read()
    return self.__class__(copy_data)
  
  def read(self, offset, length, format_string):
    self.data.seek(offset)
    requested_data = self.data.read(length)
    unpacked_data = struct.unpack(format_string, requested_data)
    return unpacked_data
  
  def read_bytes(self, offset, length):
    self.data.seek(offset)
    return self.data.read(length)
  
  def read_all_bytes(self):
    self.data.seek(0)
    return self.data.read()
  
  def read_raw(self, offset, length):
    self.data.seek(offset)
    requested_data = self.data.read(length)
    requested_data_interface = DataInterface(requested_data)
    return requested_data_interface
  
  def read_all_u8s(self):
    arr = array.array("B")
    arr.frombytes(self.read_all_bytes())
    return arr
  
  def read_all_u16s(self):
    arr = array.array("H")
    arr.frombytes(self.read_all_bytes())
    return arr
  
  def read_all_u32s(self):
    arr = array.array("I")
    arr.frombytes(self.read_all_bytes())
    return arr
  
  def decompress_read(self, offset):
    self.data.seek(offset)
    # Read everything that remains in the data since we don't yet know how much is compressed
    compressed_data = self.read_bytes(offset, len(self))
    decompressed_data, compr_length = GBALZ77.decompress(compressed_data)
    print("READ %08X %08X" % (offset, compr_length))
    self.orig_compressed_lengths_by_offset[offset] = compr_length
    decompressed_data_interface = DataInterface(decompressed_data)
    return decompressed_data_interface
  
  def compress_write(self, offset, uncompressed_data):
    compressed_data = GBALZ77.compress(uncompressed_data)
    print("WRITE %08X %08X" % (offset, len(compressed_data)))
    orig_compr_len = self.orig_compressed_lengths_by_offset[offset]
    if len(compressed_data) > orig_compr_len:
      # TODO: try to get free space instead of just throwing an error when the new data is larger
      raise Exception(
        "Failed to write compressed data to %08X as the new data is larger than the original.\n" % offset +
        "Orig compressed size: %X\n" % orig_compr_len +
        "New compressed size: %X" % len(compressed_data)
      )
    self.write_bytes(offset, compressed_data)
  
  def write(self, offset, new_values, format_string):
    new_bytes = struct.pack(format_string, *new_values)
    self.data.seek(offset)
    self.data.write(new_bytes)
  
  def write_bytes(self, offset, new_bytes):
    self.data.seek(offset)
    self.data.write(new_bytes)
  
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
  
  def write_u8(self, offset, new_value):
    new_bytes = struct.pack("B", int(new_value))
    self.write_bytes(offset, new_bytes)
  
  def write_u16(self, offset, new_value):
    new_bytes = struct.pack("H", int(new_value))
    self.write_bytes(offset, new_bytes)
  
  def write_u32(self, offset, new_value):
    new_bytes = struct.pack("I", int(new_value))
    self.write_bytes(offset, new_bytes)
  
  def write_float(self, offset, new_value):
    new_bytes = struct.pack("f", int(new_value))
    self.write_bytes(offset, new_bytes)
  
  
  def read_s8(self, offset):
    return self.read(offset, 1, "b")[0]
  
  def read_s16(self, offset):
    return self.read(offset, 2, "h")[0]
  
  def read_s32(self, offset):
    return self.read(offset, 4, "i")[0]


class InvalidAddressError(Exception):
  pass

class RomInterface(DataInterface):
  def is_pointer(self, address):
    if address & 0xFF000000 == 0x08000000:
      return True
    else:
      return False
  
  
  def max_offset(self):
    return len(self) + 0x08000000
  
  def read(self, address, length, format_string):
    if not self.is_pointer(address):
      raise InvalidAddressError("%08X is not a valid ROM address." % address)
    offset = address & 0x00FFFFFF
    return super().read(offset, length, format_string)
  
  def read_bytes(self, address, length):
    if not self.is_pointer(address):
      raise InvalidAddressError("%08X is not a valid ROM address." % address)
    offset = address & 0x00FFFFFF
    self.data.seek(offset)
    return self.data.read(length)
  
  def read_raw(self, address, length):
    if not self.is_pointer(address):
      raise InvalidAddressError("%08X is not a valid ROM address." % address)
    offset = address & 0x00FFFFFF
    return super().read_raw(offset, length)
  
  def decompress_read(self, address):
    return super().decompress_read(address)
  
  def compress_write(self, address, uncompressed_data):
    return super().compress_write(address, uncompressed_data)
  
  def write(self, address, new_values, format_string):
    if not self.is_pointer(address):
      raise InvalidAddressError("%08X is not a valid ROM address." % address)
    offset = address & 0x00FFFFFF
    super().write(offset, new_values, format_string)
  
  def write_bytes(self, address, new_bytes):
    if not self.is_pointer(address):
      raise InvalidAddressError("%08X is not a valid ROM address." % address)
    offset = address & 0x00FFFFFF
    super().write_bytes(offset, new_bytes)
  
  def write_raw(self, address, new_data):
    if not self.is_pointer(address):
      raise InvalidAddressError("%08X is not a valid ROM address." % address)
    offset = address & 0x00FFFFFF
    super().write_raw(offset, new_data)
