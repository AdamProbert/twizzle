"""
Builds the Twizzle parts from the Fusion script's own part code, in CadQuery,
and reports on them: the script's self-check, overlaps, overhangs in each
part's print orientation, STLs in print orientation and a few renders.

    pip install cadquery          (vtk comes with it)
    python cad/check/check.py [out_dir]

The same checks run as tests with `pytest cad/check`.
"""

import os
import sys

import cadquery as cq

from cqmodel import T, CQProbe, build, named_bodies, interference, oriented, overhangs, bridges

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    parts, ref = build()
    print('== parts')
    for k, s in parts.items():
        bb = s.BoundingBox()
        print('%-14s solids=%d valid=%s vol=%.0f  size %.1f x %.1f x %.1f' % (
            k, len(s.Solids()), s.isValid(), s.Volume(), bb.xlen, bb.ylen, bb.zlen))
        cq.exporters.export(cq.Workplane().add(oriented(k, s)), os.path.join(out, '%s.stl' % k.replace(' ', '_')),
                            tolerance=0.02, angularTolerance=0.1)
    print('\n' + T.format_report(T.self_check(CQProbe(parts, ref))))
    print('\n== every overlap, including expected ones (mm^3)')
    for a, b, v in interference(named_bodies(parts, ref)):
        print('  %-28s %-28s %8.2f' % (a, b, v))
    print('\n== print orientation: sloped overhangs and bridges')
    for k, s in parts.items():
        oh = overhangs(k, s)
        br = bridges(k, s)
        print('-- %s: %d sloped overhangs, %d bridges (longest unsupported span %.1f mm)' % (
            k, len(oh), len(br), max([b[0] for b in br] or [0])))
        for o in oh[:10]:
            print('   overhang', o)
    print('\nMOUNT_H %.1f  motor face y %.1f\n%s' % (T.MOUNT_H, T.MOTOR_FACE_Y, T.hardware_summary()))
    try:
        render_all(parts, ref, out)
    except Exception as e:          # no display / no OpenGL (CI): the STLs are still there
        print('\nrenders skipped: %s' % e)


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
            if not v:
                continue
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
    # front view looks down -z with +y up, as Fusion shows it
    render('1_tray_inside.png', inside, (40, 120, 160), (0, 0, 10), up=(0, 1, 0))
    render('2_tray_empty.png', ['Tray'], (40, 120, 160), (0, 0, 10), up=(0, 1, 0))
    render('3_dome_inside.png', ['Dome', 'Switch plug', 'switch'], (60, 100, -120), (0, 0, 25), up=(0, 1, 0))
    render('4_assembly.png', ['Dome', 'Tray', 'Mount', 'wand', 'usb'], (140, 160, 120), (0, 0, 0), up=(0, 1, 0))
    render('5_mount.png', ['Mount', 'usb', 'hardware'], (60, 140, 120), (0, 0, -15), up=(0, 1, 0))
    render('6_mount_back.png', ['Mount'], (40, 60, -160), (0, 0, -15), up=(0, 1, 0))
    render('8_bottom.png', ['Dome', 'Tray', 'Mount', 'usb'], (30, -170, 60), (0, 0, 0), up=(0, 0, 1))
    render('9_top.png', ['Dome', 'Tray', 'Mount'], (30, 170, 60), (0, 0, 0), up=(0, 0, 1))
    render('7_section_gear.png', ['Tray', 'Dome', 'Wand gear', 'Motor pinion', 'wand', 'motor'],
           (-160, -60, 60), (0, -25, 19), up=(0, 0, 1), opacity={'Dome': 0.35, 'Tray': 0.6})


if __name__ == '__main__':
    main()
