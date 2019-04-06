
from mclib.data_interface import DataInterface

class AssetList:
  def __init__(self, asset_list_ptr, rom):
    self.asset_list_ptr = asset_list_ptr
    self.rom = rom
    
    self.gfx_data = DataInterface(b'')
    self.palette_metadata_index = None
    self.layer_datas = [None, None, None, None]
    self.tileset_datas = [None, None, None, None]
    self.tile_mappings_8x8 = [None, None, None, None]
    self.tileset_tile_types_datas = [None, None, None, None]
    self.collision_layer_datas = [None, None, None, None]
    
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
        
        #print("%08X -> %08X (len %04X) (compressed: %s)" % (rom_address, ram_address, len(decompressed_data), compressed))
        
        if 0x06000000 <= ram_address <= 0x0600DFFF: # Tile GFX data
          #print("Tile GFX data")
          offset = ram_address - 0x06000000
          self.gfx_data.write_raw(offset, decompressed_data)
        elif ram_address == 0x0200B654: # BG1 layer data
          #print("Layer data BG1")
          if self.layer_datas[1] is not None:
            raise Exception("Duplicate tile mapping for layer BG1")
          self.layer_datas[1] = decompressed_data
        elif ram_address == 0x02025EB4: # BG2 layer data
          #print("Layer data BG2")
          if self.layer_datas[2] is not None:
            raise Exception("Duplicate tile mapping for layer BG2")
          self.layer_datas[2] = decompressed_data
        elif ram_address == 0x02012654: # BG1 tileset
          #print("tileset BG1")
          if self.tileset_datas[1] is not None:
            raise Exception("Duplicate tileset for layer BG1")
          self.tileset_datas[1] = decompressed_data
        elif ram_address == 0x0202CEB4: # BG2 tileset
          #print("tileset BG2")
          if self.tileset_datas[2] is not None:
            raise Exception("Duplicate tileset for layer BG2")
          self.tileset_datas[2] = decompressed_data
        elif ram_address == 0x02002F00: # BG1 8x8 tile mapping
          #print("8x8 tile mapping BG1")
          if self.tile_mappings_8x8[1] is not None:
            raise Exception("Duplicate tile mapping for layer BG1")
          self.tile_mappings_8x8[1] = decompressed_data
        elif ram_address == 0x02019EE0: # BG2 8x8 tile mapping
          #print("8x8 tile mapping BG2")
          if self.tile_mappings_8x8[2] is not None:
            raise Exception("Duplicate tile mapping for layer BG2")
          self.tile_mappings_8x8[2] = decompressed_data
        elif ram_address == 0x0600F000: # BG3 8x8 tile mapping
          #print("8x8 tile mapping BG3")
          if self.tile_mappings_8x8[3] is not None:
            raise Exception("Duplicate tile mapping for layer BG3")
          self.tile_mappings_8x8[3] = decompressed_data
        elif ram_address == 0x02010654: # BG1 tileset tile type data
          #print("BG1 tile type tileset")
          if self.tileset_tile_types_datas[1] is not None:
            raise Exception("Duplicate BG1 tile type tileset found")
          self.tileset_tile_types_datas[1] = decompressed_data
        elif ram_address == 0x0202AEB4: # BG2 tileset tile type data
          #print("BG2 tile type tileset")
          if self.tileset_tile_types_datas[2] is not None:
            raise Exception("Duplicate BG2 tile type tileset found")
          self.tileset_tile_types_datas[2] = decompressed_data
        elif ram_address == 0x02027EB4: # BG2 collision layer data
          #print("BG2 collision layer data")
          if self.collision_layer_datas[2] is not None:
            raise Exception("Duplicate BG2 collision layer data found")
          self.collision_layer_datas[2] = decompressed_data
        else:
          print(
            "UNKNOWN ASSET TYPE: %08X -> %08X (len: %04X) (compressed: %s)" % (
              rom_address, ram_address, properties[2], compressed
            ))
      
      if (properties[0] & 0x80000000) == 0:
        break
      
      entry_ptr += 0xC
