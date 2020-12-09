#!/usr/bin/env python


# parsers operate on non-binary data -- integers or strings
# 
# wherever possible, these are shared by registers and the persist library

from .registers import (Dsgoc2Enum, Dsgoc2DelayEnum, 
                        ScEnum, ScDelayEnum, CuvpHighDelayEnum, 
                        CovpHighDelayEnum, LabelEnum)

class BaseParser: pass

class IntParserX1(BaseParser):
    'encodes or decodes a single integer'
    factor = 1
    @classmethod
    def decode(cls, string):
        return (int(string) * cls.factor,)

    @classmethod
    def encode(cls, values):
        if type(values) not in (tuple, list):
            values = (values,)
        return str(int(values[0] / cls.factor))

class IntParserX10(IntParserX1):
    factor = 10

class IntParserD10(IntParserX1):
    factor = .1

class ScParser(BaseParser):
    @staticmethod
    def decode(string):
        i = int(string)
        sc = i & 0x7
        sc_delay = (i >> 3) & 0x3
        sc_dsgoc_x2 = bool(i & 0x80)
        return ScEnum.byValue(sc), ScDelayEnum.byValue(sc_delay), sc_dsgoc_x2

    @staticmethod
    def encode(values):
        sc, sc_delay, sc_dsgoc_x2 = values
        i = sc_delay.val << 3
        i |= sc.val
        i |= (0x80 if sc_dsgoc_x2 else 0)
        return str(i)

class Dsgoc2Parser(BaseParser):
    @staticmethod
    def decode(string):
        i = int(string)
        dsgoc2 = i & 0xF
        dsgoc2_delay = i >> 4
        return Dsgoc2Enum.byValue(dsgoc2), Dsgoc2DelayEnum.byValue(dsgoc2_delay)

    @staticmethod
    def encode(values):
        dsgoc2, dsgoc2_delay = values
        i = dsgoc2.val | (Dsgoc2DelayEnum.val << 4)
        return str(i)

    
class BitfieldParser(BaseParser):
    @staticmethod
    def decode(value):
        value = int(value)
        return [bool(value & (1 << i)) for i in range(16)]
    
    @staticmethod
    def encode(values):
        r = 0
        for i, value in enumerate(values):
            r |= (1<<i) if value else 0
        return r

class CxvpDelayParser(BaseParser):
    @staticmethod
    def decode(string):
        i = int(string)
        covp_high_delay = (i >> 6) & 0x3
        cuvp_high_delay = (i >> 4) & 0x3
        return (CovpHighDelayEnum.byValue(covp_high_delay), 
                CuvpHighDelayEnum.byValue(cuvp_high_delay))

    @staticmethod
    def encode(values):
        covp_high_delay, cuvp_high_delay = values
        i = (covp_high_delay & 0x3) << 6
        i |= (cuvp_high_delay & 0x3) << 4
        return str(i)

class DateParser(BaseParser):
    @staticmethod
    def decode(value):
        value = int(value)
        day = value & 0x1f
        value >>= 5
        month = value & 0xf
        value >>= 4
        year = (value & 0x7f) + 2000
        return year, month, day

    @staticmethod
    def encode(values):
        year, month, day = values
        value = (year - 2000) & 0x7f
        value <<= 4
        value |= month
        value <<= 5
        value |= day
        return struct.pack('>H', value)

class TempParser(IntParserX1):
    @classmethod
    def decode(cls, value):
        value = int(value)
        return ((value - 2731) / 10,)

    def encode(cls, values):
        if type(values) not in (tuple, list):
            values = (values,)
        return str(int(values[0] * 10 + 2731))


class StrParser(BaseParser):
    'encodes or decodes a single string'
    @staticmethod
    def decode(string):
        return (str(string),)

    @staticmethod
    def encode(values):
        if type(values) not in (tuple, list):
            values = (values,)
        return str(values[0])