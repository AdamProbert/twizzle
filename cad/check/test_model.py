"""
Tests for the Twizzle CAD. Run with `pytest cad/check` (needs cadquery and pytest).

The model is built once, in CadQuery, from the Fusion script's own part code.
The self-check is the same one Fusion shows after each build; the other tests
cover what only makes sense here (print orientation, one solid per part).
"""

import pytest

from cqmodel import T, CQProbe, build, bridges, overhangs

MAX_BRIDGE = 22.0           # mm; the Command strip pockets are 20 mm


@pytest.fixture(scope='session')
def model():
    return build()


@pytest.fixture(scope='session')
def report(model):
    parts, ref = model
    return T.self_check(CQProbe(parts, ref))


@pytest.mark.parametrize('group', ['Interference', 'Wall thickness', 'Gear centre distance', 'Bolts and inserts'])
def test_self_check(report, group):
    rows = [r for r in report if r[0] == group]
    assert rows, 'no %s checks ran' % group
    fails = [detail for _, ok, detail in rows if not ok]
    assert not fails, '\n'.join(fails)


@pytest.mark.parametrize('part', T.PRINTED)
def test_one_valid_solid(model, part):
    shape = model[0][part]
    assert shape.isValid()
    assert len(shape.Solids()) == 1, '%s comes out in %d pieces' % (part, len(shape.Solids()))


@pytest.mark.parametrize('part', T.PRINTED)
def test_prints_without_supports(model, part):
    shape = model[0][part]
    assert not overhangs(part, shape), 'sloped overhangs past 50 degrees: %s' % overhangs(part, shape)[:5]
    long = [b for b in bridges(part, shape) if b[0] > MAX_BRIDGE]
    assert not long, 'bridges longer than %g mm: %s' % (MAX_BRIDGE, long)


def test_no_stray_bodies(model):
    """A cut that splits a body leaves extra bodies in Fusion; they must all get joined back."""
    stray = [b.name for b in model[1]['stray bodies']]
    assert not stray, 'left over in the printed parts: %s' % stray


def test_wand_wall_gap():
    gap = (T.STRIP_T - T.STRIP_RECESS) + T.MOUNT_H + T.WAND_Z
    assert abs(gap - T.WAND_WALL_GAP) < 1e-6
