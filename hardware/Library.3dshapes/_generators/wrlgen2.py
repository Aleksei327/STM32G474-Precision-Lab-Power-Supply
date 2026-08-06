#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v0.2.37: modeli platok-moduley, shunta, transformatora, NTC i SMD-drosselya.
Geometriya BAZIRUETSYA na razmerakh iz posadochnykh mest, smeshchenie zapechyeno v modeli
(offset v futprinte = 0). VRML: X = X platy, Y = MINUS Y platy, Z = vysota. Edinitsa = 2.54 mm."""
import io, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wrlgen import box, cyl, torus, write, MAT

def pinrow(x0, y0, n, pitch, along='x', h=6.0, d=0.64, m='cu'):
    """Ryad shtyrey gребenki: nizhnyaya chast pod platoy, verkhnyaya nad."""
    p = []
    for i in range(n):
        x = x0 + (i*pitch if along == 'x' else 0)
        y = y0 + (i*pitch if along == 'y' else 0)
        p.append(box(x, y, h/2 - 2.0, d, d, h, m))
    return p

# ---------- MODUL INA228 (Adafruit-style breakout) ----------
# Plata 25.4 x 20.3 mm, tolshchina 1.6, chernyy tekstolit.
# Nachalo koordinat futprinta = pervyy pad grebenki; plata: X -3.81..21.59, Y(platy) -18.40..1.90
def ina_module():
    p = []
    cx, cy = 8.89, 8.25          # tsentr platy v VRML-koordinatakh (Y uzhe perevernut)
    p.append(box(cx, cy, 5.0 + 0.8, 25.4, 20.3, 1.6, 'pcb_b'))          # plata na vysote 5 mm (nad grebenkoy)
    p += pinrow(0, 0, 8, 2.54, 'x', 9.0, 0.64)                          # 8 shtyrey grebenki
    # klemmnik 3.5 mm sverkhu (Vin- / VBus / Vin+) - zelyonyy korpus
    p.append(box(cx, 14.3, 5.0 + 1.6 + 4.0, 12.5, 8.0, 8.0, 'green'))
    # mikroskhema INA228 i shunt R015
    p.append(box(cx, 7.0, 5.0 + 1.6 + 0.6, 4.0, 3.0, 1.2, 'plast'))
    p.append(box(cx, 10.5, 5.0 + 1.6 + 0.5, 6.4, 3.2, 1.0, 'plast_w'))
    # dva razyoma STEMMA QT po krayam
    for x in (cx - 10.5, cx + 10.5):
        p.append(box(x, 9.0, 5.0 + 1.6 + 1.5, 4.5, 6.0, 3.0, 'plast_w'))
    return write('Module_INA228_Adafruit.wrl', p)

# ---------- MODUL WeAct STM32G474 ----------
# Pady: X -29.21..29.21, Y -7.62..7.62 (2 ryada po 24 + SWD). Plata ~ 62.5 x 19.5, tolshchina 1.6
def weact_module():
    p = []
    p.append(box(0, 0, 5.0 + 0.8, 62.5, 19.5, 1.6, 'pcb_b'))
    for y in (-7.62, 7.62):
        p += pinrow(-29.21, -y, 24, 2.54, 'x', 9.0, 0.64)      # Y perevorachivaem
    # mikrokontroller UFQFPN48 v tsentre
    p.append(box(0, 0, 5.0 + 1.6 + 0.5, 7.0, 7.0, 1.0, 'plast'))
    # USB-C na krayu
    p.append(box(-29.0, 0, 5.0 + 1.6 + 1.6, 7.5, 9.0, 3.2, 'plast_w'))
    # knopki i kvartsy
    for x, y in ((-22.0, 6.0), (-22.0, -6.0)):
        p.append(box(x, y, 5.0 + 1.6 + 0.9, 3.5, 3.5, 1.8, 'plast'))
    p.append(box(8.0, 5.5, 5.0 + 1.6 + 0.6, 3.2, 2.5, 1.2, 'plast_w'))
    p.append(box(8.0, -5.5, 5.0 + 1.6 + 0.6, 3.2, 2.5, 1.2, 'plast_w'))
    return write('Module_WeAct_STM32G474.wrl', p)

# ---------- SHUNT: konstantanovaya skoba ----------
# Pady na X 0 i 20 (shag 20 mm), provod d1.5, skoba vysotoy ~10 mm
def shunt():
    p = []
    d = 1.5
    p.append(cyl(0.0, 0, 5.0, d/2, 10.0, 'cu'))          # levaya noga
    p.append(cyl(20.0, 0, 5.0, d/2, 10.0, 'cu'))         # pravaya noga
    p.append(box(10.0, 0, 10.0, 20.0, d, d, 'cu'))       # perekladina sverkhu
    return write('Shunt_Constantan_Staple.wrl', p)

# ---------- TRANSFORMATOR FLYBACK (EE16-klass) ----------
# Kern 16x15x5 (uzhe s dorabotkoy polzovatelya), karkas 5x6, vysota namotki 8
def transformer():
    p = []
    # dve E-poloviny: verkhnyaya i nizhnyaya chasti kerna
    p.append(box(0, 0, 7.5, 16.0, 5.0, 15.0, 'ferr'))            # obshchiy gabarit kerna
    # okno s namotkoy - katushka
    p.append(box(0, 0, 7.5, 9.0, 8.0, 8.0, 'wire'))              # namotka
    p.append(box(0, 0, 3.5, 10.0, 8.6, 1.2, 'plast_w'))          # bortik karkasa NIZ - pod namotkoy
    p.append(box(0, 0, 11.5, 10.0, 8.6, 1.2, 'plast_w'))         # bortik verkh
    return write('Transformer_Flyback_EE16.wrl', p)

# ---------- NTC ----------
def ntc():
    p = [cyl(-3.5, 0, 3.0, 0.3, 6.0, 'cu'), cyl(3.5, 0, 3.0, 0.3, 6.0, 'cu'),
         box(0, 0, 6.5, 4.5, 2.0, 3.0, 'plast')]
    return write('NTC_bead.wrl', p)

# ---------- SMD drossel 15x15 ----------
def l_smd():
    return write('L_SMD_15x15mm.wrl', [box(0, 0, 3.5, 15.0, 15.0, 7.0, 'ferr'),
                                       box(0, 0, 7.2, 12.0, 12.0, 0.4, 'plast')])

if __name__ == '__main__':
    for f, s in [ina_module(), weact_module(), transformer(), ntc(), l_smd()]:
        print('   %-34s %6.1f KB' % (os.path.basename(f), s/1024.0))
