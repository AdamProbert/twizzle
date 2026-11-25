"""
Twizzle: Fusion 360 script.

Builds the round-five "Chalk" puck that turns a venetian blind's 7 mm hex tilt
wand with a 28BYJ-48 stepper, a green ULN2003 board and an ESP32-C3 SuperMini.

Install: Utilities > Add-Ins > Scripts and Add-Ins > Scripts tab > "+" (or the
green plus) > pick this folder > select Twizzle > Run.
It opens a new design and builds every part as its own component, placed in
its assembled position. Export each printable body as STL (right-click the
body > Save As Mesh) and use the print orientation listed in the README.

All dimensions are millimetres. Values marked MEASURE are best guesses that
should be checked with calipers before printing.
"""

import math
import traceback

import adsk.core
import adsk.fusion

# ---------------------------------------------------------------------------
# Parameters (mm)
# ---------------------------------------------------------------------------

# Printing
CLEAR = 0.2                 # general sliding clearance per side (PLA/PETG, 0.4 nozzle)

# Wand (clear acrylic hex)
WAND_AF = 7.0               # MEASURE: across the flats
WAND_AC = 8.08              # MEASURE: across the corners (7.0 AF -> 8.08 for a perfect hex)
WAND_FIT = 0.4              # extra on the gear's hex bore so the wand slides through
WAND_WALL_GAP = 50.0        # centre of the wand to the wall, at the puck (Adam: ~5 cm)

# Puck body
PUCK_D = 90.0               # outside diameter
PUCK_DEPTH = 37.0           # back face to front face
SHELL = 2.0                 # dome shell thickness
TRAY_FLOOR = 2.5            # tray back thickness
TRAY_WALL = 2.0             # tray side wall thickness
BEVEL = 10.0                # 45 degree front bevel (prints face-down without supports)
EDGE_ROUND = 3.0            # soft round on the two bevel edges
WAND_X = -16.0              # wand sits this far left of centre (front view)
WAND_Z = 19.0               # wand axis height above the back; also the tray/dome split

# Gears (1:1 spur)
GEAR_MODULE = 1.0
GEAR_TEETH = 20
GEAR_FACE = 6.0
GEAR_ADDENDUM = 0.85        # x module; slightly short teeth print stronger tips
GEAR_BACKLASH = 0.2
GEAR_Y = -29.0              # centre of the gear pair along the wand (front view, -y = up)

# 28BYJ-48 (datasheet values)
MOTOR_D = 28.0
MOTOR_LEN = 19.0
MOTOR_SHAFT_OFFSET = 8.0    # shaft is off the body centre by this much
MOTOR_SHAFT_D = 5.0
MOTOR_SHAFT_FLATS = 3.0     # distance across the two flats
MOTOR_FACE_Y = -23.0        # where the shaft face sits
TIE_W = 4.0                 # cable-tie slot width (3.6 mm ties fit)
# Snip the two mounting ears off the motor; they would hit the floor and the dome.

# Green ULN2003 board
BOARD_W = 35.0              # MEASURE (x)
BOARD_H = 32.0              # MEASURE (y)
BOARD_HOLE_DX = 30.0        # MEASURE: hole spacing, centre to centre, along the 35 mm side
BOARD_HOLE_DY = 27.0        # MEASURE: hole spacing along the 32 mm side
BOARD_STANDOFF = 6.0        # height above the tray floor (room for solder pins)
BOARD_CENTRE = (10.0, 16.0)

# ESP32-C3 SuperMini
C3_W = 18.0
C3_H = 22.5
C3_CENTRE = (-31.0, 0.0)

# USB-C pigtail socket
USB_W = 15.8                # across the puck edge
USB_T = 9.3                 # height off the floor
USB_DEPTH = 11.0            # how far it goes into the puck
USB_X = -3.0

# 12 mm tactile switch with round cap
SW_BODY = 12.0
SW_TOTAL_H = 11.0           # MEASURE: bottom of switch body to top of fitted cap
SW_CAP_D = 12.0             # MEASURE: cap diameter
SW_CAP_PROUD = 1.0          # how far the cap stands proud of the dome
SW_POS = (14.0, 22.0)

# Wall mount: base + spacers
PLINTH_D = 60.0
SPACER_T = 5.0
BASE_T = 5.0
STRIP_T = 2.0               # MEASURE: Command strip thickness when pressed
TEETH_COUNT = 72            # 5 degree steps
TOOTH_W = 1.2
TOOTH_H = 0.8
TOOTH_R = (22.5, 28.5)
M4_HOLE = 4.4
M4_NUT_AF = 7.0
M4_NUT_T = 3.2
M4_HEAD_D = 7.6              # button or pan head
M4_HEAD_H = 3.0
M3_TAP = 2.5                # hole for an M3 screw to self-tap into plastic
M3_CLEAR = 3.3
M3_HEAD_D = 5.5
M3_HEAD_H = 3.0
SW_PLUG_T = 3.0             # printed plug that backs the switch so it can't be pushed in


# ---------------------------------------------------------------------------
# Pure geometry helpers (no Fusion calls)
# ---------------------------------------------------------------------------

def spacer_count():
    gap = WAND_WALL_GAP - WAND_Z - STRIP_T - BASE_T
    return max(0, int(round(gap / SPACER_T)))


def gear_outline(module, teeth, addendum=GEAR_ADDENDUM, backlash=GEAR_BACKLASH, flank_pts=7):
    """Closed involute outline as a list of (x, y) in mm, centred on the origin."""
    pa = math.radians(20.0)
    rp = module * teeth / 2.0
    rb = rp * math.cos(pa)
    ro = rp + addendum * module
    rr = rp - 1.25 * module
    inv = math.tan(pa) - pa
    ha = math.pi / (2 * teeth) + inv - backlash / (2 * rp)
    t0 = 0.0 if rr <= rb else math.sqrt((rr / rb) ** 2 - 1)
    t1 = math.sqrt((ro / rb) ** 2 - 1)
    if t1 - math.atan(t1) >= ha:
        raise ValueError("gear teeth come to a point; lower GEAR_ADDENDUM")
    ts = [t0 + (t1 - t0) * i / (flank_pts - 1) for i in range(flank_pts)]
    pts = []
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        flank = [(rb * math.sqrt(1 + t * t), t - math.atan(t)) for t in ts]
        if rr < rb:
            pts.append((rr * math.cos(a - ha), rr * math.sin(a - ha)))
        for r, phi in flank:
            pts.append((r * math.cos(a - ha + phi), r * math.sin(a - ha + phi)))
        for r, phi in reversed(flank):
            pts.append((r * math.cos(a + ha - phi), r * math.sin(a + ha - phi)))
        if rr < rb:
            pts.append((rr * math.cos(a + ha), rr * math.sin(a + ha)))
    return pts


def hexagon(af, rot=0.0):
    rc = af / math.sqrt(3)
    return [(rc * math.cos(math.radians(rot + 60 * i)), rc * math.sin(math.radians(rot + 60 * i))) for i in range(6)]


def d_bore(d, flats):
    """Round bore with two flats, as a closed list of segments ('L' line / 'A' arc)."""
    r = d / 2.0
    f = flats / 2.0
    y = math.sqrt(r * r - f * f)
    return [('L', (f, -y), (f, y)),
            ('A', (f, y), (0.0, r), (-f, y)),
            ('L', (-f, y), (-f, -y)),
            ('A', (-f, -y), (0.0, -r), (f, -y))]


def rounded_polyline(pts, radii):
    """Turn a polyline (list of (x, y)) into segments with round corners.
    radii[i] is the round at pts[i] (0 = sharp; ends are never rounded).
    Returns [('L', p, q) | ('A', p, mid, q)]."""
    segs = []
    cur = pts[0]
    for i in range(1, len(pts)):
        p = pts[i]
        r = radii[i] if i < len(pts) - 1 else 0
        if r <= 0:
            segs.append(('L', cur, p))
            cur = p
            continue
        a, b = pts[i - 1], pts[i + 1]
        v1 = ((a[0] - p[0]), (a[1] - p[1]))
        v2 = ((b[0] - p[0]), (b[1] - p[1]))
        l1 = math.hypot(*v1)
        l2 = math.hypot(*v2)
        u1 = (v1[0] / l1, v1[1] / l1)
        u2 = (v2[0] / l2, v2[1] / l2)
        ang = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1])))
        tlen = r / math.tan(ang / 2)
        t1 = (p[0] + u1[0] * tlen, p[1] + u1[1] * tlen)
        t2 = (p[0] + u2[0] * tlen, p[1] + u2[1] * tlen)
        bis = (u1[0] + u2[0], u1[1] + u2[1])
        bl = math.hypot(*bis)
        bis = (bis[0] / bl, bis[1] / bl)
        cdist = r / math.sin(ang / 2)
        c = (p[0] + bis[0] * cdist, p[1] + bis[1] * cdist)
        mid = (c[0] - bis[0] * r, c[1] - bis[1] * r)
        segs.append(('L', cur, t1))
        segs.append(('A', t1, mid, t2))
        cur = t2
    return segs


def dome_profiles():
    """(outer, inner) half-profiles of the dome in (radius, z), as segment lists."""
    R = PUCK_D / 2.0
    zf = PUCK_DEPTH
    rb = R - BEVEL                      # where the flat front ends
    outer_pts = [(0.0, zf), (rb, zf), (R, zf - BEVEL), (R, WAND_Z)]
    off = SHELL * math.sqrt(2)          # 45 degree line moved in by SHELL
    zi = zf - SHELL
    ri = R - SHELL
    r_flat = rb + SHELL - off           # inner flat meets inner bevel
    z_side = (zf - off) - (ri - rb)     # inner bevel meets inner wall
    inner_pts = [(0.0, zi), (r_flat, zi), (ri, z_side), (ri, WAND_Z)]
    return (rounded_polyline(outer_pts, [0, EDGE_ROUND, EDGE_ROUND, 0]),
            rounded_polyline(inner_pts, [0, max(0.5, EDGE_ROUND - SHELL), max(0.5, EDGE_ROUND - SHELL), 0]))


def dome_outer_z(r):
    """Height of the outer dome surface at radius r (ignores the small rounds)."""
    R = PUCK_D / 2.0
    rb = R - BEVEL
    if r <= rb:
        return PUCK_DEPTH
    return PUCK_DEPTH - (r - rb)


def radial_bar(r0, r1, width, ang_deg):
    a = math.radians(ang_deg)
    c, s = math.cos(a), math.sin(a)
    h = width / 2.0
    return [(r0 * c + h * s, r0 * s - h * c),
            (r1 * c + h * s, r1 * s - h * c),
            (r1 * c - h * s, r1 * s + h * c),
            (r0 * c - h * s, r0 * s + h * c)]


# ---------------------------------------------------------------------------
# Fusion helpers
# ---------------------------------------------------------------------------

def cm(v):
    return v / 10.0


def V(v):
    return adsk.core.ValueInput.createByReal(cm(v))


OP_NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
OP_JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
OP_CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
OP_INT = adsk.fusion.FeatureOperations.IntersectFeatureOperation


class Builder:
    def __init__(self, comp):
        self.c = comp

    # planes -----------------------------------------------------------
    def _offset_plane(self, base, along, value):
        if abs(value) < 1e-9:
            return base
        n = base.geometry.normal
        sign = float(getattr(n, along))
        inp = self.c.constructionPlanes.createInput()
        inp.setByOffset(base, V(value * sign))
        return self.c.constructionPlanes.add(inp)

    def sk_xy(self, z):
        return self.c.sketches.add(self._offset_plane(self.c.xYConstructionPlane, 'z', z))

    def sk_xz(self, y):
        return self.c.sketches.add(self._offset_plane(self.c.xZConstructionPlane, 'y', y))

    # drawing ----------------------------------------------------------
    @staticmethod
    def P(sk, x, y, z):
        return sk.modelToSketchSpace(adsk.core.Point3D.create(cm(x), cm(y), cm(z)))

    def circle(self, sk, x, y, z, r):
        sk.sketchCurves.sketchCircles.addByCenterRadius(self.P(sk, x, y, z), cm(r))

    def poly(self, sk, pts3):
        lines = sk.sketchCurves.sketchLines
        pts = [self.P(sk, *p) for p in pts3]
        first = lines.addByTwoPoints(pts[0], pts[1])
        prev = first.endSketchPoint
        for p in pts[2:]:
            prev = lines.addByTwoPoints(prev, p).endSketchPoint
        lines.addByTwoPoints(prev, first.startSketchPoint)

    def segs(self, sk, segs, to3):
        """Draw a closed chain of ('L', p, q) / ('A', p, m, q) given in 2D, mapped by to3."""
        lines = sk.sketchCurves.sketchLines
        arcs = sk.sketchCurves.sketchArcs
        first = None
        prev = None
        start_xy = segs[0][1]
        for n, s in enumerate(segs):
            start = prev if prev is not None else self.P(sk, *to3(s[1]))
            closes = n == len(segs) - 1 and first is not None and \
                abs(s[-1][0] - start_xy[0]) < 1e-6 and abs(s[-1][1] - start_xy[1]) < 1e-6
            end = first if closes else self.P(sk, *to3(s[-1]))
            if s[0] == 'L':
                ent = lines.addByTwoPoints(start, end)
            else:
                ent = arcs.addByThreePoints(start, self.P(sk, *to3(s[2])), end)
            if first is None:
                first = ent.startSketchPoint
            prev = ent.endSketchPoint
        return first, prev

    # profiles ---------------------------------------------------------
    @staticmethod
    def all_profiles(sk):
        col = adsk.core.ObjectCollection.create()
        for i in range(sk.profiles.count):
            col.add(sk.profiles.item(i))
        return col

    @staticmethod
    def profile_with_loops(sk, loops):
        best = None
        best_area = -1
        for i in range(sk.profiles.count):
            p = sk.profiles.item(i)
            if p.profileLoops.count == loops:
                a = float(p.areaProperties().area)
                if a > best_area:
                    best, best_area = p, a
        return best if best is not None else sk.profiles.item(0)

    @staticmethod
    def largest_profile(sk):
        best = None
        best_area = -1
        for i in range(sk.profiles.count):
            p = sk.profiles.item(i)
            a = float(p.areaProperties().area)
            if a > best_area:
                best, best_area = p, a
        return best

    # features ---------------------------------------------------------
    def extrude(self, prof, dist, op, bodies=None):
        ex = self.c.features.extrudeFeatures
        inp = ex.createInput(prof, op)
        inp.setDistanceExtent(False, V(dist))
        if bodies:
            inp.participantBodies = list(bodies)
        return ex.add(inp)

    def extrude_sym(self, prof, total, op, bodies=None):
        ex = self.c.features.extrudeFeatures
        inp = ex.createInput(prof, op)
        inp.setSymmetricExtent(V(total), True)
        if bodies:
            inp.participantBodies = list(bodies)
        return ex.add(inp)

    def revolve(self, prof, op):
        rv = self.c.features.revolveFeatures
        inp = rv.createInput(prof, self.c.zConstructionAxis, op)
        inp.setAngleExtent(False, adsk.core.ValueInput.createByString('360 deg'))
        return rv.add(inp)

    def combine(self, target, tools, op, keep=False):
        cf = self.c.features.combineFeatures
        col = adsk.core.ObjectCollection.create()
        for t in tools:
            col.add(t)
        inp = cf.createInput(target, col)
        inp.operation = op
        inp.isKeepToolBodies = keep
        return cf.add(inp)

    # shapes -----------------------------------------------------------
    def cyl_z(self, x, y, z0, h, r, op, bodies=None):
        sk = self.sk_xy(z0)
        self.circle(sk, x, y, z0, r)
        return self.extrude(sk.profiles.item(0), h, op, bodies)

    def tube_z(self, x, y, z0, h, r_out, r_in, op, bodies=None):
        sk = self.sk_xy(z0)
        self.circle(sk, x, y, z0, r_out)
        self.circle(sk, x, y, z0, r_in)
        return self.extrude(self.profile_with_loops(sk, 2), h, op, bodies)

    def box(self, x0, x1, y0, y1, z0, z1, op, bodies=None):
        sk = self.sk_xy(z0)
        self.poly(sk, [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)])
        return self.extrude(sk.profiles.item(0), z1 - z0, op, bodies)

    def cyl_y(self, x, z, y_mid, length, r, op, bodies=None):
        sk = self.sk_xz(y_mid)
        self.circle(sk, x, y_mid, z, r)
        return self.extrude_sym(sk.profiles.item(0), length, op, bodies)

    def hex_pocket_z(self, x, y, z0, h, af, op, bodies=None):
        sk = self.sk_xy(z0)
        self.poly(sk, [(x + px, y + py, z0) for px, py in hexagon(af)])
        return self.extrude(sk.profiles.item(0), h, op, bodies)

    def radial_bars(self, z0, h, width, op, bodies=None):
        sk = self.sk_xy(z0)
        for i in range(TEETH_COUNT):
            bar = radial_bar(TOOTH_R[0], TOOTH_R[1], width, 360.0 * i / TEETH_COUNT)
            self.poly(sk, [(px, py, z0) for px, py in bar])
        return self.extrude(self.all_profiles(sk), h, op, bodies)


def new_comp(root, name):
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    return comp


def first_body(feature, name):
    b = feature.bodies.item(0)
    b.name = name
    return b


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------

def build_tray(root):
    c = new_comp(root, 'Tray (print back-down)')
    b = Builder(c)
    R = PUCK_D / 2.0
    Ri = R - TRAY_WALL
    body = first_body(b.cyl_z(0, 0, 0, WAND_Z, R, OP_NEW), 'Tray')
    b.cyl_z(0, 0, TRAY_FLOOR, WAND_Z - TRAY_FLOOR, Ri, OP_CUT, [body])
    fl = TRAY_FLOOR

    # wand gear end-stops (U seats cut later)
    gap = 0.5
    g0, g1 = GEAR_Y - GEAR_FACE / 2, GEAR_Y + GEAR_FACE / 2
    stop_top = WAND_Z - 3.5
    b.box(WAND_X - 7, WAND_X + 7, g0 - gap - 4, g0 - gap, fl, stop_top, OP_JOIN, [body])
    b.box(WAND_X - 7, WAND_X + 7, g1 + gap, g1 + gap + 4, fl, stop_top, OP_JOIN, [body])

    # motor saddle
    mx = WAND_X + GEAR_MODULE * GEAR_TEETH + MOTOR_SHAFT_OFFSET   # motor body centre x
    m0, m1 = MOTOR_FACE_Y + 0.5, MOTOR_FACE_Y + MOTOR_LEN - 0.5
    b.box(mx - 12, mx + 12, m0, m1, fl, WAND_Z - 3, OP_JOIN, [body])

    # board standoffs
    bx, by = BOARD_CENTRE
    holes = [(bx + dx * BOARD_HOLE_DX / 2, by + dy * BOARD_HOLE_DY / 2) for dx in (-1, 1) for dy in (-1, 1)]
    for hx, hy in holes:
        b.cyl_z(hx, hy, fl, BOARD_STANDOFF, 3.0, OP_JOIN, [body])

    # pillars that carry the dome screws up to the split line
    for x, y in DOME_SCREWS:
        b.cyl_z(x, y, fl, WAND_Z - fl, 3.5, OP_JOIN, [body])

    # centre nut boss for the M4 clamp screw
    b.cyl_z(0, 0, fl, 4.5, 6.0, OP_JOIN, [body])

    # C3 SuperMini frame
    cx, cy = C3_CENTRE
    w, h = C3_W / 2 + CLEAR, C3_H / 2 + CLEAR
    b.box(cx - w - 1.2, cx + w + 1.2, cy - h - 1.2, cy + h + 1.2, fl, fl + 2.0, OP_JOIN, [body])
    b.box(cx - w, cx + w, cy - h, cy + h, fl, fl + 2.1, OP_CUT, [body])

    # ---- cuts ----
    # U seats in the gear stops (the wand is the gear's axle)
    b.cyl_y(WAND_X, WAND_Z, GEAR_Y, GEAR_FACE + 2 * gap + 10, WAND_AC / 2 + 1.0, OP_CUT, [body])
    # motor saddle
    b.cyl_y(mx, WAND_Z, (m0 + m1) / 2, m1 - m0 + 0.01, MOTOR_D / 2 + 0.2, OP_CUT, [body])
    # two cable-tie slots through the saddle; the ties go right round the motor
    for ty in (m0 + 3.5, m1 - 3.5):
        b.box(mx - 20, mx + 20, ty - TIE_W / 2, ty + TIE_W / 2, fl, WAND_Z, OP_CUT, [body])
    # standoff holes
    for hx, hy in holes:
        b.cyl_z(hx, hy, fl + 1, BOARD_STANDOFF, M3_TAP / 2, OP_CUT, [body])
    # M4 clamp: through hole + nut pocket
    b.cyl_z(0, 0, -1, fl + 6, M4_HOLE / 2, OP_CUT, [body])
    b.hex_pocket_z(0, 0, fl + 4.5 - (M4_NUT_T + 0.3), M4_NUT_T + 0.31, M4_NUT_AF + 0.3, OP_CUT, [body])
    # tray-to-dome screw holes (M3 x 20 from the back, heads sunk flush)
    for x, y in DOME_SCREWS:
        b.cyl_z(x, y, -1, WAND_Z + 2, M3_CLEAR / 2, OP_CUT, [body])
        b.cyl_z(x, y, -1, 1 + M3_HEAD_H, M3_HEAD_D / 2 + 0.3, OP_CUT, [body])
    # USB-C socket pocket through the bottom edge
    ux0, ux1 = USB_X - USB_W / 2 - CLEAR, USB_X + USB_W / 2 + CLEAR
    ry = math.sqrt(R * R - USB_X * USB_X)
    b.box(ux0, ux1, ry - USB_DEPTH - 0.3, R + 2, fl, fl + USB_T + 2 * CLEAR, OP_CUT, [body])
    # wand notches (half-holes; the dome supplies the other half)
    b.cyl_y(WAND_X, WAND_Z, 0, PUCK_D + 20, WAND_AC / 2 + 0.25, OP_CUT, [body])
    # angle-index grooves on the back (match the spacer teeth)
    b.radial_bars(0, TOOTH_H + 0.2, TOOTH_W + 0.4, OP_CUT, [body])
    return c


DOME_SCREWS = [(37.0, 0.0), (-30.0, -20.0)]   # M3 x 20 from the back


def build_dome(root):
    c = new_comp(root, 'Dome (print face-down)')
    b = Builder(c)
    R = PUCK_D / 2.0
    outer_segs, inner_segs = dome_profiles()

    def rev(segs, name):
        sk = b.sk_xz(0)
        to3 = lambda p: (p[0], 0.0, p[1])
        first, last = b.segs(sk, segs, to3)
        lines = sk.sketchCurves.sketchLines
        # close along the axis and the split plane
        bottom_axis = b.P(sk, 0, 0, WAND_Z)
        l1 = lines.addByTwoPoints(last, bottom_axis)
        lines.addByTwoPoints(l1.endSketchPoint, first)
        return first_body(b.revolve(b.largest_profile(sk), OP_NEW), name)

    outer = rev(outer_segs, 'Dome')
    inner = rev(inner_segs, 'dome void')

    feats = []
    # screw bosses
    for x, y in DOME_SCREWS:
        feats.append(first_body(b.cyl_z(x, y, WAND_Z, PUCK_DEPTH - WAND_Z + 2, 3.0, OP_NEW), 'boss'))
    # button socket
    sx, sy = SW_POS
    sw_bottom = PUCK_DEPTH + SW_CAP_PROUD - SW_TOTAL_H
    sock_bottom = sw_bottom - SW_PLUG_T - 0.5
    sk = b.sk_xy(sock_bottom)
    o, i = SW_BODY / 2 + CLEAR + 1.6, SW_BODY / 2 + CLEAR
    b.poly(sk, [(sx - o, sy - o, sock_bottom), (sx + o, sy - o, sock_bottom), (sx + o, sy + o, sock_bottom), (sx - o, sy + o, sock_bottom)])
    b.poly(sk, [(sx - i, sy - i, sock_bottom), (sx + i, sy - i, sock_bottom), (sx + i, sy + i, sock_bottom), (sx - i, sy + i, sock_bottom)])
    feats.append(first_body(b.extrude(b.profile_with_loops(sk, 2), PUCK_DEPTH - sock_bottom + 1, OP_NEW), 'switch socket'))

    for f in feats:
        b.combine(f, [outer], OP_INT, keep=True)
    b.combine(outer, [inner], OP_CUT)

    # press-fit lip that drops into the tray
    lip_in = R - TRAY_WALL - 1.5
    lip_up = first_body(b.tube_z(0, 0, WAND_Z, 2.0, R - SHELL + 0.2, lip_in, OP_NEW), 'lip')
    lip_lo = first_body(b.tube_z(0, 0, WAND_Z - 3.0, 3.0, R - TRAY_WALL - 0.15, lip_in, OP_NEW), 'lip2')
    b.combine(outer, feats + [lip_up, lip_lo], OP_JOIN)

    # ---- cuts ----
    b.cyl_z(sx, sy, sw_bottom, 30, SW_CAP_D / 2 + 0.3, OP_CUT, [outer])
    for x, y in DOME_SCREWS:
        depth = min(9.0, dome_outer_z(math.hypot(x, y)) - WAND_Z - 1.5)
        b.cyl_z(x, y, WAND_Z - 0.01, depth, M3_TAP / 2, OP_CUT, [outer])
    b.cyl_y(WAND_X, WAND_Z, 0, PUCK_D + 20, WAND_AC / 2 + 0.25, OP_CUT, [outer])
    # USB socket clearance in the lip
    ux0, ux1 = USB_X - USB_W / 2 - CLEAR, USB_X + USB_W / 2 + CLEAR
    b.box(ux0, ux1, R - 14, R + 2, WAND_Z - 3.5, WAND_Z + 0.01, OP_CUT, [outer])
    return c


def build_gear(root, name, cx, bore):
    c = new_comp(root, name)
    b = Builder(c)
    sk = b.sk_xz(GEAR_Y)
    to3 = lambda p: (cx + p[0], GEAR_Y, WAND_Z + p[1])
    b.poly(sk, [to3(p) for p in gear_outline(GEAR_MODULE, GEAR_TEETH)])
    if bore == 'hex':
        b.poly(sk, [to3(p) for p in hexagon(WAND_AF + WAND_FIT, 30)])
    else:
        b.segs(sk, d_bore(MOTOR_SHAFT_D + 0.1, MOTOR_SHAFT_FLATS + 0.1), to3)
    feat = b.extrude_sym(b.profile_with_loops(sk, 2), GEAR_FACE, OP_NEW)
    first_body(feat, name.split(' (')[0])
    return c


def build_switch_plug(root):
    """Square plug pressed into the back of the switch socket. Two notches let the legs out."""
    c = new_comp(root, 'Switch plug (print flat)')
    b = Builder(c)
    sx, sy = SW_POS
    top = PUCK_DEPTH + SW_CAP_PROUD - SW_TOTAL_H
    h = SW_BODY / 2 + CLEAR - 0.1
    body = first_body(b.box(sx - h, sx + h, sy - h, sy + h, top - SW_PLUG_T, top, OP_NEW), 'Switch plug')
    for side in (-1, 1):
        x0 = sx + side * h
        b.box(min(x0, x0 - side * 1.6), max(x0, x0 - side * 1.6), sy - 3.5, sy + 3.5, top - SW_PLUG_T - 1, top + 1, OP_CUT, [body])
    return c


def build_mount(root, n):
    c = new_comp(root, 'Wall mount (print flat, teeth up)')
    b = Builder(c)
    R = PLINTH_D / 2.0
    z = 0.0
    for i in range(n):
        top = z
        bot = z - SPACER_T
        body = first_body(b.cyl_z(0, 0, bot, SPACER_T, R, OP_NEW), 'Spacer %d' % (i + 1))
        b.cyl_z(0, 0, bot - 1, SPACER_T + 2, M4_HOLE / 2, OP_CUT, [body])
        b.radial_bars(top, TOOTH_H, TOOTH_W, OP_JOIN, [body])
        b.radial_bars(bot, TOOTH_H + 0.2, TOOTH_W + 0.4, OP_CUT, [body])
        z = bot
    top = z
    bot = z - BASE_T
    base = first_body(b.cyl_z(0, 0, bot, BASE_T, R, OP_NEW), 'Base')
    b.cyl_z(0, 0, bot - 1, BASE_T + 2, M4_HOLE / 2, OP_CUT, [base])
    b.cyl_z(0, 0, bot, M4_HEAD_H + 0.2, M4_HEAD_D / 2 + 0.4, OP_CUT, [base])
    b.radial_bars(top, TOOTH_H, TOOTH_W, OP_JOIN, [base])
    return c, bot


def build_reference(root, wall_z):
    c = new_comp(root, 'Reference parts (do not print)')
    b = Builder(c)
    # wand
    sk = b.sk_xz(0)
    b.poly(sk, [(WAND_X + px, 0, WAND_Z + py) for px, py in hexagon(WAND_AF, 30)])
    first_body(b.extrude_sym(sk.profiles.item(0), 160, OP_NEW), 'wand')
    # motor
    mx = WAND_X + GEAR_MODULE * GEAR_TEETH + MOTOR_SHAFT_OFFSET
    first_body(b.cyl_y(mx, WAND_Z, MOTOR_FACE_Y + MOTOR_LEN / 2, MOTOR_LEN, MOTOR_D / 2, OP_NEW), '28BYJ-48')
    # board
    bx, by = BOARD_CENTRE
    z0 = TRAY_FLOOR + BOARD_STANDOFF
    first_body(b.box(bx - BOARD_W / 2, bx + BOARD_W / 2, by - BOARD_H / 2, by + BOARD_H / 2, z0, z0 + 1.6, OP_NEW), 'ULN2003 board')
    cx, cy = C3_CENTRE
    first_body(b.box(cx - C3_W / 2, cx + C3_W / 2, cy - C3_H / 2, cy + C3_H / 2, TRAY_FLOOR, TRAY_FLOOR + 4, OP_NEW), 'ESP32-C3 SuperMini')
    R = PUCK_D / 2.0
    ry = math.sqrt(R * R - USB_X * USB_X)
    first_body(b.box(USB_X - USB_W / 2, USB_X + USB_W / 2, ry - USB_DEPTH, ry, TRAY_FLOOR, TRAY_FLOOR + USB_T, OP_NEW), 'USB-C socket')
    # wall
    first_body(b.box(-80, 80, -80, 80, wall_z - 3, wall_z, OP_NEW), 'wall')
    return c


# ---------------------------------------------------------------------------

def tidy(root):
    """Hide the helper planes and sketches so only the parts show."""
    for i in range(root.occurrences.count):
        comp = root.occurrences.item(i).component
        for j in range(comp.constructionPlanes.count):
            comp.constructionPlanes.item(j).isLightBulbOn = False
        for j in range(comp.sketches.count):
            comp.sketches.item(j).isVisible = False


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent

        n = spacer_count()
        build_tray(root)
        build_dome(root)
        build_gear(root, 'Wand gear (print flat)', WAND_X, 'hex')
        build_gear(root, 'Motor pinion (print flat)', WAND_X + GEAR_MODULE * GEAR_TEETH, 'd')
        build_switch_plug(root)
        _, base_back = build_mount(root, n)
        build_reference(root, base_back - STRIP_T)
        tidy(root)

        head_seat = base_back + M4_HEAD_H + 0.2
        nut_top = TRAY_FLOOR + 4.5
        screw = nut_top - head_seat
        ui.messageBox(
            'Twizzle built.\n\n'
            'Spacers to print: %d (plus the base)\n'
            'Clamp screw: M4 x %d (needs at least %.1f mm) + M4 nut\n'
            'Dome screws: 2 x M3 x 20 from the back\n'
            'Motor: 2 cable ties, up to %.1f mm wide, round the motor and saddle\n'
            'Board screws: 4 x M3 x 6 (or M2.5)\n\n'
            'Parts marked "do not print" are for checking fit only.'
            % (n, int(math.ceil(screw / 5.0) * 5), screw, TIE_W - 0.5))
    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
