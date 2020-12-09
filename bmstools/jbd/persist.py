#!/usr/bin/env python

from .parsers import *

class JBDPersist:
    fields =  {
        #'FileCode' __unknown__ 3838
        'DesignCapacity':       (('design_cap',), IntParserX10),
        'CycleCapacity':        (('cycle_cap',), IntParserX10),
        'FullChargeVol':        (('cap_100',), IntParserX1),
        'ChargeEndVol':         (('cap_0',), IntParserX1),
        'DischargingRate':      (('dsg_rate',), IntParserD10),
        'ManufactureDate':      (('year', 'month', 'day'), DateParser),
        'SerialNumber':         (('serial_num',), IntParserX1),
        'CycleCount':           (('cycle_cnt',), IntParserX1),
        'ChgOverTemp':          (('chgot',), TempParser),
        'ChgOTRelease':         (('chgot_rel',), TempParser),
        'ChgLowTemp':           (('chgut',), TempParser),
        'ChgUTRelease':         (('chgut_rel',), TempParser),
        'DisOverTemp':          (('dsgot',), TempParser),
        'DsgOTRelease':         (('dsgot_rel',), TempParser),
        'DisLowTemp':           (('dsgut' ,), TempParser),
        'DsgUTRelease':         (('dsgut_rel',), TempParser),
        'PackOverVoltage':      (('povp',), IntParserX10),
        'PackOVRelease':        (('povp_rel',), IntParserX10),
        'PackUnderVoltage':     (('puvp',), IntParserX10),
        'PackUVRelease':        (('puvp_rel',), IntParserX10),
        'CellOverVoltage':      (('covp',), IntParserX1),
        'CellOVRelease':        (('covp_rel',), IntParserX1),
        'CellUnderVoltage':     (('cuvp',), IntParserX1),
        'CellUVRelease':        (('cuvp_rel',), IntParserX1),
        'OverChargeCurrent':    (('chgoc',), IntParserX1),
        'OverDisCurrent':       (('dsgoc',), IntParserX1),
        'BalanceStartVoltage':  (('bal_start',), IntParserX1),
        'BalanceWindow':        (('bal_window',), IntParserX1),
        'SenseResistor':        (('shunt_res',), IntParserX1),
        'BatteryConfig':        (('switch', 'scrl', 'balance_en', 'chg_balance_en', 'led_en', 'led_num'), BitfieldParser), 
        'NtcConfig':            (tuple([f'ntc{i+1}' for i in range(8)]), BitfieldParser),
        'PackNum':              (('cell_cnt',), IntParserX1),
        'fet_ctrl_time_set':    (('fet_ctrl',), IntParserX1),
        'led_disp_time_set':    (('led_timer',), IntParserX1),
        'VoltageCap80':         (('cap_80',), IntParserX1),
        'VoltageCap60':         (('cap_60',), IntParserX1),
        'VoltageCap40':         (('cap_40',), IntParserX1),
        'VoltageCap20':         (('cap_20',), IntParserX1),
        'HardCellOverVoltage':  (('covp_high',), IntParserX1),
        'HardCellUnderVoltage': (('cuvp_high',), IntParserX1),
         
        'ChgUTDelay':           (('chgut_delay',), IntParserX1),
        'ChgOTDelay':           (('chgot_delay',), IntParserX1),
        'DsgUTDelay':           (('dsgut_delay',), IntParserX1),
        'DsgOTDelay':           (('dsgot_delay',), IntParserX1),
        'PackUVDelay':          (('puvp_delay',), IntParserX1),
        'PackOVDelay':          (('povp_delay',), IntParserX1),
        'CellUVDelay':          (('cuvp_delay',), IntParserX1),
        'CellOVDelay':          (('covp_delay',), IntParserX1),
        'ChgOCDelay':           (('chgoc_delay',), IntParserX1),
        'ChgOCRDelay':          (('chgoc_rel',), IntParserX1),
        'DsgOCDelay':           (('dsgoc_delay',), IntParserX1),
        'DsgOCRDelay':          (('dsgoc_rel',), IntParserX1),
         
        'ManufacturerName':     (('mfg_name',), StrParser),
        'DeviceName':           (('device_name',), StrParser),
        'BarCode':              (('barcode',), StrParser),
        'HardChgOverCurrent':   (('sc', 'sc_delay', 'sc_dsgoc_x2'), ScParser),
        'HardDsgOverCurrent':   (('dsgoc2', 'dsgoc2_delay'), Dsgoc2Parser),

        'HardTime':             (('covp_high_delay', 'cuvp_high_delay'), CxvpDelayParser),
        'SCReleaseTime':        (('sc_rel',), IntParserX1),
    }

    def __init__(self):
        pass

    def deserialize(self, data):
        opened = False
        ret = {}
        lines = [l.strip() for l in data.splitlines() if l.strip()] # non-empty lines
        kv = [l.split(maxsplit=1) for l in lines]               # split into key/value
        kv = [(i + [''])[:2] for i in kv]                       # ensure empty values are '' 
        for fieldName, data in kv:
            if fieldName not in self.fields:
                print(f'unknown field {fieldName}')
                continue
            valueNames, conv = self.fields[fieldName]
            values = conv.decode(data)
            values = values[:len(valueNames)] #sometimes decoders return too many values
            ret.update(dict(zip(valueNames, values)))
        return ret

    def serialize(self, values):
        pass