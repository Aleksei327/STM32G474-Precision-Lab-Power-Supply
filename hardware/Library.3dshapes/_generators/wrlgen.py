#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v0.2.36: generator 3D-modeley (.wrl) dlya proekta.
Edinitsy VRML v KiCad = 0.1 dyuyma = 2.54 mm (proverено na demo-modeli knopki 6x6).
Osi: X - vpravo po plate, Y - VVERKH na ekrane (= minus Y platy), Z - vysota nad platoy.
Vse razmery v skripte zadayutsya v MILLIMETRAKH, delenie na 2.54 delaetsya avtomaticheski.
"""
import io, os, math

K = 2.54  # mm v odnoy edinitse VRML
OUT = r'D:\Документы\Power supply 0 - 50 V DC-DC\POWER_0-50\Library.3dshapes'

MAT = {
    'alu':   (0.62, 0.64, 0.66, 0.35, 0.45),   # aluminiy: diffuse rgb, specular, shininess
    'alu_d': (0.48, 0.50, 0.52, 0.25, 0.30),   # temneye (rebra)
    'pcb':   (0.05, 0.30, 0.10, 0.05, 0.10),   # zelenyy tekstolit
    'pcb_b': (0.10, 0.10, 0.12, 0.05, 0.10),   # chernyy tekstolit
    'cu':    (0.75, 0.55, 0.25, 0.60, 0.60),   # med / zoloto
    'plast': (0.10, 0.10, 0.10, 0.10, 0.20),   # chernyy plastik
    'plast_w':(0.85, 0.85, 0.85, 0.10, 0.20),  # belyy plastik
    'ferr':  (0.18, 0.18, 0.20, 0.10, 0.15),   # ferrit / poroshok
    'green': (0.10, 0.45, 0.15, 0.20, 0.30),   # zelyonoe kolzo
    'wire':  (0.80, 0.52, 0.25, 0.55, 0.55),   # obmotochnyy provod
}

def head():
    return '#VRML V2.0 utf8\n# Generated for the Precision Lab PSU project\n\n'

def mat(name):
    r, g, b, sp, sh = MAT[name]
    return ('appearance Appearance { material Material {\n'
            '  diffuseColor %.3f %.3f %.3f\n  specularColor %.2f %.2f %.2f\n'
            '  shininess %.2f\n  ambientIntensity 0.3\n} }' % (r, g, b, sp, sp, sp, sh))

def box(x, y, z, sx, sy, sz, m='alu'):
    """Korobka: tsentr (x,y,z) v mm, razmery sx,sy,sz v mm."""
    return ('Transform { translation %.4f %.4f %.4f children [ Shape {\n  %s\n'
            '  geometry Box { size %.4f %.4f %.4f }\n} ] }\n'
            % (x/K, y/K, z/K, mat(m), sx/K, sy/K, sz/K))

def cyl(x, y, z, r, h, m='alu', axis='z', seg=20):
    """Tsilindr YAVNOY setkoy (IndexedFaceSet).
    !!! Vstroennyy VRML-primitiv `Cylinder` KiCad 10 NE RISUET VOOBSHCHE - proverено:
    propadali nozhki shunta, vintiki klemmnika, kolba predokhranitelya. Boxes i
    IndexedFaceSet risuyutsya normalno, poetomu vse kruglye detali - setkoy."""
    NL = chr(10)
    pts, faces = [], []
    for s in (-0.5, 0.5):
        for i in range(seg):
            a = 2*math.pi*i/seg
            c, d = r*math.cos(a), r*math.sin(a)
            if axis == 'x':   p = (h*s, c, d)
            elif axis == 'y': p = (c, h*s, d)
            else:             p = (c, d, h*s)
            pts.append(((x + p[0])/K, (y + p[1])/K, (z + p[2])/K))
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((i, j, seg + j, seg + i))
    faces.append(tuple(range(seg - 1, -1, -1)))
    faces.append(tuple(range(seg, 2*seg)))
    ps = (',' + NL).join('%.4f %.4f %.4f' % p for p in pts)
    fs = (',' + NL).join(', '.join(str(i) for i in f) + ', -1' for f in faces)
    return NL.join(['Transform { children [ Shape {', '  ' + mat(m),
                    '  geometry IndexedFaceSet { solid FALSE creaseAngle 1.0',
                    '    coord Coordinate { point [', ps, '] }',
                    '    coordIndex [', fs, ']', '  }', '} ] }', ''])

def torus(x, y, z, R, r, m='wire', seg=48, sides=16):
    """Tor (obmotka kolza): R - radius kolza, r - tolshchina, ploskost XZ (kolzo stoit vertikalno)."""
    pts, faces = [], []
    for i in range(seg):
        a = 2*math.pi*i/seg
        cx, cz = R*math.cos(a), R*math.sin(a)
        for j in range(sides):
            bta = 2*math.pi*j/sides
            rr = r*math.cos(bta)
            pts.append(((cx + rr*math.cos(a))/K, (r*math.sin(bta))/K, (cz + rr*math.sin(a))/K))
    for i in range(seg):
        for j in range(sides):
            a0 = i*sides + j
            a1 = i*sides + (j+1) % sides
            b0 = ((i+1) % seg)*sides + j
            b1 = ((i+1) % seg)*sides + (j+1) % sides
            faces.append((a0, a1, b1, b0))
    ps = ',\n'.join('%.4f %.4f %.4f' % p for p in pts)
    fs = ',\n'.join('%d, %d, %d, %d, -1' % f for f in faces)
    return ('Transform { translation %.4f %.4f %.4f children [ Shape {\n  %s\n'
            '  geometry IndexedFaceSet { solid TRUE creaseAngle 1.0\n'
            '    coord Coordinate { point [\n%s\n] }\n    coordIndex [\n%s\n]\n  }\n} ] }\n'
            % (x/K, y/K, z/K, mat(m), ps, fs))

def write(name, parts):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    io.open(p, 'w', encoding='utf-8').write(head() + ''.join(parts))
    return p, os.path.getsize(p)

# ---------------- RADIATOR 1: ot usilitelya (prokhodnoy Q3) ----------------
# Osnovanie 4 mm (utolshchenie do 9 pod tranzistorom), 62 mm shirina, 40 mm vysota,
# 8 bolshikh reber 15 mm + 8 srednikh 10 mm, tolshchina rebra 1.3 mm, s obeikh storon.
def heatsink_amp():
    W, H, BASE, BOSS = 62.0, 40.0, 4.0, 9.0
    FIN_T, BIG, MED = 1.3, 15.0, 10.0
    p = []
    # osnovanie: stoit na plate, tolshchina po X, shirina po Y, vysota po Z
    p.append(box(0, 0, H/2, BASE, W, H, 'alu'))
    # utolshchenie pod tranzistor: TSENTRIROVANO po tolshchine plastiny (9 mm vsego, po 2.5 s kazhdoy storony)
    p.append(box(0, 0, 15.0, BOSS, 10.0, 30.0, 'alu'))
    # 4 bolshikh rebra: krayniye - vroven s tortsom plastiny (ne dolzhna torchat)
    edges = [-W/2 + FIN_T/2, -W/2 + 5.0, W/2 - 5.0, W/2 - FIN_T/2]
    for y in edges:
        for sx in (-1, 1):
            p.append(box(sx*(BASE/2 + BIG/2), y, H/2, BIG, FIN_T, H, 'alu_d'))
    # srednie rebra: 2 samyh tsentralnyh (+-2 mm) UBRANY - tuda vstayot tranzistor (zazor 10 mm)
    inner = [5.65, 12.0, 19.0]   # 5.65 -> chistyy zazor v tsentre rovno 10.0 mm (shirina TO-220);
    # 26.0 ubrano - tam stoit krayneye bolshoye rebro
    for y in inner:
        for sx in (-1, 1):
            p.append(box(sx*(BASE/2 + MED/2), y, H/2, MED, FIN_T, H, 'alu_d'))
            p.append(box(sx*(BASE/2 + MED/2), -y, H/2, MED, FIN_T, H, 'alu_d'))
    return write('Heatsink_Amp_62x40x34.wrl', p)

# ---------------- RADIATOR 2/3: profil s 7 rebrami (klyuchi buck) ----------------
def heatsink_profile(length, name):
    HGT, BASE, FIN_T, FIN_H = 28.0, 4.0, 1.3, 8.0
    p = []
    # model tsentrirovana po glubine (12 mm = 4 osnovanie + 8 rebra), chtoby sovpadat s konturom futprinta
    p.append(box(0, -BASE/2 - 2.0, HGT/2, length, BASE, HGT, 'alu'))   # osnovanie: dlina po X, tolshchina po Y
    for i in range(7):
        z = 2.0 + i*4.0 + FIN_T/2          # 7 reber GORIZONTALNO, po vysote s shagom 4 mm
        if z > HGT - 1: break
        p.append(box(0, FIN_H/2 - 2.0, z, length, FIN_H, FIN_T, 'alu_d'))   # rebra TOLKO s odnoy storony
    return write(name, p)

# ---------------- TOROIDY ----------------
def toroid(od, thick, turns_r, name, core='green'):
    """Kolzo stoit vertikalno (na rebro): ploskost kolza - XZ."""
    R = (od - thick)/2.0
    rt = thick/2.0 + turns_r          # naruzhnyy radius s namotkoy
    zc = R + rt                       # kolzo stoit na plate
    p = [torus(0, 0, zc, R, thick/2.0, core, 40, 14),
         torus(0, 0, zc, R, rt, 'wire', 64, 18)]
    return write(name, p)

# ---------------- RELE ----------------
def relay(name, sx, sy, sz, m='plast'):
    return write(name, [box(0, 0, sz/2, sx, sy, sz, m)])

if __name__ == '__main__':
    print('=== generatsiya modeley ===')
    for f, s in [heatsink_amp(),
                 heatsink_profile(60.0, 'Heatsink_Profile_60mm.wrl'),
                 heatsink_profile(20.0, 'Heatsink_Profile_20mm.wrl'),
                 toroid(25.0, 10.0, 2.0, 'Toroid_L1_wound_OD29.wrl'),
                 toroid(21.0, 7.0, 1.9, 'Toroid_L3_wound_OD25.wrl'),
                 relay('Relay_MPH_S112A.wrl', 21.0, 16.0, 15.0),
                 relay('Relay_HF3FA.wrl', 15.5, 10.5, 12.0)]:
        print('   %-34s %6.1f KB' % (os.path.basename(f), s/1024.0))
