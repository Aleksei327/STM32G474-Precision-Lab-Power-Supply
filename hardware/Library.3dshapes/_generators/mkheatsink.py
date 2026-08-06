#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v0.2.36: posadochnye mesta radiatorov v Local-biblioteku (mekhanicheskie, bez tsepey)
+ privyazka 3D-modeley k relye i drosselyam."""
import io, os, uuid

LIB = r'D:\Документы\Power supply 0 - 50 V DC-DC\POWER_0-50\Library.pretty'
M3D = '${KIPRJMOD}/Library.3dshapes/'

def U(): return str(uuid.uuid4())

def fp_heatsink(name, sx, sy, model, holes, descr):
    """sx,sy - gabarit v plane platy (mm); holes - [(x,y,d_real)] pilotnye 0.6"""
    hx, hy = sx/2.0, sy/2.0
    s = ['(footprint "%s"' % name,
         '\t(version 20240108)', '\t(generator "python")', '\t(generator_version "10.0")',
         '\t(layer "F.Cu")',
         '\t(descr "%s")' % descr,
         '\t(tags "heatsink mechanical handmade")',
         '\t(attr through_hole exclude_from_pos_files exclude_from_bom)',
         '\t(property "Reference" "HS**" (at 0 %.2f 0) (layer "F.SilkS") (uuid "%s")' % (-hy - 1.5, U()),
         '\t\t(effects (font (size 1 1) (thickness 0.15))))',
         '\t(property "Value" "%s" (at 0 %.2f 0) (layer "F.Fab") (uuid "%s")' % (name, hy + 1.5, U()),
         '\t\t(effects (font (size 1 1) (thickness 0.15))))',
         '\t(property "Datasheet" "" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "%s")' % U(),
         '\t\t(effects (font (size 1 1) (thickness 0.15))))',
         '\t(property "Description" "" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "%s")' % U(),
         '\t\t(effects (font (size 1 1) (thickness 0.15))))']
    # kontur na silke i courtyard
    s.append('\t(fp_rect (start %.2f %.2f) (end %.2f %.2f) (stroke (width 0.15) (type solid)) (fill no) (layer "F.SilkS") (uuid "%s"))' % (-hx, -hy, hx, hy, U()))
    s.append('\t(fp_rect (start %.2f %.2f) (end %.2f %.2f) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd") (uuid "%s"))' % (-hx-0.3, -hy-0.3, hx+0.3, hy+0.3, U()))
    s.append('\t(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab") (uuid "%s")' % U())
    s.append('\t\t(effects (font (size 1 1) (thickness 0.15))))')
    for (x, y, dreal) in holes:
        s.append('\t(pad "" np_thru_hole circle (at %.2f %.2f) (size 0.6 0.6) (drill 0.6) (layers "F&B.Cu" "*.Mask") (uuid "%s"))' % (x, y, U()))
        s.append('\t(fp_circle (center %.2f %.2f) (end %.2f %.2f) (stroke (width 0.12) (type solid)) (fill no) (layer "F.SilkS") (uuid "%s"))' % (x, y, x + dreal/2.0, y, U()))
    s.append('\t(model "%s%s"' % (M3D, model))
    s.append('\t\t(offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
    s.append(')')
    txt = '\n'.join(s) + '\n'
    assert txt.count('(') == txt.count(')'), name
    p = os.path.join(LIB, name + '.kicad_mod')
    io.open(p, 'w', encoding='utf-8').write(txt)
    return name

made = []
made.append(fp_heatsink('Heatsink_Amp_62x40x34', 34.0, 62.0, 'Heatsink_Amp_62x40x34.wrl',
    [(0, -28.0, 2.6), (0, 28.0, 2.6)],
    'Heatsink from an old audio amplifier: 62 x 40 mm, 34 mm deep (4 mm base, 9 mm boss under the transistor, '
    '8 big fins 15 mm + 8 medium 10 mm, 1.3 mm thick, both sides, VERTICAL fins). ~215 cm2, about 2.5 C/W with the fan. '
    'For the linear pass element. Mounting holes are 0.6 mm PILOTS - drill out to 2.6 mm.'))
made.append(fp_heatsink('Heatsink_Profile_60mm', 60.0, 12.0, 'Heatsink_Profile_60mm.wrl',
    [(-20.0, 0.15, 2.25), (20.0, 0.15, 2.25)],
    'Ribbed aluminium profile, 60 mm long: base 4 mm + 7 HORIZONTAL fins 8 x 1.3 mm on one side, 28 mm tall. '
    'For the buck high-side FET, needs airflow. Mounting holes are 0.6 mm pilots - drill out to 2.25 mm.'))
made.append(fp_heatsink('Heatsink_Profile_20mm', 20.0, 12.0, 'Heatsink_Profile_20mm.wrl',
    [(-0.15, 0, 2.25)],
    'Same ribbed profile, 20 mm offcut, for the buck low-side FET (0.3-0.5 W). '
    'Mounting hole is a 0.6 mm pilot - drill out to 2.25 mm.'))
print('sozdano posadochnykh mest: %s' % ', '.join(made))

# --- privyazka modeley k sushchestvuyushchim Local-futprintam ---
LINK = [('Relay_MPH_1A.kicad_mod', 'Relay_MPH_S112A.wrl', (10.6, -6.0, 0), (0, 0, 0)),
        ('Relay_HF3FA_1C.kicad_mod', 'Relay_HF3FA.wrl', (7.0, 0.0, 0), (0, 0, 0)),
        ('L_Toroid_Vertical_Core25x10mm_P14.00mm_D1.8mm.kicad_mod', 'Toroid_L1_wound_OD29.wrl', (0, 0, 0), (0, 0, 90)),
        ('L_Toroid_Vertical_Core21x7mm_P10.00mm_D2.0mm.kicad_mod', 'Toroid_L3_wound_OD25.wrl', (0, 0, 0), (0, 0, 90))]
for fn, model, off, rot in LINK:
    p = os.path.join(LIB, fn)
    s = io.open(p, encoding='utf-8').read()
    if '(model "' in s:
        print('   %s: model uzhe est, propusk' % fn[:44]); continue
    blk = ('\t(model "%s%s"\n\t\t(offset (xyz %.2f %.2f %.2f))\n\t\t(scale (xyz 1 1 1))\n\t\t(rotate (xyz %.0f %.0f %.0f))\n\t)\n'
           % (M3D, model, off[0], off[1], off[2], rot[0], rot[1], rot[2]))
    tail = s.rstrip()
    assert tail.endswith(')')
    s = tail[:-1] + blk + ')\n'
    assert s.count('(') == s.count(')'), fn
    io.open(p, 'w', encoding='utf-8').write(s)
    print('   %-46s -> %s' % (fn[:46], model))
