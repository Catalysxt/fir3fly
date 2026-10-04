# fir3fly enclosure generator -- run inside FreeCAD with enclosure.FCStd active:
#   exec(open(r"<path>\enclosure_gen.py").read())
# Builds Enclosure_Base and Enclosure_Lid around the imported PCB model.
#
# Design: the left/right (X) ends are flush with the PCB edges so two enclosed
# boards butt together and the right-angle header of one fully mates with the
# socket of the next. End walls sit ON the PCB edge strip (lid above, base rib
# below) and are notched for the connectors. Y walls are conventional.
# Lid is a solid thin top meant to be printed in white/translucent as a diffuser.
# Fastening: 3x M2 screws through lid + PCB into pilot holes in base bosses.
import FreeCAD, Part
from FreeCAD import Vector as V

# ---- PCB (from the KiCad model, global coords, mm) ----
PX0, PX1 = 25.35, 107.6          # board X extents (flush ends)
PY0, PY1 = -152.525, -21.775     # board Y extents
PT = 1.51                        # board thickness (Z 0..PT)
HOLES = [(30.6, -25.77), (103.1, -25.77), (66.47, -142.65)]   # Ø2.5 plated
# connector footprints on the edge strip (Y range of plastic body)
SOCKET_Y = (-148.97, -133.73)    # left, female
HEADER_Y = (-149.00, -133.76)    # right, male (pins protrude 5.4 mm past edge)

# ---- enclosure parameters ----
WALL = 2.0          # Y wall thickness, and width of the end-wall strip on the PCB
CLR = 0.3           # PCB-to-wall clearance in Y
NOTCH_CLR = 0.3     # connector notch clearance each side
FLOOR = 2.0         # base floor thickness
UNDER = 2.5         # gap under PCB (THT pins reach -1.7)
LEDGE = 1.5         # PCB support ledge width along the Y edges
CEIL = 6.0          # lid inner ceiling Z (tallest part 4.135)
TOP = 1.2           # lid top thickness (diffuser)
SPLIT = 1.5         # base/lid seam Z (just under PCB top so lid clamps PCB)
BOSS_D = 5.0        # boss / lid column OD
PILOT_D = 1.7       # M2 self-tap pilot in base
CLEAR_D = 2.4       # M2 clearance in lid

OY0, OY1 = PY0 - CLR - WALL, PY1 + CLR + WALL    # outer Y
IY0, IY1 = PY0 - CLR, PY1 + CLR                  # inner Y
ZB = -UNDER - FLOOR                              # base bottom
ZT = CEIL + TOP                                  # lid top
EX0, EX1 = PX0 + WALL, PX1 - WALL                # inner faces of end walls


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(d, x, y, z0, z1):
    return Part.makeCylinder(d / 2, z1 - z0, V(x, y, z0))


def post(x, y, z0, z1, wy0, wy1):
    """Boss/column; merged into any nearby wall face (X: EX0/EX1, Y: wy0/wy1)
    with a web so it never touches a wall tangentially or leaves a sliver gap
    (both give non-manifold / unprintable geometry)."""
    p = cyl(BOSS_D, x, y, z0, z1)
    r = BOSS_D / 2
    if x - r - EX0 < 1.5:
        p = p.fuse(box(EX0 - 0.01, x, y - r, y + r, z0, z1))
    if EX1 - (x + r) < 1.5:
        p = p.fuse(box(x, EX1 + 0.01, y - r, y + r, z0, z1))
    if y - r - wy0 < 1.5:
        p = p.fuse(box(x - r, x + r, wy0 - 0.01, y, z0, z1))
    if wy1 - (y + r) < 1.5:
        p = p.fuse(box(x - r, x + r, y, wy1 + 0.01, z0, z1))
    return p


def make_base():
    s = box(PX0, PX1, OY0, OY1, ZB, SPLIT)
    s = s.cut(box(PX0 - 1, PX1 + 1, IY0, IY1, 0, SPLIT + 1))          # PCB pocket, open at ends
    ly0, ly1 = IY0 + LEDGE + CLR, IY1 - LEDGE - CLR                   # ledge inner faces
    s = s.cut(box(EX0, EX1, ly0, ly1, -UNDER, 0.01))                   # cavity under PCB
    for x, y in HOLES:
        s = s.fuse(post(x, y, -UNDER - 0.01, 0, ly0, ly1))
        s = s.cut(cyl(PILOT_D, x, y, ZB + 0.8, 0.1))                   # blind, 0.8 mm skin
    return s.removeSplitter()


def make_lid():
    s = box(PX0, PX1, OY0, OY1, SPLIT, ZT)
    s = s.cut(box(PX0 - 1, PX1 + 1, IY0, IY1, SPLIT - 1, PT + 0.05))   # seat over PCB
    s = s.cut(box(EX0, EX1, IY0, IY1, PT, CEIL))                       # inner cavity
    for x, y in HOLES:
        s = s.fuse(post(x, y, PT + 0.05, CEIL + 0.01, IY0, IY1))  # clamping column
        s = s.cut(cyl(CLEAR_D, x, y, PT - 1, ZT + 1))
    # connector notches through the end walls
    for (y0, y1), (x0, x1) in ((SOCKET_Y, (PX0 - 1, EX0 + 0.01)),
                               (HEADER_Y, (EX1 - 0.01, PX1 + 1))):
        s = s.cut(box(x0, x1, y0 - NOTCH_CLR, y1 + NOTCH_CLR, PT, CEIL))
    return s.removeSplitter()


doc = FreeCAD.ActiveDocument
for name, fn, color in (("Enclosure_Base", make_base, (0.25, 0.25, 0.28)),
                        ("Enclosure_Lid", make_lid, (0.95, 0.95, 0.9))):
    o = doc.getObject(name) or doc.addObject("Part::Feature", name)
    o.Shape = fn()
    if FreeCAD.GuiUp:
        o.ViewObject.ShapeColor = color
        if name == "Enclosure_Lid":
            o.ViewObject.Transparency = 60
doc.recompute()
