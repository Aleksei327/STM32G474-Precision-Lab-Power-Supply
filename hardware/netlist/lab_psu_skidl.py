#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Лабораторный БП 0-50В — генератор KiCad НЕТЛИСТА (и черновой схемы) через SKiDL.
Символы: СТОКОВЫЕ библиотеки KiCad 10 для всех деталей; 4 чипа (UCC27211/OPA454/
DAC8830/MP9486A) — рисованные из lab_psu_chips.kicad_sym; модуль WeAct — из Library.kicad_sym.
Реле/энкодеры/транс представлены стоковыми коннекторами/трансформатором (модули на гребёнках).

Запуск:  python lab_psu_skidl.py            (нетлист + черновая схема со stub-метками)
         python lab_psu_skidl.py --no-sch   (только нетлист, быстро)
Выход:   lab_psu.net + lab_psu_skidl*.kicad_sch
"""
import os, io, sys
os.environ['KICAD8_SYMBOL_DIR'] = r'C:\Program Files\KiCad\10.0\share\kicad\symbols'
from skidl import (Part, Net, Group, generate_netlist, generate_schematic,
                   set_default_tool, lib_search_paths, KICAD8)

HERE = os.path.dirname(os.path.abspath(__file__))
WEACT_LIB_DIR = r'D:\Документы\Power_Charg_AUTO_12V'
set_default_tool(KICAD8)
lib_search_paths[KICAD8].append(HERE)            # lab_psu_chips.kicad_sym
lib_search_paths[KICAD8].append(WEACT_LIB_DIR)   # Library.kicad_sym (модуль WeAct)

class _NetDict:
    def __init__(self): self._d = {}
    def __getitem__(self, k):
        if k not in self._d: self._d[k] = Net(k)
        return self._d[k]
    def __setitem__(self, k, v): pass
N = _NetDict()

import contextlib
@contextlib.contextmanager
def Blk(name):                       # тегирует все детали блока (для кластерной раскладки)
    before = {id(p) for p in default_circuit.parts}
    yield
    for p in default_circuit.parts:
        if id(p) not in before and not getattr(p, 'blk', None):
            p.blk = name

# ---- фабрики на СТОКОВЫХ символах KiCad ----
def R(v, fp='Resistor_SMD:R_1206_3216Metric'):  return Part('Device','R', value=v, footprint=fp)  # общие R = 1206 (3мм)
def Rp(v, fp='Resistor_SMD:R_2512_6332Metric'): return Part('Device','R', value=v, footprint=fp)
def C(v, fp='Capacitor_SMD:C_1206_3216Metric'): return Part('Device','C', value=v, footprint=fp)  # керамика по умолчанию 1206 (удобно паять; v0.2.20)
def Cc(v, fp='Capacitor_SMD:C_1210_3225Metric'):return Part('Device','C', value=v, footprint=fp)
def CP(v, fp='Capacitor_THT:CP_Radial_D10.0mm_P5.00mm'): return Part('Device','C_Polarized', value=v, footprint=fp)
def D(v='1N4148', fp='Local:D_SOD-323_HandSolder'):    return Part('Device','D', value=v, footprint=fp)  # SOD-323 с удлинёнными падами под ручную пайку (v0.2.19)
def Dp(v, fp='Diode_THT:D_DO-201AD_P15.24mm_Horizontal'): return Part('Device','D', value=v, footprint=fp)
def Z(v, fp='Diode_SMD:D_SOD-123'):             return Part('Device','D_Zener', value=v, footprint=fp)
def TVS(v, fp='Diode_THT:D_DO-201AD_P15.24mm_Horizontal'): return Part('Device','D_TVS', value=v, footprint=fp)
def L(v, fp='Inductor_THT:L_Toroid_Horizontal_D17.3mm_P15.24mm_Bourns_2000'): return Part('Device','L', value=v, footprint=fp)
def NMOS(v, fp='Package_TO_SOT_THT:TO-220-3_Vertical'): return Part('Transistor_FET','Q_NMOS_GDS', value=v, footprint=fp)
def NPN(v, fp='Package_TO_SOT_THT:TO-126-3_Vertical'): return Part('Transistor_BJT','BD139', value=v, footprint=fp)  # 1=E 2=C 3=B
def Fuse(v, fp='Fuse:Fuseholder_Clip-5x20mm_Littelfuse_100_Inline_P20.50x4.60mm_D1.30mm_Horizontal'): return Part('Device','Fuse', value=v, footprint=fp)
def LED(v, fp='LED_SMD:LED_0805_2012Metric'):   return Part('Device','LED', value=v, footprint=fp)
def Jn(n, fp, val):  return Part('Connector_Generic', 'Conn_01x%02d'%n, value=val, footprint=fp)
SOIC8 = 'Local:SOIC-8_3.9x4.9mm_P1.27mm_Pad0.8mm'   # v0.2.28: лапки 0,8мм вместо 0,6 (ручная пайка, домашнее травление);
                                                     # позиции пятаков стоковые -> разводка не поехала
MSOP8 = 'Package_SO:MSOP-8_3x3mm_P0.65mm'
def CHIP(name, fp=SOIC8):   # рисованный символ из lab_psu_chips.kicad_sym (пинаут подтверждён)
    return Part('lab_psu_chips', name, value=name, footprint=fp, ref_prefix='U')

# ================= Модуль WeAct (верхний уровень: его цепи глобальны) =================
MOD = {1:'GND',2:'GND',3:'3V3',4:'3V3',5:'BUZZER',6:'ENC2_B',7:'V_USB',8:'REV_DET',
 9:'I_OPAMP_OUT',10:'ENC2_A',11:'VTERM_SENSE',12:'NTC',13:'VIN_SENSE',14:'VDRAIN_SENSE',
 15:'RAILS_BTN',16:'I_SENSE_LO',17:'I_OPAMP_OUT',18:'I_SENSE_HI',19:'VOUT_SENSE',
 20:'NRST',22:'3V3',23:'3V3',24:'GND',25:'GND',26:'GND',27:'5VSB',28:'5VSB',   # пин 21 (PC13) НЕ подключён (v0.2.11): no-connect; KEY-кнопка живёт на модуле
 29:'DAC_V_SYNC',30:'SPI2_SCK',31:'ENC2_BTN',32:'SPI2_DIN',33:'BTN_OUT',34:'PWM_H',35:'PWM_L',
 36:'ENC1_A',37:'USB_DM',38:'USB_DP',39:'RELAY_DRV',40:'ENC1_B',41:'ENC1_BTN',42:'SPI1_SCK',
 43:'TFT_RST',44:'SPI1_MOSI',45:'TFT_CS',46:'TFT_DC',47:'FAN_DRV',48:'GND'}
SWD = {'G':'GND','CLK':'I2C1_SDA','DIO':'I2C1_SCL','3V3':'3V3'}
mcu = Part('Library', 'WeAct_STM32G474CEU6_MiniCore', ref_prefix='U',
           footprint='Local:WeAct_STM32G474CEU6_MiniCore')
for p in MOD: N[MOD[p]] += mcu[p]
for k in SWD: N[SWD[k]] += mcu[k]
mcu.blk = 'MCU'
for g in ['GND','3V3','5VSB','5V_VCC','V12','VIN_55','VDRAIN','VOUT_REG','OUT_MINUS',
          'OUT_PLUS','OUT_PLUS_F','V_P67','V_N5','VREF_2V5','VSET','I2C1_SCL','I2C1_SDA']:
    _ = N[g]

# ================= Блок A — синхронный buck =================
with Blk('A_buck'):
    # v0.2.25: посадочные доработаны пользователем на плате (лапки шире 0,8мм + PowerPAD).
    # EP драйвера = подложка/VSS (даташит SLUSAT7B: "PowerPAD ... substrate which is the ground") -> пятак EP пронумерован "7".
    drv = CHIP('UCC27211', 'Local:UCC27211_HSOP-8-1EP_HandSolder')
    qh, ql = NMOS('IRFB4110'), NMOS('IRFB4110')
    # v0.2.27: намотан по факту — зелёное порошковое кольцо 25x15x10 из АТХ, 33 витка (17 старых 2x1мм + 16 домотанных 4x0.8мм),
    # измерено 31,34 мкГн (AL = 28,8 нГн/вит²). Под нагрузкой с учётом подмагничивания: ~22 мкГн при 5 А, ~19 мкГн при 7 А.
    lmain = L('31uH', 'Local:L_Toroid_Vertical_Core25x10mm_P14.00mm_D1.8mm'); dboot = D('HS1M','Diode_SMD:D_SMA'); cboot=C('1uF'); cvcc=C('10uF')  # boot-диод >=100В! (HS1M 1кВ fast из запасов; SS14 40В видит ~55В реверса)
    rgh, rgl = Rp('10'), Rp('10'); rgsh, rgsl = R('10k'), R('10k')
    rhin, rlin, rpdh, rpdl = R('220'), R('220'), R('10k'), R('10k')
    C106 = 'Capacitor_SMD:C_1206_3216Metric'   # доступная керамика: 4,7µФ/100В 1206
    CP18 = 'Capacitor_THT:CP_Radial_D18.0mm_P7.50mm'   # банки пользователя: Ø18мм, ножки ~8мм (v0.2.17)
    cin1, cin2 = CP('1000uF/100V',CP18), C('4.7uF/100V',C106); cout1, cout2 = CP('1000uF/100V',CP18), C('4.7uF/100V',C106)  # 10µФ 1210 -> 4,7µФ/100В 1206; доп. банки и П-фильтр — Блок X
    N['V12'] += drv['VDD'], dboot[2], cvcc[1]
    N['GND'] += drv['VSS'], cvcc[2], rpdh[2], rpdl[2]
    N['HI'] += drv['HI'], rhin[2], rpdh[1]; N['PWM_H'] += rhin[1]
    N['LI'] += drv['LI'], rlin[2], rpdl[1]; N['PWM_L'] += rlin[1]
    N['VB'] += drv['HB'], dboot[1], cboot[1]
    N['SW'] += drv['HS'], cboot[2], qh['S'], ql['D'], lmain[1]
    N['GATE_QH'] += drv['HO'], rgh[1]; rgh[2] += qh['G'], rgsh[1]; rgsh[2] += N['SW']
    N['GATE_QL'] += drv['LO'], rgl[1]; rgl[2] += ql['G'], rgsl[1]; rgsl[2] += N['GND']
    N['VIN_55'] += qh['D'], cin1[1], cin2[1]
    N['GND'] += cin1[2], cin2[2], ql['S'], cout1[2], cout2[2]
    N['VBUCK_OUT'] += lmain[2], cout1[1], cout2[1]   # банка buck (до П-фильтра; сам П-фильтр — Блок X)

# ================= Блок B — проходной =================
with Blk('B_pass'):
    qpass = NMOS('IRFB4110'); rgs = Rp('22', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal')
    zgs = Z('15V', 'Diode_THT:D_DO-35_SOD27_P10.16mm_Horizontal')   # стекляшка DO-35 (есть у пользователя)
    N['VDRAIN'] += qpass['D']
    N['GATE_PASS'] += rgs[1]; rgs[2] += qpass['G'], zgs[1]
    N['VOUT_REG'] += qpass['S'], zgs[2]
    rt0, rb0, rs0, cf0 = R('180k'), R('10k'), R('4k7'), C('100nF')   # 180k как у PA5: иначе PA0 сатурирует выше ~36В
    N['VOUT_REG'] += rt0[1]; N['VS0'] += rt0[2], rb0[1], rs0[1]; N['GND'] += rb0[2], cf0[2]
    N['VOUT_SENSE'] += rs0[2], cf0[1]
    dvo_h, dvo_l = D('BAT'), D('BAT')   # ESD/кламп ADC-входа к 3V3/GND (рек. ST)
    N['3V3'] += dvo_h[1]; N['VOUT_SENSE'] += dvo_h[2], dvo_l[1]; N['GND'] += dvo_l[2]
    # делитель VDRAIN (PA5) для трекинга Vds: 180k/10k -> ~2.8В при 53В; series+фильтр+клампы
    rda, rdb, rds, cd = R('180k'), R('10k'), R('4k7'), C('100nF')
    N['VDRAIN'] += rda[1]; N['VDS0'] += rda[2], rdb[1], rds[1]; N['GND'] += rdb[2], cd[2]
    N['VDRAIN_SENSE'] += rds[2], cd[1]
    dvd_h, dvd_l = D('BAT'), D('BAT')
    N['3V3'] += dvd_h[1]; N['VDRAIN_SENSE'] += dvd_h[2], dvd_l[1]; N['GND'] += dvd_l[2]

# ================= Блок C — линейник + преднагрузка =================
with Blk('C_linear'):
    # v0.2.25: OPA454 = корпус DDA (SO-8 PowerPAD)! Даташит SBOS391: PowerPAD внутри соединён с V-,
    # "Soldering the PowerPAD to the PCB is always required" -> HSOP-8-1EP, пятак EP пронумерован "4" (=V-, наш -5В!).
    # ВАЖНО: EP под брюхом = -5В, не земля -> держать зазор от GND-полигона.
    opa = CHIP('OPA454', 'Local:OPA454_HSOP-8-1EP_HandSolder')
    O805 = 'Resistor_SMD:R_0805_2012Metric'
    rf, rg = R('110k', O805), R('5k1', O805)   # прецизионный делитель ОС 0,1% -> 0805 (2мм)
    ccmp, ren = C('33pF'), R('100k')
    cp67, cn5 = C('100nF'), C('100nF')
    cld1, cld2 = C('4.7uF/100V','Capacitor_SMD:C_1206_3216Metric'), C('4.7uF/100V','Capacitor_SMD:C_1206_3216Metric')  # выход линейника: 2× керамика (бак-электролит — на buck)
    N['V_P67'] += opa['V+'], cp67[1], ren[2]; N['V_N5'] += opa['V-'], cn5[1]
    N['VSET'] += opa['+IN']; N['FB_LIN'] += opa['-IN'], rf[2], rg[1], ccmp[2]
    N['GATE_PASS'] += opa['OUT'], ccmp[1]; N['EN_LIN'] += opa['E/D'], ren[1]
    N['GND'] += opa['E/D_COM']
    N['VOUT_REG'] += rf[1], cld1[1], cld2[1]; N['GND'] += rg[2], cld1[2], cld2[2], cp67[2], cn5[2]
    # v0.2.24: зенера 2V5 нет в запасах -> TL431 (REF+K вместе = стабилитрон 2,495В, колено резче зенера).
    # Корпус TO-92 в посадочное TO-126 (как BD139): средний пин 2 = A, крайние 1(REF)/3(K) на одной цепи -> встаёт любой стороной.
    # rfpl 2к->1к: ток катода ~2,3мА (мин. TL431 = 1мА, с 2к было бы ~1,05мА — впритык).
    # cpl 100нФ->470пФ: 1нФ..2мкФ на катоде — зона неустойчивости TL431 (даташит), 470пФ ниже зоны.
    qpl = NPN('MJE340'); re=R('300'); rfpl=R('1k'); cpl=C('470pF')
    zpl = Part('Reference_Voltage','TL431LP', value='TL431', ref_prefix='D',
               footprint='Package_TO_SOT_THT:TO-126-3_Vertical')   # ref_prefix='D': остаётся D7, нумерация не едет
    N['VOUT_REG'] += qpl['C']; qpl['E'] += re[1]; N['V_N5'] += re[2], zpl[2], cpl[2]
    N['PRELOAD_B'] += qpl['B'], zpl[1], zpl[3], rfpl[2], cpl[1]; N['GND'] += rfpl[1]  # v0.2.24: узел именован (метки в схеме на проводах пользователя)

# ================= Блок D — токовый (INA228) =================
with Blk('D_current'):
    rsh1 = Rp('10m', 'Local:Shunt_Constantan_Staple_P20mm')   # v0.2.13: ОДНА константановая скоба ~10 мОм (d1,5мм, шаг 20мм); PGA OPAMP1 -> x8, порог COMP 250мВ@25А
    # v0.2.18: rsh2/rsh3 (запасные 2512) удалены — шунт один, константановая скоба
    rinp, rinm, cdiff = R('220'), R('220'), C('1nF')
    ina = Part('Sensor_Energy','INA228', value='INA228',
               footprint='Local:INA228_Module_1x08')   # v0.2.12: Adafruit-модуль на гребёнке 1x8; R015 с модуля ВЫПАЯТЬ, перемычку VBUS-VIN+ разомкнуть, Addr не мостить (0x40)
    rscl, rsda, cina = R('4k7'), R('4k7'), C('100nF')
    N['OUT_MINUS'] += rsh1[1], rinp[1], ina['Vin+']
    N['GND'] += rsh1[2], rinm[1], ina['Vin-']
    N['I_SENSE_HI'] += rinp[2], cdiff[1]; N['I_SENSE_LO'] += rinm[2], cdiff[2]
    N['VBUS_INA'] += ina['Vbus']   # v0.2.5: пин за R 470 Ом; линия VBUS_SENSE (K91: откл->VOUT_REG, вкл->клеммы) + кламп SS110 — Блок X
    N['3V3'] += ina['VS'], cina[1], rscl[2], rsda[2]; N['GND'] += ina['GND'], cina[2], ina['A0'], ina['A1']  # A0=A1=GND -> адрес 0x40
    N['I2C1_SCL'] += ina['SCL'], rscl[1]; N['I2C1_SDA'] += ina['SDA'], rsda[1]

# ================= Блок E — уставка V (REF5025 + DAC8830) =================
with Blk('E_vset'):
    ref = Part('Reference_Voltage','REF5025AD', value='REF5025', footprint=SOIC8)
    cref1, cref2 = C('100nF'), C('1uF')
    dac = CHIP('DAC8830'); cdac = C('100nF')   # v0.2.28: корпус SOIC-8, а НЕ MSOP (у пользователя обычная 8-ногая SMD без пузика)
    # OPA2188-буфер УБРАН: DAC8830 (выход 0..VREF) грузится только на высокоомный +IN OPA454
    N['5VSB'] += ref['Vin']; N['VREF_2V5'] += ref['Vout'], cref1[1], cref2[1], dac['VREF']
    N['GND'] += ref['GND'], cref1[2], cref2[2], dac['AGND'], dac['DGND'], cdac[2]
    N['3V3'] += dac['VDD'], cdac[1]
    N['SPI2_SCK'] += dac['SCLK']; N['SPI2_DIN'] += dac['SDI']; N['DAC_V_SYNC'] += dac['CS']
    N['VSET'] += dac['VOUT']

# ================= Блок F — реле/защиты/звук =================
with Blk('F_protect'):
    krel = Part('Relay','Relay_SPST-NO', value='MPH-S-112-A-2F', ref_prefix='K',
                footprint='Local:Relay_MPH_1A')  # 1×Form A; 13/14=контакт NO, A1/A2=катушка; футпринт кастомный под MPH (4 выв. Ø1.3)
    qrel = NPN('BD139'); drel = Dp('1N4007'); rbrel = R('1k')   # 1к: две катушки (K90+K91 ~65мА) — запас насыщения BD139
    dclamp = Dp('SR5100')  # кламп ДО реле: ток только импульсный -> осевой цилиндрик быстрый/Шоттки (DO-201AD ~5×9мм), 5А ок; опц. 2 в параллель
    tvs = TVS('1.5KE56A'); fout = Fuse('15A'); rbleed = Rp('15k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal')   # 15А: 1,4-1,6x от рабочих 10А; керамика 5x20 (не стекло: дуга 50В DC)
    rsnub, csnub = Rp('47', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'), C('100nF/250V','Capacitor_SMD:C_1206_3216Metric')   # RC-снаббер на контакты реле
    PC817 = Part('Isolator','PC817', footprint='Package_DIP:DIP-4_W7.62mm', value='PC817')
    rrev, dser, rpull, crev = Rp('6k8', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'), D('1N4148', 'Diode_THT:D_DO-35_SOD27_P10.16mm_Horizontal'), R('10k'), C('10nF')   # rpull 10к (не 47к): на PB2 модуля висит синий LED через 5,1к — жёсткий HIGH
    ntc, rpu, rser_n, cntc = R('10k_NTC', 'Local:NTC_THT_P7.00mm_Pad2.0mm_D0.6mm'), R('10k'), R('1k'), C('100nF')
    # v0.2.31: термистор выводной — впаивается проводами прямо в плату (несъёмный, разъём не нужен);
    # пятаки Ø2 мм, шаг 7 мм, сверло 0,6 как везде. Сам термистор крепится на радиаторе проходного.
    jspk = Jn(2, 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', 'SPEAKER')   # v0.2.21: BD139-пищалка убрана -> PAM8403 (Блок X)
    jout = Part('Connector_Generic','Conn_01x02', value='OUT',
                footprint='TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm')
    N['VOUT_REG'] += krel['13']; N['OUT_PLUS_F'] += krel['14']
    N['V12'] += krel['A1'], drel[1]; N['RLY_COIL'] += krel['A2'], drel[2], qrel['C']
    # v0.2.33: база Q5 висела без подтяжки, а трасса RELAY_DRV от модуля до неё ~120 мм.
    # Пока МК в ресете, PA15 = высокоимпедансный вход -> наводка могла приоткрыть BD139 = САМОПРОИЗВОЛЬНОЕ
    # включение реле (подача напряжения на клеммы!). Ставим 10к Б-Э + 10нФ Б-Э прямо у транзистора:
    # 10к держит базу прижатой (потеря тока базы всего 75 мкА из 2,55 мА — насыщение не страдает),
    # 10нФ убивает ёмкостную наводку с дорожки (заряд импульса даёт на нём милливольты вместо вольт;
    # постоянная с 1к = 10 мкс, для реле это ничто).
    # САМИ детали защиты созданы в Блоке X (в конце файла) — иначе поедет нумерация рефов!
    N['RELAY_DRV'] += rbrel[1]; N['RLY_BASE'] += rbrel[2], qrel['B']; N['GND'] += qrel['E']
    N['VOUT_REG'] += rsnub[1]; rsnub[2] += csnub[1]; N['OUT_PLUS_F'] += csnub[2]   # снаббер поперёк контактов реле
    # кламп + TVS — ДО реле, на узле VOUT_REG<->GND (при разомкнутом реле отрезаны от клемм)
    N['VOUT_REG'] += dclamp[1], tvs[1]; N['GND'] += dclamp[2], tvs[2]
    N['OUT_PLUS_F'] += fout[1]; N['OUT_PLUS'] += fout[2], jout[1]; N['OUT_MINUS'] += jout[2]
    N['VOUT_REG'] += rbleed[1]; N['GND'] += rbleed[2]
    N['OUT_MINUS'] += rrev[1]; rrev[2] += PC817[1]; PC817[2] += dser[2]; N['OUT_PLUS'] += dser[1]
    N['REV_DET'] += PC817[4], rpull[1], crev[1]; N['3V3'] += rpull[2]; N['GND'] += PC817[3], crev[2]
    N['3V3'] += rpu[1]; N['NTC_DIV'] += rpu[2], ntc[1], rser_n[1]; N['GND'] += ntc[2], cntc[2]
    N['NTC'] += rser_n[2], cntc[1]
    N['SPK_P'] += jspk[1]; N['SPK_N'] += jspk[2]   # динамик на выход PAM8403 (BTL), не на V12

# ================= Блок G — питание (MP9486A buck 12В + UC3845 флайбэк +67/-5) =================
with Blk('G_supply'):
    u12 = CHIP('MP9486A', 'Local:MP9486A_HSOP-8-1EP_HandSolder')   # v0.2.25: EP -> GND (даташит: "Connect the exposed pad to GND plane"), пятак EP пронумерован "8"
    l12 = L('68uH','Local:L_SMD_15x15mm'); d12 = D('SK59','Diode_SMD:D_SMC'); cin12, cout12 = CP('22uF/100V'), CP('47uF/25V')   # 68µH SMD 15x15 экранир. (v0.2.20); SK59 (SS510 нет; на SMC встанет и SMA)
    rfb12a, rfb12b = R('100k'), R('10k'); cbst = C('100nF'); ren1, ren2 = R('360k'), R('20k')
    N['VIN_55'] += u12['VIN'], cin12[1], ren1[1]; N['GND'] += u12['GND'], cin12[2], cout12[2], ren2[2]
    N['EN12'] += u12['EN'], ren1[2], ren2[1]
    N['SW12'] += u12['SW'], l12[1], d12[1], cbst[2]; N['GND'] += d12[2]
    N['BST12'] += u12['BST'], cbst[1]
    # v0.2.25 ИСПРАВЛЕНИЕ: DIM НЕЛЬЗЯ оставлять висящим! Даташит MP9486A: IDIM = ±1мкА (подтяжки НЕТ),
    # порог 0,8..1,5В, и прямо сказано: "If the dimming function is not needed... connect DIM and EN together".
    # Висящий DIM = ШИМ может быть заперт -> нет 12В -> нет ничего. Сажаем DIM на EN12 (2,9В с делителя).
    N['EN12'] += u12['DIM']
    N['V12'] += l12[2], cout12[1], rfb12a[1]; N['FB12'] += rfb12a[2], rfb12b[1], u12['FB']; N['GND'] += rfb12b[2]
    # v0.2.15: делитель V12_SENSE УДАЛЁН целиком (PC4 отдан VTERM_SENSE ещё в v0.2.1, тест-поинт был не нужен)
    rva,rvb,rvs,cv = R('180k'),R('22k'),R('4k7'),C('100nF')
    N['VIN_55'] += rva[1]; N['DVIN'] += rva[2], rvb[1], rvs[1]; N['GND'] += rvb[2], cv[2]; N['VIN_SENSE'] += rvs[2], cv[1]
    dvin_h, dvin_l = D('BAT'), D('BAT')   # ESD-клампы VIN_SENSE к 3V3/GND
    N['3V3'] += dvin_h[1]; N['VIN_SENSE'] += dvin_h[2], dvin_l[1]; N['GND'] += dvin_l[2]
    # --- неизолированный флайбэк UC3845: 12В -> +67 / -5 (рельсы OPA454) ---
    ufb = Part('Regulator_Controller','UC3843_SOIC8', value='UC3845', footprint=SOIC8)  # пинаут UC3843=UC3845; UC3845: Dmax~50% + Fosc/2
    qfb = NMOS('CS630', 'Package_TO_SOT_SMD:TO-252-2')          # ключ флайбэка: аналог IRF630 (200В/9А, DPAK у пользователя; если D2PAK ~10мм -> TO-263-2)
    t1 = Part('Device','Transformer_1P_2S', value='CFL_T1', ref_prefix='T',
              footprint='Local:Transformer_Flyback_EE16')  # 1,2=pri; 3=S67(+67) 4=GND 5=GND 6=S5(-5); center-tap, первичка/вторичка ПРОТИВОФАЗА (v0.2.20)
    rcs = Rp('0R82','Resistor_THT:R_Axial_DIN0411_L9.9mm_D3.6mm_P12.70mm_Horizontal'); rcsf, ccsf = R('1k'), C('470pF')   # CS-шунт: выводной 1Вт ~10мм (v0.2.20)
    rg_fb, rgpd = R('10'), R('10k'); rt, ct = R('10k'), C('910pF')   # UC3845 делит частоту /2 -> Ct вдвое меньше для Fsw~95кГц
    cvcc, cvcc2, cvref, cvref2 = CP('22uF/25V'), C('100nF'), C('1uF'), C('100nF')
    rfb_t, rfb_b = R('130k'), R('5k1')                          # ОС +67 -> FB (2.5В)
    cz, rz, cp = C('2.2nF'), R('10k'), C('220pF')               # компенсация COMP-FB
    d67, c67, c67b = Dp('UF4005','Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal'), CP('10uF/100V'), C('100nF')  # выпрямитель +67: UF4005 (600В, запасы; DO-41 5x2,5мм; v0.2.22)
    d5, c5, c5b = D('SS14','Diode_SMD:D_SMA'), CP('10uF/16V'), C('100nF')   # -5
    dsn, rsn, csn = Dp('UF4005','Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal'), R('22k'), C('1nF')   # RCD-снаббер: UF4005 DO-41 (v0.2.22)
    rpl67, rpl5 = R('15k', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'), R('1k')                             # преднагрузка
    N['V12'] += ufb['VCC'], t1[1], cvcc[1], cvcc2[1], rsn[1], csn[1]
    N['GND'] += ufb['GND'], cvcc[2], cvcc2[2]
    N['VREF5'] += ufb['VREF'], cvref[1], cvref2[1], rt[1]; N['GND'] += cvref[2], cvref2[2]
    N['RC_FB'] += ufb['RC'], rt[2], ct[1]; N['GND'] += ct[2]
    N['GATE_FB'] += ufb['OUT'], rg_fb[1]; rg_fb[2] += qfb['G'], rgpd[1]; N['GND'] += rgpd[2]
    N['SW_FB'] += t1[2], qfb['D'], dsn[2]                       # дрейн ключа
    N['FB_CLAMP'] += dsn[1], rsn[2], csn[2]                     # RCD кламп
    N['ISENSE_FB'] += qfb['S'], rcs[1], rcsf[1]; N['GND'] += rcs[2]
    N['CS_FB'] += ufb['CS'], rcsf[2], ccsf[1]; N['GND'] += ccsf[2]
    N['S67'] += t1[3], d67[2]                                   # +67: обмотка -> диод
    N['V_P67R'] += d67[1], c67[1], c67b[1], rfb_t[1]            # v0.2.23: сырой узел до RC-фильтра; ОС ЗДЕСЬ (вне петли UC3845 — без резонанса)
    N['V_P67'] += rpl67[1]                                      # преднагрузка ПОСЛЕ фильтра (перенёс пользователь; +0,2В падения на R фильтра — не важно)
    N['GND'] += t1[4], c67[2], c67b[2], rpl67[2]
    N['FB67'] += rfb_t[2], rfb_b[1], ufb['FB'], cp[2], rz[2]; N['GND'] += rfb_b[2]
    N['COMP_FB'] += ufb['COMP'], cp[1], cz[1]; cz[2] += rz[1]
    N['S5'] += t1[6], d5[1]                                     # -5: обмотка -> диод (реверс)
    N['V_N5R'] += d5[2], c5[2], c5b[2]                          # v0.2.23: сырой узел до RC-фильтра
    N['V_N5'] += rpl5[2]                                        # преднагрузка ПОСЛЕ фильтра (как на +67)
    N['GND'] += t1[5], c5[1], c5b[1], rpl5[1]

# ================= Блок H — UI =================
with Blk('H_ui'):
    jtft = Jn(8, 'Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical', 'TFT')
    enc1 = Jn(5, 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical', 'ENC1')  # 1=A 2=C 3=B 4=S1 5=S2
    enc2 = Jn(5, 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical', 'ENC2')
    swout = Part('Switch','SW_Push', value='OUT', footprint='Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical')  # v0.2.23: кнопка на ПАНЕЛИ, на плате штекер 1x02
    # USB-разъём УБРАН: USB берём с модуля G474 на панель. ESD — дискретные шоттки 1206 (сборки нет), D+/D- к 3V3/GND.
    edp_h, edp_l = D('BAT'), D('BAT')
    edm_h, edm_l = D('BAT'), D('BAT')
    rbl = R('100')   # ключ подсветки TFT; v0.2.18: led/rled удалены совсем (PC13 = кнопка модуля, no-connect)
    N['GND'] += jtft[1]; N['5VSB'] += jtft[2]; N['SPI1_SCK'] += jtft[3]; N['SPI1_MOSI'] += jtft[4]   # VCC дисплея = 5VSB (v0.2.10): подсветка MSP3520 ~120мА идёт от VCC через бортовой S8050; LDO модуля разгружен; SPI-логика 3,3В совместима
    N['TFT_RST'] += jtft[5]; N['TFT_CS'] += jtft[6]; N['TFT_DC'] += jtft[7]
    N['3V3'] += rbl[1]; N['TFT_BL'] += rbl[2], jtft[8]
    re1a,re1b,re1s = R('10k'),R('10k'),R('10k')
    N['ENC1_A'] += enc1[1], re1a[1]; N['ENC1_B'] += enc1[3], re1b[1]; N['GND'] += enc1[2]
    N['ENC1_BTN'] += enc1[4], re1s[1]; N['GND'] += enc1[5]; N['3V3'] += re1a[2], re1b[2], re1s[2]
    re2a,re2b,re2s = R('10k'),R('10k'),R('10k')
    N['ENC2_A'] += enc2[1], re2a[1]; N['ENC2_B'] += enc2[3], re2b[1]; N['GND'] += enc2[2]
    N['ENC2_BTN'] += enc2[4], re2s[1]; N['GND'] += enc2[5]; N['3V3'] += re2a[2], re2b[2], re2s[2]
    rob = R('10k'); N['BTN_OUT'] += swout[1], rob[1]; N['GND'] += swout[2]; N['3V3'] += rob[2]
    # ESD-клампы USB (D: pin1=K, pin2=A): верхний к 3V3, нижний к GND, на каждую линию D+/D-
    N['3V3'] += edp_h[1], edm_h[1]
    N['USB_DP'] += edp_h[2], edp_l[1]; N['USB_DM'] += edm_h[2], edm_l[1]
    N['GND'] += edp_l[2], edm_l[2]

# ================= Блок X — добавки v0.2 =================
# ВАЖНО: новые детали создаём ТОЛЬКО здесь, в конце — рефы существующих не сдвигаются,
# и импорт нетлиста в PCB по рефам остаётся валидным для уже сделанной разводки.
with Blk('A_buck'):
    cin2b, cin2c = C('4.7uF/100V',C106), C('4.7uF/100V',C106)     # ещё 2 банки по входу buck (итого 3x4,7µФ/100В)
    cout2b, cout2c = C('4.7uF/100V',C106), C('4.7uF/100V',C106)   # ещё 2 по выходу buck
    N['VIN_55'] += cin2b[1], cin2c[1]; N['GND'] += cin2b[2], cin2c[2]
    N['VBUCK_OUT'] += cout2b[1], cout2c[1]; N['GND'] += cout2b[2], cout2c[2]
    # v0.2.27: посадочные тороидов — вертикальная установка (кольцо на ребро), пятаки 6мм под жгут; правлено пользователем на плате -> Local
    l2 = L('6.3uH', 'Local:L_Toroid_Vertical_Core21x7mm_P10.00mm_D2.0mm'); cdr1, cdr2 = C('4.7uF/100V',C106), C('4.7uF/100V',C106); cdamp = CP('220uF/100V', 'Capacitor_THT:CP_Radial_D13.0mm_P5.00mm')  # v0.2.27: 100->220мкФ под L3=6,3мкГн:
    # просадка стока при набросе 0->7А падает с 1,69 до 1,16В, а подавление на 100кГц растёт с 48,7 до 55 дБ.
    # Шаг выводов оставлен 5мм (отверстия на плате не двигаются, разводка цела), корпус Ø13мм  # П-фильтр C-L-C + демпфер перед линейником
    # v0.2.7: диоды ускорения РАЗРЯДА затворов buck (в обход 10-омников, как в ATX): анод к затвору, катод к драйверу.
    # Пиковый разряд ~4А импульсами -> B340 (3А Шоттки); BAT54 нельзя (200мА класс). Закрытие ключа ~150нс -> ~40нс; DT можно ужать до 60-80нс.
    dgh, dgl = D('B340','Diode_SMD:D_SMC'), D('B340','Diode_SMD:D_SMC')   # B340 пользователя в SMC 6x7мм
    N['GATE_QH'] += dgh[1]; dgh[2] += qh['G']   # K -> драйвер, A -> затвор
    N['GATE_QL'] += dgl[1]; dgl[2] += ql['G']
    N['VBUCK_OUT'] += l2[1]
    N['VDRAIN'] += l2[2], cdr1[1], cdr2[1], cdamp[1]   # сток проходного (после фильтра); ОС buck (PA5) — тут
    N['GND'] += cdr1[2], cdr2[2], cdamp[2]
with Blk('B_pass'):
    rgsd = R('100k')                                   # bleed затвор-исток проходного
    rgsd[1] += qpass['G']; N['VOUT_REG'] += rgsd[2]
with Blk('F_protect'):
    # делитель напряжения КЛЕММ -> PB1 (VTERM_SENSE): видеть внешний источник ДО замыкания реле + детект залипшего реле
    rvt_a, rvt_b, rvt_s, cvt = R('180k'), R('10k'), R('4k7'), C('100nF')
    dvt_h, dvt_l = D('BAT'), D('BAT')
    N['OUT_PLUS'] += rvt_a[1]; N['VT0'] += rvt_a[2], rvt_b[1], rvt_s[1]; N['GND'] += rvt_b[2], cvt[2]
    N['VTERM_SENSE'] += rvt_s[2], cvt[1], dvt_h[2], dvt_l[1]
    N['3V3'] += dvt_h[1]; N['GND'] += dvt_l[2]
with Blk('D_current'):
    # K91 (v0.2.4): перекидное реле сенса INA228 — катушка ПАРАЛЛЕЛЬНО K90 (тот же PA15/BD139/гасящий диод).
    # Отпущено: VBUS = VOUT_REG (узел регулятора). Сработало (одновременно с основным): VBUS = OUT_PLUS (клеммы).
    # Прошивка цифровым remote sense доводит КЛЕММЫ до уставки (падение реле/предохранителя компенсируется при любом токе).
    krel2 = Part('Relay','Relay_SPDT', value='HF3FA/012-ZTF', ref_prefix='K',
                 footprint='Local:Relay_HF3FA_1C')  # v0.2.17: пады переименованы под символ (11=COM ср.левый, A1/A2 катушка, 14=NO пр.верх, 12=NC пр.низ); ПРОЗВОНИТЬ HF3FA: в покое 11<->12!
    N['V12'] += krel2['A1']; N['RLY_COIL'] += krel2['A2']
    N['VBUS_SENSE'] += krel2['11']   # COM -> линия сенса
    N['VOUT_REG'] += krel2['12']     # NC  -> узел регулятора (реле откл)
    N['OUT_PLUS'] += krel2['14']     # NO  -> клеммы (реле вкл)
    # v0.2.5: защита VBUS. Кламп ДО резистора (утечка горячего Шоттки стекает с низкоомной линии — ошибки нет),
    # R ограничивает инжекцию в пин (<0,2 мА при -12В), C сглаживает перелёт контакта K91 (~1 мс).
    # Зачем: индуктивный выброс при КАЖДОМ обрыве нагрузки — силовой кламп держит клеммы на -0,6...-1,5В, а VBUS терпит лишь -0,3В.
    dvb = D('SK59','Diode_SMD:D_SMC'); rvb = R('470'); cvb = C('100nF')   # SK59: Шоттки 5А/90В из запасов (SMC)
    N['VBUS_SENSE'] += dvb[1], rvb[1]   # катод клампа + вход R — сторона линии
    N['VBUS_INA'] += rvb[2], cvb[1]     # пин INA228
    N['GND'] += dvb[2], cvb[2]
with Blk('G_supply'):
    # v0.2.8: МЕЖПЛАТНЫЕ РАЗЪЁМЫ (обе половины пар в одном нетлисте; пользователь сам разносит по платам).
    # Цепи ОБЩИЕ: при физическом распиле ратснест между зонами закрыть жертвенными перемычками по линии реза
    # (или позже разрезать цепи на _F-версии по сторонам разъёмов — отдельной операцией).
    j55  = Jn(4, 'Connector_Molex:Molex_KK-396_A-41791-0004_1x04_P3.96mm_Vertical', 'ATX_55V_IN')  # силовой вход: 2x55 + 2xGND (~7А/контакт)
    jsb  = Jn(2, 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', '5VSB_IN')
    jf_o = Jn(2, 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', 'FLY_55_OUT')       # папа, основная плата
    jf_i = Jn(2, 'Local:Conn_FLY55_JST_EH_1x03_P2.5_pins13', 'FLY_55_IN')   # v0.2.25: пользователь поставил JST EH 1x03, задействованы крайние контакты (пад 2 = средний, шаг 5мм)
    jr_o = Jn(4, 'Local:Conn_RAILS_1x04_P2.54_D0.6', 'RAILS_OUT')   # v0.2.25: пользователь увеличил пятаки до 2мм, сверло 0,6 (под пайку проводов)
    jr_i = Jn(4, 'Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical', 'RAILS_IN')         # мама, основная плата
    N['VIN_55'] += j55[1], j55[2], jf_o[1], jf_i[1]
    N['GND'] += j55[3], j55[4], jsb[2], jf_o[2], jf_i[2], jr_o[3], jr_i[3]
    N['5VSB'] += jsb[1]
    csb1, csb2 = CP('47uF/25V'), C('100nF')   # входной буфер дежурки у J21 (5VSB едет проводом от АТХ; на модуле свои кондёры есть, у входа — нет)
    N['5VSB'] += csb1[1], csb2[1]; N['GND'] += csb1[2], csb2[2]
    N['V_P67'] += jr_o[1], jr_i[1]   # пин 1 = +67
    N['V12'] += jr_o[2], jr_i[2]     # пин 2 = +12
    N['V_N5'] += jr_o[4], jr_i[4]    # пин 4 = -5 (пин 3 = GND между ними)
    # RAILS_BTN (v0.2.2): детект +67/−5 лесенкой на PA4 вместе с кнопкой RESET_FAULT.
    # Уровни PA4: ~0 = кнопка (панель, на GND), ~1,65В = рельсы ОК, ~3,3В = FAIL.
    # +67 И −5 живы => +12/MP9486/UC3845 живы (флайбэк питается от +12) — отдельный тест +12 не нужен.
    q_r67, q_r5 = NPN('BD139'), NPN('BD139')
    r_up, r_mid, rb67, rbe = R('10k'), R('10k'), R('680k'), R('100k')
    rq2a, rq2b, cflt = R('100k'), R('47k'), C('100nF')
    N['3V3'] += r_up[1], rq2a[1]
    N['RAILS_BTN'] += r_up[2], r_mid[1], cflt[1]                     # узел PA4
    N['RAILS_Q1C'] += r_mid[2], q_r67['C']
    N['RAILS_Q1B'] += q_r67['B'], rb67[2], rbe[1], q_r5['C']         # Q2 глушит Q1 при пропаже −5
    N['V_P67'] += rb67[1]
    N['RAILS_Q2B'] += q_r5['B'], rq2a[2], rq2b[1]                    # инверсный детектор −5
    N['V_N5'] += rq2b[2]
    N['GND'] += q_r67['E'], q_r5['E'], rbe[2], cflt[2]

with Blk('F_protect'):
    # v0.2.21: PAM8403 Class-D моно (левый канал). Вход: PB11(BUZZER,PWM ~300кГц) -> RC ФНЧ -> разд.конд -> INL.
    pam = CHIP('PAM8403','Local:SOIC-16_3.9x9.9mm_P1.27mm_Pad0.8mm')
    rpwm, cpwm, cinl = R('2k2'), C('10nF'), C('1uF')      # ФНЧ ~7кГц + разделительный
    cinr, cvref, cvdd = C('1uF'), C('1uF'), C('100nF')
    cpv1, cpv2 = C('100nF'), CP('100uF/16V')
    N['BUZZER'] += rpwm[1]; N['AUDIO_F'] += rpwm[2], cpwm[1], cinl[1]; N['GND'] += cpwm[2]
    N['AUDIO_INL'] += pam[7], cinl[2]                      # INL
    N['AUDIO_INR'] += pam[10], cinr[1]; N['GND'] += cinr[2]   # INR не исп. -> C на GND
    N['AUDIO_VREF'] += pam[8], cvref[1]; N['GND'] += cvref[2] # VREF
    N['5VSB'] += pam[6], pam[4], pam[13], pam[5], pam[12], cvdd[1], cpv1[1], cpv2[1]  # VDD,PVDD,MUTE,SHDN=высокий(вкл)
    N['GND'] += pam[2], pam[9], pam[11], pam[16], cvdd[2], cpv1[2], cpv2[2]           # PGND,GND
    N['SPK_P'] += pam[3]; N['SPK_N'] += pam[1]            # OUTL+/OUTL- на динамик (BTL); правый 14,15 не исп.

with Blk('G_supply'):
    # v0.2.23: RC-фильтры выходов флайбэка: 47 Ом + 4,7 мкФ (срез ~700 Гц -> ~-42 дБ на 95 кГц).
    # RC вместо LC: при нагрузке ~5 мА падение ~0,25 В (не важно), давит сильнее LC 56мкГн и без резонанса.
    # ОС (rfb_t) и преднагрузки остались ДО фильтра (петля UC3845 фильтра не видит). Разъём RAILS — ПОСЛЕ (наружу чистые рельсы).
    rf67, cf67 = R('47'), C('4.7uF/100V')
    rf5, cf5 = R('47'), C('4.7uF/100V')
    N['V_P67R'] += rf67[1]; N['V_P67'] += rf67[2], cf67[1]
    N['V_N5R'] += rf5[1];  N['V_N5'] += rf5[2], cf5[1]
    N['GND'] += cf67[2], cf5[2]

with Blk('C_linear'):
    # v0.2.26: анти-помеховый конденсатор на E/D OPA454 (рекомендация TI E2E: 33..47пФ на пин).
    # Даташит 9.3.6: быстрый ОТРИЦАТЕЛЬНЫЙ фронт, наведённый ёмкостно, может пересилить внутренний
    # источник 1мкА и выключить усилитель ("appears as an oscillation"). Рядом buck 100кГц/55В — риск реальный.
    # Ставим 100пФ (больше 47пФ = крепче; постоянная с подтяжкой 100к всего 10мкс, ни на что не влияет).
    # Узел в работе ~2В, НО через R18 100к на нём висит +67В при обрыве пина -> корпус 1206, напряжение >=50В (C0G).
    ced = C('100pF')
    N['EN_LIN'] += ced[1]; N['GND'] += ced[2]

with Blk('H_ui'):
    # v0.2.23: вентилятор 12В (PB9 = FAN_DRV, был голым пином U1.47): BD139 low-side (запасы; освободился от пищалки).
    # Ib=(3,3-0,7)/470 ≈ 5,5 мА, hFE(min)~40 -> до ~200 мА кол-ра: типовой 80мм 12В (~100-150 мА) в насыщении.
    # 10к Б-Э держит ключ запертым при ресете MCU; SS14 гасит выброс мотора; до прошивки FAN- можно перемкнуть на GND.
    qfan, rfanb, rfanpd = NPN('BD139'), R('470'), R('10k')
    dfan = D('SS14', 'Diode_SMD:D_SMA')
    jfan = Jn(2, 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', 'FAN')
    N['FAN_DRV'] += rfanb[1]
    N['FAN_B'] += rfanb[2], qfan['B'], rfanpd[1]
    N['GND'] += rfanpd[2], qfan['E']
    N['V12'] += jfan[1], dfan[1]                 # пин 1 разъёма = +12; катод гасящего диода
    N['FAN_N'] += jfan[2], dfan[2], qfan['C']    # пин 2 = FAN- -> коллектор

with Blk('F_protect'):
    # v0.2.33: защита базы Q5 (драйвер реле) — ставится ПРЯМО У ТРАНЗИСТОРА.
    # 10к Б-Э: пока МК в ресете, PA15 = вход, а трасса RELAY_DRV длиной ~120 мм ловит наводки —
    # без подтяжки BD139 может приоткрыться = самопроизвольное включение реле (напряжение на клеммах!).
    # Потеря тока базы 75 мкА из 2,55 мА, насыщение не страдает (нужно 63 мА на две катушки, hFE>=26).
    # 10нФ Б-Э: гасит ёмкостную наводку с длинной дорожки (импульсный заряд даёт милливольты вместо вольт);
    # постоянная с R26 1к = 10 мкс, для реле это ничто.
    rbepd, cbe = R('10k'), C('10nF')
    N['RLY_BASE'] += rbepd[1], cbe[1]; N['GND'] += rbepd[2], cbe[2]

# ================= вывод =================
generate_netlist(file_='lab_psu.net')
print('OK -> lab_psu.net', flush=True)

if '--no-sch' not in sys.argv:
    # --- СВОЯ раскладка: блоки-кластеры, детали по спирали; впрыск в writer SKiDL ---
    import math
    from collections import defaultdict
    import skidl.tools.kicad8 as _tm
    from skidl.geometry import Tx
    from skidl.schematics.sch_node import SchNode
    from skidl.tools.kicad8.gen_schematic import preprocess_circuit
    from skidl.tools.kicad8.sexp_schematic import write_top_schematic
    import skidl.tools.kicad8.sexp_schematic as _sx
    _sx._get_power_symbol_names = lambda: set()  # GND/питание тоже метками (чтобы роутер их видел)
    c = default_circuit
    for net in c.nets: net.stub = True          # все цепи -> метки на пинах (ratsnest), без проводов
    preprocess_circuit(c, use_push_pull=True, rotate_parts=False, pin_normalize=True)
    node = SchNode(c, _tm, 'lab_psu_sch', 'lab_psu_sch', 'Lab PSU 0-50V', 1.0)  # flatness=1 -> один лист
    MIL = 1/0.0254; GA = math.radians(137.508); STEP = 16.0   # шаг спирали-подсолнуха, мм
    CEN = {'A_buck':(0,0), 'B_pass':(176,0), 'C_linear':(337,0), 'D_current':(516,0),
           'F_protect':(704,0), 'G_supply':(-234,10), 'E_vset':(0,-183),
           'H_ui':(330,205), 'MCU':(-234,-183)}    # buck в центре, тракт вправо; зазоры между блоками ~вдвое меньше
    def _units(p):
        u = getattr(p,'unit',None); return list(u.values()) if u else [p]
    byblk = defaultdict(list)
    for p in c.parts: byblk[getattr(p,'blk','MCU')].append(p)
    gi = 0
    for blk, parts in byblk.items():
        cx, cy = CEN.get(blk, (0,500))
        for i, p in enumerate(parts):            # спираль-подсолнух вокруг центра блока
            gi += 1
            r = STEP*math.sqrt(i); ang = i*GA
            x = (cx + r*math.cos(ang))*MIL; y = (cy + r*math.sin(ang))*MIL
            for pu in _units(p):
                t = Tx(); t.dx = x; t.dy = y; pu.tx = t
    import re as _re
    # привязка к сетке 1.27мм: все координаты -> ближайший узел (пины на сетке, ручная разводка снапается;
    # смещения пинов кратны 1.27 -> символ и его метки остаются совмещёнными) + дописать sheet_instances.
    def _snap_file(path):
        s = io.open(path, encoding='utf-8').read().rstrip()
        def _sn(m):
            x = round(float(m.group(1))/1.27)*1.27; y = round(float(m.group(2))/1.27)*1.27
            return '(at %.2f %.2f%s)' % (x, y, m.group(3) or '')
        s = _re.sub(r'\(at (-?[\d.]+) (-?[\d.]+)( -?[\d.]+)?\)', _sn, s)
        if '(sheet_instances' not in s and s.endswith(')'):
            s = s[:-1] + '\n  (sheet_instances\n    (path "/"\n      (page "1")))\n)\n'
        io.open(path, 'w', encoding='utf-8').write(s); return s
    def _collisions(s):
        from collections import defaultdict
        d = defaultdict(set)
        for n,x,y in _re.findall(r'\(global_label "([^"]+)"\s*\(shape[^)]*\)\s*\(at ([\-\d.]+) ([\-\d.]+)', s):
            d[(round(float(x),2), round(float(y),2))].add(n)
        return [pt for pt,ns in d.items() if len(ns) > 1]
    out = write_top_schematic(c, node, 'lab_psu_sch', 'lab_psu_sch', 'Lab PSU 0-50V', version=20230409)
    txt = _snap_file(out)
    for _ in range(12):                      # авто-разведение совпавших узлов: сдвиг детали на 2 клетки
        cols = _collisions(txt)
        if not cols: break
        sym = [(float(x),float(y),r) for x,y,r in _re.findall(
               r'\(lib_id "[^"]+"\)\s*\(at ([\-\d.]+) ([\-\d.]+) \d+\)[\s\S]*?\(property "Reference" "([^"]+)"', txt)]
        for pt in cols:
            x,y,r = min(sym, key=lambda s: (s[0]-pt[0])**2 + (s[1]-pt[1])**2)
            for p in c.parts:
                if getattr(p,'ref',None) == r:
                    for pu in _units(p): pu.tx.dy = pu.tx.dy + 6.35*MIL
        out = write_top_schematic(c, node, 'lab_psu_sch', 'lab_psu_sch', 'Lab PSU 0-50V', version=20230409)
        txt = _snap_file(out)
    print('OK -> схема (сетка 1.27мм, совпадений осталось: %d):' % len(_collisions(txt)), out, flush=True)
