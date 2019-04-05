import glob
import re
from subprocess import call
import os
import tempfile
import shutil
from collections import OrderedDict
import struct
import yaml
import traceback
from sys import platform

ASM_PATH = "../asm"

if platform == "win32":
  devkitbasepath = r"C:\devkitPro\devkitARM\bin"
else:
  if not "DEVKITARM" in os.environ:
    raise Exception(r"Could not find devkitARM. Path to devkitARM should be in the DEVKITARM env var")
  devkitbasepath = os.environ.get("DEVKITARM") + "/bin"

def get_bin(name):
  suff = ".exe"
  if not platform == "win32":
    return os.path.join(devkitbasepath, name)
  return os.path.join(devkitbasepath, name + ".exe")

if not os.path.isfile(get_bin("arm-none-eabi-as")):
  raise Exception(r"Failed to assemble code: Could not find devkitARM. devkitARM should be installed to: C:\devkitPro\devkitARM")

# Allow yaml to dump OrderedDicts for the diffs.
yaml.CDumper.add_representer(
  OrderedDict,
  lambda dumper, data: dumper.represent_dict(data.items())
)

temp_dir = tempfile.mkdtemp()
print(temp_dir)
print()

custom_symbols = OrderedDict()

try:
  linker_script_path = os.path.join(ASM_PATH, "linker.ld")
  with open(linker_script_path) as f:
    linker_script = f.read()
  
  external_symbols = {}
  for line in linker_script.splitlines():
    symbol_match = re.search(r"^\s*([\._a-z][\._a-z0-9]+)\s+=\s*0x([0-9a-f]+)\s*;\s*$", line, re.IGNORECASE)
    if symbol_match:
      symbol_name = symbol_match.group(1)
      symbol_address = int(symbol_match.group(2), 16)
      external_symbols[symbol_name] = symbol_address
  
  all_asm_file_paths = glob.glob(os.path.join(ASM_PATH, '*.asm'))
  
  for file_path in all_asm_file_paths:
    filename = os.path.basename(file_path)
    print("Assembling " + filename)
    with open(file_path) as f:
      asm = f.read()
    basename = os.path.splitext(filename)[0]
    
    temp_linker_script = linker_script + "\n"
    # Add custom function symbols to the temporary linker script.
    for symbol_name, symbol_address in custom_symbols.items():
      temp_linker_script += "%s = 0x%s;\n" % (symbol_name, symbol_address)
    
    code_chunks = OrderedDict()
    most_recent_org_offset = None
    for line in asm.splitlines():
      line = re.sub(r";.+$", "", line)
      line = line.strip()
      
      org_match = re.match(r"\.org\s+0x([0-9a-f]+)$", line, re.IGNORECASE)
      org_symbol_match = re.match(r"\.org\s+([\._a-z][\._a-z0-9]+)$", line, re.IGNORECASE)
      branch_match = re.match(r"(?:b|beq|bne|blt|bgt|ble|bge)\s+0x([0-9a-f]+)(?:$|\s)", line, re.IGNORECASE)
      bl_to_symbol_match = re.match(r"bl\s+([\._a-z][\._a-z0-9]+)(?:$|\s)", line, re.IGNORECASE)
      if org_match:
        org_offset = int(org_match.group(1), 16)
        code_chunks[org_offset] = ""
        most_recent_org_offset = org_offset
        continue
      elif org_symbol_match:
        if not most_recent_file_path:
          raise Exception("Found .org directive when no file was open")
        
        org_symbol = org_symbol_match.group(1)
        code_chunks[most_recent_file_path][org_symbol] = ""
        most_recent_org_offset = org_symbol
        continue
      elif branch_match:
        # Replace branches to specific addresses with labels, and define the address of those labels in the linker script.
        branch_dest = int(branch_match.group(1), 16)
        branch_temp_label = "branch_label_%X" % branch_dest
        temp_linker_script += "%s = 0x%X;\n" % (branch_temp_label, branch_dest)
        line = re.sub(r"0x" + branch_match.group(1), branch_temp_label, line, 1)
      elif bl_to_symbol_match:
        # Need to replace function calls to external symbols with calls to the exact address of the symbol instead.
        # This is because the linker doesn't seem to be able to tell the external symbols are THUMB functions, so it doesn't work properly.
        symbol_name = bl_to_symbol_match.group(1)
        
        if symbol_name not in external_symbols:
          raise Exception("bl to unknown symbol name: %s" % symbol_name)
        symbol_address = external_symbols[symbol_name]
        
        line = re.sub(
          r"(bl)\s+([\._a-z][\._a-z0-9]+)($|\s)",
          "\\1 0x%08X\\3" % symbol_address,
          line,
          flags=re.IGNORECASE
        )
      elif not line:
        # Blank line
        continue
      
      split_parts = line.split(" ", 1)
      if len(split_parts) > 1:
        opcode, operands = split_parts
        
        operands = operands.strip()
        
        if opcode != "bl" and opcode[0] != ".":
          operands = re.sub(
            r"0x([0-9a-f]+)",
            r"#0x\1",
            operands,
            flags=re.IGNORECASE
          )
          operands = re.sub(
            r"([0-9a-f]+)h(?=$|\]|\,)",
            r"#0x\1",
            operands,
            flags=re.IGNORECASE
          )
        
        if opcode in ["push", "pop"]:
          operands = "{" + operands + "}"
        
        line = opcode + " " + operands
      
      if not most_recent_org_offset:
        raise Exception("Found code before any .org directive")
      
      code_chunks[most_recent_org_offset] += line + "\n"
    
    if not code_chunks:
      raise Exception("No code found")
    
    diffs = OrderedDict()
    for org_offset_or_symbol, temp_asm in code_chunks.items():
      if isinstance(org_offset_or_symbol, int):
        org_offset = org_offset_or_symbol
      else:
        org_symbol = org_offset_or_symbol
        if org_symbol not in custom_symbols:
          raise Exception(".org specified an invalid custom symbol: %s" % org_symbol)
        org_offset = int(custom_symbols[org_symbol], 16)
      
      temp_linker_name = os.path.join(temp_dir, "tmp_linker.ld")
      with open(temp_linker_name, "w") as f:
        f.write(temp_linker_script)
      
      temp_asm_name = os.path.join(temp_dir, "tmp_" + basename + "_%08X.asm" % org_offset)
      with open(temp_asm_name, "w") as f:
        f.write(temp_asm)
      
      o_name = os.path.join(temp_dir, "tmp_" + basename + "_%08X.o" % org_offset)
      command = [
        get_bin("arm-none-eabi-as"),
        "-mcpu=arm7tdmi",
        "-mthumb",
        "-mthumb-interwork",
        temp_asm_name,
        "-o", o_name
      ]
      print(" ".join(command))
      print()
      result = call(command)
      if result != 0:
        raise Exception("Assembler call failed")
      
      elf_name = os.path.join(temp_dir, "tmp_" + basename + "_%08X.elf" % org_offset)
      map_name = os.path.join(temp_dir, "tmp_" + basename + "_%08X.map" % org_offset)
      command = [
        get_bin("arm-none-eabi-ld"),
        "-Ttext", "%X" % org_offset,
        "-T", temp_linker_name,
        "-Map=" + map_name,
        o_name,
        "-o", elf_name
      ]
      print(" ".join(command))
      print()
      result = call(command)
      if result != 0:
        raise Exception("Linker call failed")
      
      bin_name = os.path.join(temp_dir, "tmp_" + basename + "_%08X.bin" % org_offset)
      command = [
        get_bin("arm-none-eabi-objcopy"),
        "-O", "binary",
        elf_name,
        bin_name
      ]
      print(" ".join(command))
      print()
      result = call(command)
      if result != 0:
        raise Exception("Objcopy call failed")
      
      # Keep track of custom symbols so they can be passed in the linker script to future assembler calls.
      with open(map_name) as f:
        on_custom_symbols = False
        for line in f.read().splitlines():
          if line.startswith(" .text          "):
            on_custom_symbols = True
            continue
          
          if on_custom_symbols:
            if not line:
              break
            match = re.search(r" +0x(?:00000000)?([0-9a-f]{8}) +([\._a-z][\._a-z0-9]+)$", line)
            if match:
              symbol_address = match.group(1)
              symbol_name = match.group(2)
              custom_symbols[symbol_name] = symbol_address
              temp_linker_script += "%s = 0x%s;\n" % (symbol_name, symbol_address)
              print("%s = 0x%s;\n" % (symbol_name, symbol_address))
      
      # Keep track of changed bytes.
      if org_offset in diffs:
        raise Exception("Duplicate .org directive: %X" % org_offset)
      
      with open(bin_name, "rb") as f:
        binary_data = f.read()
      
      bytes = list(struct.unpack("B"*len(binary_data), binary_data))
      diffs[org_offset] = bytes
    
    diff_name = basename + "_diff.txt"
    diff_path = os.path.join(ASM_PATH, diff_name)
    with open(diff_path, "w") as f:
      f.write(yaml.dump(diffs, Dumper=yaml.CDumper))
except Exception as e:
  stack_trace = traceback.format_exc()
  error_message = str(e) + "\n\n" + stack_trace
  print(error_message)
  input()
finally:
  shutil.rmtree(temp_dir)

custom_symbols_path = os.path.join(ASM_PATH, "custom_symbols.txt")
with open(custom_symbols_path, "w") as f:
  for symbol_name, symbol_address in custom_symbols.items():
    f.write("%s %s\n" % (symbol_address, symbol_name))
