
import struct

class DecompressionError(Exception):
  pass
class CompressionError(Exception):
  pass

class GBALZ77:
  @staticmethod
  def decompress(compr):
    header = struct.unpack("I", compr[0:4])[0]
    compression_type = header & 0xFF
    uncompressed_size = (header & 0xFFFFFF00) >> 8
    
    if compression_type != 0x10:
      raise DecompressionError("Not LZ77 compressed: %02X" % compression_type)
    
    decomp = []
    decomp_len = 0
    read_bytes = 4
    
    while True:
      type_flags_for_next_8_subblocks = struct.unpack("B", compr[read_bytes:read_bytes+1])[0]
      read_bytes += 1
      
      for subblock_index in range(8):
        if decomp_len == uncompressed_size:
          break
        
        block_type = (type_flags_for_next_8_subblocks >> (7 - subblock_index)) & 1
        
        if block_type == 0: # uncompressed byte
          byte = struct.unpack("B", compr[read_bytes:read_bytes+1])[0]
          decomp.append(byte)
          decomp_len += 1
          read_bytes += 1
        else: # compressed
          subblock = struct.unpack(">H", compr[read_bytes:read_bytes+2])[0]
          read_bytes += 2
          
          backwards_offset  =  subblock & 0b00001111_11111111
          num_bytes_to_copy = (subblock & 0b11110000_00000000) >> 12
          num_bytes_to_copy += 3
          
          pointer = decomp_len - backwards_offset - 1
          for i in range(num_bytes_to_copy):
            #if pointer+i >= decomp_len:
            #  print("%08X" % pointer)
            byte = decomp[pointer+i]
            decomp.append(byte)
            decomp_len += 1
      
      if decomp_len == uncompressed_size:
        break
    
    decomp = struct.pack("B"*decomp_len, *decomp)
    return decomp
