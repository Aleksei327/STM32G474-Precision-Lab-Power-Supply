#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v0.2.38: nedostayushchie modeli (F1, J2, J6) + ispravleniya po zamechaniyam polzovatelya."""
import io, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wrlgen import box, cyl, write, mat, MAT, K

def arc(cx, cy, cz, R, r, a0, a1, m='cu', seg=14, sides=12, plane='xz'):
    """Chast tora (skruglenie): dugа ot a0 do a1 gradusov v ploskosti plane."""
    pts, faces = [], []
    a0, a1 = math.radians(a0), math.radians(a1)
    for i in range(seg + 1):
        a = a0 + (a1 - a0) * i / seg
        if plane == 'xz':
            px, py, pz = R*math.cos(a), 0.0, R*math.sin(a)
            tx, ty, tz = math.cos(a), 0.0, math.sin(a)
        else:
            px, py, pz = R*math.cos(a), R*math.sin(a), 0.0
            tx, ty, tz = math.cos(a), math.sin(a), 0.0
        for j in range(sides):
            b = 2*math.pi*j/sides
            if plane == 'xz':
                ox = r*math.cos(b)*tx; oy = r*math.sin(b); oz = r*math.cos(b)*tz
            else:
                ox = r*math.cos(b)*tx; oy = r*math.cos(b)*ty; oz = r*math.sin(b)
            pts.append(((px+ox)/K, (py+oy)/K, (pz+oz)/K))
    for i in range(seg):
        for j in range(sides):
            a_ = i*sides + j; b_ = i*sides + (j+1) % sides
            c_ = (i+1)*sides + j; d_ = (i+1)*sides + (j+1) % sides
            faces.append((a_, b_, d_, c_))
    ps = ',\n'.join('%.4f %.4f %.4f' % p for p in pts)
    fs = ',\n'.join('%d, %d, %d, %d, -1' % f for f in faces)
    return ('Transform { translation %.4f %.4f %.4f children [ Shape {\n  %s\n'
            '  geometry IndexedFaceSet { solid FALSE creaseAngle 1.0\n'
            '    coord Coordinate { point [\n%s\n] }\n    coordIndex [\n%s\n]\n  }\n} ] }\n'
            % (cx/K, cy/K, cz/K, mat(m), ps, fs))

def tube(x, y, z, r, length, m='cu', axis='x', seg=20):
    return cyl(x, y, z, r, length, m, axis, seg)   # sovmestimost: cyl() teper sam setkoy

# ---------- F1: derzhatel 5x20 + steklyannyy predokhranitel ----------
def fuse():
    p = []
    for x in (2.3, 18.2):                          # dve klipsy (pary padov 0/4.6 i 15.9/20.5)
        p.append(box(x, 0, 5.5, 5.6, 1.0, 5.0, 'alu'))      # spinka klipsy
        for sy in (-1, 1):
            p.append(box(x, sy*3.0, 5.5, 5.6, 0.8, 5.0, 'alu'))   # lapki
        for dx in (-2.3, 2.3):
            p.append(box(x + dx, 0, 1.5, 0.8, 6.0, 3.0, 'alu'))   # nogi v platu
    p.append(tube(10.25, 0, 6.0, 2.5, 20.0, 'plast_w', 'x', 24))       # steklyannaya trubka 5x20 vdol X
    for x in (1.75, 18.75):                                        # metallicheskie kolpachki
        p.append(tube(x, 0, 6.0, 2.6, 3.0, 'alu', 'x', 24))
    p.append(tube(10.25, 0, 6.0, 0.25, 16.0, 'alu', 'x', 8))          # plavkaya nit vnutri
    return write('Fuseholder_5x20_with_fuse.wrl', p)

# ---------- J2: vintovoy klemmnik MX126-5.0, 2 pozitsii ----------
# Pady na x = 0 i 5 (v sisteme modeli). Korpus 10 x 8.5 x 10 mm, provod vhodit s -Y.
def terminal2():
    # Gabarity iz futprinta: X -3.00..7.50, Y(platy) -4.00..3.80 -> 10.5 x 7.8 mm.
    # Vinty stoyat TOChNO nad padami (F.Fab: okruzhnosti d3.2 v (0,0) i (5,0)).
    CX, CY, W, D, H = 2.25, 0.1, 10.5, 7.8, 10.0
    FRONT = CY - D/2                                               # litsevaya storona (vhod provoda)
    p = [box(CX, CY, H/2 - 0.6, W, D, H - 1.2, 'green'),           # korpus
         box(CX, CY, H - 0.5, W - 0.8, D - 0.8, 1.0, 'green'),     # verkhnyaya ploshchadka pod vinty
         box(CX, FRONT + 0.7, 1.0, W, 1.4, 2.0, 'green')]          # yubka u platy
    for x in (0.0, 5.0):
        p.append(cyl(x, FRONT + 1.0, 3.4, 1.75, 2.4, 'plast', 'y'))  # otverstie pod provod
        p.append(box(x, FRONT + 2.8, 2.8, 3.6, 3.2, 3.2, 'alu'))     # kletka-zazhim vnutri
        p.append(cyl(x, 0, H - 0.1, 1.6, 1.4, 'alu'))                # golovka vinta M2.5
        p.append(box(x, 0, H + 0.45, 3.2, 0.55, 0.45, 'plast'))      # shlits
    return write('TerminalBlock_5.0mm_2pin.wrl', p)

# ---------- J6: Molex KK-396 vertikalnyy, 4 pozitsii, shag 3.96 ----------
# Pady x = 0..11.88. Kozhukh s otkrytym verkhom, vnutri torchat kvadratnye shtyri.
def molex4():
    # Gabarity iz futprinta: X -1.91..13.79, Y(platy) -5.11..4.90 -> kozhukh 15.7 x 10.0 mm.
    PT, N = 3.96, 4
    CX, CY = 5.94, 0.1
    L, W, H, T = 15.7, 10.0, 10.2, 1.0
    p = [box(CX, CY, 0.9, L, W, 1.8, 'plast_w')]                   # dno kozhukha
    p.append(box(CX, CY - W/2 + T/2, H/2, L, T, H, 'plast_w'))     # dlinnye stenki
    p.append(box(CX, CY + W/2 - T/2, H/2, L, T, H, 'plast_w'))
    for sx in (-1, 1):                                             # tortsevye stenki
        p.append(box(CX + sx*(L/2 - T/2), CY, H/2, T, W, H, 'plast_w'))
    for i in range(N):                                             # shtyri 1.14 kv., verkh na z=9
        p.append(box(i*PT, 0, 3.25, 1.14, 1.14, 11.5, 'cu'))
    p.append(box(CX, CY + 2.7, 5.0, L - 3.6, 1.3, 6.0, 'plast_w'))     # vnutrenniy pandus friktsionnogo zamka
    p.append(box(CX, CY + 2.2, 8.6, L - 3.6, 2.3, 1.3, 'plast_w'))     # zatsep pandusa
    return write('Molex_KK-396_1x04.wrl', p)

# ---------- SHUNT v2: kruglyy provod, nogi v platu, skruglennye peregiby ----------
def shunt2():
    d, H, R = 1.5, 10.0, 2.0        # diametr provoda, vysota skoby, radius zagiba
    p = []
    for x in (0.0, 20.0):
        p.append(cyl(x, 0, (H - R)/2 - 1.5, d/2, H - R + 3.0, 'cu'))   # noga: ot -3 (v plate) do H-R
    p.append(tube(10.0, 0, H, d/2, 20.0 - 2*R, 'cu', 'x', 16))              # ona zhe kruglaya
    p.append(arc(R, 0, H - R, R, d/2, 90, 180, 'cu'))                  # levoe skruglenie
    p.append(arc(20.0 - R, 0, H - R, R, d/2, 0, 90, 'cu'))             # pravoe skruglenie
    return write('Shunt_Constantan_Staple.wrl', p)

if __name__ == '__main__':
    for f, s in [fuse(), terminal2(), molex4(), shunt2()]:
        print('   %-36s %6.1f KB' % (os.path.basename(f), s/1024.0))
