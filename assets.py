
from mclib.data_interface import DataInterface

class AssetList:
  def __init__(self, asset_list_ptr, rom):
    self.asset_list_ptr = asset_list_ptr
    self.rom = rom
    
    self.entries = []
    
    self.gfx_data = DataInterface(b'')
    self.palette_group_index = None
    self.layers = [None, None, None, None]
    self.tileset_datas = [None, None, None, None]
    self.tile_mappings_8x8 = [None, None, None, None]
    self.tileset_tile_types_datas = [None, None, None, None]
    self.collision_layer_datas = [None, None, None, None]
    
    self.read()
  
  def read(self):
    entry_ptr = self.asset_list_ptr
    while True:
      #print("ON: %08X" % entry_ptr)
      entry = AssetEntry(entry_ptr, self.rom)
      self.entries.append(entry)
      
      if entry.type == "palette_group":
        if self.palette_group_index is not None:
          raise Exception("Found more than 1 palette group!")
        
        # TODO: how to handle accessing the entry later?
        self.palette_group_index = entry.properties[0] & 0x0000FFFF
      else:
        rom_address = entry.rom_address
        ram_address = entry.ram_address
        data_length = entry.data_length
        compressed = entry.compressed
        #print("%08X -> %08X (len %04X) (compressed: %s)" % (rom_address, ram_address, data_length, compressed))
        
        # TODO: how to handle accessing the entry later?
        # I guess make these variables point to the entry, not the data of the entry
        if entry.type == "gfx":
          offset = ram_address - 0x06000000
          self.gfx_data.write_raw(offset, entry.raw_data)
        elif entry.type == "layer":
          if self.layers[entry.layer_index] is not None:
            raise Exception("Duplicate layer data for layer BG%d" % entry.layer_index)
          self.layers[entry.layer_index] = entry
        elif entry.type == "tileset":
          if self.tileset_datas[entry.layer_index] is not None:
            raise Exception("Duplicate tileset data for layer BG%d" % entry.layer_index)
          self.tileset_datas[entry.layer_index] = entry.data
        elif entry.type == "mapping":
          if self.tile_mappings_8x8[entry.layer_index] is not None:
            raise Exception("Duplicate 8x8 tile mapping data for layer BG%d" % entry.layer_index)
          self.tile_mappings_8x8[entry.layer_index] = entry.data
        elif entry.type == "tile_types":
          if self.tileset_tile_types_datas[entry.layer_index] is not None:
            raise Exception("Duplicate tile types data for layer BG%d" % entry.layer_index)
          self.tileset_tile_types_datas[entry.layer_index] = entry.data
        elif entry.type == "collision":
          if self.collision_layer_datas[entry.layer_index] is not None:
            raise Exception("Duplicate collision layer data for layer BG%d" % entry.layer_index)
          self.collision_layer_datas[entry.layer_index] = entry.data
      
      if (entry.properties[0] & 0x80000000) == 0:
        break
      
      entry_ptr += 0xC

class AssetEntry:
  def __init__(self, entry_ptr, rom):
    self.entry_ptr = entry_ptr
    self.rom = rom
    
    self.has_unsaved_changes = False
    
    self.read()
  
  def read(self):
    self.properties = self.rom.read(self.entry_ptr, 0xC, "III")
    
    if self.properties[1] == 0:
      self.type = "palette_group"
      self.layer_index = None
    else:
      self.rom_address = (0x08324AE4 + (self.properties[0] & 0x7FFFFFFF))
      self.ram_address = self.properties[1]
      
      if (self.properties[2] & 0x80000000) == 0:
        self.compressed = False
        self.data_length = self.properties[2]
        self.raw_data = self.rom.read_raw(self.rom_address, self.data_length)
      else:
        self.compressed = True
        self.raw_data = self.rom.decompress_read(self.rom_address)
        self.data_length = len(self.raw_data)
      
      if 0x06000000 <= self.ram_address <= 0x0600DFFF: # Tile GFX data
        self.type = "gfx"
        self.layer_index = None
      elif self.ram_address == 0x0200B654: # BG1 layer data
        self.type = "layer"
        self.layer_index = 1
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x02025EB4: # BG2 layer data
        self.type = "layer"
        self.layer_index = 2
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x02012654: # BG1 tileset
        self.type = "tileset"
        self.layer_index = 1
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x0202CEB4: # BG2 tileset
        self.type = "tileset"
        self.layer_index = 2
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x02002F00: # BG1 8x8 tile mapping
        self.type = "mapping"
        self.layer_index = 1
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x02019EE0: # BG2 8x8 tile mapping
        self.type = "mapping"
        self.layer_index = 2
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x0600F000: # BG3 8x8 tile mapping
        self.type = "mapping"
        self.layer_index = 3
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x02010654: # BG1 tileset tile type data
        self.type = "tile_types"
        self.layer_index = 1
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x0202AEB4: # BG2 tileset tile type data
        self.type = "tile_types"
        self.layer_index = 2
        self.data = self.raw_data.read_all_u16s()
      elif self.ram_address == 0x02027EB4: # BG2 collision layer data
        self.type = "collision"
        self.layer_index = 2
        self.data = self.raw_data.read_all_u8s()
      else:
        self.type = "unknown"
        self.layer_index = None
        print(
          "UNKNOWN ASSET TYPE: %08X -> %08X (len: %04X) (compressed: %s)" % (
            self.rom_address, self.ram_address, self.data_length, self.compressed
          ))
  
  def save_any_unsaved_changes(self):
    if self.has_unsaved_changes:
      self.save()
      self.has_unsaved_changes = False
  
  def save(self):
    if self.type == "layer":
      self.rom.compress_write(self.rom_address, self.data.tostring())
