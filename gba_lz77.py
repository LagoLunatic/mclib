
import struct
import array

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
    compr_length = read_bytes
    return (decomp, compr_length)
  
  @staticmethod
  def compress(decomp_bytes):
    data_length = len(decomp_bytes)
    if data_length > 0xFFFFFF:
      raise Exception("Data is too long: %X bytes long" % data_length)
    
    comp = array.array("B")
    comp.fromlist([
      0x10,
      (data_length & 0x0000FF),
      (data_length & 0x00FF00) >> 8,
      (data_length & 0xFF0000) >> 16,
    ])
    
    decomp = array.array("B")
    decomp.frombytes(decomp_bytes)
    
    outbuffer = [0]
    buffered_blocks = 0
    read_bytes = 0
    while read_bytes < data_length:
      if buffered_blocks == 8:
        # Reached number of blocks to buffer, so write them.
        comp.fromlist(outbuffer)
        
        outbuffer = [0]
        buffered_blocks = 0
      
      old_length = min(read_bytes, 0x1000)
      occ_length, disp = GBALZ77.get_occurrence_length_and_disp(
        decomp[read_bytes:],
        min(len(decomp[read_bytes:]), 0x12),
        decomp[read_bytes-old_length:],
        old_length
      )
      
      if occ_length < 3:
        # If length is less than 3 it should be uncompressed data.
        outbuffer.append(decomp[read_bytes])
        read_bytes += 1
      else:
        read_bytes += occ_length
        
        outbuffer[0] |= (1 << (7-buffered_blocks))
        
        outbuffer.append(((disp-1) >> 8) & 0x0F) # disp MSBs
        outbuffer[-1] |= (((occ_length-3) << 4) & 0xF0) # number of bytes to copy
        outbuffer.append((disp-1) & 0xFF) # disp LSBs
      
      buffered_blocks += 1
    
    if buffered_blocks > 0:
      # Still have some leftovers in the buffer, so write them.
      comp.fromlist(outbuffer)
    
    return comp.tobytes()
  
  @staticmethod
  def get_occurrence_length_and_disp(new_data, new_length, old_data, old_length):
    if new_length == 0:
      return (0, 0)
    
    disp = 0
    max_length = 0
    
    # Try every possible offset in the already compressed data
    for i in range(old_length):
      current_old_start = i
      
      # Figure out how many bytes can be copied at this offset.
      current_copyable_length = 0
      for j in range(new_length):
        if old_data[current_old_start + j] != new_data[j]:
          break
        current_copyable_length += 1
      
      if current_copyable_length > max_length:
        max_length = current_copyable_length
        disp = old_length - i
        
        if max_length == new_length:
          break
    
    return (max_length, disp)
  
  # Alternate compression method that compresses data slightly more efficiently, but is drastically slower.
  @staticmethod
  def compress_lookahead(decomp_bytes):
    data_length = len(decomp_bytes)
    if data_length > 0xFFFFFF:
      raise Exception("Data is too long: %X bytes long" % data_length)
    
    comp = array.array("B")
    comp.fromlist([
      0x10,
      (data_length & 0x0000FF),
      (data_length & 0x00FF00) >> 8,
      (data_length & 0xFF0000) >> 16,
    ])
    
    decomp = array.array("B")
    decomp.frombytes(decomp_bytes)
    
    outbuffer = [0]
    buffered_blocks = 0
    read_bytes = 0
    
    lengths, disps = GBALZ77.get_optimal_compression_lengths(decomp)
    
    while read_bytes < data_length:
      if buffered_blocks == 8:
        # Reached number of blocks to buffer, so write them.
        comp.fromlist(outbuffer)
        
        outbuffer = [0]
        buffered_blocks = 0
      
      if lengths[read_bytes] == 1:
        outbuffer.append(decomp_bytes[read_bytes])
      else:
        outbuffer[0] |= (1 << (7-buffered_blocks))
        
        disp = disps[read_bytes]
        occ_length = lengths[read_bytes]
        outbuffer.append(((disp-1) >> 8) & 0x0F) # disp MSBs
        outbuffer[-1] |= (((occ_length-3) << 4) & 0xF0) # number of bytes to copy
        outbuffer.append((disp-1) & 0xFF) # disp LSBs
      
      read_bytes += lengths[read_bytes]
      
      buffered_blocks += 1
    
    if buffered_blocks > 0:
      # Still have some leftovers in the buffer, so write them.
      comp.fromlist(outbuffer)
    
    return comp.tobytes()
  
  @staticmethod
  def get_optimal_compression_lengths(decomp):
    data_length = len(decomp)
    
    lengths = [None]*data_length
    disps = [None]*data_length
    min_lengths = [None]*data_length
    
    int_max_value = (1 << 32) - 1
    
    for i in range(data_length-1, 0-1, -1):
      min_lengths[i] = int_max_value
      lengths[i] = 1
      if i + 1 >= data_length:
        min_lengths[i] = 1
      else:
        min_lengths[i] = 1 + min_lengths[i + 1]
      
      old_length = min(i, 0x1000)
      max_len, disps[i] = GBALZ77.get_occurrence_length_and_disp(
        decomp[i:],
        min(len(decomp[i:]), 0x12),
        decomp[i-old_length:],
        old_length
      )
      
      if disps[i] > i:
        raise Exception("Lookahead compression error: Disp is too large")
      
      for j in range(3, max_len+1):
        if i + j >= data_length:
          new_comp_len = 2
        else:
          new_comp_len = 2 + min_lengths[i+j]
        
        if new_comp_len < min_lengths[i]:
          lengths[i] = j
          min_lengths[i] = new_comp_len
    
    return (lengths, disps)
