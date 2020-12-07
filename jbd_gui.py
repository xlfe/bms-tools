#!/usr/bin/env python
import os
import sys
import time
import re
import serial
import math
import enum
import random
import threading
import traceback

from pprint import pprint

import wx
import wx.grid
import wx.svg
import wx.lib.scrolledpanel as scrolled
import wx.lib.newevent
import wx.lib.masked.numctrl

import bmstools.jbd as jbd

try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_path = sys._MEIPASS
except Exception:
    base_path = os.path.dirname(os.path.abspath(__file__))

rflags = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT
lflags = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT
defaultBorder = wx.EXPAND | wx.TOP | wx.BOTTOM | wx.LEFT | wx.RIGHT, 7
colGap = (10,1)
boxGap = (3,3)

cellRange   = (0, 65536, 100)
packRange   = (0, 655350, 100)
tempRange   = (-273.15, 6316.4, 1)
mahRange     = (0, 655350, 1000)
chgRange    = (0, 327670, 100)
dsgRange    = (-327680, 0, 100)
delayRange  = (0, 255, 1)
ranges = {
    'covp':         cellRange,
    'covp_rel':     cellRange,
    'covp_delay':   delayRange,
    'cuvp':         cellRange,
    'cuvp_rel':     cellRange,
    'cuvp_delay':   delayRange,
    'povp':         packRange,
    'povp_rel':     packRange,
    'povp_delay':   delayRange,
    'puvp':         packRange,
    'puvp_rel':     packRange,
    'chgot':        tempRange,
    'chgot_rel':    tempRange,
    'chgot_delay':  delayRange,
    'chgut':        tempRange,
    'chgut_rel':    tempRange,
    'chgut_delay':  delayRange,
    'dsgot':        tempRange,
    'dsgot_rel':    tempRange,
    'dsgot_delay':  delayRange,
    'dsgut':        tempRange,
    'dsgut_rel':    tempRange,
    'dsgut_delay':  delayRange,

    'chgoc':        chgRange,
    'chgoc_rel':    delayRange,
    'chgoc_delay':  delayRange,
    'dsgoc':        dsgRange,
    'dsgoc_rel':    delayRange,
    'dsgoc_delay':  delayRange,

    'covp_high':    cellRange,
    'cuvp_high':    cellRange,

    'bal_start':    cellRange,
    'bal_window':   cellRange,

    'design_cap':   mahRange,
    'cycle_cap':    mahRange,
    'dsg_rate':     (0.0, 100.0, .1),
    'fet_ctrl':     (0, 65535, 1),
    'led_timer':    (0, 65535, 1),

    'cap_100':      cellRange,
    'cap_80':       cellRange,
    'cap_60':       cellRange,
    'cap_40':       cellRange,
    'cap_20':       cellRange,
    'cap_0':        cellRange,


    'cycle_cnt':    (0, 65535, 1),
    'shunt_res':    (0.0, 6553.5, .1),
}

class BetterChoice(wx.Choice):
    def __init__(self, parent, **kwargs):
        choices = kwargs.get('choices')
        kwargs['choices'] = [str(i) for i in choices]
        super().__init__(parent, **kwargs)
        self.SetSelection(0)

    def GetValue(self):
        idx = self.GetSelection()
        if idx == wx.NOT_FOUND:
            return None
        return self.GetString(idx)

    def SetValue(self, value):
        idx = self.FindString(str(value))
        if idx == wx.NOT_FOUND: 
            print(f'{self.__class__.__name__}: {self.Name} to unknown choice {value}')
            return
        self.SetSelection(idx)

class EnumChoice(BetterChoice):
    def __init__(self, parent, **kwargs):
        choices = kwargs.get('choices')
        assert issubclass(choices, jbd.LabelEnum)
        self.__enum_cls = choices
        super().__init__(parent, **kwargs)
        self.SetSelection(0)
    
    def GetValue(self):
        idx = self.GetSelection()
        s = self.GetString(idx)
        return self.__enum_cls.byDisplay(int(s))

class SVGImage(wx.Panel):
    def __init__(self, parent, img, name):
        super().__init__(parent, name = name)
        self.reqWidth = None
        self.reqHeight = None
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.SetImage(img)
        self.Refresh()


    def SetImage(self, img):
        if isinstance(img, wx.svg.SVGimage):
            self.img = img
        else:
            self.img = wx.svg.SVGimage.CreateFromFile(img)
        self.Refresh()

    def SetReqSize(self, width, height):
        self.reqWidth = width
        self.reqHeight = height

    def OnPaint(self, event):
        w,h = self.Size
        if self.reqWidth is not None:
            w = self.reqWidth
        if self.reqHeight is not None:
            h = self.reqHeight
        self.SetSize(w,h)
        

        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(wx.GREEN, wx.TRANSPARENT))
        #dc.SetBackground(wx.Brush(wx.GREEN))
        dc.Clear()
        hscale = self.Size.width / self.img.width
        vscale = self.Size.height / self.img.height
        scale = min(hscale, vscale)
        w,h = [int(i * scale) for i in (self.img.width, self.img.height)]

        bm = self.img.ConvertToScaledBitmap(self.Size)
        dc2 = wx.MemoryDC(bm)
        xoff = (dc.Size.width - w)//2
        yoff = (dc.Size.height - h)//2
        dc.Blit(xoff,yoff,*dc2.Size,dc2,0,0)

class BoolImage(SVGImage):
    def __init__(self, parent, img1, img2, name):
        if isinstance(img1, wx.svg.SVGimage):
            self.img1 = fn
        else:
            self.img1 = wx.svg.SVGimage.CreateFromFile(img1)
        if isinstance(img2, wx.svg.SVGimage):
            self.img2 = fn
        else:
            self.img2 = wx.svg.SVGimage.CreateFromFile(img2)

        super().__init__(parent, img1, name)
    
    def SetValue(self, which):
        self.SetImage(self.img1 if bool(which) else self.img2)
        self.Refresh()

class IntValidator(wx.Validator):
    def __init__(self, lower, upper):
        super().__init__()
        self.lower = lower
        self.upper = upper

    def Clone(self):
        print('clone')
        return self.__class__(self.lower, self.upper)

    def Validate(self, win):
        print('validate')
            
        return True

        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()
        print('got value:', text)

        if text.isdigit():
            return True
        else:
            wx.MessageBox("Please enter numbers only", "Invalid Input",
            wx.OK | wx.ICON_ERROR)
        return False

    def TransferToWindow(self):
        print('xferto')
        return True

    def TransferFromWindow(self):
        print('xferfrom')
        return True

    def OnChar(self, event):
        print('onchar')
        keycode = int(event.GetKeyCode())
        if keycode < 256:
            key = chr(keycode)
            if key not in string.digits:
                return
        event.Skip()


class LayoutGen: 
    def __init__(self, parent):
        tc = wx.TextCtrl(parent)
        self.txtSize30 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 30))
        self.txtSize25 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 25))
        self.txtSize20 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 20))
        self.txtSize10 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 10))
        self.txtSize8  = tc.GetSizeFromTextSize(parent.GetTextExtent('99999999'))
        self.txtSize6  = tc.GetSizeFromTextSize(parent.GetTextExtent('999999'))
        self.txtSize4  = tc.GetSizeFromTextSize(parent.GetTextExtent('9999'))
        self.txtSize3  = tc.GetSizeFromTextSize(parent.GetTextExtent('999'))
        self.txtSize2  = tc.GetSizeFromTextSize(parent.GetTextExtent('99'))
        self.txtSize1  = tc.GetSizeFromTextSize(parent.GetTextExtent('9'))
        tc.Destroy()
    
    ####
    ##### Info tab methods 
    ####

    def infoTabLayout(self, tab):
        hsizer = wx.BoxSizer()
        tab.SetSizer(hsizer)
        self.cellsInfoLayout(tab, hsizer, colGap, boxGap)
        self.packInfoLayout(tab, hsizer, colGap, boxGap)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer.Add(vsizer, 1, wx.EXPAND)
        self.deviceInfoLayout(tab, vsizer, colGap, boxGap)
        self.deviceStatusLayout(tab, vsizer, colGap, boxGap)

        tab.Layout()
        tab.Fit()

    def cellsInfoLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 0, *defaultBorder)

        sb = wx.StaticBox(panel, label='Cells')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        sp = scrolled.ScrolledPanel(sb)

        sbs.Add(sp, 1, *defaultBorder)
        bs = wx.BoxSizer(wx.VERTICAL)
        sp.SetSizer(bs)

        if isinstance(sp, scrolled.ScrolledPanel):
            sp.SetupScrolling(scroll_x=False)

        rows = 3
        cols = 4
        g = wx.grid.Grid(sp, name='cell_grid')
        g.CreateGrid(rows, cols)
        g.EnableEditing(False)
        g.DisableDragColSize()
        g.DisableDragRowSize()
        g.SetColLabelSize(self.txtSize4[1])

        g.SetColLabelValue(0, 'Cell')
        g.SetColLabelValue(1, 'mV')
        g.SetColLabelValue(2, 'Bal')
        g.SetColLabelValue(3, 'Temp')
        g.SetRowLabelSize(1)
        for i in range(cols):
            g.SetColSize(i, self.txtSize4[0])

        bs.Add(g, 1, wx.EXPAND)

    def packInfoLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 0, *defaultBorder)

        sb = wx.StaticBox(panel, label='Pack')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        fgs = wx.FlexGridSizer(3, gap = boxGap)
        sbs.Add(fgs, 0, *defaultBorder)

        def gen(label, fn, unit = ''):
            t = wx.TextCtrl(sb, name=fn, size=self.txtSize6, style=wx.TE_RIGHT)
            t.Enable(False)
            return [
                (wx.StaticText(sb, label=label + ':'), 0, rflags),
                (t, 0, lflags),
                (wx.StaticText(sb, label=unit), 0, lflags),
            ]
        fgs.AddMany(gen('Pack V', 'pack_mv', 'mv'))
        fgs.AddMany(gen('Pack I', 'pack_ma', 'mA'))
        fgs.AddMany(gen('Avg V', 'cell_avg_mv', 'mv'))
        fgs.AddMany(gen('Max V', 'cell_max_mv', 'mv'))
        fgs.AddMany(gen('Min V', 'cell_min_mv', 'mv'))
        fgs.AddMany(gen('Δ V', 'cell_delta_mv', 'mv'))
        fgs.AddMany(gen('Cycles', 'cycle_cnt'))
        fgs.AddMany(gen('Capacity', 'cap_nom', 'mAh'))
        fgs.AddMany(gen('Cap Rem', 'cap_rem', 'mAh'))
        sbs.Add(RoundGauge(sb, name='cap_pct'), 1, wx.EXPAND)
        bs = wx.BoxSizer()
        sbs.Add(bs, 1, wx.EXPAND)
        bs.AddStretchSpacer()
        bs.Add(wx.StaticText(sb, label='Remaining Capacity'), 0,  wx.TOP)
        bs.AddStretchSpacer()

    def deviceInfoLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 1, *defaultBorder)

        sb = wx.StaticBox(panel, label='Device')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        fgs = wx.FlexGridSizer(2, gap = boxGap)
        sbs.Add(fgs, 0, *defaultBorder)

        # device name
        fgs.Add(wx.StaticText(sb, label='Name:'), 0, rflags)
        t = wx.TextCtrl(sb, name='device_name', size=self.txtSize30)
        t.Enable(False)
        fgs.Add(t, 0, lflags)

        # mfg date
        fgs.Add(wx.StaticText(sb, label='Mfg Date:'), 0, rflags)
        t = wx.TextCtrl(sb, name='mfg_date', size=self.txtSize8)
        t.Enable(False)
        fgs.Add(t, 0, lflags)

        # version
        fgs.Add(wx.StaticText(sb, label='Version:'), 0, rflags)
        t = wx.TextCtrl(sb, name='version', size=self.txtSize4)
        t.Enable(False)
        fgs.Add(t, 0, lflags)

    def deviceStatusLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 3, *defaultBorder)

        sb = wx.StaticBox(panel, label='Status')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        cf_en_svg = os.path.join(base_path, 'img', 'chg_fet_enabled.svg')
        cf_dis_svg = os.path.join(base_path, 'img', 'chg_fet_disabled.svg')
        df_en_svg = os.path.join(base_path, 'img', 'dsg_fet_enabled.svg')
        df_dis_svg = os.path.join(base_path, 'img', 'dsg_fet_disabled.svg')

        chg_fet_img = BoolImage(sb, cf_en_svg, cf_dis_svg, 'chg_fet_status_img')
        dsg_fet_img = BoolImage(sb, df_en_svg, df_dis_svg, 'dsg_fet_status_img')

        bsh = wx.BoxSizer()
        sbs.Add(bsh, 1, wx.EXPAND)

        bsv1 = wx.BoxSizer(wx.VERTICAL)
        bsv2 = wx.BoxSizer(wx.VERTICAL)
        bsh.Add(bsv1, 8, wx.EXPAND | wx.ALL, 3)
        bsh.AddStretchSpacer(2)
        bsh.Add(bsv2, 8, wx.EXPAND | wx.ALL, 3)

        bsg = wx.BoxSizer()
        bsg.AddStretchSpacer(1)
        bsg.Add(chg_fet_img, 5,  wx.EXPAND)
        bsg.AddStretchSpacer(1)
        bsv1.Add(bsg, 1, wx.EXPAND)
        bst = wx.BoxSizer()
        bsv1.Add(bst, 1, wx.ALIGN_CENTER_HORIZONTAL)
        bst.Add(wx.StaticText(sb, label='Charge FET:'), 0)
        bst.Add(wx.StaticText(sb, label='ENABLED', name='chg_fet_status_txt'), 0)

        bsg = wx.BoxSizer()
        bsg.AddStretchSpacer(1)
        bsg.Add(dsg_fet_img, 5,  wx.EXPAND)
        bsg.AddStretchSpacer(1)
        bsv2.Add(bsg, 1, wx.EXPAND)
        bst = wx.BoxSizer()
        bsv2.Add(bst, 1, wx.ALIGN_CENTER_HORIZONTAL)
        bst.Add(wx.StaticText(sb, label='Discharge FET:'), 0)
        bst.Add(wx.StaticText(sb, label='ENABLED', name='dsg_fet_status_txt'), 0)

        ok_svg = os.path.join(base_path, 'img', 'ok.svg')
        err_svg = os.path.join(base_path, 'img', 'err.svg')

        # error flags
        gbs = wx.GridBagSizer(3,3)
        sbs.Add(gbs, 1, *defaultBorder)

        class Gen:
            size = (self.txtSize8[1], self.txtSize8[1])
            def __init__(self, l):
                self.row = 0
                self.col = 0
                self.cols = 11
                self.l = l

            def incLine(self):
                self.row += 1
                self.col = 0

            def __call__(self, label, img1, img2, fn):
                bi = BoolImage(sb, img1, img2, fn)
                bi.SetMinSize(self.size)
                bi.SetValue(False)
                txt = wx.StaticText(sb, label = label + ':')
                gbs.Add(txt, (self.row, self.col), flag = rflags)
                self.col += 1
                gbs.Add(bi, (self.row, self.col), flag = rflags)
                self.col += 1

                if self.col == self.cols:
                    self.incLine()
                else:
                    gbs.Add(*self.l.txtSize2,(self.row, self.col))
                    self.col += 1

        gen = Gen(self)
        gen('COVP', err_svg, ok_svg, 'covp_err')
        gen('CUVP', err_svg, ok_svg, 'cuvp_err')
        gen('POVP', err_svg, ok_svg, 'povp_err')
        gen('PUVP', err_svg, ok_svg, 'puvp_err')
        gen('CHGOT', err_svg, ok_svg, 'chgot_err')
        gen('CHGUT', err_svg, ok_svg, 'chgut_err')
        gen('DSGOT', err_svg, ok_svg, 'dsgot_err')
        gen('DSGUT', err_svg, ok_svg, 'dsgut_err')
        gen('CHGOC', err_svg, ok_svg, 'chgoc_err')
        gen('DSGOC', err_svg, ok_svg, 'dsgoc_err')
        gen.incLine()
        gen('Short', err_svg, ok_svg, 'sc_err')
        gen.incLine()
        gen('AFE', err_svg, ok_svg, 'afe_err')
        gen('SW Lock', err_svg, ok_svg, 'software_err')

    ####
    ##### Settings tab methods 
    ####

    def settingsTabLayout(self, tab):
        boxSizer  = wx.BoxSizer(wx.HORIZONTAL)
        tab.SetSizer(boxSizer)
        col1Sizer = wx.BoxSizer(wx.VERTICAL)
        col2Sizer = wx.FlexGridSizer(1)
        col3Sizer = wx.FlexGridSizer(1)
        boxSizer.AddMany([col1Sizer, col2Sizer, col3Sizer])

        self.basicConfigLayout(tab, col1Sizer, colGap, boxGap)
        self.highProtectConfigLayout(tab, col1Sizer, colGap, boxGap)
        self.functionConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.ntcConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.balanceConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.otherConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.controlConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.capacityConfigLayout(tab, col3Sizer, colGap, boxGap)
        self.faultCountsLayout(tab, col3Sizer, colGap, boxGap)

        tab.Layout()
        tab.Fit()

    def basicConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)

        sb = wx.StaticBox(panel, label='Basic Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(11, gap=boxGap)
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 0, *defaultBorder)

        def gen(fn, unit1, unit2 = None, unit3 = 'S', spacing=10, digits = 0):
            unit2 = unit2 or unit1
            c1 = wx.SpinCtrlDouble(sb, name = fn,  size = self.txtSize10)
            c2 = wx.SpinCtrlDouble(sb, name = fn + '_rel', size=self.txtSize10)
            c1.SetDigits(digits)
            c2.SetDigits(digits)
            items = [
                (wx.StaticText(sb, label = fn.upper()), 0, rflags),
                (c1, 0, lflags),
                (wx.StaticText(sb, label = unit1), 0, lflags),
                colGap,
                (wx.StaticText(sb, label = 'Rel'), 0, rflags),
                (c2, 0, lflags),
                (wx.StaticText(sb, label = unit2), 0, lflags),
                colGap,
                (wx.StaticText(sb, label = 'Delay'), 0, rflags),
                (wx.SpinCtrlDouble(sb, name = fn + '_delay', size=self.txtSize6), 0, lflags),
                (wx.StaticText(sb, label = unit3), 0, lflags),
            ]
            return items

        fgs.AddMany(gen('covp', 'mV'))
        fgs.AddMany(gen('cuvp', 'mV'))
        fgs.AddMany(gen('povp', 'mV'))
        fgs.AddMany(gen('puvp', 'mV'))
        fgs.AddMany(gen('chgot', 'C', digits = 1))
        fgs.AddMany(gen('chgut', 'C', digits = 1))
        fgs.AddMany(gen('dsgot', 'C', digits = 1))
        fgs.AddMany(gen('dsgut', 'C', digits = 1))
        fgs.AddMany(gen('chgoc', 'mA', 'S'))
        fgs.AddMany(gen('dsgoc', 'mA', 'S'))

        fgs.Fit(panel)

    def highProtectConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='High Protection Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(5, gap=boxGap)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)
        
        fgs.AddGrowableCol(2)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(wx.CheckBox(sb, label='2X OC and SC values', name = 'sc_dsgoc_x2'))
        sbs.Add(fgs, 0, *defaultBorder)
        # DSGOC2
        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()

        s1.AddMany([
            (EnumChoice(sb, choices = jbd.Dsgoc2Enum, name='dsgoc2'), 0, a),
            (wx.StaticText(sb, label = 'mV'), 0, a),
        ])
        s2.AddMany([ 
                (EnumChoice(sb, choices = jbd.Dsgoc2DelayEnum, name='dsgoc2_delay'), 0, a),
                (wx.StaticText(sb, label = 'mS'), 0, a),
        ])
        

        fgs.AddMany([
            (wx.StaticText(sb, label = 'DSGOC2'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Delay'), 0, a), (s2,)
            ])

        # SC value / delay
        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()
        s1.AddMany([     
                (EnumChoice(sb, choices = jbd.ScEnum, name = 'sc'), 0, a),
                (wx.StaticText(sb, label = 'mV'), 0, a)
        ])
        s2.AddMany([ 
                (EnumChoice(sb, choices = jbd.ScDelayEnum, name = 'sc_delay'), 0, a),
                (wx.StaticText(sb, label = 'uS'), 0, a)
        ])

        fgs.AddMany([
            (wx.StaticText(sb, label = 'SC Value'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Delay'), 0, a), (s2,)
            ])

        # COVP High
        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()
        s1.AddMany([
                (wx.SpinCtrlDouble(sb, name = 'covp_high'), 0, a),
                (wx.StaticText(sb, label = 'mV'), 0, a),
        ])
        s2.AddMany([
                (EnumChoice(sb, choices = jbd.CovpHighDelayEnum, name = 'covp_high_delay'), 0, a),
                (wx.StaticText(sb, label = 'S'), 0, a),
        ])

        fgs.AddMany([
            (wx.StaticText(sb, label = 'COVP High'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Delay'), 0, a), (s2,)
            ])

        # CUVP High
        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()
        s1.AddMany([
                (wx.SpinCtrlDouble(sb, name = 'cuvp_high'), 0, a),
                (wx.StaticText(sb, label = 'mV'), 0, a),
        ])
        s2.AddMany([
                (EnumChoice(sb, choices = jbd.CuvpHighDelayEnum, name = 'cuvp_high_delay'), 0, a),
                (wx.StaticText(sb, label = 'S'), 0, a),
        ])
        fgs.AddMany([
            (wx.StaticText(sb, label = 'CUVP High'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Delay'), 0, a), (s2,)
            ])

        # SC Release
        s1 = wx.BoxSizer()
        s1.AddMany([
                (BetterChoice(sb, choices = [str(i) for i in range(256)], name = 'sc_rel'), 0, lflags),
                (wx.StaticText(sb, label = 'S'), 0, lflags),
        ])
        fgs.AddMany([
            (wx.StaticText(sb, label = 'SC Rel'), 0, a), (s1,), 
            ])

    def functionConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Function Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(3, gap=boxGap)
        sbs.Add(fgs, 1, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        fgs.AddMany([
            (wx.CheckBox(sb, name='switch', label='Switch'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='scrl', label='SC Rel'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='balance_en', label='Bal En'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='led_en', label='LED En'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='led_num', label='LED Num'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='chg_balance_en', label='Chg Bal En'),0, wx.EXPAND),
        ])
        for c in range(fgs.Cols):
            fgs.AddGrowableCol(c)

    def ntcConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='NTC Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(4, gap=boxGap)
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        fgs.AddMany([
            (wx.CheckBox(sb, name=f'ntc{i}', label=f'NTC{i}'),) for i in range(1,9)
        ])
        for c in range(fgs.Cols):
            fgs.AddGrowableCol(c)

    def balanceConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Balance Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(3, gap=boxGap)
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        fgs.AddMany([
            (wx.StaticText(sb, label='Start Voltage'), 0, rflags),
            (wx.SpinCtrlDouble(sb, name='bal_start'), 0, lflags),
            (wx.StaticText(sb, label='mV'), 0, lflags),

            (wx.StaticText(sb, label='Balance Window'), 0, rflags),
            (wx.SpinCtrlDouble(sb, name='bal_window'), 0, lflags),
            (wx.StaticText(sb, label='mV'), 0, lflags),
        ])

    def otherConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Other Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(5, gap=boxGap)
        fgs.AddGrowableCol(2)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()

        sr = wx.SpinCtrlDouble(sb, name='shunt_res', size=self.txtSize8)
        sr.SetDigits(1)
        sr.SetIncrement(0.1)
        s1.AddMany([
            (sr, 0, a),
            (wx.StaticText(sb, label = 'mΩ'), 0, a),
        ])
        s2.AddMany([ 
                (BetterChoice(sb, choices = [str(i) for i in range(1,17)], name='cell_cnt'), 0, a),
        ])
        fgs.AddMany([
            (wx.StaticText(sb, label = 'Shunt res'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Cell cnt'), 0, a), (s2,)
            ])

        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()

        s1.AddMany([
            (wx.SpinCtrlDouble(sb, name='cycle_cnt', size=self.txtSize8), 0, a),
        ])
        s2.AddMany([ 
            (wx.TextCtrl(sb, name='serial_num', size=self.txtSize6), 0, a),
        ])
        fgs.AddMany([
            (wx.StaticText(sb, label = 'Cycle cnt'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Serial num'), 0, a), (s2,)
            ])


        fgs = wx.FlexGridSizer(2, gap=boxGap)
        sbs.Add(fgs, 0, *defaultBorder)

        d = wx.BoxSizer()
        d.AddMany([
            (wx.TextCtrl(sb, name='year', size=self.txtSize4), 0, a),
            (wx.StaticText(sb,label='-'), 0, a),
            (wx.TextCtrl(sb, name='month', size=self.txtSize2), 0, a),
            (wx.StaticText(sb,label='-'), 0, a),
            (wx.TextCtrl(sb, name='day', size=self.txtSize2), 0, a),
        ])

        fgs.AddMany([
            (wx.StaticText(sb, label='Mfg Name'), 0, a),
            (wx.TextCtrl(sb, name='mfg_name', size=self.txtSize20), 0, a),

            (wx.StaticText(sb, label='Device Name'), 0, a),
            (wx.TextCtrl(sb, name='device_name', size=self.txtSize30), 0, a),

            (wx.StaticText(sb, label='Mfg Date'), 0, a),
            d,

            (wx.StaticText(sb, label='Barcode'), 0, a),
            (wx.TextCtrl(sb, name='barcode', size=self.txtSize20), 0, a),
        ])

    def controlConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Control')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(3, gap=boxGap)
        fgs.AddGrowableCol(1)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        read_btn = wx.Button(sb, label='Read EEPROM', name='read_eeprom_btn')
        write_btn = wx.Button(sb, label='Write EEPROM', name='write_eeprom_btn')
        load_btn = wx.Button(sb, label='Load EEPROM', name='load_eeprom_btn')
        save_btn = wx.Button(sb, label='Save EEPROM', name='save_eeprom_btn')
        write_btn.Enable(False)
        save_btn.Enable(False)

        fgs.Add(read_btn, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(0,0)
        fgs.Add(write_btn, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(load_btn, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(0,0)
        fgs.Add(save_btn, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

    def capacityConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Capacity Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(3, gap=boxGap)
        fgs.AddGrowableCol(2)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        def gen(label, fn, unit, digits = 0):
            c = wx.SpinCtrlDouble(sb, name = fn, size = self.txtSize10)
            c.SetDigits(digits)
            c.SetIncrement(10 ** -digits)
            items = [
                (wx.StaticText(sb, label = label), 0, rflags),
                (c, 0, lflags),
                (wx.StaticText(sb, label = unit), 0, lflags),
            ]
            return items

        fgs.AddMany(gen('Design Cap', 'design_cap', 'mAh'))
        fgs.AddMany(gen('Cycle Cap', 'cycle_cap', 'mAh'))
        fgs.AddMany(gen('Cell 100%', 'cap_100', 'mV'))
        fgs.AddMany(gen('Cell 80%', 'cap_80', 'mV'))
        fgs.AddMany(gen('Cell 60%', 'cap_60', 'mV'))
        fgs.AddMany(gen('Cell 40%', 'cap_40', 'mV'))
        fgs.AddMany(gen('Cell 20%', 'cap_20', 'mV'))
        fgs.AddMany(gen('Cell 0%', 'cap_0', 'mV'))
        fgs.AddMany(gen('Dsg Rate', 'dsg_rate', '%', 1))
        fgs.AddMany(gen('FET ctrl', 'fet_ctrl', 'S'))
        fgs.AddMany(gen('LED timer', 'led_timer', 'S'))

    def faultCountsLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Fault Counts')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(4, gap=boxGap)
        fgs.AddGrowableCol(2)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        def gen(label1, field1, label2 = None, field2 = None):
            items = [
                (wx.StaticText(sb, label = label1+':'), 0, rflags),
                (wx.StaticText(sb, name = field1, label='-'), 0, lflags)
            ]
            if field2:
                items += [
                (wx.StaticText(sb, label = label2+':'), 0, rflags),
                (wx.StaticText(sb, name = field2, label='-'), 0, lflags),
            ]
            return items

        fgs.AddMany(gen('CHGOC', 'chgoc_err_cnt', 'DSGOC', 'dsgoc_err_cnt'))
        fgs.AddMany(gen('CHGOT', 'chgot_err_cnt', 'CHGUT', 'chgut_err_cnt'))
        fgs.AddMany(gen('DSGOT', 'dsgot_err_cnt', 'DSGUT', 'dsgut_err_cnt'))
        fgs.AddMany(gen('POVP',  'povp_err_cnt',  'PUVP',  'puvp_err_cnt'))
        fgs.AddMany(gen('COVP',  'covp_err_cnt',  'CUVP',  'cuvp_err_cnt'))
        fgs.AddMany(gen('SC',    'sc_err_cnt'))
        fgs.Add(wx.Button(sb, label='Clear', name='clear_errors_btn'))

class ProgressBar(wx.StatusBar):
    def __init__(self, parent):
        self.parent = parent
        super().__init__(parent=self.parent)
        self.SetFieldsCount(3)
        self.SetStatusText('0/0')
        self.SetStatusText('Mango',1)
        self.SetStatusWidths([100, 100, -1])
        gauge_pos, gauge_size = self.get_gauge_dimensions()
        self.gauge = wx.Gauge (self, -1, 100, gauge_pos, gauge_size)
        # bindings
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Show()

    def get_gauge_dimensions(self):
        """Get gauge position and dimensions"""
        c = self.GetFieldsCount()
        pos_x, pos_y, dim_x, dim_y = self.GetFieldRect(c-1)
        return (pos_x, pos_y), (dim_x, dim_y)
        
    def on_size(self, event):
        """Resize gauge when the main frame is resized"""
        size = self.GetSize()
        self.SetSize(size)
        gauge_pos, gauge_size = self.get_gauge_dimensions()
        self.gauge.SetSize(gauge_size)
        event.Skip()       
        self.Update()
 
    def SetValue(self, value):
        self.gauge.SetValue(value)

class RoundGauge(wx.Panel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer)
        self.width = 15
        self.value = 0
        self.SetRange(0, 100)
        self.SetArc(135, 405)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.SetDoubleBuffered(True)
        self.font = wx.Font(kwargs.get('font_size', 12), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        self.bgColor = '#707070'
        self.fgColor = '#20d020'
        self.valueSuffix = '%'
        self.SetTransparent(0)

    def onTimer(self, event):
        # smooooooooove
        cutoff = (self.max - self.min) / 500
        delta = self.targetValue - self.value
        step = math.copysign(max(cutoff, abs(delta) *.08), delta)
        if abs(delta) < cutoff:
            self.value = self.targetValue
            self.timer.Stop()
        else:
            self.value += math.copysign(step, delta)
        self.Refresh()
        

    def SetArc(self, start, end):
        self.arcStart = start
        self.arcEnd = end

    def SetRange(self, min, max):
        self.min = min
        self.max = max
        self.SetValue(self.value) # for range checking
        self.Refresh()

    def SetValue(self, val):
        val = int(val)
        self.targetValue = val
        self.targetValue = max(self.min, self.targetValue)
        self.targetValue = min(self.max, self.targetValue)
        self.timer.Start(5)
        self.Refresh()

    def SetWidth(self):
        self.width = width

    def OnPaint(self, event=None):
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(wx.WHITE, wx.TRANSPARENT))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        self.Draw(gc)

    def Draw(self, gc):
        size = gc.GetSize()

        center = [i//2 for i in size]
        radius = min(size)//2 - self.width//1.8

        # background
        radStart = math.radians(self.arcStart)
        radEnd = math.radians(self.arcEnd)
        path = gc.CreatePath()
        path.AddArc(*center, radius, radStart, radEnd, True)
        pen = wx.Pen(self.bgColor, self.width)
        pen.SetCap(wx.CAP_BUTT)
        gc.SetPen(pen)
        gc.SetBrush(wx.Brush('#000000', wx.TRANSPARENT))
        gc.DrawPath(path)

        #progress bar
        pct = self.value / (self.max - self.min)
        end = (self.arcEnd - self.arcStart) * pct + self.arcStart
        start = math.radians(self.arcStart)
        end = math.radians(end)
        path = gc.CreatePath()
        path.AddArc(*center, radius, start, end, True)
        pen = wx.Pen(self.fgColor, self.width)
        pen.SetCap(wx.CAP_BUTT)
        gc.SetPen(pen)
        gc.SetBrush(wx.Brush('#000000', wx.TRANSPARENT))
        gc.DrawPath(path)

        #text

        gc.SetFont(self.font, '#000000')
        s = str(int(self.value)) + self.valueSuffix
        w,h = self.GetTextExtent(s)
        x,y = center[0] - w // 2, center[1] - h // 2

        gc.DrawText(s, x,y)

class ChildIter:
    ignoredNames = {
        'staticText', 
        'panel', 
        'GridWindow', 
        'text', 
        'wxSpinButton',
        'groupBox', 
        'scrolledpanel',
        }
    ignoredRE = [
        re.compile(r'^.*?_btn$')
    ]

    class Brk(Exception): pass

    @classmethod
    def iter(cls, w):
        for c in w.GetChildren():
            yield c
            yield from cls.iter(c)

    @classmethod
    def iterNamed(cls, w):
        for c in cls.iter(w):
            try:
                if c.Name in cls.ignoredNames: raise cls.Brk()
                for r in cls.ignoredRE:
                    if r.match(c.Name): raise cls.Brk()
                yield c
            except cls.Brk:
                pass

class Main(wx.Frame):
    ntc_RE = re.compile(r'ntc\d+')
    def __init__(self, *args, **kwargs):
        kwargs['style'] = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        wx.Frame.__init__(self, *args, **kwargs)

        self.j = jbd.JBD(serial.Serial('COM4'))
        #self.j = jbd.JBD(serial.Serial('/dev/ttyUSB0'))

        font = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.SetFont(font)

        layout = LayoutGen(self)

        # tabs layout
        nb_panel = wx.Panel(self)

        nb = wx.Notebook(nb_panel)
        self.infoTab = wx.Panel(nb)
        self.settingsTab = wx.Panel(nb)

        layout.infoTabLayout(self.infoTab)
        layout.settingsTabLayout(self.settingsTab)

        nb.AddPage(self.infoTab, 'Info')
        nb.AddPage(self.settingsTab, 'Settings')

        for c in ChildIter.iterNamed(self.settingsTab):
            c.Name = 'eeprom_' + c.Name

        for c in ChildIter.iterNamed(self.infoTab):
            c.Name = 'info_' + c.Name

        for name, r in ranges.items():
            name = 'eeprom_'+name
            w = self.FindWindowByName(name)
            if not w:
                print(f'unknown control {name}')
                continue
            try:
                min, max, increment = r
                w.SetRange(min, max)
                w.SetIncrement(increment)
            except Exception as e:
                print(f'unable to call SetRange on {name}')

        nb_sizer = wx.BoxSizer()
        nb_sizer.Add(nb, 1, wx.EXPAND | wx.ALL, 5)
        nb_panel.SetSizer(nb_sizer)

        # self layout

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(nb_panel, 1, wx.EXPAND)
        self.SetSizer(sizer)

        testButton = wx.Button(self, label='Test', name = 'test_btn')
        self.Bind(wx.EVT_BUTTON, self.onButtonClick)
        bot_sizer = wx.FlexGridSizer(4)
        bot_sizer.Add(wx.StaticText(self, name='status_txt'), 1, wx.ALIGN_CENTER_VERTICAL |wx.TEXT_ALIGNMENT_LEFT)
        bot_sizer.Add(testButton, 1, wx.TEXT_ALIGNMENT_CENTER)
        bot_sizer.Add(wx.StaticText(self, name='serial_txt'), 1, wx.ALIGN_CENTER_VERTICAL |wx.TEXT_ALIGNMENT_CENTER)
        t = wx.StaticText(self, name='date_time_txt')
        t.SetBackgroundColour(wx.GREEN)
        bot_sizer.Add(t, 1, wx.ALIGN_CENTER_VERTICAL | wx.TEXT_ALIGNMENT_RIGHT)
        for c in range(bot_sizer.Cols):
            bot_sizer.AddGrowableCol(c)

        sizer.Add(bot_sizer, 0, wx.EXPAND | wx.ALL, 5)

        p = ProgressBar(self)
        self.SetStatusBar(p)

        self.Bind(EepromWorker.EVT_EEP_PROG, self.onProgress)
        self.Bind(EepromWorker.EVT_EEP_DONE, self.onEepromDone)

        # ---

        def sizeFix(event):
            # https://trac.wxwidgets.org/ticket/16088#comment:4
            win = event.GetEventObject()
            win.GetSizer().SetSizeHints(self)
            win.Bind(wx.EVT_SHOW, None)

        self.Bind(wx.EVT_SHOW, sizeFix)

        self.setupClockTimer()

    def readEeprom(self):
        worker = EepromWorker(self, self.j)
        worker.run(worker.readEeprom)

    def writeEeprom(self):
        data = {}
        for c in ChildIter.iterNamed(self):
            if not c.Name.startswith('eeprom_'): continue
            n = c.Name[7:]
            data[n] = self.get(c.Name)
        worker = EepromWorker(self, self.j)
        worker.run(worker.writeEeprom, data)

    def readInfo(self):
        basicInfo = self.j.readBasicInfo()
        cellInfo = self.j.readCellInfo()
        deviceInfo = self.j.readDeviceInfo()
        temps = [v for k,v in basicInfo.items() if self.ntc_RE.match(k) and v is not None]
        bals  = [v for k,v in basicInfo.items() if k.startswith('bal') and v is not None]
        volts = [v for v in cellInfo.values() if v is not None]
        
        # Populate cell grid
        grid = self.FindWindowByName('info_cell_grid')
        gridRowsNeeded = max(len(volts), len(temps))
        gridRowsCurrent = grid.GetNumberRows()
        if gridRowsNeeded != gridRowsCurrent:
            grid.DeleteRows(numRows = gridRowsCurrent)
            grid.InsertRows(numRows = gridRowsNeeded)

        for i in range(gridRowsNeeded):
            grid.SetCellValue(i, 0, str(i))
            grid.SetCellValue(i, 1, str(volts[i]) if i < len(volts) else '')
            grid.SetCellValue(i, 2, 'BAL' if i < len(bals) and bals[i] else '--')
            grid.SetCellValue(i, 3, str(temps[i]) if i < len(temps) else '')


        cell_max_mv = max(volts)
        cell_min_mv = min(volts)
        cell_delta_mv = cell_max_mv - cell_min_mv
        self.set('info_pack_mv', basicInfo['pack_mv'])
        self.set('info_pack_ma', basicInfo['pack_ma'])
        self.set('info_cell_avg_mv', sum(volts) // len(volts))
        self.set('info_cell_max_mv', cell_max_mv)
        self.set('info_cell_min_mv', cell_min_mv)
        self.set('info_cell_delta_mv', cell_delta_mv)
        self.set('info_cycle_cnt', basicInfo['cycle_cnt'])
        self.set('info_cap_nom', basicInfo['cap_nom'])
        self.set('info_cap_rem', basicInfo['cap_rem'])
        self.set('info_cap_pct', basicInfo['cap_pct'])

        self.set('info_device_name', deviceInfo['device_name'])
        date = f"{basicInfo['year']}-{basicInfo['month']}-{basicInfo['day']}"
        self.set('info_mfg_date', date)
        self.set('info_version', f"0x{basicInfo['version']:02X}")

        pprint(basicInfo)

        cfe = basicInfo['chg_fet_en']
        dfe = basicInfo['dsg_fet_en']
        self.set('info_chg_fet_status_txt', 'ENABLED' if cfe else 'DISABLED')
        self.set('info_dsg_fet_status_txt', 'ENABLED' if dfe else 'DISABLED')
        self.set('info_chg_fet_status_img', cfe)
        self.set('info_dsg_fet_status_img', dfe)

        err_fn = [i for i in basicInfo.keys() if i.endswith('_err')]
        for f in err_fn:
            self.set('info_' + f,basicInfo[f])

    def onProgress(self, evt):
        self.GetStatusBar().SetValue(evt.value)

    def onEepromDone(self, evt):
        print('eeprom done')
        if isinstance(evt.data, Exception):
            traceback.print_tb(evt.data.__traceback__)
            print(f'eeprom error: {repr(evt.data)}')
        elif evt.data is not None:
            pprint(evt.data)
            for k,v in evt.data.items():
                self.set('eeprom_'+k,v)
            self.FindWindowByName('write_eeprom_btn').Enable(True)
            self.FindWindowByName('save_eeprom_btn').Enable(True)
        else:
            pass # was eeprom write ...

    def setupClockTimer(self):
        self.clockTimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer)
        self.clockTimer.Start(1000)

    def onTimer(self, event):
        t = self.FindWindowByName('date_time_txt')
        t.SetLabel(time.asctime())
        self.Layout()

    def set(self, name, value):
        svalue = str(value)
        w = self.FindWindowByName(name)
        if w is None:
            print(f'set: unknown field: {name}')
            return
        if (isinstance(w, wx.TextCtrl) or 
            isinstance(w, RoundGauge) or 
            isinstance(w, wx.SpinCtrlDouble)):
            w.SetValue(svalue)
        elif isinstance(w, wx.StaticText):
            w.SetLabel(svalue)
        elif (isinstance(w, BoolImage) or 
              isinstance(w, wx.CheckBox) or 
              isinstance(w, BetterChoice)):
            w.SetValue(value)
        else:
            print(f'set: unknown control type: {type(w)}')

    def get(self, name):
        w = self.FindWindowByName(name)
        if w is None:
            print(f'get: unknown field: {name}')
            return
        if (isinstance(w, EnumChoice) or 
            isinstance(w, wx.TextCtrl) or 
            isinstance(w, wx.SpinCtrlDouble) or 
            isinstance(w, wx.CheckBox) or
            isinstance(w, BetterChoice)):
            return w.GetValue()
        elif isinstance(w, wx.StaticText):
            return None
        else:
            print(f'get: unknown control type {type(w)}, name: {w.Name}')

    def onButtonClick(self, evt):
        n = evt.EventObject.Name
        
        if n == 'read_eeprom_btn':
            self.readEeprom()
        elif n == 'write_eeprom_btn':
            self.writeEeprom()
        elif n == 'load_eeprom_btn':
            self.loadEeprom()
        elif n == 'save_eeprom_btn':
            self.saveEeprom()
        elif n == 'test_btn':
            print('skipping read info -- validate')
            #self.readInfo()
            self.Validate()
        elif n == 'clear_errors_btn':
            self.clearErrors()
        else:
            print(f'unknown button {n}')

    def loadEeprom(self):
        self.j.loadEepromFile('factory.fig')

    def clearErrors(self):
        try:
            self.j.clearErrors()

            for c in ChildIter.iterNamed(self):
                if not c.Name.endswith('_err_cnt'): continue
                if not c.Name.startswith('eeprom_'): continue
                print(c.Name)
                c.SetLabel('0')
        except jbd.BMSError:
            self.setStatus('BMS comm error')

    def setStatus(self, t):
        self.GetStatusBar().SetStatusText(t)

class EepromWorker:
    EepProg, EVT_EEP_PROG = wx.lib.newevent.NewEvent()
    EepDone, EVT_EEP_DONE = wx.lib.newevent.NewEvent()

    def __init__(self, parent, jbd):
        self.parent = parent
        self.j = jbd
        self.thr = None

    def progress(self, value):
        wx.PostEvent(self.parent, self.EepProg(value = value))

    def readEeprom(self):
        try:
            data = self.j.readEeprom(self.progress)
            wx.PostEvent(self.parent, self.EepDone(data = data))
        except Exception as e:
            wx.PostEvent(self.parent, self.EepDone(data = e))
        finally:
            wx.PostEvent(self.parent, self.EepProg(value = 100))

    def writeEeprom(self, data):
        try:
            self.j.writeEeprom(data, self.progress)
            wx.PostEvent(self.parent, self.EepDone(data = None))
        except Exception as e:
            wx.PostEvent(self.parent, self.EepDone(data = e))
        finally:
            wx.PostEvent(self.parent, self.EepProg(value = 100))

    def run(self, func, *args, **kwargs):
        self.thr = threading.Thread(target = func, args = args, kwargs = kwargs)
        self.thr.start()

    def join(self):
        if not thr: return True
        thr.join(1)
        return not thr.is_alive()



appName = 'BMS Tools'
appVersion = '0.0.1-alpha'
releaseDate = 'N/A'

    
class MyApp(wx.App):
    def OnInit(self):
        frame = Main(None, title = f'{appName} {appVersion}',style = wx.DEFAULT_FRAME_STYLE | wx.WS_EX_VALIDATE_RECURSIVELY )
        frame.SetIcon(wx.Icon(os.path.join(base_path, 'img', 'batt_icon_128.ico')))
        frame.Show()
        return True

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()