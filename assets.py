
from mclib.data_interface import DataInterface

class AssetList:
  def __init__(self, asset_list_ptr, rom):
    self.asset_list_ptr = asset_list_ptr
    self.rom = rom
    
    self.gfx_data = DataInterface(b'')
    self.palette_metadata_index = None
    self.tile_mappings = [None, None]
    
    self.read()
  
  def read(self):
    entry_ptr = self.asset_list_ptr
    while True:
      #print("ON: %08X" % entry_ptr)
      properties = self.rom.read(entry_ptr, 0xC, "III")
      
      if properties[1] == 0:
        # Palette
        if self.palette_metadata_index is not None:
          raise Exception("Found more than 1 palette metadata!")
        
        self.palette_metadata_index = properties[0] & 0x0000FFFF
        #print("Palette: %02X" % self.palette_metadata_index)
      else:
        rom_address = (0x08324AE4 + (properties[0] & 0x7FFFFFFF))
        ram_address = properties[1]
        
        if (properties[2] & 0x80000000) == 0:
          # Uncompressed
          data_length = properties[2]
          decompressed_data = self.rom.read_raw(rom_address, data_length)
          compressed = False
        else:
          # Compressed
          decompressed_data = self.rom.decompress_read(rom_address)
          compressed = True
        
        #print(compressed)
        #print("%08X" % rom_address)
        
        if ram_address >= 0x06000000 and ram_address <= 0x06FFFFFF: # Tile GFX data
          #print(f"Tile GFX data: %08X -> %08X (len %04X) (compressed: {compressed})" % (rom_address, ram_address, len(decompressed_data)))
          offset = ram_address - 0x06000000
          self.gfx_data.write_raw(offset, decompressed_data)
        elif ram_address == 0x02025EB4: # BG1 8x8 tile mappings
          #print(f"8x8 tile mapping BG1: %08X -> %08X (compressed: {compressed})" % (rom_address, ram_address))
          if self.tile_mappings[0] is not None:
            raise Exception("Duplicate tile mapping for layer BG1")
          self.tile_mappings[0] = decompressed_data
        elif ram_address == 0x0200B654: # BG2 tile mappings
          #print(f"8x8 tile mapping BG2: %08X -> %08X (compressed: {compressed})" % (rom_address, ram_address))
          if self.tile_mappings[1] is not None:
            raise Exception("Duplicate tile mapping for layer BG2")
          self.tile_mappings[1] = decompressed_data
        elif ram_address == 0x0202CEB4: # BG1 16x16 tile mappings
          #print(f"16x16 tile mapping BG1: %08X -> %08X (compressed: {compressed})" % (rom_address, ram_address))
          if self.tile_mappings[0] is not None:
            raise Exception("Duplicate tile mapping for layer BG1")
          self.tile_mappings[0] = decompressed_data
        elif ram_address in [0x02012654, 0x02019EE0]: # BG2 16x16 tile mappings
          #print(f"16x16 tile mapping BG2: %08X -> %08X (compressed: {compressed})" % (rom_address, ram_address))
          if self.tile_mappings[1] is not None:
            raise Exception("Duplicate tile mapping for layer BG2")
          self.tile_mappings[1] = decompressed_data
        else:
          pass
          # TODO:
          #print(f"UNKNOWN ASSET TYPE: %08X -> %08X (len: %04X) (compressed: {compressed})" % (rom_address, ram_address, properties[2]))
          # unknowns found in area 00:
          # 0832EAF0 -> 0202AEB4 (len: 80001000) (compressed: True)
          # 0832EF20 -> 02010654 (len: 80000FFC) (compressed: True)
          # unknowns found in area 03:
          # 08385130 -> 0202AEB4 (len: 80001000) (compressed: True)
          # 08385748 -> 02010654 (len: 80000FFC) (compressed: True)
          # unknowns found in room 20-09:
          # 0847ED74 -> 02027EB4 (len: 80000159) (compressed: True)
          # 0847A370 -> 02019EE0 (len: 80001000) (compressed: True)
      
      if (properties[0] & 0x80000000) == 0:
        break
      
      entry_ptr += 0xC
