"""
Twizzle: Fusion 360 script.

Builds the "Chalk" puck that turns a venetian blind's 7 mm hex tilt wand with a
28BYJ-48 stepper, a green ULN2003 board and an ESP32-C3 SuperMini, plus the
90 mm mount that holds it off the wall.

Install: Utilities > Add-Ins > Scripts and Add-Ins > Scripts tab > "+" (or the
green plus) > pick this folder > select Twizzle > Run.
It opens a new design and builds every part as its own component, placed in
its assembled position. Each component's name says how to print it. Export
each printable body as STL (right-click the body > Save As Mesh).

The geometry is written against a small Builder interface, so the same part
code also runs outside Fusion (cad/check/check.py builds it in CadQuery to
check fits and overhangs).

All dimensions are millimetres. Values marked MEASURE are best guesses that
should be checked with calipers before printing.
"""

import math
import traceback

try:
    import adsk.core
    import adsk.fusion
except ImportError:          # running outside Fusion (cad/check)
    adsk = None

# ---------------------------------------------------------------------------
# Parameters (mm)
# ---------------------------------------------------------------------------

# Printing
CLEAR = 0.2                 # general sliding clearance per side (PLA/PETG, 0.4 nozzle)
MIN_WALL = 1.2              # self-check: thinnest wall allowed (3 lines at 0.4 mm)
MIN_ENGAGE = 3.5            # self-check: least thread a screw must have in its insert

# Fasteners: M3 everywhere, into brass heat-set inserts
INSERT_D = 4.2              # pocket diameter (PokePi coupon: fitted perfectly)
INSERT_L = 5.7              # MEASURE: insert length
INSERT_DEPTH = INSERT_L + 1.0
INSERT_BOSS_D = 8.6         # boss round an insert pocket (2.2 mm wall; 1.2 mm round a counterbore)
M3_CLEAR = 3.4
M3_HEAD_D = 5.5             # socket head
M3_HEAD_H = 3.0
M3_CB_D = 6.2               # counterbore for the head
M3_CB_SINK = 0.5            # head sits this far below the surface

# Wand (clear acrylic hex)
WAND_AF = 7.0               # MEASURE: across the flats
WAND_AC = WAND_AF * 2 / math.sqrt(3)   # across the corners (8.08 for a 7.0 hex)
WAND_FIT = 0.4              # extra on the gear's hex bore so the wand slides through
WAND_LEAD = 1.2             # 45 degree lead-in on each end of the gear's hex bore
WAND_PORT_CLEAR = 1.5       # the case never touches the wand: the gear's journals carry it
WAND_WALL_GAP = 50.0        # centre of the wand to the wall (Adam: ~5 cm)

# Puck body
PUCK_D = 90.0               # outside diameter (the mount matches it)
PUCK_DEPTH = 37.0           # tray back to dome front
SHELL = 2.0                 # dome shell thickness
TRAY_FLOOR = 3.0            # tray back thickness (index grooves take 1 mm of it)
TRAY_WALL = 2.0             # tray side wall thickness
BEVEL = 10.0                # 45 degree front bevel (prints face-down without supports)
EDGE_ROUND = 3.0            # soft round on the two bevel edges
WAND_X = -16.0              # wand sits this far left of centre (front view)
WAND_Z = 19.0               # wand axis height above the tray back; also the tray/dome seam
LIP_H = 3.0                 # dome lip that drops into the tray
LIP_T = 1.8
LIP_CLEAR = 0.15

# Gears (1:1 spur)
GEAR_MODULE = 1.0
GEAR_TEETH = 20
GEAR_FACE = 6.0
GEAR_ADDENDUM = 0.85        # x module; slightly short teeth print stronger tips
GEAR_BACKLASH = 0.2
GEAR_Y = -26.5              # centre of the gear pair along the wand (+y is up in Fusion, so the gears sit low).
                            # Far enough from the wall that the bottom bearing stays inside it (self-check: wand ports)
HUB_R = 7.5                 # wand gear journals, one each side
HUB_L = 3.5
JOURNAL_CLEAR = 0.25        # per side, journal in its bearing
GEAR_SIDE_GAP = 0.3         # gear to bearing face
BEARING_WALL = 2.5
PINION_FIT = 0.1            # added to the D bore (diameter and flats)

# 28BYJ-48 (datasheet values)
MOTOR_D = 28.0
MOTOR_LEN = 19.0
MOTOR_SHAFT_OFFSET = 8.0    # shaft is off the body centre by this much
MOTOR_SHAFT_D = 5.0
MOTOR_SHAFT_FLATS = 3.0     # distance across the two flats
MOTOR_SHAFT_LEN = 9.0       # MEASURE: motor face to shaft tip (listings say 8 to 10)
MOTOR_FLAT_LEN = 6.0        # MEASURE: length of the flats at the tip
MOTOR_BOSS_D = 9.0
MOTOR_BOSS_H = 1.5
MOTOR_COVER_W = 16.0        # MEASURE: blue wire cover, width
MOTOR_COVER_R = 17.0        # MEASURE: can centre to the outside of the blue cover
MOTOR_COVER_LEN = 17.0      # MEASURE: blue cover, length along the can
MOTOR_CLEAR = 0.15
# Snip the two mounting ears off the motor; they would hit the floor and the dome.
# The motor is clamped between the tray cradle and the dome cap, keyed by its blue cover.

# Green ULN2003 board
BOARD_W = 35.0              # MEASURE (x)
BOARD_H = 32.0              # MEASURE (y)
BOARD_HOLE_DX = 30.0        # MEASURE: hole spacing, centre to centre, along the 35 mm side
BOARD_HOLE_DY = 27.0        # MEASURE: hole spacing along the 32 mm side
BOARD_HOLE_D = 3.0          # MEASURE: an M3 needs about 3.2
BOARD_COMP_H = 9.0          # MEASURE: tallest part on the board (header pins / plug)
BOARD_STANDOFF = 7.0        # floor to the underside of the board
BOARD_CENTRE = (9.0, 17.0)  # just clear of the motor's back stop

# ESP32-C3 SuperMini
C3_W = 18.0
C3_H = 22.5
C3_T = 4.5                  # board plus its USB-C receptacle
C3_CENTRE = (-27.0, -2.0)   # under the wand; the wand runs 10 mm above it
C3_FRAME_H = 3.0

# 12 mm tactile switch with round cap
SW_BODY = 12.0
SW_TOTAL_H = 11.0           # MEASURE: bottom of switch body to top of fitted cap
SW_CAP_D = 12.0             # MEASURE: cap diameter
SW_CAP_PROUD = 1.0          # how far the cap stands proud of the dome
SW_POS = (14.0, 22.0)
SW_CLEAR = 0.3               # square socket round the switch body (0.2 was too tight on the first print)
SW_PLUG_T = 3.0             # printed plug that backs the switch so it can't be pushed in

# Dome screws: M3 x 20 from the back of the tray into inserts in the dome
DOME_SCREWS = [(34.0, 6.0), (-31.0, 15.0), (21.0, -29.0)]

# Wall mount: one 90 mm drum, Command strips on the back, M3 from the back into the tray
STRIP_T = 2.0               # MEASURE: Command strip pair thickness when pressed
STRIP_W = 19.0              # MEASURE: Medium picture-hanging strip
STRIP_L = 70.0              # MEASURE
STRIP_RECESS = 1.0          # strips sit this deep in the back
STRIP_RIB_W = 0.5           # break-away support ribs in the strip pockets (one line wide)
STRIP_RIB_PITCH = 6.0       # rib spacing, so the pocket ceilings are short bridges
STRIP_Y = 13.0              # strip centre lines, above and below the middle
MOUNT_WALL = 2.4
MOUNT_BASE = 3.0
MOUNT_FLANGE_R = 39.5       # inner edge of the top flange that carries the index ridges
MOUNT_POST_R = 6.0          # posts for the two clamp screws
MOUNT_SCREWS = [(11.0, 9.0), (-11.0, -9.0)]   # clamp screw positions, puck frame: open floor either
                            # side of the centre (under the board, and left of the motor).
                            # Opposite each other, so the strips can run either side of the line.
MOUNT_TWIST = 30.0          # MEASURE: wand angle. The puck is turned this far relative to the mount,
                            # so the mount (strips, USB) shows turned in Fusion. Change it and
                            # reprint the mount; the tray stays the same.
MOUNT_WEB = 3.0             # screw head bears on this, under the tray
RIDGES = 72                 # 5 degree steps
RIDGE_R = (41.0, 44.0)
RIDGE_DEG = 1.8             # ridge width in degrees
RIDGE_H = 0.8
WIRE_HOLE = (-30.0, -18.5)  # pigtail wires come up through the tray floor here, near the socket
WIRE_HOLE_D = 7.0

# USB-C pigtail socket, pinched between the mount and the tray back
USB_W = 15.8                # listing: 15.8 x 9.3 x 11 mm black square block, wires out the back
USB_T = 9.3                 # thickness (pinched between the mount and the tray)
USB_DEPTH = 11.0            # length, front face to where the wires come out
USB_PINCH = 0.2             # pocket is this much shallower than the socket
USB_FACE_T = 1.6            # wall in front of the socket; the plug reaches through a window
USB_WIN_W = 13.5            # window for a USB-C plug's overmould
USB_WIN_H = 7.5
USB_X = 0.0                 # centred
USB_SIDE = -1               # -1 puts it on the -y edge: the bottom, with Fusion's default Y-up view


# ---------------------------------------------------------------------------
# Derived positions
# ---------------------------------------------------------------------------

R = PUCK_D / 2.0
PINION_X = WAND_X + GEAR_MODULE * GEAR_TEETH
MOTOR_X = PINION_X + MOTOR_SHAFT_OFFSET          # motor body centre (shaft is on the wand side)
MOTOR_FACE_Y = GEAR_Y + MOTOR_SHAFT_LEN - MOTOR_FLAT_LEN / 2   # pinion sits on the flats
MOTOR_BACK_Y = MOTOR_FACE_Y + MOTOR_LEN
GEAR_ROOT_R = GEAR_MODULE * GEAR_TEETH / 2 - 1.25 * GEAR_MODULE
GEAR_TIP_R = GEAR_MODULE * GEAR_TEETH / 2 + GEAR_ADDENDUM * GEAR_MODULE
HUB_CONE = GEAR_ROOT_R - HUB_R                    # 45 degree step from journal to gear
TOOTH_CHAMFER = GEAR_TIP_R - GEAR_ROOT_R          # 45 degree chamfer on the wand gear's tooth ends
WAND_PORT_R = WAND_AC / 2 + WAND_PORT_CLEAR
BEARING_R = HUB_R + JOURNAL_CLEAR
BEARING_HALF_W = BEARING_R + BEARING_WALL
MOUNT_H = WAND_WALL_GAP - WAND_Z - (STRIP_T - STRIP_RECESS)
BOARD_Z = TRAY_FLOOR + BOARD_STANDOFF


def wand_gear_stations():
    """y stations of the wand gear, from the motor-far end: journal end, journal/cone,
    cone/teeth, full face start, full face end, teeth/cone, cone/journal, journal end.
    The full face (GEAR_FACE) meshes with the pinion; the chamfered ends let it print on a hub."""
    g0, g1 = GEAR_Y - GEAR_FACE / 2, GEAR_Y + GEAR_FACE / 2
    c0, c1 = g0 - TOOTH_CHAMFER, g1 + TOOTH_CHAMFER
    return (c0 - HUB_CONE - HUB_L, c0 - HUB_CONE, c0, g0, g1, c1, c1 + HUB_CONE, c1 + HUB_CONE + HUB_L)


def bearing_spans():
    """y ranges of the two bearings (journal length, less a gap at the gear side)."""
    s = wand_gear_stations()
    return [(s[0] - 0.5, s[1] - GEAR_SIDE_GAP), (s[6] + GEAR_SIDE_GAP, s[7])]


def bearing_blocks():
    """y ranges of the bearing blocks. The one by the wall runs into it, so the wand
    port goes through solid material and that hub's end has a thrust face."""
    (a0, a1), (b0, b1) = bearing_spans()
    return [(-R - 1, a1), (b0, b1)]


def board_holes():
    bx, by = BOARD_CENTRE
    return {(sx, sy): (bx + sx * BOARD_HOLE_DX / 2, by + sy * BOARD_HOLE_DY / 2)
            for sx in (-1, 1) for sy in (-1, 1)}


def centre_boss_top():
    return INSERT_DEPTH + MIN_WALL


def dome_outer_z(r):
    """Height of the dome's outer surface at radius r (ignores the small rounds)."""
    rb = R - BEVEL
    return PUCK_DEPTH if r <= rb else PUCK_DEPTH - (r - rb)


def fasteners():
    """Every screw and the insert it goes into. z values: head = underside of the head,
    tip = end of the shaft, entry = the insert's top face; dir = +1 if the shaft runs up."""
    out = []
    for x, y in DOME_SCREWS:
        head = M3_HEAD_H + M3_CB_SINK
        out.append(dict(name='dome screw at (%g, %g)' % (x, y), x=x, y=y, length=20, dir=1, head=head,
                        tip=head + 20, entry=WAND_Z, part='Dome'))
    for x, y in MOUNT_SCREWS:
        out.append(dict(name='mount screw at (%g, %g)' % (x, y), x=x, y=y, length=8, dir=1, head=-MOUNT_WEB,
                        tip=-MOUNT_WEB + 8, entry=0.0, part='Tray'))
    for hx, hy in board_screw_holes()[0]:
        head = BOARD_Z + 1.6
        out.append(dict(name='board screw at (%g, %g)' % (hx, hy), x=hx, y=hy, length=6, dir=-1, head=head,
                        tip=head - 6, entry=BOARD_Z, part='Tray'))
    return out


def board_screw_holes():
    """Two diagonal corners get M3 screws into inserts, the other two locate on pins."""
    h = board_holes()
    return [h[(1, -1)], h[(-1, 1)]], [h[(-1, -1)], h[(1, 1)]]


# ---------------------------------------------------------------------------
# Pure geometry helpers (no CAD calls)
# ---------------------------------------------------------------------------

def gear_outline(module, teeth, addendum=GEAR_ADDENDUM, backlash=GEAR_BACKLASH, flank_pts=7, rot=0.0):
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
        a = 2 * math.pi * k / teeth + rot
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


def d_bore(d, flats, n=24):
    """Round bore with two flats, as a polygon (flats at x = +-flats/2)."""
    r = d / 2.0
    f = flats / 2.0
    a0 = math.acos(f / r)                      # angle where the flat meets the circle
    pts = []
    for side in (1, -1):                       # top arc then bottom arc
        start, end = (a0, math.pi - a0) if side == 1 else (math.pi + a0, 2 * math.pi - a0)
        for i in range(n + 1):
            a = start + (end - start) * i / n
            pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def circle_pts(r, n=48, cx=0.0, cy=0.0):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


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


def close_on_axis(segs, z_seam):
    """Close a dome half-profile (from the axis at the front round to the seam) back to the axis."""
    start = segs[0][1]
    end = segs[-1][-1]
    return segs + [('L', end, (0.0, z_seam)), ('L', (0.0, z_seam), start)]


def dome_profiles():
    """(outer, inner) closed half-profiles of the dome in (radius, z), as segment lists."""
    zf = PUCK_DEPTH
    rb = R - BEVEL                      # where the flat front ends
    outer_pts = [(0.0, zf), (rb, zf), (R, zf - BEVEL), (R, WAND_Z)]
    off = SHELL * math.sqrt(2)          # 45 degree line moved in by SHELL
    zi = zf - SHELL
    ri = R - SHELL
    r_flat = rb + SHELL - off           # inner flat meets inner bevel
    z_side = (zf - off) - (ri - rb)     # inner bevel meets inner wall
    inner_pts = [(0.0, zi), (r_flat, zi), (ri, z_side), (ri, WAND_Z)]
    outer = rounded_polyline(outer_pts, [0, EDGE_ROUND, EDGE_ROUND, 0])
    inner = rounded_polyline(inner_pts, [0, max(0.5, EDGE_ROUND - SHELL), max(0.5, EDGE_ROUND - SHELL), 0])
    return close_on_axis(outer, WAND_Z), close_on_axis(inner, WAND_Z)


def poly_segs(pts):
    return [('L', pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]


def wedge(r0, r1, ang_deg, width_deg):
    a0, a1 = math.radians(ang_deg - width_deg / 2), math.radians(ang_deg + width_deg / 2)
    return [(r0 * math.cos(a0), r0 * math.sin(a0)), (r1 * math.cos(a0), r1 * math.sin(a0)),
            (r1 * math.cos(a1), r1 * math.sin(a1)), (r0 * math.cos(a1), r0 * math.sin(a1))]


def ridge_wedges(grow=0.0):
    """The 72 index ridges (grow > 0 gives the matching grooves)."""
    r0, r1 = RIDGE_R[0] - grow, RIDGE_R[1] + grow
    w = RIDGE_DEG + math.degrees(2 * grow / RIDGE_R[0])
    return [wedge(r0, r1, 360.0 * i / RIDGES, w) for i in range(RIDGES)]


# ---------------------------------------------------------------------------
# Parts. Each takes a Builder for its own component.
#
# Builder interface (all world coordinates, mm). op is 'new', 'join', 'cut'
# or 'int'; for anything but 'new', target is the body to change.
#   cyl_z(x, y, z0, h, r)             cylinder along z
#   cyl_y(x, z, y_mid, length, r)     cylinder along y, centred on y_mid
#   box(x0, x1, y0, y1, z0, z1)
#   prism_z(polys, z0, h)             polygons in (x, y), extruded along z
#   prism_y(polys, y_mid, length)     polygons in (x, z), extruded along y, centred
#   revolve_z(segs)                   closed (r, z) profile round the z axis
#   revolve_y(cx, cz, segs)           closed (r, y) profile round a y axis at (cx, cz)
#   combine(target, tools, op, keep=False)
#   pieces(body)                      the body plus any bits a cut split off it
# ---------------------------------------------------------------------------

def screw_pillar(b, body, x, y):
    """Tray pillar for a dome screw: M3 clearance, head counterbored into the back."""
    b.cyl_z(x, y, 0, WAND_Z, INSERT_BOSS_D / 2, 'join', body)


def build_tray(b):
    fl = TRAY_FLOOR
    env = b.cyl_z(0, 0, 0, WAND_Z, R, 'new', name='tray envelope')
    body = b.cyl_z(0, 0, 0, WAND_Z, R, 'new', name='Tray')
    b.cyl_z(0, 0, fl, WAND_Z, R - TRAY_WALL, 'cut', body)
    feats = []

    # wand gear bearings (bottom halves)
    for y0, y1 in bearing_blocks():
        f = b.box(WAND_X - BEARING_HALF_W, WAND_X + BEARING_HALF_W, y0, y1, fl - 0.5, WAND_Z, 'new')
        feats.append(f)

    # motor cradle (bottom half)
    feats.append(motor_block(b, fl - 0.5, WAND_Z))

    # board standoffs: two with inserts, two with locating pins
    screws, pins = board_screw_holes()
    for hx, hy in screws:
        feats.append(b.cyl_z(hx, hy, fl - 0.5, BOARD_STANDOFF + 0.5, INSERT_BOSS_D / 2, 'new'))
    for hx, hy in pins:
        f = b.cyl_z(hx, hy, fl - 0.5, BOARD_STANDOFF + 0.5, 3.0, 'new')
        b.cyl_z(hx, hy, BOARD_Z, 2.0, BOARD_HOLE_D / 2 - 0.2, 'join', f)
        feats.append(f)

    # pillars for the dome screws
    for x, y in DOME_SCREWS:
        feats.append(b.cyl_z(x, y, fl - 0.5, WAND_Z - fl + 0.5, INSERT_BOSS_D / 2, 'new'))

    # bosses for the two mount screw inserts, pressed in from the back
    for x, y in MOUNT_SCREWS:
        feats.append(b.cyl_z(x, y, fl - 0.5, centre_boss_top() - fl + 0.5, INSERT_BOSS_D / 2, 'new'))

    # C3 SuperMini frame (a dab of hot glue holds the board in it)
    cx, cy = C3_CENTRE
    w, h = C3_W / 2 + CLEAR, C3_H / 2 + CLEAR
    f = b.box(cx - w - 1.2, cx + w + 1.2, cy - h - 1.2, cy + h + 1.2, fl - 0.5, fl + C3_FRAME_H, 'new')
    b.box(cx - w, cx + w, cy - h, cy + h, fl, fl + C3_FRAME_H + 1, 'cut', f)
    # finger notches so the board can be lifted out
    b.box(cx - 4, cx + 4, cy - h - 2, cy + h + 2, fl + 1.0, fl + C3_FRAME_H + 1, 'cut', f)
    feats.append(f)

    for f in feats:
        b.combine(f, [env], 'int', keep=True)
    b.combine(body, feats, 'join')
    b.combine(body, [env], 'int')          # tidy anything that poked outside

    # ---- cuts ----
    # wand gear bearing seats and the wand ports (clearance only, no contact)
    for y0, y1 in bearing_spans():
        b.cyl_y(WAND_X, WAND_Z, (y0 + y1) / 2, y1 - y0 + 0.02, BEARING_R, 'cut', body)
    b.cyl_y(WAND_X, WAND_Z, 0, PUCK_D + 20, WAND_PORT_R, 'cut', body)
    # motor
    motor_cuts(b, body)
    # board: insert pockets
    for hx, hy in screws:
        b.cyl_z(hx, hy, BOARD_Z - INSERT_DEPTH, INSERT_DEPTH + 1, INSERT_D / 2, 'cut', body)
    # dome screws: clearance and a counterbore from the back
    for x, y in DOME_SCREWS:
        b.cyl_z(x, y, -1, WAND_Z + 2, M3_CLEAR / 2, 'cut', body)
        b.cyl_z(x, y, -1, 1 + M3_HEAD_H + M3_CB_SINK, M3_CB_D / 2, 'cut', body)
    # mount screw inserts, from the back
    for x, y in MOUNT_SCREWS:
        b.cyl_z(x, y, -1, INSERT_DEPTH + 1, INSERT_D / 2, 'cut', body)
    # wires from the USB socket in the mount
    b.cyl_z(WIRE_HOLE[0], WIRE_HOLE[1], -1, fl + 2, WIRE_HOLE_D / 2, 'cut', body)
    # index grooves on the back (the mount's ridges drop into them)
    b.prism_z(ridge_wedges(0.25), -1, RIDGE_H + 0.2 + 1, 'cut', body)
    return body


def motor_block(b, z0, z1):
    """Block round the motor can; the tray takes the bottom half, the dome the top."""
    x0 = MOTOR_X - MOTOR_D / 2 - 3.0
    x1 = MOTOR_X + MOTOR_COVER_R + 1.6
    f = b.box(x0, x1, MOTOR_FACE_Y + 0.5, MOTOR_BACK_Y + 2.0, z0, z1, 'new')
    # front stop on the side away from the shaft
    b.box(MOTOR_X + 4.0, MOTOR_X + MOTOR_D / 2 + 1.0, MOTOR_FACE_Y - 1.5, MOTOR_FACE_Y + 0.6, z0, z1, 'join', f)
    return f


def motor_cuts(b, body):
    yc = (MOTOR_FACE_Y + MOTOR_BACK_Y) / 2
    # the can (the block's back end stays as an end stop)
    b.cyl_y(MOTOR_X, WAND_Z, yc, MOTOR_LEN + 2 * 0.2, MOTOR_D / 2 + MOTOR_CLEAR, 'cut', body)
    # front stop must clear the can face: it only bears on the rim
    b.cyl_y(MOTOR_X, WAND_Z, MOTOR_FACE_Y - 1, 2.2, MOTOR_D / 2 - 2.0, 'cut', body)
    # blue wire cover: keys the motor so it can't turn; wires leave through the side
    hw = MOTOR_COVER_W / 2 + 0.3
    b.box(MOTOR_X + MOTOR_D / 2 - 3, MOTOR_X + MOTOR_COVER_R + 5, MOTOR_FACE_Y + 0.5 - 0.01, MOTOR_BACK_Y + 0.2,
          WAND_Z - hw, WAND_Z + hw, 'cut', body)


def build_dome(b):
    outer_segs, inner_segs = dome_profiles()
    outer = b.revolve_z(outer_segs, name='Dome')
    inner = b.revolve_z(inner_segs, name='dome void')
    top = PUCK_DEPTH + 1

    feats = []
    # screw bosses with inserts at the seam end
    for x, y in DOME_SCREWS:
        feats.append(b.cyl_z(x, y, WAND_Z, top - WAND_Z, INSERT_BOSS_D / 2, 'new'))
    # wand gear bearing caps
    for y0, y1 in bearing_blocks():
        f = b.box(WAND_X - BEARING_HALF_W, WAND_X + BEARING_HALF_W, y0, y1, WAND_Z, top, 'new')
        feats.append(f)
    # motor cap
    feats.append(motor_block(b, WAND_Z, top))
    # button socket
    sx, sy = SW_POS
    sw_bottom = PUCK_DEPTH + SW_CAP_PROUD - SW_TOTAL_H
    sock_bottom = sw_bottom - SW_PLUG_T - 0.5
    o = SW_BODY / 2 + SW_CLEAR + 1.6
    feats.append(b.box(sx - o, sx + o, sy - o, sy + o, sock_bottom, top, 'new'))

    for f in feats:
        b.combine(f, [outer], 'int', keep=True)
    b.combine(outer, [inner], 'cut')

    # lip that drops into the tray, with a 45 degree shoulder so it prints face-down
    r_out = R - TRAY_WALL - LIP_CLEAR
    r_in = r_out - LIP_T
    r_sh = R - SHELL + 0.5
    lip = b.revolve_z(poly_segs([(r_in, WAND_Z - LIP_H), (r_out, WAND_Z - LIP_H), (r_out, WAND_Z),
                                 (r_sh, WAND_Z), (r_sh, WAND_Z + 2 + (r_sh - r_in)),
                                 (r_in, WAND_Z + 2)]), name='lip')
    # no lip where the wand passes
    for s in (-1, 1):
        b.box(WAND_X - GEAR_TIP_R - 2, WAND_X + GEAR_TIP_R + 2, s * 25, s * (R + 5),
              WAND_Z - LIP_H - 1, WAND_Z + 10, 'cut', lip)
    # those cuts split the ring in two; Fusion makes each piece its own body
    b.combine(outer, feats + b.pieces(lip), 'join')

    # ---- cuts ----
    sw = b.box(sx - SW_BODY / 2 - SW_CLEAR, sx + SW_BODY / 2 + SW_CLEAR, sy - SW_BODY / 2 - SW_CLEAR, sy + SW_BODY / 2 + SW_CLEAR,
               sock_bottom - 1, PUCK_DEPTH - SHELL, 'new')
    b.combine(outer, [sw], 'cut')
    b.cyl_z(sx, sy, sw_bottom, 30, SW_CAP_D / 2 + 0.3, 'cut', outer)
    for x, y in DOME_SCREWS:
        b.cyl_z(x, y, WAND_Z - 0.01, INSERT_DEPTH, INSERT_D / 2, 'cut', outer)
    for y0, y1 in bearing_spans():
        b.cyl_y(WAND_X, WAND_Z, (y0 + y1) / 2, y1 - y0 + 0.02, BEARING_R, 'cut', outer)
    b.cyl_y(WAND_X, WAND_Z, 0, PUCK_D + 20, WAND_PORT_R, 'cut', outer)
    motor_cuts(b, outer)
    return outer


def build_wand_gear(b):
    to3 = lambda p: (WAND_X + p[0], WAND_Z + p[1])
    a0, j0, c0, g0, g1, c1, j1, a1 = wand_gear_stations()
    gear = b.prism_y([[to3(p) for p in gear_outline(GEAR_MODULE, GEAR_TEETH)]], GEAR_Y, c1 - c0, name='Wand gear')
    # 45 degree chamfers on the tooth ends, so it prints on a hub with no flat overhangs
    tip = GEAR_TIP_R + 0.05
    env = b.revolve_y(WAND_X, WAND_Z, poly_segs([
        (3.0, c0 - 0.01), (GEAR_ROOT_R - 0.01, c0 - 0.01), (tip, g0 - 0.06), (tip, g1 + 0.06),
        (GEAR_ROOT_R - 0.01, c1 + 0.01), (3.0, c1 + 0.01)]))
    b.combine(gear, [env], 'int')
    hub = b.revolve_y(WAND_X, WAND_Z, poly_segs([
        (3.0, a0), (HUB_R, a0), (HUB_R, j0), (GEAR_ROOT_R, c0),
        (GEAR_ROOT_R, c1), (HUB_R, j1), (HUB_R, a1), (3.0, a1)]))
    b.combine(gear, [hub], 'join')
    b.prism_y([[to3(p) for p in hexagon(WAND_AF + WAND_FIT, 30)]], GEAR_Y, a1 - a0 + 2, 'cut', gear)
    # 45 degree lead-ins on both ends of the hex, so the rod's end and corners get caught
    rc = (WAND_AF + WAND_FIT) / math.sqrt(3)
    for end, d in ((a0, 1), (a1, -1)):
        cone = b.revolve_y(WAND_X, WAND_Z, poly_segs([
            (0.5, end - d), (rc + WAND_LEAD + 1, end - d), (rc - 0.2, end + d * (WAND_LEAD + 0.2)),
            (0.5, end + d * (WAND_LEAD + 0.2))]))
        b.combine(gear, [cone], 'cut')
    return gear


def build_pinion(b):
    to3 = lambda p: (PINION_X + p[0], WAND_Z + p[1])
    half_tooth = math.pi / GEAR_TEETH        # shown in mesh with the wand gear
    gear = b.prism_y([[to3(p) for p in gear_outline(GEAR_MODULE, GEAR_TEETH, rot=half_tooth)]], GEAR_Y, GEAR_FACE,
                     name='Motor pinion')
    # flats face the wand gear so the print's layer lines don't matter
    bore = d_bore(MOTOR_SHAFT_D + PINION_FIT, MOTOR_SHAFT_FLATS + PINION_FIT)
    b.prism_y([[to3(p) for p in bore]], GEAR_Y, GEAR_FACE + 2, 'cut', gear)
    return gear


def build_switch_plug(b):
    """Square plug pressed into the back of the switch socket. Two notches let the legs out."""
    sx, sy = SW_POS
    top = PUCK_DEPTH + SW_CAP_PROUD - SW_TOTAL_H
    h = SW_BODY / 2 + SW_CLEAR      # same as the socket: a press fit once printed
    body = b.box(sx - h, sx + h, sy - h, sy + h, top - SW_PLUG_T, top, 'new', name='Switch plug')
    for side in (-1, 1):
        x0 = sx + side * h
        b.box(min(x0, x0 - side * 1.6), max(x0, x0 - side * 1.6), sy - 3.5, sy + 3.5, top - SW_PLUG_T - 1, top + 1, 'cut', body)
    return body


def usb_face_y():
    """Front face of the socket. The mount stays round outside; the wall in front of the
    socket is at least USB_FACE_T where the plug window meets the curve."""
    return math.sqrt(R * R - (USB_WIN_W / 2) ** 2) - USB_FACE_T


def usb_corner_wall():
    """Thinnest bit of wall in front of the socket: at the pocket's corners."""
    return math.sqrt(R * R - (USB_W / 2 + CLEAR) ** 2) - usb_face_y()


def build_mount(b):
    """One drum, the same 90 mm as the tray. Printed base-down: the Command strip
    pockets are on the bed, the index ridges on top."""
    H = MOUNT_H
    ri = R - MOUNT_WALL
    body = b.revolve_z(poly_segs([(ri, -H), (R, -H), (R, 0), (MOUNT_FLANGE_R, 0),
                                  (MOUNT_FLANGE_R, -1.5), (ri, -1.5 - (ri - MOUNT_FLANGE_R))]), name='Mount')
    b.cyl_z(0, 0, -H, MOUNT_BASE, ri + 0.2, 'join', body)
    posts = mount_posts()
    for px, py in posts:
        b.cyl_z(px, py, -H, H, MOUNT_POST_R, 'join', body)
    b.prism_z(ridge_wedges(), -0.01, RIDGE_H + 0.01, 'join', body)

    # USB-C socket cradle at the bottom: drops in from the top, the tray back pinches it
    # The socket is a plain moulded block with no flange, so it's captive: a front wall
    # with a window for the plug, a back stop, and the tray back pressing down on it.
    s = USB_SIDE
    uy = usb_face_y()
    hw = USB_W / 2 + CLEAR
    back = uy - USB_DEPTH - 0.2
    zt = -(USB_T - USB_PINCH)
    b.box(USB_X - hw - 2, USB_X + hw + 2, s * (back - 2), s * (ri + 1), -H + 1, 0, 'join', body)
    b.box(USB_X - hw, USB_X + hw, s * back, s * uy, zt, 1, 'cut', body)
    # window for the plug's overmould
    b.box(USB_X - USB_WIN_W / 2, USB_X + USB_WIN_W / 2, s * (uy - 0.5), s * (R + 1),
          zt / 2 - USB_WIN_H / 2, zt / 2 + USB_WIN_H / 2, 'cut', body)
    # slot in the back stop for the wires
    b.box(USB_X - 3, USB_X + 3, s * (back - 3), s * (back + 0.1), zt / 2 - 3, 1, 'cut', body)

    # clamp screws: M3 x 8 from the back, heads on the post webs under the tray
    for px, py in posts:
        b.cyl_z(px, py, -H - 1, H + 1 - MOUNT_WEB, M3_CB_D / 2, 'cut', body)
        b.cyl_z(px, py, -H - 1, H + 2, M3_CLEAR / 2, 'cut', body)
    # Command strip pockets, either side of the line through the two screw holes
    phi = math.atan2(posts[0][1], posts[0][0])
    u = (math.cos(phi), math.sin(phi))           # along the strips
    v = (-u[1], u[0])                            # across them
    def rect(a0, a1, b0, b1):
        return [(u[0] * a + v[0] * c, u[1] * a + v[1] * c) for a, c in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
    a0, a1 = -STRIP_L / 2 - 0.5, STRIP_L / 2 + 0.5
    for s in (-1, 1):
        c0, c1 = s * STRIP_Y - STRIP_W / 2 - 0.5, s * STRIP_Y + STRIP_W / 2 + 0.5
        b.prism_z([rect(a0, a1, c0, c1)], -H - 1, STRIP_RECESS + 1, 'cut', body)
        # our own supports: thin ribs under the pocket ceiling, touching only the ceiling,
        # so the bridges are short and the ribs snap out with pliers
        n = int(math.ceil((a1 - a0) / STRIP_RIB_PITCH))
        ribs = []
        for i in range(1, n):
            a = a0 + (a1 - a0) * i / n
            ribs.append(rect(a - STRIP_RIB_W / 2, a + STRIP_RIB_W / 2, c0 + 0.4, c1 - 0.4))
        b.prism_z(ribs, -H, STRIP_RECESS + 0.01, 'join', body)
    return body


def rotate(p, deg):
    a = math.radians(deg)
    return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a))


def mount_posts():
    """The two clamp screws, in the mount's own frame (the mount is turned MOUNT_TWIST
    relative to the puck, so its strips and USB socket stay square to the wall)."""
    return [rotate(p, -MOUNT_TWIST) for p in MOUNT_SCREWS]


def build_reference(b):
    """Bought parts and hardware, for checking fit only."""
    out = {}
    out['wand'] = b.prism_y([[(WAND_X + px, WAND_Z + py) for px, py in hexagon(WAND_AF, 30)]], 0, 160, name='wand')
    yc = (MOTOR_FACE_Y + MOTOR_BACK_Y) / 2
    m = b.cyl_y(MOTOR_X, WAND_Z, yc, MOTOR_LEN, MOTOR_D / 2, 'new', name='28BYJ-48')
    b.cyl_y(PINION_X, WAND_Z, MOTOR_FACE_Y - MOTOR_BOSS_H / 2, MOTOR_BOSS_H + 0.02, MOTOR_BOSS_D / 2, 'join', m)
    b.cyl_y(PINION_X, WAND_Z, MOTOR_FACE_Y - (MOTOR_SHAFT_LEN - MOTOR_FLAT_LEN) / 2,
            MOTOR_SHAFT_LEN - MOTOR_FLAT_LEN + 0.02, MOTOR_SHAFT_D / 2, 'join', m)
    b.prism_y([[(PINION_X + px, WAND_Z + py) for px, py in d_bore(MOTOR_SHAFT_D, MOTOR_SHAFT_FLATS)]],
              MOTOR_FACE_Y - MOTOR_SHAFT_LEN + MOTOR_FLAT_LEN / 2, MOTOR_FLAT_LEN, 'join', m)
    b.box(MOTOR_X + MOTOR_D / 2 - 2, MOTOR_X + MOTOR_COVER_R, MOTOR_BACK_Y - MOTOR_COVER_LEN, MOTOR_BACK_Y,
          WAND_Z - MOTOR_COVER_W / 2, WAND_Z + MOTOR_COVER_W / 2, 'join', m)
    out['motor'] = m
    bx, by = BOARD_CENTRE
    out['board'] = b.box(bx - BOARD_W / 2, bx + BOARD_W / 2, by - BOARD_H / 2, by + BOARD_H / 2, BOARD_Z, BOARD_Z + 1.6, 'new', name='ULN2003 board')
    for hx, hy in board_holes().values():
        b.cyl_z(hx, hy, BOARD_Z - 1, 3.6, BOARD_HOLE_D / 2, 'cut', out['board'])
    # the parts on top keep 5 mm in from the edges, clear of the mounting holes
    out['board parts'] = b.box(bx - BOARD_W / 2 + 5, bx + BOARD_W / 2 - 5, by - BOARD_H / 2 + 5, by + BOARD_H / 2 - 5,
                               BOARD_Z + 1.6, BOARD_Z + 1.6 + BOARD_COMP_H, 'new', name='board parts (envelope)')
    cx, cy = C3_CENTRE
    out['c3'] = b.box(cx - C3_W / 2, cx + C3_W / 2, cy - C3_H / 2, cy + C3_H / 2, TRAY_FLOOR, TRAY_FLOOR + C3_T, 'new', name='ESP32-C3 SuperMini')
    sx, sy = SW_POS
    swb = PUCK_DEPTH + SW_CAP_PROUD - SW_TOTAL_H
    s = b.box(sx - SW_BODY / 2, sx + SW_BODY / 2, sy - SW_BODY / 2, sy + SW_BODY / 2, swb, swb + 4, 'new', name='switch')
    b.cyl_z(sx, sy, swb + 4, SW_TOTAL_H - 4, SW_CAP_D / 2, 'join', s)
    out['switch'] = s
    uy = usb_face_y()
    ux0, ux1 = USB_X - USB_W / 2, USB_X + USB_W / 2
    uy0, uy1 = USB_SIDE * (uy - USB_DEPTH), USB_SIDE * uy
    out['usb'] = b.prism_z([[rotate(p, MOUNT_TWIST) for p in ((ux0, uy0), (ux1, uy0), (ux1, uy1), (ux0, uy1))]],
                           -USB_T, USB_T, 'new', name='USB-C socket')   # it lives in the (turned) mount
    # hardware: inserts and screws
    hw = []
    for f in fasteners():
        d = f['dir']
        lo, hi = sorted((f['entry'], f['entry'] + d * INSERT_L))
        i = b.cyl_z(f['x'], f['y'], lo, hi - lo, INSERT_D / 2 - 0.1, 'new', name='insert')
        b.cyl_z(f['x'], f['y'], lo - 1, hi - lo + 2, 1.55, 'cut', i)
        hw.append(i)
        head0, head1 = sorted((f['head'], f['head'] - d * M3_HEAD_H))
        s = b.cyl_z(f['x'], f['y'], head0, head1 - head0, M3_HEAD_D / 2, 'new', name='M3x%d' % f['length'])
        lo, hi = sorted((f['head'], f['tip']))
        b.cyl_z(f['x'], f['y'], lo, hi - lo, 1.45, 'join', s)
        hw.append(s)
    out['hardware'] = hw
    wall_z = -MOUNT_H - (STRIP_T - STRIP_RECESS)
    out['wall'] = b.box(-80, 80, -80, 80, wall_z - 3, wall_z, 'new', name='wall')
    return out


PARTS = [
    ('Tray (print back-down)', build_tray),
    ('Dome (print face-down)', build_dome),
    ('Wand gear (print on either hub)', build_wand_gear),
    ('Motor pinion (print flat)', build_pinion),
    ('Switch plug (print flat)', build_switch_plug),
    ('Mount (print back-down)', build_mount),
    ('Reference parts (do not print)', build_reference),
]
# parts built in their own frame and then turned about the puck's axis (degrees)
PART_TURN = {'Mount (print back-down)': MOUNT_TWIST}


def hardware_summary():
    return ('Mount to tray: 2 x M3 x 8 socket head from the back into inserts\n'
            'Dome to tray: 3 x M3 x 20 socket head from the back into inserts\n'
            'Board: 2 x M3 x 6 into inserts (the other two corners sit on pins)\n'
            'Heat-set inserts: 7 x M3 (%.1f mm pockets)\n'
            'Motor: snip the ears; the tray and dome clamp it, no ties\n'
            'Mount turned %g deg to the puck, height %.1f mm' % (INSERT_D, MOUNT_TWIST, MOUNT_H))


# ---------------------------------------------------------------------------
# Self-check. Runs after every build, in Fusion and in cad/check (pytest).
#
# The probe answers questions about the built model:
#   probe.inside(part, x, y, z)  -> True if the point is inside that printed part
#   probe.centre(part)           -> (x, y, z) centre of mass
#   probe.interference()         -> [(body name, body name, overlap mm^3), ...]
# ---------------------------------------------------------------------------

PRINTED = ['Tray', 'Dome', 'Wand gear', 'Motor pinion', 'Switch plug', 'Mount']
EXPECTED_CONTACT = {frozenset(('Mount', 'USB-C socket'))}   # the 0.2 mm pinch
INTERFERENCE_TOL = 0.1      # mm^3; touching faces can show a sliver


def wall_list():
    """(name, thickness) for every wall that the parameters decide."""
    hex_corner = (WAND_AF + WAND_FIT) / math.sqrt(3)
    dome_caps = [dome_outer_z(math.hypot(x, y) + INSERT_BOSS_D / 2) - (WAND_Z + INSERT_DEPTH) for x, y in DOME_SCREWS]
    return [
        ('insert boss round its pocket', (INSERT_BOSS_D - INSERT_D) / 2),
        ('screw pillar round its counterbore', (INSERT_BOSS_D - M3_CB_D) / 2),
        ('tray side wall', TRAY_WALL),
        ('dome shell', SHELL),
        ('dome lip', LIP_T),
        ('tray floor under the index grooves', TRAY_FLOOR - (RIDGE_H + 0.2)),
        ('tray boss over the mount insert', centre_boss_top() - INSERT_DEPTH),
        ('tray floor under the board inserts', BOARD_Z - INSERT_DEPTH),
        ('dome over its insert pockets', min(dome_caps)),
        ('wand gear hub round the hex', HUB_R - hex_corner),
        ('pinion round the D bore', GEAR_ROOT_R - (MOTOR_SHAFT_D + PINION_FIT) / 2),
        ('gear bearing wall', BEARING_WALL),
        ('mount side wall', MOUNT_WALL),
        ('mount wall in front of the USB socket', min(USB_FACE_T, usb_corner_wall())),
        ('switch socket wall', 1.6),
        ('wand gear hub round the hex lead-in', HUB_R - (WAND_AC / 2 + WAND_FIT + WAND_LEAD)),
        ('mount web under the clamp screw', MOUNT_WEB),
        ('mount back under the strip pockets', MOUNT_BASE - STRIP_RECESS),
        ('mount post round the screw bore', MOUNT_POST_R - M3_CB_D / 2),
    ]


def self_check(probe):
    """Returns [(group, ok, detail)]."""
    res = []

    # 1. interference
    try:
        hits = [(a, b, v) for a, b, v in probe.interference()
                if v > INTERFERENCE_TOL and frozenset((a, b)) not in EXPECTED_CONTACT
                and not (a.startswith(('M3', 'insert')) and b.startswith(('M3', 'insert')))]
        if hits:
            for a, b, v in hits:
                res.append(('Interference', False, '%s and %s overlap by %.2f mm3' % (a, b, v)))
        else:
            res.append(('Interference', True, 'no parts overlap (the USB pinch is expected)'))
    except Exception as e:                       # keep the build even if the API call fails
        res.append(('Interference', False, 'could not run: %s' % e))

    # 2. wall thickness
    thin = [(n, t) for n, t in wall_list() if t < MIN_WALL - 1e-6]
    for n, t in thin:
        res.append(('Wall thickness', False, '%s is %.2f mm (min %.1f)' % (n, t, MIN_WALL)))
    if not thin:
        n, t = min(wall_list(), key=lambda w: w[1])
        res.append(('Wall thickness', True, 'all %d walls >= %.1f mm (thinnest: %s, %.2f)' % (len(wall_list()), MIN_WALL, n, t)))

    # 3. gears
    want = GEAR_MODULE * (GEAR_TEETH + GEAR_TEETH) / 2
    g, p = probe.centre('Wand gear'), probe.centre('Motor pinion')
    cd = math.hypot(g[0] - p[0], g[2] - p[2])
    res.append(('Gear centre distance', abs(cd - want) < 0.05 and abs(g[1] - p[1]) < 0.05,
                '%.3f mm (should be %.3f), faces offset %.3f mm' % (cd, want, abs(g[1] - p[1]))))
    f0 = MOTOR_FACE_Y - MOTOR_SHAFT_LEN
    f1 = f0 + MOTOR_FLAT_LEN
    on = GEAR_Y - GEAR_FACE / 2 >= f0 - 1e-6 and GEAR_Y + GEAR_FACE / 2 <= f1 + 1e-6
    res.append(('Gear centre distance', on, 'pinion %s on the shaft flats' % ('sits' if on else 'does NOT sit')))

    # wand ports: a clean round hole, with case material all the way round it on the outside
    # (catches a bearing bore or hub breaking out through the curved wall)
    for s, where in ((-1, 'bottom'), (1, 'top')):
        rr = WAND_PORT_R + 1.0
        gaps = []
        for i in range(16):
            t = 2 * math.pi * i / 16
            x = WAND_X + rr * math.cos(t)
            z = WAND_Z + rr * math.sin(t)
            y = s * (math.sqrt(R * R - x * x) - 0.4)
            if abs(z - WAND_Z) < 0.05:
                continue                      # on the seam itself
            if not (probe.inside('Tray', x, y, z) or probe.inside('Dome', x, y, z)):
                gaps.append(round(math.degrees(t)))
        res.append(('Wand ports', not gaps, '%s port: %s' % (
            where, 'round, solid all the way round' if not gaps else 'wall missing round the hole at %s degrees' % gaps)))

    # 4. bolts line up with inserts
    for f in fasteners():
        problems = []
        d = f['dir']
        # thread in the insert, and the tip stops short of the pocket bottom
        ins = sorted((f['entry'], f['entry'] + d * INSERT_L))
        shaft = sorted((f['head'], f['tip']))
        engage = min(ins[1], shaft[1]) - max(ins[0], shaft[0])
        if engage < MIN_ENGAGE:
            problems.append('only %.1f mm in the insert' % engage)
        if (f['tip'] - f['entry']) * d > INSERT_DEPTH - 0.3:
            problems.append('tip hits the bottom of the pocket')
        # clear path for the shaft and head through every printed part
        pts = []
        n = max(2, int(abs(f['tip'] - f['head'])))
        for i in range(n + 1):
            z = f['head'] + d * (0.3 + (abs(f['tip'] - f['head']) - 0.6) * i / n)
            pts.append((f['x'], f['y'], z))
            for a in range(4):
                t = math.pi / 2 * a + math.pi / 4
                pts.append((f['x'] + 1.5 * math.cos(t), f['y'] + 1.5 * math.sin(t), z))
        zh = f['head'] - d * M3_HEAD_H / 2
        for a in range(4):
            t = math.pi / 2 * a
            pts.append((f['x'] + (M3_HEAD_D / 2 - 0.1) * math.cos(t), f['y'] + (M3_HEAD_D / 2 - 0.1) * math.sin(t), zh))
        blocked = sorted({part for part in PRINTED for pt in pts if probe.inside(part, *pt)})
        if blocked:
            problems.append('hole blocked by %s' % ', '.join(blocked))
        # plastic all round the insert
        zm = f['entry'] + d * INSERT_L / 2
        rr = INSERT_D / 2 + 1.0
        missing = sum(1 for a in range(6)
                      if not probe.inside(f['part'], f['x'] + rr * math.cos(a * math.pi / 3), f['y'] + rr * math.sin(a * math.pi / 3), zm))
        if missing:
            problems.append('insert boss missing on %d of 6 sides' % missing)
        res.append(('Bolts and inserts', not problems,
                    '%s (M3x%d): %s' % (f['name'], f['length'], '; '.join(problems) if problems else
                                        'clear hole, %.1f mm in the insert' % engage)))
    return res


def format_report(res):
    fails = [r for r in res if not r[1]]
    lines = ['Self-check: %s (%d checks, %d failed)' % ('PASS' if not fails else 'FAIL', len(res), len(fails)), '']
    for group, ok, detail in res:
        lines.append('%s  %s: %s' % ('PASS' if ok else 'FAIL', group, detail))
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Fusion backend
# ---------------------------------------------------------------------------

def cm(v):
    return v / 10.0


class FusionBuilder:
    def __init__(self, comp):
        self.c = comp
        self.OPS = {
            'new': adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            'join': adsk.fusion.FeatureOperations.JoinFeatureOperation,
            'cut': adsk.fusion.FeatureOperations.CutFeatureOperation,
            'int': adsk.fusion.FeatureOperations.IntersectFeatureOperation,
        }

    @staticmethod
    def V(v):
        return adsk.core.ValueInput.createByReal(cm(v))

    # planes / sketches -----------------------------------------------------
    def _offset_plane(self, base, along, value):
        if abs(value) < 1e-9:
            return base
        n = base.geometry.normal
        sign = float(getattr(n, along))
        inp = self.c.constructionPlanes.createInput()
        inp.setByOffset(base, self.V(value * sign))
        return self.c.constructionPlanes.add(inp)

    def sk_xy(self, z):
        return self.c.sketches.add(self._offset_plane(self.c.xYConstructionPlane, 'z', z))

    def sk_xz(self, y):
        return self.c.sketches.add(self._offset_plane(self.c.xZConstructionPlane, 'y', y))

    @staticmethod
    def P(sk, x, y, z):
        return sk.modelToSketchSpace(adsk.core.Point3D.create(cm(x), cm(y), cm(z)))

    def _poly(self, sk, pts3):
        lines = sk.sketchCurves.sketchLines
        pts = [self.P(sk, *p) for p in pts3]
        first = lines.addByTwoPoints(pts[0], pts[1])
        prev = first.endSketchPoint
        for p in pts[2:]:
            prev = lines.addByTwoPoints(prev, p).endSketchPoint
        lines.addByTwoPoints(prev, first.startSketchPoint)

    def _segs(self, sk, segs, to3):
        lines = sk.sketchCurves.sketchLines
        arcs = sk.sketchCurves.sketchArcs
        first = None
        prev = None
        for n, s in enumerate(segs):
            start = prev if prev is not None else self.P(sk, *to3(s[1]))
            end = first if (n == len(segs) - 1 and first is not None) else self.P(sk, *to3(s[-1]))
            if s[0] == 'L':
                ent = lines.addByTwoPoints(start, end)
            else:
                ent = arcs.addByThreePoints(start, self.P(sk, *to3(s[2])), end)
            if first is None:
                first = ent.startSketchPoint
            prev = ent.endSketchPoint

    @staticmethod
    def _all_profiles(sk):
        col = adsk.core.ObjectCollection.create()
        for i in range(sk.profiles.count):
            col.add(sk.profiles.item(i))
        return col

    @staticmethod
    def _largest_profile(sk):
        best, best_area = None, -1
        for i in range(sk.profiles.count):
            p = sk.profiles.item(i)
            a = float(p.areaProperties().area)
            if a > best_area:
                best, best_area = p, a
        return best

    # features ----------------------------------------------------------------
    def _finish(self, feature, op, target, name):
        if op == 'new':
            body = feature.bodies.item(0)
            if name:
                body.name = name
            return body
        return target

    def _extrude(self, profs, dist, op, target, name, symmetric=False):
        ex = self.c.features.extrudeFeatures
        inp = ex.createInput(profs, self.OPS[op])
        if symmetric:
            inp.setSymmetricExtent(self.V(dist), True)
        else:
            inp.setDistanceExtent(False, self.V(dist))
        if op != 'new':
            inp.participantBodies = [target]
        return self._finish(ex.add(inp), op, target, name)

    def cyl_z(self, x, y, z0, h, r, op='new', target=None, name=None):
        sk = self.sk_xy(z0)
        sk.sketchCurves.sketchCircles.addByCenterRadius(self.P(sk, x, y, z0), cm(r))
        return self._extrude(sk.profiles.item(0), h, op, target, name)

    def cyl_y(self, x, z, y_mid, length, r, op='new', target=None, name=None):
        sk = self.sk_xz(y_mid)
        sk.sketchCurves.sketchCircles.addByCenterRadius(self.P(sk, x, y_mid, z), cm(r))
        return self._extrude(sk.profiles.item(0), length, op, target, name, symmetric=True)

    def box(self, x0, x1, y0, y1, z0, z1, op='new', target=None, name=None):
        sk = self.sk_xy(z0)
        self._poly(sk, [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)])
        return self._extrude(sk.profiles.item(0), z1 - z0, op, target, name)

    def prism_z(self, polys, z0, h, op='new', target=None, name=None):
        sk = self.sk_xy(z0)
        sk.isComputeDeferred = True
        for poly in polys:
            self._poly(sk, [(px, py, z0) for px, py in poly])
        sk.isComputeDeferred = False
        return self._extrude(self._all_profiles(sk), h, op, target, name)

    def prism_y(self, polys, y_mid, length, op='new', target=None, name=None):
        sk = self.sk_xz(y_mid)
        sk.isComputeDeferred = True
        for poly in polys:
            self._poly(sk, [(px, y_mid, pz) for px, pz in poly])
        sk.isComputeDeferred = False
        profs = self._largest_profile(sk) if len(polys) == 1 else self._all_profiles(sk)
        return self._extrude(profs, length, op, target, name, symmetric=True)

    def revolve_z(self, segs, op='new', target=None, name=None):
        sk = self.sk_xz(0)
        self._segs(sk, segs, lambda p: (p[0], 0.0, p[1]))
        rv = self.c.features.revolveFeatures
        inp = rv.createInput(self._largest_profile(sk), self.c.zConstructionAxis, self.OPS[op])
        inp.setAngleExtent(False, adsk.core.ValueInput.createByString('360 deg'))
        if op != 'new':
            inp.participantBodies = [target]
        return self._finish(rv.add(inp), op, target, name)

    def revolve_y(self, cx, cz, segs, op='new', target=None, name=None):
        sk = self.sk_xy(cz)
        self._segs(sk, segs, lambda p: (cx + p[0], p[1], cz))
        ys = [s[1][1] for s in segs]
        axis = sk.sketchCurves.sketchLines.addByTwoPoints(self.P(sk, cx, min(ys) - 5, cz), self.P(sk, cx, max(ys) + 5, cz))
        axis.isConstruction = True
        rv = self.c.features.revolveFeatures
        inp = rv.createInput(self._largest_profile(sk), axis, self.OPS[op])
        inp.setAngleExtent(False, adsk.core.ValueInput.createByString('360 deg'))
        if op != 'new':
            inp.participantBodies = [target]
        return self._finish(rv.add(inp), op, target, name)

    def pieces(self, body):
        """A cut that splits a body leaves the extra pieces as new bodies named 'name (1)' and so on."""
        base = body.name
        out = []
        for j in range(self.c.bRepBodies.count):
            b = self.c.bRepBodies.item(j)
            if b.name == base or b.name.startswith(base + ' ('):
                out.append(b)
        return out

    def combine(self, target, tools, op, keep=False):
        cf = self.c.features.combineFeatures
        col = adsk.core.ObjectCollection.create()
        for t in tools:
            col.add(t)
        inp = cf.createInput(target, col)
        inp.operation = self.OPS[op]
        inp.isKeepToolBodies = keep
        cf.add(inp)
        return target


class FusionProbe:
    def __init__(self, design, printed, everything):
        self.design = design
        self.printed = printed
        self.everything = everything

    def inside(self, part, x, y, z):
        pc = self.printed[part].pointContainment(adsk.core.Point3D.create(cm(x), cm(y), cm(z)))
        return pc == adsk.fusion.PointContainment.PointInsidePointContainment

    def centre(self, part):
        p = self.printed[part].physicalProperties.centerOfMass
        return (p.x * 10, p.y * 10, p.z * 10)

    def interference(self):
        col = adsk.core.ObjectCollection.create()
        for b in self.everything:
            col.add(b)
        inp = self.design.createInterferenceInput(col)
        inp.areCoincidentFacesIncluded = False
        out = []
        for r in self.design.analyzeInterference(inp):
            out.append((r.entityOne.name, r.entityTwo.name, r.interferenceBody.volume * 1000.0))
        return out


def tidy(root):
    """Hide the helper planes, sketches and leftover tool bodies so only the parts show."""
    for i in range(root.occurrences.count):
        comp = root.occurrences.item(i).component
        for j in range(comp.constructionPlanes.count):
            comp.constructionPlanes.item(j).isLightBulbOn = False
        for j in range(comp.sketches.count):
            comp.sketches.item(j).isVisible = False
        for j in range(comp.bRepBodies.count):
            body = comp.bRepBodies.item(j)
            if body.name in ('tray envelope', 'dome void'):
                body.isLightBulbOn = False


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent
        printed = {}
        everything = []
        for name, fn in PARTS:
            place = adsk.core.Matrix3D.create()
            if name in PART_TURN:
                place.setToRotation(math.radians(PART_TURN[name]), adsk.core.Vector3D.create(0, 0, 1),
                                    adsk.core.Point3D.create(0, 0, 0))
            occ = root.occurrences.addNewComponent(place)
            occ.component.name = name
            out = fn(FusionBuilder(occ.component))
            if not isinstance(out, dict):
                # the assembly-context copy, so the checks see turned parts where they really are
                printed[name.split(' (')[0]] = out.createForAssemblyContext(occ)
            for j in range(occ.component.bRepBodies.count):
                body = occ.component.bRepBodies.item(j)
                if body.name not in ('tray envelope', 'dome void', 'wall'):
                    everything.append(body.createForAssemblyContext(occ))
        tidy(root)
        report = format_report(self_check(FusionProbe(design, printed, everything)))
        ui.messageBox('Twizzle built.\n\n' + report + '\n\n' + hardware_summary() +
                      '\n\nParts marked "do not print" are for checking fit only.')
    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
