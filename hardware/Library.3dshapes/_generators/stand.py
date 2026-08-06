# -*- coding: utf-8 -*-
"""Mini-stend: kopiya platy, gde ostavleny tolko nuzhnye detali, sdvinuty v ryad
i obvedeny malenkim konturom -> render krupno, bez vozni s --pan."""
import io, os, sys
import pcbnew
SRC = r'D:\Документы\Power supply 0 - 50 V DC-DC\POWER_0-50\POWER_0-50.kicad_pcb'
KEEP = sys.argv[1].split(',')
W, H, STEP = 30.0*len(KEEP), 44.0, 30.0
b = pcbnew.LoadBoard(SRC)
kill = [f for f in b.GetFootprints() if f.GetReference() not in KEEP]
kill += [t for t in b.GetTracks()]
kill += [d for d in b.GetDrawings()]
kill += [z for z in b.Zones()]
for it in kill: b.Remove(it)
keep = {f.GetReference(): f for f in b.GetFootprints()}
for i, r in enumerate(KEEP):
    if r in keep:
        keep[r].SetOrientationDegrees(0.0)   # vse detali vdol X - udobno smotret sboku
        keep[r].SetPosition(pcbnew.VECTOR2I(int((15.0 + i*STEP)*1e6), int(22.0*1e6)))
# modeli po ABSOLYUTNYM putyam - inache ${KIPRJMOD} ukazhet na papku stenda
PRJ = os.path.dirname(SRC)
for f in b.GetFootprints():
    ms = []
    for m in f.Models():
        n = pcbnew.FP_3DMODEL()
        n.m_Filename = m.m_Filename.replace('${KIPRJMOD}', PRJ.replace(chr(92), '/'))
        n.m_Offset, n.m_Rotation, n.m_Scale, n.m_Show = m.m_Offset, m.m_Rotation, m.m_Scale, True
        ms.append(n)
    f.Models().clear()
    for n in ms: f.Models().push_back(n)
pts = [(0,0),(W,0),(W,H),(0,H),(0,0)]
for i in range(4):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(int(pts[i][0]*1e6), int(pts[i][1]*1e6)))
    s.SetEnd(pcbnew.VECTOR2I(int(pts[i+1][0]*1e6), int(pts[i+1][1]*1e6)))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(100000)
    b.Add(s)
pcbnew.SaveBoard(os.path.join(os.getcwd(), 'stand.kicad_pcb'), b)
io.open('stand.txt','w',encoding='utf-8').write('ok: ' + ','.join(KEEP))
