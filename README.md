# U2GLHub

Python class for talking to Genesys Logic USB hubs via USB vendor commands.

Info partly stolen from fwupd's GL plugin, partly from reverse engineering ISP tool and firmware images.

Tested with GL3523, GL3525.

## Documentation

What documentation?! Code is documentation enough! ;-)

## Example usage

```
> import u2glhub
> gl = u2glhub.GLHub(0x17ef, 0x0630)

# read firmware version
> gl.read_fw_version().tobytes()
b'\x18\x11'

# read xram
> gl.read_xram(0x100, 10).tobytes()
b'\x07\x00\x00\x04\x00\x00\x00\x18\x85\x03'

# read flash
> gl.read_flash(0x00, 16).tobytes()
b'\x02P\x8d\x02"kGLHUB\x02b\xe4\x04\xc3'  # yes, it's 8051!

# patch some code in SRAM (yeah, flash gets copied to SRAM on boot \o/)
> hexlify(gl.read_xram(0x4000+0x17dc, 16))
b'7411f080167854761fa852e6ff08e6fd'
> gl.write_xram(0x4000+0x17dd, [0x99])
> hexlify(gl.read_fw_version())
b'1899'

# brick you device (no worries, it has DFU mode!)
> gl.erase_flash()

# flash new firmware
> gl.program_flash(open('gl3525.bin', 'r+b').read())

# dump ram by patching firmware (only works on my specific firmware, you need to modify it for yours!)
> gl.write_xram(0x4000+0x17dc, unhexlify("126BC0"))
> gl.write_xram(0x4000+0x6bc0, unhexlify("785476229022007418f07800907000e6f0a308e870f922"))
> gl.ctrl_read(CMD.READ, SUB.FW_VER, 0, 1)
> hexdump_data(gl.read_xram(0x7000, 0x100))  # custom hexdump function
      00 01 02 03  04 05 06 07  08 09 0a 0b  0c 0d 0e 0f
      -- -- -- --  -- -- -- --  -- -- -- --  -- -- -- --
0000: 00 71 00 01  03 01 00 03  fd b0 57 03  44 02 05 06
0010: 03 03 08 00  00 30 01 03  00 00 00 03  00 00 51 00
0020: 00 5c 11 00  01 03 02 00  00 01 4a 00  20 c0 82 03
0030: 00 00 00 01  00 09 03 0a  00 80 40 00  01 2e 00 09
0040: 00 10 00 00  00 00 1b 03  00 00 01 20  2d 42 04 00
0050: 00 00 f1 1b  22 01 00 43  00 00 00 00  00 00 00 00
0060: 00 00 00 00  00 00 00 00  00 d0 b8 02  00 00 0c 80
0070: 07 07 07 22  00 20 03 03  05 00 00 00  00 00 00 01
0080: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
0090: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
00a0: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
00b0: 00 00 00 00  00 00 00 00  00 b9 58 c0  5b 02 43 89
00c0: 40 11 2e df  17 3f 01 24  fa 9a 99 00  97 15 00 00
00d0: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
00e0: 00 00 00 00  00 00 00 00  00 00 00 00  20 00 20 1f
00f0: 00 03 00 00  00 00 00 01  c0 04 00 ab  2c 00 82 2c

# dump SFRs by patching firmware
data = array.array('B', [])
for addr in range(0,0x100):
    gl.write_xram(0x4000+0x6bc0, unhexlify(f"78547622902200e5{addr:02x}f022"))
    data += gl.ctrl_read(CMD.READ, SUB.FW_VER, 0, 1)
hexdump_data(data)
      00 01 02 03  04 05 06 07  08 09 0a 0b  0c 0d 0e 0f
      -- -- -- --  -- -- -- --  -- -- -- --  -- -- -- --
0000: 00 70 02 01  03 01 00 03  fd b0 57 03  44 02 05 06
0010: 03 03 08 00  00 30 01 03  00 00 00 03  00 00 51 00
0020: 00 5c 11 00  01 03 02 00  00 01 4a 00  20 c0 82 03
0030: 00 00 00 01  00 09 03 0a  00 80 40 00  01 2e 00 09
0040: 00 10 00 00  00 00 1b 03  00 00 01 20  2d 42 04 00
0050: 00 00 f1 1b  22 01 00 43  00 00 00 00  00 00 00 00
0060: 00 00 00 00  00 00 00 00  00 d0 b8 02  00 00 0c 80
0070: 07 07 07 22  00 20 03 03  05 00 00 00  00 00 00 01
0080: 00 c4 82 70  00 00 00 00  40 11 30 1d  ff fc 00 00
0090: 01 00 00 00  00 00 04 00  00 00 02 00  00 00 02 00
00a0: 00 00 00 00  ff ff ff ff  8a 00 00 00  00 00 00 00
00b0: ff 00 00 00  00 00 00 00  0a 00 00 00  00 00 00 00
00c0: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 e7
00d0: 01 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
00e0: e0 00 68 01  00 1f 20 00  00 01 03 00  00 20 00 00
00f0: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00


# dump SFRs by using self-modifying code \o/ (patch MOV A, <reg> in each iteration)
# note: this also dumps iRAM from 0x00-0x7f
gl.write_xram(0x4000+0x17dc, unhexlify("126BC0"))
gl.write_xram(0x4000+0x6bc0, unhexlify("7854762200788079707a0000e890abd7f00089838a82e5fff0a3a983aa820008e870e922"))
gl.ctrl_read(CMD.READ, SUB.FW_VER, 0, 1)
hexdump_data(gl.read_xram(0x7000, 0x100))
      00 01 02 03  04 05 06 07  08 09 0a 0b  0c 0d 0e 0f
      -- -- -- --  -- -- -- --  -- -- -- --  -- -- -- --
0000: 00 70 02 01  03 01 00 03  fd b0 57 03  44 02 05 06
0010: 03 03 08 00  00 30 01 03  00 00 00 03  00 00 51 00
0020: 00 5c 11 00  01 03 02 00  00 01 4a 00  20 c0 82 03
0030: 00 00 00 01  00 09 03 0a  00 80 40 00  01 2e 00 09
0040: 00 10 00 00  00 00 1b 03  00 00 01 20  2d 42 04 00
0050: 00 00 f1 1b  22 01 00 43  00 00 00 00  00 00 00 00
0060: 00 00 00 00  00 00 00 00  00 d0 b8 02  00 00 0c 80
0070: 07 07 07 22  00 20 03 03  05 00 00 00  00 00 00 01
0080: 00 c4 82 70  00 00 00 00  40 11 30 1d  ff fc 00 00
0090: 01 00 00 00  00 00 04 00  00 00 02 00  00 00 02 00
00a0: 00 00 00 00  ff ff ff ff  8a 00 00 00  00 00 00 00
00b0: ff 00 00 00  00 00 00 00  0a 00 00 00  00 00 00 00
00c0: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 e7
00d0: 01 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
00e0: e0 00 68 01  00 1f 20 00  00 01 03 00  00 20 00 00
00f0: 00 00 00 00  00 00 00 00  00 00 00 00  00 00 00 00
```

## License

Copyright (c) 2024 Michael Niewöhner

This is open source software, licensed under GPLv2. See LICENSE file for details.
