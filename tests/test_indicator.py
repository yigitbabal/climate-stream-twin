import numpy as np

from cstwin.indicator import power_curve


def test_power_curve_regions():
    ws = np.array([0.0, 2.9, 3.0, 12.0, 20.0, 25.0, 30.0])
    p = power_curve(ws, cut_in=3.0, rated=12.0, cut_out=25.0)
    np.testing.assert_allclose(p, [0, 0, 0, 1, 1, 0, 0])


def test_power_curve_monotonic_between_cut_in_and_rated():
    ws = np.linspace(3.0, 11.99, 50)
    p = power_curve(ws, 3.0, 12.0, 25.0)
    assert np.all(np.diff(p) > 0) and p.max() < 1.0
