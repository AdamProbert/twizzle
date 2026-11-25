"""
Builds the Twizzle parts from the Fusion script's own part code, in CadQuery,
and checks them: parts that overlap, printed parts that come out in more than
one piece, and downward-facing overhangs in each part's print orientation.
It also exports STLs and renders a few views.

    pip install cadquery          (vtk comes with it)
    python cad/check/check.py [out_dir]
"""

import importlib.util
import itertools
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('twizzle', os.path.join(HERE, '..', 'fusion', 'Twizzle', 'Twizzle.py'))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


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


PRINT_FLIP = {   # how each part sits on the bed: rotation to apply (axis, degrees)
    'Tray': None,
    'Dome': (('X', 180),),
    'Wand gear': (('X', 90),),
    'Motor pinion': (('X', 90),),
    'Switch plug': None,
    'Mount': None,
}


def build():
    parts = {}
    ref = {}
    for name, fn in T.PARTS:
        b = CQBuilder(name)
        out = fn(b)
        if name.startswith('Reference'):
            ref = out
        else:
            key = name.split(' (')[0]
            parts[key] = out.shape
    return parts, ref


def vol(s):
    try:
        return s.Volume()
    except Exception:
        return -1


def flat_ref(ref):
    out = {}
    for k, v in ref.items():
        if isinstance(v, list):
            for i, b in enumerate(v):
                out['%s %d (%s)' % (k, i, b.name)] = b.shape
        else:
            out[k] = v.shape
    return out


def interference(parts, ref):
    allp = dict(parts)
    allp.update(flat_ref(ref))
    # contacts that are expected (screw in its insert)
    skip = set()
    res = []
    names = list(allp)
    for a, b in itertools.combinations(names, 2):
        if ('hardware' in a and 'hardware' in b):
            continue
        sa, sb = allp[a], allp[b]
        bba, bbb = sa.BoundingBox(), sb.BoundingBox()
        if (bba.xmax < bbb.xmin or bbb.xmax < bba.xmin or bba.ymax < bbb.ymin or bbb.ymax < bba.ymin
                or bba.zmax < bbb.zmin or bbb.zmax < bba.zmin):
            continue
        v = vol(sa.intersect(sb))
        if v > 0.01:
            bb = sa.intersect(sb).BoundingBox()
            res.append((a, b, v, (round(bb.xmin, 1), round(bb.xmax, 1), round(bb.ymin, 1), round(bb.ymax, 1),
                                  round(bb.zmin, 1), round(bb.zmax, 1))))
    return res


def oriented(name, shape):
    s = shape
    for axis, deg in (PRINT_FLIP.get(name) or ()):
        ax = {'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[axis]
        s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(*ax), deg)
    bb = s.BoundingBox()
    return s.translate(cq.Vector(0, 0, -bb.zmin))


def overhangs(name, shape, limit_deg=50.0, min_area=1.0):
    """Down-facing faces (steeper than limit from vertical) that are not on the bed."""
    s = oriented(name, shape)
    lim = math.cos(math.radians(90 - limit_deg))   # |nz| above this counts
    found = []
    for f in s.Faces():
        c = f.Center()
        if c.z < 0.05:
            continue
        try:
            n = f.normalAt(c)
        except Exception:
            continue
        if n.z < -lim:
            a = f.Area()
            if a >= min_area:
                bb = f.BoundingBox()
                found.append((round(a, 1), round(n.z, 2), f.geomType(),
                              (round(bb.xmin, 1), round(bb.xmax, 1), round(bb.ymin, 1), round(bb.ymax, 1), round(bb.zmin, 1))))
    found.sort(reverse=True)
    return found


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    parts, ref = build()
    print('== parts')
    for k, s in parts.items():
        n = len(s.Solids())
        bb = s.BoundingBox()
        print('%-14s solids=%d valid=%s vol=%.0f  size %.1f x %.1f x %.1f' % (
            k, n, s.isValid(), vol(s), bb.xlen, bb.ylen, bb.zlen))
        cq.exporters.export(cq.Workplane().add(oriented(k, s)), os.path.join(out, '%s.stl' % k.replace(' ', '_')),
                            tolerance=0.02, angularTolerance=0.1)
    for k, s in flat_ref(ref).items():
        cq.exporters.export(cq.Workplane().add(s), os.path.join(out, 'ref_%s.stl' % k.split(' ')[0]), tolerance=0.05)
    print('\n== interference (mm^3)')
    for a, b, v, bb in interference(parts, ref):
        print('%-28s %-28s %8.2f  %s' % (a, b, v, bb))
    print('\n== overhangs in print orientation (area mm^2, normal z, type, bbox)')
    for k, s in parts.items():
        oh = overhangs(k, s)
        print('-- %s: %d faces' % (k, len(oh)))
        for o in oh[:25]:
            print('   ', o)
    print('\nMOUNT_H %.1f  motor face y %.1f  hardware:\n%s' % (T.MOUNT_H, T.MOTOR_FACE_Y, T.hardware_summary()))
    render_all(parts, ref, out)


COLOURS = {'Tray': (0.93, 0.92, 0.88), 'Dome': (0.97, 0.96, 0.93), 'Mount': (0.85, 0.84, 0.80),
           'Wand gear': (0.95, 0.65, 0.25), 'Motor pinion': (0.94, 0.39, 0.32), 'Switch plug': (0.3, 0.6, 0.6),
           'wand': (0.6, 0.8, 0.95), 'motor': (0.75, 0.75, 0.78), 'board': (0.2, 0.55, 0.3),
           'board parts': (0.25, 0.65, 0.35), 'c3': (0.2, 0.3, 0.6), 'usb': (0.15, 0.15, 0.15),
           'switch': (0.3, 0.3, 0.35), 'hardware': (0.7, 0.6, 0.3)}


def render_all(parts, ref, out):
    import vtk
    shapes = dict(parts)
    for k, v in ref.items():
        if k == 'wall':
            continue
        if isinstance(v, list):
            shapes[k] = cq.Compound.makeCompound([b.shape for b in v])
        else:
            shapes[k] = v.shape
    files = {}
    for k, s in shapes.items():
        fn = os.path.join(out, 'asm_%s.stl' % k.replace(' ', '_'))
        cq.exporters.export(cq.Workplane().add(s), fn, tolerance=0.03, angularTolerance=0.15)
        files[k] = fn

    def render(fn, names, pos, focal, up=(0, 0, 1), opacity=None):
        ren = vtk.vtkRenderer()
        ren.SetBackground(1, 1, 1)
        for n in names:
            r = vtk.vtkSTLReader()
            r.SetFileName(files[n])
            nm = vtk.vtkPolyDataNormals()
            nm.SetInputConnection(r.GetOutputPort())
            nm.SetFeatureAngle(30)
            nm.SplittingOn()
            m = vtk.vtkPolyDataMapper()
            m.SetInputConnection(nm.GetOutputPort())
            a = vtk.vtkActor()
            a.SetMapper(m)
            a.GetProperty().SetColor(*COLOURS.get(n, (0.8, 0.8, 0.8)))
            if opacity and n in opacity:
                a.GetProperty().SetOpacity(opacity[n])
            ren.AddActor(a)
            fe = vtk.vtkFeatureEdges()
            fe.SetInputConnection(r.GetOutputPort())
            fe.BoundaryEdgesOff()
            fe.ManifoldEdgesOff()
            fe.NonManifoldEdgesOff()
            fe.SetFeatureAngle(30)
            em = vtk.vtkPolyDataMapper()
            em.SetInputConnection(fe.GetOutputPort())
            em.ScalarVisibilityOff()
            ea = vtk.vtkActor()
            ea.SetMapper(em)
            ea.GetProperty().SetColor(0.25, 0.25, 0.3)
            ren.AddActor(ea)
        cam = ren.GetActiveCamera()
        cam.SetPosition(*pos)
        cam.SetFocalPoint(*focal)
        cam.SetViewUp(*up)
        ren.ResetCamera()
        cam.Zoom(1.2)
        rw = vtk.vtkRenderWindow()
        rw.SetOffScreenRendering(1)
        rw.AddRenderer(ren)
        rw.SetSize(1000, 1000)
        rw.Render()
        wi = vtk.vtkWindowToImageFilter()
        wi.SetInput(rw)
        wi.Update()
        pw = vtk.vtkPNGWriter()
        pw.SetFileName(os.path.join(out, fn))
        pw.SetInputConnection(wi.GetOutputPort())
        pw.Write()

    inside = ['Tray', 'Wand gear', 'Motor pinion', 'wand', 'motor', 'board', 'board parts', 'c3', 'hardware']
    # front view looks down -z with -y up
    render('1_tray_inside.png', inside, (40, 120, 160), (0, 0, 10), up=(0, -1, 0))
    render('2_tray_empty.png', ['Tray'], (40, 120, 160), (0, 0, 10), up=(0, -1, 0))
    render('3_dome_inside.png', ['Dome', 'Switch plug', 'switch'], (60, 100, -120), (0, 0, 25), up=(0, -1, 0))
    render('4_assembly.png', ['Dome', 'Tray', 'Mount', 'wand', 'usb'], (140, 160, 120), (0, 0, 0), up=(0, -1, 0))
    render('5_mount.png', ['Mount', 'usb', 'hardware'], (60, 140, 120), (0, 0, -15), up=(0, -1, 0))
    render('6_mount_back.png', ['Mount'], (40, 60, -160), (0, 0, -15), up=(0, -1, 0))
    render('7_section_gear.png', ['Tray', 'Dome', 'Wand gear', 'Motor pinion', 'wand', 'motor'],
           (-160, -60, 60), (0, -25, 19), up=(0, 0, 1), opacity={'Dome': 0.35, 'Tray': 0.6})


if __name__ == '__main__':
    main()
