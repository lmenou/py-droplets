"""
.. codeauthor:: David Zwicker <david.zwicker@ds.mpg.de>
"""

import math
import random

import numpy as np
import pytest
from numba import njit
from scipy import integrate

import pde

from droplets.tools import spherical


@pytest.mark.parametrize("dim", [1, 2, 3])
def test_volume_conversion(dim):
    """Tests conversion of volume and radius of droplet."""
    radius = 1 + random.random()
    volume = spherical.volume_from_radius(radius, dim=dim)
    radius2 = spherical.radius_from_volume(volume, dim=dim)
    assert radius2 == pytest.approx(radius)

    r2v = spherical.make_volume_from_radius_compiled(dim)
    v2r = spherical.make_radius_from_volume_compiled(dim)
    assert r2v(radius) == pytest.approx(volume)
    assert v2r(volume) == pytest.approx(radius)

    r2v_jit = njit(lambda r: r2v(r))
    v2r_jit = njit(lambda r: v2r(r))
    assert r2v_jit(radius) == pytest.approx(volume)
    assert v2r_jit(volume) == pytest.approx(radius)


@pytest.mark.parametrize("dim", [1, 2, 3])
def test_surface(dim):
    """Test whether the surface is calculated correctly."""
    radius = 1 + random.random()
    eps = 1e-10
    vol1 = spherical.volume_from_radius(radius + eps, dim=dim)
    vol0 = spherical.volume_from_radius(radius, dim=dim)
    surface_approx = (vol1 - vol0) / eps
    surface = spherical.surface_from_radius(radius, dim=dim)
    assert surface == pytest.approx(surface_approx, rel=1e-3)

    r2s = spherical.make_surface_from_radius_compiled(dim)
    assert r2s(radius) == pytest.approx(surface)
    r2s_jit = njit(lambda r: r2s(r))
    assert r2s_jit(radius) == pytest.approx(surface)

    if dim == 1:
        with pytest.raises(RuntimeError):
            spherical.radius_from_surface(surface, dim=dim)
    else:
        assert spherical.radius_from_surface(surface, dim=dim) == pytest.approx(radius)


def test_spherical_conversion(rng):
    """Test the conversion between spherical and Cartesian coordinates."""
    s2c = spherical.points_spherical_to_cartesian
    c2s = spherical.points_cartesian_to_spherical

    ps = rng.normal(size=(64, 3))
    np.testing.assert_allclose(s2c(c2s(ps)), ps)

    # enforce angles
    ps[:, 0] = np.abs(ps[:, 0])  # radius is positive
    ps[:, 1] %= np.pi  # θ is between 0 and pi
    ps[:, 2] %= 2 * np.pi  # φ is between 0 and 2 pi
    np.testing.assert_allclose(c2s(s2c(ps)), ps, rtol=1e-6)


def test_spherical_harmonics_examples():
    """Test the conventions of our spherical harmonics."""
    theta, phi = 0.3, 0.4

    # test symmetric version
    expect = 0.25 * np.sqrt(5 / np.pi) * (3 * np.cos(theta) ** 2 - 1)
    assert spherical.spherical_harmonic_symmetric(2, theta) == pytest.approx(expect)
    assert spherical.spherical_harmonic_real(2, 0, theta, phi) == pytest.approx(expect)

    # test real spherical harmonics for l=0
    expect = 0.5 * np.sqrt(1 / np.pi)
    assert spherical.spherical_harmonic_real(0, 0, theta, phi) == pytest.approx(expect)

    # test real spherical harmonics for l=1
    expect = np.sqrt(3 / (4 * np.pi)) * np.sin(theta) * np.sin(phi)
    assert spherical.spherical_harmonic_real(1, -1, theta, phi) == pytest.approx(expect)
    expect = np.sqrt(3 / (4 * np.pi)) * np.cos(theta)
    assert spherical.spherical_harmonic_real(1, 0, theta, phi) == pytest.approx(expect)
    expect = np.sqrt(3 / (4 * np.pi)) * np.sin(theta) * np.cos(phi)
    assert spherical.spherical_harmonic_real(1, 1, theta, phi) == pytest.approx(expect)

    # test real spherical harmonics for l=2
    expect = 0.25 * np.sqrt(15 / np.pi) * np.sin(theta) ** 2 * np.sin(2 * phi)
    assert spherical.spherical_harmonic_real(2, -2, theta, phi) == pytest.approx(expect)
    expect = 0.25 * np.sqrt(15 / np.pi) * np.sin(2 * theta) * np.sin(phi)
    assert spherical.spherical_harmonic_real(2, -1, theta, phi) == pytest.approx(expect)


def test_spherical_index():
    """Test the conversion of the spherical index."""
    # check initial state
    assert spherical.spherical_index_lm(0) == (0, 0)
    assert spherical.spherical_index_k(0, 0) == 0

    # check conversion
    for k in range(20):
        l, m = spherical.spherical_index_lm(k)
        assert spherical.spherical_index_k(l, m) == k

    # check order
    k = 0
    for l in range(4):
        for m in range(-l, l + 1):
            assert spherical.spherical_index_k(l, m) == k
            k += 1

    for l in range(4):
        k_max = spherical.spherical_index_k(l, l)
        assert spherical.spherical_index_count(l) == k_max + 1

    for l in range(4):
        for m in range(-l, l + 1):
            is_optimal = m == l
            k = spherical.spherical_index_k(l, m)
            assert spherical.spherical_index_count_optimal(k + 1) == is_optimal


def test_spherical_harmonics_real():
    """Test spherical harmonics."""
    # test real spherical harmonics for symmetric case
    for deg in range(4):
        for _ in range(5):
            θ = math.pi * random.random()
            φ = 2 * math.pi * random.random()
            y1 = spherical.spherical_harmonic_symmetric(deg, θ)
            y2 = spherical.spherical_harmonic_real(deg, 0, θ, φ)
            assert y1 == pytest.approx(y2)

    # test orthogonality of real spherical harmonics
    deg = 1
    Ylm = spherical.spherical_harmonic_real
    for m1 in range(-deg, deg + 1):
        for m2 in range(-deg, m1 + 1):

            def integrand(t, p):
                return Ylm(deg, m1, t, p) * Ylm(deg, m2, t, p) * np.sin(t)  # noqa: B023

            overlap = integrate.dblquad(
                integrand, 0, 2 * np.pi, lambda _: 0, lambda _: np.pi
            )[0]
            if m1 == m2:
                assert overlap == pytest.approx(1)
            else:
                assert overlap == pytest.approx(0)


def test_polar_coordinates_1d():
    """Test polar_coordinates function in 1d."""
    grid = pde.UnitGrid([2])
    p1, a1 = spherical.polar_coordinates(grid, ret_angle=True)
    p2 = grid.c.pos_from_cart(grid.cell_coords)
    np.testing.assert_allclose(a1, 1)
    np.testing.assert_allclose(p1[:, np.newaxis], p2)


def test_polar_coordinates_2d():
    """Test polar_coordinates function in 2d."""
    grid = pde.UnitGrid([2, 2])
    grid_sph = pde.PolarSymGrid(5, 1)
    p1 = spherical.polar_coordinates(grid, ret_angle=True)
    p2 = grid_sph.c.pos_from_cart(grid.cell_coords)
    np.testing.assert_allclose(np.moveaxis(p1, 0, -1), p2)


def test_polar_coordinates_3d():
    """Test polar_coordinates function in 3d."""
    grid = pde.UnitGrid([2, 2, 2])
    p1 = spherical.polar_coordinates(grid, ret_angle=True)
    p2 = spherical.points_cartesian_to_spherical(grid.cell_coords)
    np.testing.assert_allclose(np.moveaxis(p1, 0, -1), p2)

    grid_sph = pde.SphericalSymGrid(5, 1)
    p3 = grid_sph.c.pos_from_cart(grid.cell_coords)
    np.testing.assert_allclose(np.moveaxis(p1, 0, -1), p3)
