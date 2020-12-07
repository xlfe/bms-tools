#!/usr/bin/env python

import serial
import time
import struct
import threading
import sys
from enum import Enum
from functools import partial

__all__ = 'JBD'

class Unit(Enum):
    MV  = ('millivolt', 'mV')
    V   = ('volt', 'V')
    C   = ('Celsius', '°C')
    S   = ('second', 's')
    K   = ('Kelvin', 'K')
    MA  = ('milliampere', 'mA')
    MAH = ('milliampere hour', 'mAh')
    AH  = ('ampere hour', 'Ah')
    A   = ('ampere', 'A')
    PCT = ('percent', '%')
    MO  = ('milliohms', 'mΩ')

    def __init__(self, long_name, symbol):
        self.long_name = long_name
        self.symbol = symbol

def hexDump(d):
    print(' '.join(f'{i:02X}' for i in d))
    
class LabelEnum(Enum):
    def __new__(cls, display, value):
        obj = object.__new__(cls)
        obj.val = value
        obj.display = display
        return obj

    def __str__(self):
        return str(self.display)

    @classmethod
    def byDisplay(cls, value):
        for v in cls:
            if value == v.display:
                return v
        return None

    @classmethod
    def byValue(cls, value):
        for v in cls:
            if value == v.val:
                return v
        return None

class Dsgoc2Enum(LabelEnum):
    _8MV  = (8,   0x0)
    _11MV = (11,  0x1)
    _14MV = (14 , 0x2)
    _17MV = (17 , 0x3)
    _19MV = (19 , 0x4)
    _22MV = (22 , 0x5)
    _25MV = (25 , 0x6)
    _28MV = (28 , 0x7)
    _31MV = (31 , 0x8)
    _33MV = (33 , 0x9)
    _36MV = (36 , 0xa)
    _39MV = (39 , 0xb)
    _42MV = (42 , 0xc)
    _44MV = (44 , 0xd)
    _47MV = (47 , 0xe)
    _50MV = (50 , 0xf)

class Dsgoc2DelayEnum(LabelEnum):
    _8MS    = (8,    0x0)
    _20MS   = (20,   0x1)
    _40MS   = (40,   0x2)
    _80MS   = (80,   0x3)
    _160MS  = (160,  0x4)
    _320MS  = (320,  0x5)
    _640MS  = (640,  0x6)
    _1280MS = (1280, 0x7)

class ScEnum(LabelEnum):
    _22MV  = (22,  0x0)
    _33MV  = (33,  0x1)
    _44MV  = (44,  0x2)
    _56MV  = (56,  0x3)
    _67MV  = (67,  0x4)
    _78MV  = (78,  0x5)
    _89MV  = (89,  0x6)
    _100MV = (100, 0x7)

class ScDelayEnum(LabelEnum):
    _70US  = (70,  0x0) 
    _100US = (100, 0x1) 
    _200US = (200, 0x2) 
    _400US = (400, 0x3) 

class CuvpHighDelayEnum(LabelEnum):
    _1S  = (1,  0x0)
    _4S  = (4,  0x1)
    _8S  = (8,  0x2)
    _16S = (16, 0x3)

class CovpHighDelayEnum(LabelEnum):
    _1S  = (1,  0x0)
    _2S  = (2,  0x1)
    _4S  = (4,  0x2)
    _8S  = (8,  0x3)

class BaseReg:
    'register base class; mostly exists for documenting methods and properties'

    @property 
    def regName(self):
        'get name of register'
        return self._regName

    @property
    def valueNames(self):
        'return a list of values this register covers'
        return self._valueNames

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.regName}>'

    @property
    def unit(self, valueName):
        'return the unit for this value'
        raise NotImplementedError()

    @property
    def adx(self):
        'get the address of the register'
        return self._adx

    def get(self, valueName):
        'return a single value'
        raise NotImplementedError()

    def set(self, valueName, value):
        'set a single value'
        raise NotImplementedError()

    def unpack(self, payload):
        'extract value(s) from register payload and store internally'
        raise NotImplementedError()

    def pack(self):
        'return a device-compatible payload from the current value(s)'
        raise NotImplementedError()

    def __getitem__(self, valueName):
        return self.get(valueName)
       
    def __setitem__(self, valueName, value):
        return self.set(valueName, value)

    def _toDict(self):
        return {k:self.get(k) for k in self.valueNames}

    def keys(self):
        return self._toDict().keys()

    def values(self):
        return self._toDict().values()

    def items(self):
        return self._toDict().items()

class ReadOnlyException(RuntimeError): pass
class ReadOnlyMixin:
    def set(self, valueName, value):
        raise ReadOnlyException(f'{self._regName} is read-only')

    def pack(self):
        raise ReadOnlyException(f'{self._regName} is read-only')


class IntReg(BaseReg): 
    def __init__(self, regName, adx, unit, factor, range=(-32768, 32768)):
        self._regName = regName
        self._adx = adx
        self._unit = unit
        self._value = 0
        self._factor = factor # multiplier for (un)packing
        assert type(range) in (list, tuple) and len(range) == 2 and all([type(i) == int for i in range])
        self.range = tuple((i * factor for i in range))
        if self.range[0] >= 0:
            self.format = '>H'
        else:
            self.format = '>h'

    @property
    def valueNames(self):
        return [self._regName]
    
    @property
    def unit(self, valueName):
        if not valueName == self._regName:
            raise KeyError(f'unknown value name {valuename}')
        return self._unit

    def get(self, valueName): 
        if not valueName == self._regName:
            raise KeyError(f'unknown value name {valueName}')
        return self._value
    
    def set(self, valueName, value):
        if not valueName == self._regName:
            raise KeyError(f'unknown value name {valuename}')
        value = value or 0
        try:
            value = float(value)
            if value < self.range[0] or value > self.range[1]:
                raise ValueError(f'value {repr(value)} is outside of range {self.range}')
        except Exception as e:
            raise ValueError(f'value {repr(value)} is not valid for {self.__class__.__name__}')
        self._value = value

    def unpack(self, payload):
        self._value = struct.unpack(self.format, payload)[0] * self._factor

    def pack(self):
        return struct.pack(self.format, int(self._value // self._factor))

    def __str__(self):
        return f'{self._regName}: {self._value}'

class TempReg(IntReg):
    'actual temperatures on device are stored as Kelvin * 10'
    def __init__(self, valueName, adx):
        super().__init__(valueName, adx, Unit.C, 0)

    def set(self, valueName, value):
        if not valueName == self._regName:
            raise KeyError(f'unknown value name {valuename}')
        try:
            value = float(value)
            if not -273.15 <= value <= 6136.4: # maps to 0 --> 65535
                raise ValueError(f'value {repr(value)} is outside of range(-32768, 327670)')
        except:
            raise ValueError(f'value {repr(value)} is not valid for {self.__class__.__name__}')
        self._value = value

    @staticmethod
    def unpackTemp(payload):
        return (struct.unpack('>H', payload)[0] - 2731) / 10

    @staticmethod
    def packTemp(value):
        return struct.pack('>H', int(value) * 10 + 2731)
    
    def unpack(self, payload):
        self._value = self.unpackTemp(payload)

    def pack(self):
        return self.packTemp(self._value)

class TempRegRO(TempReg, ReadOnlyMixin): pass

class ErrorCountReg(ReadOnlyMixin, BaseReg):
    def __init__(self, regName, adx):
        self._regName = regName
        self._adx = adx

        valueNames = 'sc chgoc dsgoc covp cuvp chgot chgut dsgot dsgut povp puvp'.split()
        self._values = {n+'_err_cnt':0 for n in valueNames}

    @property
    def valueNames(self):
        return self._values.keys()
    
    @property
    def unit(self):
        return int

    def __str__(self):
        ', '.join(f'{k}: {v}' for k,v in self._values.items())
    
    def get(self, valueName):
        return self._values[valueName]
    
    def unpack(self, payload):
        values = struct.unpack('>11H', payload)
        self._values = dict(zip(self._values.keys(), values))

class DelayReg(BaseReg):
    'class that deals with registers that store two time values, in seconds'

    def __init__(self, regName, adx, name1, name2):
        self._regName = regName
        self._adx = adx
        self._values = {name1: 0, name2: 0}

    def get(self, valueName):
        return self._values[valueName]

    def set(self, valueName, value):
        if valueName not in self._values:
            raise KeyError(valueName)
        value = value or 0
        try:
            value = int(value)
            if not 0 <= value <= 255:
                raise ValueError(f'value {repr(value)} is outside of range(0, 255)')
        except:
            raise ValueError(f'value {repr(value)} is not valid for {self.__class__.__name__}')
        self._values[valueName] = value

    def __str__(self):
        return ', '.join(f'{k}: {v}' for k,v in self._values.items())

    @property
    def valueNames(self):
        return self._values.keys()

    def unpack(self, payload):
        values = struct.unpack('>2B', payload)
        self._values = dict(zip(self._values.keys(), values))

    def pack(self):
        return struct.pack('>2B', *self._values.values())


class BitfieldReg(BaseReg):
    def __init__(self, regName, adx, *fields):
        'fields are in order, from bit 0'
        self._regName = regName
        self._adx = adx
        self._values = {f:False for f in fields}

    @property
    def valueNames(self):
        return self._values.keys()
        
    def get(self, valueName):
        return self._values[valueName]
    
    def set(self, valueName, value):
        if valueName not in self._values:
            raise KeyError(valueName)
        self._values[valueName] = bool(value)

    def unpack(self, payload):
        value = struct.unpack('>H', payload)[0]
        for i, valueName in enumerate(self._values.keys()):
            self._values[valueName] = bool(value & (1 << i))

    def pack(self):
        value = 0
        for i, valueName in enumerate(self._values.keys()):
            if self._values[valueName]:
                value |= (1 << i)
        return struct.pack('>H', value)

class StringReg(BaseReg):
    def __init__(self, regName, adx, maxLen = 30):
        self._regName = regName
        self._adx = adx

    @property
    def valueNames(self):
        return [self._regName]

    def get(self, valueName):
        if not valueName == self._regName:
            raise KeyError(f'unknown value name {valuename}')
        return self._value

    def set(self, valueName, value):
        if not valueName == self._regName:
            raise KeyError(f'unknown value name {valuename}')

        if type(value) not in (str, bytes, bytearray):
            raise ValueError(f'value should be str, byte, or bytearray')
        if len(value) > 30:
            raise ValueError(f'string length should not exceed 30')

        self._value = value

    def pack(self):
        l = len(self._value)
        return struct.pack(f'>B{l}s', l, bytes(self._value, 'utf-8'))

    def unpack(self, payload):
        l = payload[0]
        self._value = str(payload[1:1+l], 'utf-8')

    def __str__(self):
        return f'{self._regName}: {self._value}'

class DateReg(BaseReg):
    _valueNames = ('year', 'month', 'day')
    def __init__(self, regName, adx):
        self._regName = regName
        self._adx = adx
        self._year = 0
        self._month = 0
        self._day = 0
        self._yearRange = range(2000,2128)
        self._monthRange = range(1,13)
        self._dayRange = range(1,32)

    def get(self, valueName):
        if valueName not in self._valueNames:
            raise KeyError(valueName)
        return getattr(self, '_'+valueName)
    
    def set(self, valueName, value):
        if valueName not in self._valueNames:
            raise KeyError(valueName)
        value = int(value)
        if value not in getattr(self, f'_{valueName}Range'):
            raise ValueError(f'invalid value for {valueName}: {repr(value)}')
        setattr(self, '_'+valueName, value)

    def __str__(self):
        return f'{self.year}-{self.month}-{self.day}'

    @staticmethod
    def unpackDate(payload):
        value = struct.unpack('>H', payload)[0]
        day = value & 0x1f
        value >>= 5
        month = value & 0xf
        value >>= 4
        year = (value & 0x7f) + 2000
        return year, month, day

    @staticmethod
    def packDate(year, month, day):
        value = (year - 2000) & 0x7f
        value <<= 4
        value |= month
        value <<= 5
        value |= day
        return struct.pack('>H', value)

    def unpack(self, payload):
        self._year, self._month, self._day = self.unpackDate(payload)
    
    def pack(self):
        return self.packDate(self._year, self._month, self._day)

class ScDsgoc2Reg(BaseReg):
    _valueNames = ('sc', 'sc_delay', 'dsgoc2', 'dsgoc2_delay', 'sc_dsgoc_x2')
    def __init__(self, regName, adx):
        self._regName = regName
        self._adx = adx
        self._sc = ScEnum._22MV
        self._sc_delay = ScDelayEnum._70US
        self._dsgoc2 = Dsgoc2Enum._8MV
        self._dsgoc2_delay = Dsgoc2DelayEnum._8MS
        self._sc_dsgoc_x2 = False
    
    def get(self, valueName):
        if valueName not in self._valueNames:
            raise KeyError(valueName)
        return getattr(self, '_'+valueName)

    def set(self, valueName, value):
        if valueName == 'sc':
            if  value not in ScEnum:
                raise ValueError(value)
            self._sc = value
        elif valueName == 'sc_delay':
            if value not in ScDelayEnum:
                raise ValueError(value)
            self._sc_delay = value
        elif valueName == 'dsgoc2':
            if value not in Dsgoc2Enum:
                raise ValueError(value)
            self._dsgoc2 = value
        elif valueName == 'dsgoc2_delay':
            if value not in Dsgoc2DelayEnum:
                raise ValueError(value)
            self._dsgoc2_delay = value
        elif valueName == 'sc_dsgoc_x2':
            self._sc_dsgoc_x2 = bool(value)
        else:
            raise KeyError(valueName)

    def unpack(self, payload):
        b1, b2 = struct.unpack('>BB', payload)

        self._sc_dsgoc_x2 = bool(b1 & 0x80)

        sc = b1 & 0x7
        sc_delay = (b1 >> 3) & 0x3

        self._sc = ScEnum.byValue(sc) or ScEnum._22MV
        self._sc_delay = ScDelayEnum.byValue(sc_delay) or ScDelayEnum._70US

        dsgoc2_delay = b2 >> 4
        dsgoc2 = b2 & 0xf

        self._dsgoc2 = Dsgoc2Enum.byValue(dsgoc2) or Dsgoc2Enum._8MV
        self._dsgoc2_delay = Dsgoc2DelayEnum.byValue(dsgoc2_delay) or Dsgoc2DelayEnum._8MS

    def pack(self):
        x2 = 0x80 if self._sc_dsgoc_x2 else 0
        b1 = self._sc.val | (self._sc_delay.val << 3) | x2
        b2 = (self._dsgoc2_delay.val << 4) | self._dsgoc2.val
        return struct.pack('>BB', b1, b2)

class CxvpHighDelayScRelReg(BaseReg):
    _valueNames = ('cuvp_high_delay', 'covp_high_delay', 'sc_rel')
    def __init__(self, regName, adx):
        self._regName = regName
        self._adx = adx

        self._cuvp_high_delay = CuvpHighDelayEnum._1S
        self._covp_high_delay = CovpHighDelayEnum._1S
        self._sc_rel = 0

    def get(self, valueName):
        if valueName not in self._valueNames:
            raise KeyError(valueName)
        return getattr(self, '_'+valueName)

    def set(self, valueName, value):
        if valueName == 'cuvp_high_delay':
            if value not in CuvpHighDelayEnum:
                raise ValueError(value)
            self._cuvp_high_delay = value
        elif valueName == 'covp_high_delay':
            if value not in CovpHighDelayEnum:
                raise ValueError(value)
            self._covp_high_delay = value
        elif valueName == 'sc_rel':
            value = value or 0
            value = int(value)
            if value not in range(256):
                raise ValueError(value)
            self._sc_rel = value
        else:
            raise KeyError(valueName)

    def unpack(self, payload):
        b1, self._sc_rel = struct.unpack('>BB', payload)
        cuvp_high_delay = b1 >> 6
        covp_high_delay = (b1 >> 4) & 0x3
        self._cuvp_high_delay = CuvpHighDelayEnum.byValue(cuvp_high_delay) or CuvpHighDelayEnum._1S
        self._covp_high_delay = CovpHighDelayEnum.byValue(covp_high_delay) or CovpHighDelayEnum._1S
    
    def pack(self):
        b1 = (self._cuvp_high_delay.val) << 6
        b1 |= (self._covp_high_delay.val) << 4
        return struct.pack('>BB', b1, self._sc_rel)

class BasicInfoReg(BaseReg):
    _balBits = [f'bal{i}' for i in range(32)]
    _faultBits = [f'{i}_err' for i in 'covp cuvp povp puvp chgot chgut dsgot dsgut chgoc dsgoc sc afe software'.split() ]
    _ntcFields = [f'ntc{i}' for i in range(8)]
    _fetBits = 'chg_fet_en', 'dsg_fet_en'
    _valueNames = [
        'pack_mv', 'pack_ma', 'cap_rem', 
        'cap_nom', 'cycle_cnt', 
        'year', 'month', 'day',
        *_balBits,
        *_faultBits,
        'version',
        'cap_pct',
        *_fetBits,
        'ntc_cnt',
        'cell_cnt',
        *_ntcFields
    ]

    def __init__(self, regName, adx):
        self._regName = regName
        self._adx = adx
    
    def get(self, valueName):
        if valueName not in self._valueNames:
            raise KeyError(valueName)
        return getattr(self, '_'+valueName)

    @staticmethod
    def _unpackBits(fields, value):
        ret = []
        for bit, field in enumerate(fields):
            ret.append(('_'+field,  bool(value & (1 << bit))))
        return ret

    def unpack(self, payload):
        offset = 0
        fmt = '>HhHHH2s'
        values = struct.unpack_from(fmt, payload, offset)
        self._pack_mv, self._pack_ma, self._cap_rem, self._cap_nom, self._cycle_cnt, date_raw = values
        self._pack_mv *= 10
        self._pack_ma *= 10
        self._cap_rem *= 10
        self._cap_nom *= 10
        self._year, self._month, self._day = DateReg.unpackDate(date_raw)
        offset += struct.calcsize(fmt)

        fmt = '>LHBBBBB'
        values = struct.unpack_from(fmt, payload, offset)
        bal_raw, fault_raw, self._version, self._cap_pct, fet_raw, self._cell_cnt, self._ntc_cnt = values
        for fn, value in self._unpackBits(self._balBits, bal_raw):
            setattr(self, fn, value)
        for fn, value in self._unpackBits(self._faultBits, fault_raw):
            setattr(self, fn, value)
        for fn, value in self._unpackBits(self._fetBits, fet_raw):
            setattr(self, fn, value)
        offset += struct.calcsize(fmt)

        for i in range(8):
            fn = f'_ntc{i}'
            if i < self._ntc_cnt:
                o = offset + i *2
                setattr(self, fn, TempReg.unpackTemp(payload[o:o+2]))
            else:
                setattr(self, fn, None)


class CellInfoReg(BaseReg):
    def __init__(self, regName, adx):
        self._regName = regName
        self._adx = adx
        self._cellCnt = 0
        self._values = []

    @property
    def valueNames(self):
        return [f'cell{i}_mv' for i in range(self._cellCnt)]

    def unpack(self, payload):
        self._cellCnt = len(payload) // 2
        self._values = struct.unpack(f'>{self._cellCnt}H', payload)

    def get(self, valueName):
        if valueName not in self.valueNames:
            raise KeyError(valueName)

        d = ''.join([i for i in valueName if i.isdigit()])
        return self._values[int(d)]

class DeviceInfoReg(BaseReg):
    _valueNames = ['device_name']
    def __init__(self, regName, adx):
        self._regName = regName
        self._adx = adx

    def get(self, valueName):
        if valueName not in self._valueNames:
            raise KeyError(valueName)
        return getattr(self, '_'+valueName, None)

    def unpack(self, payload):
        try:
            self._device_name = str(payload, 'utf-8')
        except UnicodeDecodeError:
            self._device_name = payload
        

class JBDPersist:
    pass

    
#savefile_fields =  [
#    #'FileCode' __unknown__ 3838
#    ('DesignCapacity', ('design_ca,) int)           # reg
#    ('CycleCapacity', ('cycle_ca,) int)             # reg
#    ('FullChargeVol', ('cap_10,) int)               # reg
#    ('ChargeEndVol', ('cap_,) int)                  # reg
#    ('DischargingRate', ('dsg_rat,) int)            # reg
#    ('ManufactureDate', ('mfg_dat,) int)            # reg
#    ('SerialNumber', ('serial_nu,) int)             # reg
#    ('CycleCount', ('cycle_cn,) int)                # reg
#    ('ChgOverTemp', ('chgo,) int)                   # reg
#    ('ChgOTRelease', ('chgot_re,) int)              # reg
#    ('ChgLowTemp', ('chgu,) int)                    # reg
#    ('ChgUTRelease', ('chgut_re,) int)              # reg
#    ('DisOverTemp', ('dsgo,) int)                   # reg
#    ('DsgOTRelease', ('dsgot_re,) int)              # reg
#    ('DisLowTemp', ('dsgut') ,                   # reg
#    ('DsgUTRelease', ('dsgut_re,) int)              # reg
#    ('PackOverVoltage', ('pov,) int)                # reg
#    ('PackOVRelease', ('povp_re,) int)              # reg
#    ('PackUnderVoltage', ('puv,) int)               # reg
#    ('PackUVRelease', ('puvp_re,) int)              # reg
#    ('CellOverVoltage', ('cov,) int)                # reg
#    ('CellOVRelease', ('covp_re,) int)              # reg
#    ('CellUnderVoltage', ('cuv,) int)               # reg
#    ('CellUVRelease', ('cuvp_re,) int)              # reg
#    ('OverChargeCurrent', ('chgo,) int)             # reg
#    ('OverDisCurrent', ('dsgo,) int)                # reg
#    ('BalanceStartVoltage', ('bal_star,) int)       # reg
#    ('BalanceWindow', ('bal_windo,) int)            # reg
#    ('SenseResistor', ('current_re,) int)           # reg
#    ('BatteryConfig', ('func_confi,) int)           # reg
#    ('NtcConfig', ('ntc_confi,) int)                # reg
#    ('PackNum', ('cell_cn,) int)                    # reg
#    ('fet_ctrl_time_set', ('fet_ctr,) int)          # reg
#    ('led_disp_time_set', ('led_time,) int)         # reg
#    ('VoltageCap80', ('cap_8,) int)                 # reg
#    ('VoltageCap60', ('cap_6,) int)                 # reg
#    ('VoltageCap40', ('cap_4,) int)                 # reg
#    ('VoltageCap20', ('cap_2,) int)                 # reg
#    ('HardCellOverVoltage', ('covp_hig,) int)       # reg
#    ('HardCellUnderVoltage', ('cuvp_hig,) int)      # reg
#
#    ('HardChgOverCurrent', ( 'sc,: ('sc_dela,': ('sc_dsgoc2)', int)
#    ('HardDsgOverCurrent', ('dsgoc2,: ('dsgoc2_del'), int)
#
#    ('HardTime', ('covp_high_delay,: ('cuvp_high_del'), int)
#    ('SCReleaseTime', ('sc_re,) int)
#
#
#    ('ChgUTDelay', ('chgut_dela,) int)              # field
#    ('ChgOTDelay', ('chgot_dela,) int)              # field
#    ('DsgUTDelay', ('dsgut_dela,) int)              # field
#    ('DsgOTDelay', ('dsgot_dela,) int)              # field
#    ('PackUVDelay', ('puvp_dela,) int)              # field
#    ('PackOVDelay', ('povp_dela,) int)              # field
#    ('CellUVDelay', ('cuvp_dela,) int)              # field
#    ('CellOVDelay', ('covp_dela,) int)              # field
#    ('ChgOCDelay', ('chgoc_dela,) int)              # field
#    ('ChgOCRDelay', ('chgoc_re,) int)               # field
#    ('DsgOCDelay', ('dsgoc_dela,) int)              # field
#    ('DsgOCRDelay', ('dsgoc_re,) int)               # field
#
#    ('ManufacturerName', ('mfg_nam,) int)           # reg
#    ('DeviceName', ('device_nam,) int)              # reg
#    ('BarCode', ('barcod,) int)                     # reg
#]


class BMSError(Exception): pass

class JBD:
    START           = 0xDD
    END             = 0x77
    READ            = 0xA5
    WRITE           = 0x5A

    def __init__(self, s, timeout = 3, debug = False):
        self.s = s
        try:
            self.s.close()
            s.timeout=0.5
        except: 
            pass
        self._open_cnt = 0
        self._lock = threading.RLock()
        self.timeout = timeout
        self.debug = debug

        self.eeprom_regs = [
            ### EEPROM settings
            ## Settings
            # Basic Parameters
            IntReg('covp', 0x24, Unit.MV, 1),
            IntReg('covp_rel', 0x25, Unit.MV, 1),
            IntReg('cuvp', 0x26, Unit.MV, 1),
            IntReg('cuvp_rel', 0x27, Unit.MV, 1),
            IntReg('povp', 0x20, Unit.MV, 10),
            IntReg('povp_rel', 0x21, Unit.MV, 10),
            IntReg('puvp', 0x22, Unit.MV, 10),
            IntReg('puvp_rel', 0x23, Unit.MV, 10),
            TempReg('chgot', 0x18),
            TempReg('chgot_rel', 0x19),
            TempReg('chgut', 0x1a),
            TempReg('chgut_rel', 0x1b),
            TempReg('dsgot', 0x1c),
            TempReg('dsgot_rel', 0x1d),
            TempReg('dsgut', 0x1e),
            TempReg('dsgut_rel', 0x1f),
            IntReg('chgoc', 0x28, Unit.MA, 10),
            IntReg('dsgoc', 0x29, Unit.MA, 10),
            DelayReg('cell_v_delays', 0x3d, 'cuvp_delay', 'covp_delay'),
            DelayReg('pack_v_delays', 0x3c, 'puvp_delay', 'povp_delay'),
            DelayReg('chg_t_delays', 0x3a, 'chgut_delay', 'chgot_delay'),
            DelayReg('dsg_t_delays', 0x3b, 'dsgut_delay', 'dsgot_delay'),
            DelayReg('chgoc_delays', 0x3e, 'chgoc_delay', 'chgoc_rel'),
            DelayReg('dsgoc_delays', 0x3f, 'dsgoc_delay', 'dsgoc_rel'),

            # High Protection Configuration
            IntReg('covp_high', 0x36, Unit.MV, 1),
            IntReg('cuvp_high', 0x37, Unit.MV, 1),
            ScDsgoc2Reg('sc_dsgoc2', 0x38),
            CxvpHighDelayScRelReg('cxvp_high_delay_sc_rel', 0x39),

            # Function Configuration
            BitfieldReg('func_config', 0x2d, 'switch', 'scrl', 'balance_en', 'chg_balance_en', 'led_en', 'led_num'),

            # NTC Configuration
            BitfieldReg('ntc_config', 0x2e, *(f'ntc{i+1}' for i in range(8))),

            # Balance Configuration
            IntReg('bal_start', 0x2a, Unit.MV, 1),
            IntReg('bal_window', 0x2b, Unit.MV, 1),

            # Other Configuration
            IntReg('shunt_res', 0x2c, Unit.MO, .1),
            IntReg('cell_cnt', 0x2f, int, 1),
            IntReg('cycle_cnt', 0x17, int, 1),
            IntReg('serial_num', 0x16, int, 1),
            StringReg('mfg_name', 0xa0),
            StringReg('device_name', 0xa1),
            StringReg('barcode', 0xa2),
            DateReg('mfg_date', 0x15),

            # Capacity Config
            IntReg('design_cap', 0x10, Unit.MAH, 10), 
            IntReg('cycle_cap', 0x11, Unit.MAH, 10),
            IntReg('dsg_rate', 0x14, Unit.PCT, .1), # presuming this means rate of self-discharge
            IntReg('cap_100', 0x12, Unit.MV, 1), # AKA "Full Chg Vol"
            IntReg('cap_80', 0x32, Unit.MV, 1),
            IntReg('cap_60', 0x33, Unit.MV, 1),
            IntReg('cap_40', 0x34, Unit.MV, 1),
            IntReg('cap_20', 0x35, Unit.MV, 1),
            IntReg('cap_0', 0x13, Unit.MV, 1), # AKA "End of Dsg VOL"
            IntReg('fet_ctrl', 0x30, Unit.S, 1),
            IntReg('led_timer', 0x31, Unit.S, 1),

            # Errors
            ErrorCountReg('error_cnts', 0xaa),
        ]
        self.eeprom_reg_by_valuename = {}
        for reg in self.eeprom_regs:
            map = {k:reg for k in reg.valueNames}
            self.eeprom_reg_by_valuename.update(map)

        self.basicInfoReg = BasicInfoReg('basic_info', 0x03)
        self.cellInfoReg = CellInfoReg('cell_info', 0x04)
        self.deviceInfoReg = DeviceInfoReg('device_info', 0x05)

    @staticmethod
    def toHex(data):
        return ' '.join([f'{i:02X}' for i in data])

    def dbgPrint(self, *args, **kwargs):
        kwargs['file'] = sys.stderr
        if self.debug:
            print(*args, **kwargs)

    @property
    def port(self):
        return s
    
    @port.setter
    def port(self, s):
        self.s = s 

    def open(self):
        if not self._open_cnt:
            self._lock.acquire()
            self.s.open()
        self._open_cnt += 1
    
    def close(self):
        if not self._open_cnt: 
            return
        self._open_cnt -= 1
        if not self._open_cnt:
            self.s.close()
            self._lock.release()

    @staticmethod
    def chksum(payload):
        return 0x10000 - sum(payload)

    def extractPayload(self, data):
        assert len(data) >= 7
        datalen = data[3]
        data = data[4:4+datalen]
        self.dbgPrint('extractPayload returning', self.toHex(data))
        return data

    def cmd(self, op, reg, data):

        payload = [reg, len(data)] + list(data)
        chksum = self.chksum(payload)
        data = [self.START, op] + payload + [chksum, self.END]
        format = f'>BB{len(payload)}BHB'
        return struct.pack(format, *data) 

    def readCmd(self, reg, data  = []):
        return self.cmd(self.READ, reg, data)

    def writeCmd(self, reg, data = []):
        return self.cmd(self.WRITE, reg, data)

    def readPacket(self):
        then = time.time() + self.timeout
        d = []
        msgLen = 0
        complete = False
        while then > time.time():
            byte = self.s.read()
            if not byte: break
            byte = byte[0]
            d.append(byte)
            if len(d) == 4:
                msgLen = d[-1]
            if byte == 0x77 and len(d) == 7 + msgLen: 
                complete = True
                break
        if d and complete:
            self.dbgPrint('readPacket:', self.toHex(d))
            ok = not d[2]
            return ok, self.extractPayload(bytes(d))
        self.dbgPrint(f'readPacket failed with {len(d)} bytes')
        return False, None

    def enterFactory(self):
        try:
            self.open()
            cnt = 5
            while cnt:
                cmd = self.writeCmd(0, [0x56, 0x78])
                self.s.write(cmd)
                ok, x = self.readPacket()
                if ok and x is not None: # empty payload is valid
                    self.dbgPrint('pong')
                    return x
                self.dbgPrint('no response')
                cnt -= 1
                time.sleep(.3)
            return False
        finally:
            self.close()

    def exitFactory(self, clearErrors = False):
        try:
            self.open()
            cmd = self.writeCmd(1,  [0x28, 0x28] if clearErrors else [0,0])
            self.s.write(cmd)
            ok, d = self.readPacket()
            return ok
        finally:
            self.close()

    def readEeprom(self, progressFunc = None):
        try:
            self.open()
            self.enterFactory()
            ret = {}
            numRegs = len(self.eeprom_regs)
            if progressFunc: progressFunc(0)

            for i, reg in enumerate(self.eeprom_regs):
                cmd = self.readCmd(reg.adx)
                self.s.write(cmd)
                ok, payload = self.readPacket()
                if not ok: raise BMSError()
                if payload is None: raise TimeoutError()
                if progressFunc: progressFunc(int(i / (numRegs-1) * 100))
                reg.unpack(payload)
                ret.update(dict(reg))
            self.exitFactory()
            return ret
        finally:
            self.close()

    def writeEeprom(self, data, progressFunc = None):
        try:
            self.open()
            self.enterFactory()
            ret = {}
            numRegs = len(self.eeprom_regs)
            if progressFunc: progressFunc(0)
            regs = set()

            for valueName, value in data.items():
                reg = self.eeprom_reg_by_valuename.get(valueName)
                if not reg: raise RuntimeError(f'unknown valueName {valueName}')
                try:
                    reg.set(valueName, value)
                    regs.add(reg)
                except ReadOnlyException:
                    print(f'skipping read-only valueName {valueName}')

            toWrite = set('ntc1 led_en covp covp_rel covp_delay design_cap cycle_cap cap_100 cap_80 cap_60 cap_40 cap_20 cap_0'.split())
            
            for i,reg in enumerate(regs):
                if toWrite & set(reg.valueNames) or 1:
                    print('reg', reg.regName)
                    data = reg.pack()
                    cmd = self.writeCmd(reg.adx, data)
                    self.s.write(cmd)
                    ok, payload = self.readPacket()
                    if not ok: raise BMSError()
                    if payload is None: raise TimeoutError()
                    hexDump(cmd)
                if progressFunc: progressFunc(int(i / (numRegs-1) * 100))
        finally:
            self.close()

    def loadEepromFile(self, f):
        pass

    def readBasicInfo(self):
        try:
            self.open()
            self.exitFactory()
            cmd = self.readCmd(self.basicInfoReg.adx)
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            self.basicInfoReg.unpack(payload)
            return dict(self.basicInfoReg)
        finally:
            self.close()

    def readCellInfo(self):
        try:
            self.open()
            self.exitFactory()
            cmd = self.readCmd(cellInfoReg.adx)
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            cellInfoReg.unpack(payload)
            return dict(cellInfoReg)
        finally:
            self.close()

    def readDeviceInfo(self):
        try:
            self.open()
            self.exitFactory()
            cmd = self.readCmd(deviceInfoReg.adx)
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            deviceInfoReg.unpack(payload)
            return dict(deviceInfoReg)
        finally:
            self.close()
    
    def clearErrors(self):
        self.enterFactory()
        self.exitFactory(True)

def checkRegNames():
    jbd = JBD(None)
    errors = []
    valueNamesToRegs = {}
    regNameCounts = {}
    # These have duplicate fields, but we don't care.
    ignore=BasicInfoReg,
    for reg in jbd.eeprom_regs:
        if reg.__class__ in ignore: continue
        if reg.regName not in regNameCounts:
            regNameCounts[reg.regName] = 1
        else:
            regNameCounts[reg.regName] += 1

    for regName, count in regNameCounts.items():
        if count == 1: continue
        errors.append(f'register name {regName} occurs {count} times')

    for reg in jbd.eeprom_regs:
        if reg.__class__ in ignore: continue
        valueNames = reg.valueNames
        for n in valueNames:
            if n in valueNamesToRegs:
                otherReg = valueNamesToRegs[n]
                errors.append(f'duplicate value name "{n}" in regs {reg.regName} and {otherReg.regName}')
            else:
                valueNamesToRegs[n] = reg
    return errors

# sanity check for reg setup
errors = checkRegNames()
if errors:
    for error in errors:
        print(error)
    raise RuntimeError('register errors')
del errors

def main():
    from pprint import pprint
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('port')
    args = p.parse_args()
    s = serial.Serial(args.port, 9600, timeout=.2)
    j = JBD(s)

    if 0:
        eeprom = j.readEeprom()
        pprint(eeprom)
    elif 0:
        basic = j.readBasicInfo()
        pprint(basic)
    elif 0:
        cell = j.readCellInfo()
        pprint(cell)
    elif 1:
        device = j.readDeviceInfo()
        pprint(device)

if __name__ == '__main__':
    main()
