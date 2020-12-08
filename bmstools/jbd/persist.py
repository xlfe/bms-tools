#!/usr/bin/env python

from .registers import DateReg
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

class TempParser(IntParserX1):
    @classmethod
    def decode(cls, string):
        i = int(string)
        return ((i - 2731) / 10,)

    def encode(cls, values):
        if type(values) not in (tuple, list):
            values = (values,)
        return str(int(values[0] * 10 + 2731))

class DateParser(BaseParser):
    @staticmethod
    def decode(string):
        d = int(string)
        return DateReg.unpackDate(d)

    @staticmethod
    def encode(values):
        d = DateReg.packDate(*values)
        return str(d)

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

class NtcParser(BaseParser):

    @staticmethod
    def decode(string):
        i = int(string)
        return [bool(i & (1 << j)) for j in range(8)]

    @staticmethod
    def encode(values):
        i = 0
        for j, val in enuemrate(values):
            i |= ((1 << j) if val else 0)

class JBDPersist:
    fields =  {
        #'FileCode' __unknown__ 3838
        'DesignCapacity':       (('design_cap',), IntParserX10),               # reg
        'CycleCapacity':        (('cycle_cap',), IntParserX10),                # reg
        'FullChargeVol':        (('cap_100',), IntParserX1),                   # reg
        'ChargeEndVol':         (('cap_0',), IntParserX1),                     # reg
        'DischargingRate':      (('dsg_rate',), IntParserD10),                 # reg
        'ManufactureDate':      (('year', 'month', 'day'), DateParser),        # reg
        'SerialNumber':         (('serial_num',), IntParserX1),                # reg
        'CycleCount':           (('cycle_cnt',), IntParserX1),                 # reg
        'ChgOverTemp':          (('chgot',), TempParser),                      # reg
        'ChgOTRelease':         (('chgot_rel',), TempParser),                  # reg
        'ChgLowTemp':           (('chgut',), TempParser),                      # reg
        'ChgUTRelease':         (('chgut_rel',), TempParser),                  # reg
        'DisOverTemp':          (('dsgot',), TempParser),                      # reg
        'DsgOTRelease':         (('dsgot_rel',), TempParser),                  # reg
        'DisLowTemp':           (('dsgut' ,), TempParser),                     # reg
        'DsgUTRelease':         (('dsgut_rel',), TempParser),                  # reg
        'PackOverVoltage':      (('povp',), IntParserX10),                     # reg
        'PackOVRelease':        (('povp_rel',), IntParserX10),                 # reg
        'PackUnderVoltage':     (('puvp',), IntParserX10),                     # reg
        'PackUVRelease':        (('puvp_rel',), IntParserX10),                 # reg
        'CellOverVoltage':      (('covp',), IntParserX1),                      # reg
        'CellOVRelease':        (('covp_rel',), IntParserX1),                  # reg
        'CellUnderVoltage':     (('cuvp',), IntParserX1),                      # reg
        'CellUVRelease':        (('cuvp_rel',), IntParserX1),                  # reg
        'OverChargeCurrent':    (('chgoc',), IntParserX1),                     # reg
        'OverDisCurrent':       (('dsgoc',), IntParserX1),                     # reg
        'BalanceStartVoltage':  (('bal_start',), IntParserX1),                 # reg
        'BalanceWindow':        (('bal_window',), IntParserX1),                # reg
        'SenseResistor':        (('current_res',), IntParserX1),               # reg
        'BatteryConfig':        (('func_config',), FIXME),               # reg
        'NtcConfig':            (tuple([f'ntc{i+1}' for i in range(8)]), NtcParser),                # reg
        'PackNum':              (('cell_cnt',), IntParserX1),                  # reg
        'fet_ctrl_time_set':    (('fet_ctrl',), IntParserX1),                  # reg
        'led_disp_time_set':    (('led_timer',), IntParserX1),                 # reg
        'VoltageCap80':         (('cap_80',), IntParserX1),                    # reg
        'VoltageCap60':         (('cap_60',), IntParserX1),                    # reg
        'VoltageCap40':         (('cap_40',), IntParserX1),                    # reg
        'VoltageCap20':         (('cap_20',), IntParserX1),                    # reg
        'HardCellOverVoltage':  (('covp_high',), IntParserX1),                 # reg
        'HardCellUnderVoltage': (('cuvp_high',), IntParserX1),                 # reg
         
        'ChgUTDelay':           (('chgut_delay',), IntParserX1),               # field
        'ChgOTDelay':           (('chgot_delay',), IntParserX1),               # field
        'DsgUTDelay':           (('dsgut_delay',), IntParserX1),               # field
        'DsgOTDelay':           (('dsgot_delay',), IntParserX1),               # field
        'PackUVDelay':          (('puvp_delay',), IntParserX1),                # field
        'PackOVDelay':          (('povp_delay',), IntParserX1),                # field
        'CellUVDelay':          (('cuvp_delay',), IntParserX1),                # field
        'CellOVDelay':          (('covp_delay',), IntParserX1),                # field
        'ChgOCDelay':           (('chgoc_delay',), IntParserX1),               # field
        'ChgOCRDelay':          (('chgoc_rel',), IntParserX1),                 # field
        'DsgOCDelay':           (('dsgoc_delay',), IntParserX1),               # field
        'DsgOCRDelay':          (('dsgoc_rel',), IntParserX1),                 # field
         
        'ManufacturerName':     (('mfg_name',), StrParser),                  # reg
        'DeviceName':           (('device_name',), StrParser),               # reg
        'BarCode':              (('barcode',), StrParser),                   # reg
        'HardChgOverCurrent':   (('sc', 'sc_delay', 'sc_dsgoc_x2'), ScParser),
        'HardDsgOverCurrent':   (('dsgoc2', 'dsgoc2_delay'), Dsgoc2Parser),

        'HardTime':             (('covp_high_delay', 'cuvp_high_delay'), CxvpDelayParser),
        'SCReleaseTime':        (('sc_rel',), IntParserX1),
    }

    def __init__(self):
        pass

    def load(self, f):
        opened = False
        ret = {}
        try:
            if type(f) in (bytes, bytearray, str): 
                f = open(f)
                opened = True
            lines = [l.strip() for l in f.readlines() if l.strip()] # non-empty lines
            kv = [l.split(maxsplit=1) for l in lines]               # split into key/value
            kv = [(i + [''])[:2] for i in kv]                       # ensure empty values are '' 
            for fieldName, data in kv:
                if fieldName not in self.fields:
                    print(f'unknown field {fieldName}')
                    continue
                valueNames, conv = self.fields[fieldName]
                values = conv.decode(data)
                ret.update(dict(zip(valueNames, values)))
            return ret
        finally:
            if opened: f.close()

    def save(self, f):
        opened = False
        try:
            if type(f) in (bytes, bytearray, str): 
                f = open(f)
                opened = True
        finally:
            if opened: f.close()