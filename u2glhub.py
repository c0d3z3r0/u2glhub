#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

__title__       = "U2GLHub"
__description__ = "Python class for talking to Genesys Logic USB hubs via USB vendor commands"
__author__      = "Michael Niewöhner"
__email__       = "foss@mniewoehner.de"
__license__     = 'GPL-2.0-or-later'
__copyright__   = 'Copyright (c) 2024 Michael Niewöhner'

import usb
import sys
import threading
import time
from array import array
from enum import IntEnum
from collections.abc import Iterable

class CMD(IntEnum):
    VERIFY        = 0x71
    READ_XRAM     = 0x72
    WRITE_XRAM    = 0x73
   #UNK_78        = 0x78
    SWITCH        = 0x81
    READ          = 0x82
    WRITE         = 0x83
    SWITCH_SIGNED = 0xa1
    READ_SIGNED   = 0xa2
    WRITE_SIGNED  = 0xa3
    READ_SMBUS    = 0xaa
    WRITE_SMBUS   = 0xab
    HW_SECURITY   = 0xac
   #UNK_BB        = 0xbb

class SUB(IntEnum):
    # READ
    FLASH   = 0x00
    SPI01   = 0x01
    SPI02   = 0x02
    FW_VER  = 0x03
   #READ04  = 0x04
    # SWITCH
    ISP_OFF = 0x00
    ISP_ON  = 0x01
    RESET   = 0x03
    # READ XRAM
    XRAM    = 0x04
    XRAM05  = 0x05

class SPI(IntEnum):
    RDSR    = 0x05
    RDID    = 0x9f
    ERASE   = 0xc7
    # SR
    P_ERR   = (1 << 6)
    E_ERR   = (1 << 5)

class GLHub:

    def __init__(self, idVendor, idProduct):
        self.dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        self._bgthread = None

    def reconnect(self):
        self.dev = usb.core.find(idVendor=self.dev.idVendor, idProduct=self.dev.idProduct)
        if not self.dev:
            raise(Exception("device not found"))

    def ctrl_read(self, request, value=0, index=0, length=0, timeout=1000):
        request_type = usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_IN
        return self.dev.ctrl_transfer(request_type, request, value, index, length)

    def ctrl_write(self, request, value=0, index=0, data=[], timeout=1000):
        if not isinstance(data, Iterable): raise(Exception("data must be iterable"))
        request_type = usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT
        self.dev.ctrl_transfer(request_type, request, value, index, data, timeout)

    def reset(self):
        self.ctrl_write(CMD.SWITCH, SUB.RESET)
        time.sleep(5)
        self.reconnect()

    def read_fw_version(self):
        return self.ctrl_read(CMD.READ, SUB.FW_VER, 0, 2)

    def read_xram(self, addr, length=1):
        return self.ctrl_read(CMD.READ_XRAM, SUB.XRAM, addr, length)

    def write_xram(self, addr, data):
        if not isinstance(data, Iterable): raise(Exception("data must be iterable"))
        for i, v in enumerate(data):
            self.ctrl_write(CMD.WRITE_XRAM, SUB.XRAM, addr + i, [v])

    def read_i2c(self, addr, length):
        return self.ctrl_read(CMD.READ_SMBUS, (addr & 0xff)|1, 0, length)

    def write_i2c(self, addr, data):
        if not isinstance(data, Iterable): raise(Exception("data must be iterable"))
        self.ctrl_write(CMD.WRITE_SMBUS, (addr & 0xfe) | data[0] << 8, 0, data[1:])

    def read_smbus(self, addr, cmd, length):
        return self.ctrl_read(CMD.READ_SMBUS, (addr & 0xff)|1 | (cmd & 0xff) << 8, 0, length)

    def set_isp_mode(self, onoff=False):
        self.ctrl_write(CMD.SWITCH, int(onoff))

    def read_spi(self, cmd, length):
        # TODO: find out why there are two sub functions 0x01, 0x02 (SPI01, SPI02)
        # TODO: additional data (args)
        return self.ctrl_read(CMD.READ, (cmd << 8) | SUB.SPI01, 0, length)

    def write_spi(self, cmd):
        # TODO: find out why there are two sub functions 0x01, 0x02 (SPI01, SPI02)
        # TODO: additional data (args)
        self.ctrl_write(CMD.WRITE, (cmd << 8) | SUB.SPI01, 0)
        self.wait_spi_busy()

    def wait_spi_busy(self):
        while self.read_spi_status() & 1:
            time.sleep(0.01)

        status = self.read_spi_status()
        if status & SPI.P_ERR:
            raise(Exception("SPI program error"))
        elif status & SPI.E_ERR:
            raise(Exception("SPI erase error"))

    def read_spi_id(self):
        return self.read_spi(SPI.RDID, 3)

    def read_spi_status(self):
        return self.read_spi(SPI.RDSR, 1)[0]

    def read_flash(self, addr, length=1):
        data = array('B', [])
        for _addr in range(addr, addr + length, 4096):
            addrh, addrl = (_addr >> 4 & 0xf000), (_addr & 0xffff)
            data += self.ctrl_read(CMD.READ, SUB.FLASH | addrh, addrl, min(4096, length))
            length -= 4096

        return data

    def write_flash(self, addr, data, verify=True):
        for _addr in range(addr, addr+len(data), 4096):
            addrh, addrl = (_addr >> 4 & 0xf000), (_addr & 0xffff)
            self.ctrl_write(CMD.WRITE, SUB.FLASH | addrh, addrl, data[_addr:_addr+4096])
            self.wait_spi_busy()

        # verify
        _data = self.read_flash(addr, len(data))
        if bytes(_data) != bytes(data):
            raise(Exception("SPI flash verification failed"))

    def erase_flash(self):
        self.write_spi(SPI.ERASE)

    def program_flash(self, data):
        self.set_isp_mode(True)
        self.erase_flash()
        self.write_flash(0, data)
        self.reset()

