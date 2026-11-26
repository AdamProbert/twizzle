"""
CadQuery backend for the Twizzle part code in cad/fusion/Twizzle/Twizzle.py.

build() runs every part function from the Fusion script against a CadQuery
Builder and returns the printed parts and the reference parts. CQProbe lets
the script's own self_check() run against that model.
"""

import importlib.util
import itertools
import math
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'fusion', 'Twizzle', 'Twizzle.py')


def load_twizzle():
    spec = importlib.util.spec_from_file_location('twizzle', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = load_twizzle()


class Body:
    def __init__(self, shape, name):
        self.shape = shape
        self.name = name


class CQBuilder:
    def __init__(self, part):
        self.part = part
        self.bodies = []

    def _apply(self, shape, op, target, name):
        if op == 'new':
            b = Body(shape, name or 'body')
            self.bodies.append(b)
            return b
        if op == 'join':
            target.shape = target.shape.fuse(shape).clean()
        elif op == 'cut':
            target.shape = target.shape.cut(shape).clean()
        elif op == 'int':
            target.shape = target.shape.intersect(shape).clean()
        return target

    def cyl_z(self, x, y, z0, h, r, op='new', target=None, name=None):
        if h < 0:
            z0, h = z0 + h, -h
        s = cq.Solid.makeCylinder(r, h, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))
        return self._apply(s, op, target, name)

    def cyl_y(self, x, z, y_mid, length, r, op='new', target=None, name=None):
        s = cq.Solid.makeCylinder(r, length, cq.Vector(x, y_mid - length / 2, z), cq.Vector(0, 1, 0))
        return self._apply(s, op, target, name)

    def box(self, x0, x1, y0, y1, z0, z1, op='new', target=None, name=None):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        s = cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))
        return self._apply(s, op, target, name)

    def prism_z(self, polys, z0, h, op='new', target=None, name=None):
        solids = [cq.Workplane('XY', origin=(0, 0, z0)).polyline(p).close().extrude(h).val() for p in polys]
        s = solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)
        return self._apply(s, op, target, name)

    def prism_y(self, polys, y_mid, length, op='new', target=None, name=None):
        solids = [cq.Workplane('XZ', origin=(0, y_mid, 0)).polyline(p).close().extrude(length / 2, both=True).val()
                  for p in polys]
        s = solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)
        return self._apply(s, op, target, name)

    @staticmethod
    def _wire(wp, segs):
        wp = wp.moveTo(*segs[0][1])
        for i, s in enumerate(segs):
            last = i == len(segs) - 1
            if s[0] == 'L':
                if last:
                    break
                wp = wp.lineTo(*s[2])
            else:
                wp = wp.threePointArc(s[2], s[3])
        return wp.close()

    def revolve_z(self, segs, op='new', target=None, name=None):
        wp = self._wire(cq.Workplane('XZ'), segs)
        s = wp.revolve(360, (0, 0, 0), (0, 1, 0)).val()
        return self._apply(s, op, target, name)

    def revolve_y(self, cx, cz, segs, op='new', target=None, name=None):
        wp = self._wire(cq.Workplane('XY', origin=(cx, 0, cz)), segs)
        s = wp.revolve(360, (0, 0, 0), (0, 1, 0)).val()
        return self._apply(s, op, target, name)

    def combine(self, target, tools, op, keep=False):
        for t in tools:
            self._apply(t.shape, op, target, None)
        if not keep:
            self.bodies = [b for b in self.bodies if b not in tools]
        return target


def build():
    """Returns ({printed part: shape}, {reference name: Body or [Body]})."""
    parts, ref = {}, {}
    for name, fn in T.PARTS:
        out = fn(CQBuilder(name))
        if isinstance(out, dict):
            ref = out
        else:
            parts[name.split(' (')[0]] = out.shape
    return parts, ref


def named_bodies(parts, ref, skip=('wall',)):
    """Every body as (name, shape), with the same names the Fusion bodies get."""
    out = [(k, s) for k, s in parts.items()]
    for k, v in ref.items():
        if k in skip:
            continue
        for b in (v if isinstance(v, list) else [v]):
            out.append((b.name, b.shape))
    return out


def interference(bodies):
    res = []
    for (a, sa), (b, sb) in itertools.combinations(bodies, 2):
        ba, bb = sa.BoundingBox(), sb.BoundingBox()
        if (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
                or ba.zmax < bb.zmin or bb.zmax < ba.zmin):
            continue
        common = sa.intersect(sb)
        v = common.Volume()
        if v > 1e-4:
            res.append((a, b, v))
    return res


PRINT_FLIP = {   # how each part sits on the bed: rotations to apply (axis, degrees)
    'Tray': (),
    'Dome': (('X', 180),),
    'Wand gear': (('X', 90),),
    'Motor pinion': (('X', 90),),
    'Switch plug': (),
    'Mount': (),
}


def oriented(name, shape):
    s = shape
    for axis, deg in PRINT_FLIP.get(name, ()):
        ax = {'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[axis]
        s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(*ax), deg)
    bb = s.BoundingBox()
    return s.translate(cq.Vector(0, 0, -bb.zmin))


def _down_faces(name, shape):
    for f in oriented(name, shape).Faces():
        c = f.Center()
        if c.z < 0.05:                     # on the bed
            continue
        try:
            n = f.normalAt(c)
        except Exception:
            continue
        yield f, n


def overhangs(name, shape, limit_deg=50.0, min_area=0.5):
    """Sloped down-facing faces steeper than limit_deg from vertical (flat ceilings are bridges)."""
    lim = math.cos(math.radians(90 - limit_deg))
    out = []
    for f, n in _down_faces(name, shape):
        if -0.999 < n.z < -lim and f.Area() >= min_area:
            bb = f.BoundingBox()
            out.append((round(f.Area(), 1), round(n.z, 2), (round(bb.xmin, 1), round(bb.ymin, 1), round(bb.zmin, 1))))
    return sorted(out, reverse=True)


def bridges(name, shape, min_area=0.5):
    """Flat ceilings, with the shorter side of each (the span a bridge has to cross)."""
    out = []
    for f, n in _down_faces(name, shape):
        if n.z <= -0.999 and f.Area() >= min_area:
            bb = f.BoundingBox()
            out.append((round(min(bb.xlen, bb.ylen), 1), round(f.Area(), 1), (round(bb.xmin, 1), round(bb.ymin, 1), round(bb.zmin, 1))))
    return sorted(out, reverse=True)


class CQProbe:
    def __init__(self, parts, ref):
        self.parts = parts
        self.bodies = named_bodies(parts, ref)

    def inside(self, part, x, y, z):
        return self.parts[part].isInside(cq.Vector(x, y, z), 1e-4)

    def centre(self, part):
        c = cq.Shape.centerOfMass(self.parts[part])
        return (c.x, c.y, c.z)

    def interference(self):
        return interference(self.bodies)
