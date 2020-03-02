'''
.. codeauthor:: David Zwicker <david.zwicker@ds.mpg.de>
'''

import pytest
import numpy as np
from scipy import integrate

from .. import droplets



def test_simple_droplet():
    """ test a given simple droplet """
    d = droplets.SphericalDroplet((1, 2), 1)
    assert d.surface_area == pytest.approx(2*np.pi)
    np.testing.assert_allclose(d.interface_position(0), [2, 2])
    np.testing.assert_allclose(d.interface_position([0]), [[2, 2]])
    
    d.volume = 3
    assert d.volume == pytest.approx(3)



@pytest.mark.parametrize("dim", [1, 2, 3])
def test_random_droplet(dim):
    """ tests simple droplet """
    pos = np.random.randn(dim)
    radius = 1 + np.random.random()
    d1 = droplets.SphericalDroplet(pos, radius)
    d2 = droplets.SphericalDroplet(np.zeros(dim), radius)
    d2.position = pos
    
    assert d1.dim == dim
    assert d1.volume > 0
    assert d1.surface_area > 0
    assert d1 == d2

    d3 = d1.copy()
    assert d1 == d3
    assert d1 is not d3
    
    vol = np.random.random()
    d1.volume = vol
    assert d1.volume == pytest.approx(vol)
    


def test_perturbed_volume():
    """ test volume calculation of perturbed droplets """
    pos = np.random.randn(2)
    radius = 1 + np.random.random()
    amplitudes = np.random.uniform(-0.2, 0.2, 6)
    d = droplets.PerturbedDroplet2D(pos, radius, 0, amplitudes)
    
    def integrand(φ):
        r = d.interface_distance(φ)
        return 0.5 * r**2
    
    vol = integrate.quad(integrand, 0, 2 * np.pi)[0]
    assert vol == pytest.approx(d.volume)
    
    vol = np.random.uniform(1, 2)
    d.volume = vol
    assert vol == pytest.approx(d.volume)
    
    pos = np.random.randn(3)
    radius = 1 + np.random.random()
    d = droplets.PerturbedDroplet3D(pos, radius, 0, np.zeros(7))
    assert d.volume == pytest.approx(4 * np.pi / 3 * radius**3)



def test_surface_area():
    """ test surface area calculation of droplets """
    # perturbed 2d droplet        
    R0 = 3
    amplitudes = np.random.uniform(-1e-2, 1e-2, 6)
    
    # unperturbed droplets
    d1 = droplets.SphericalDroplet([0, 0], R0)
    d2 = droplets.PerturbedDroplet2D([0, 0], R0) 
    assert d1.surface_area == pytest.approx(d2.surface_area)
    assert d2.surface_area == pytest.approx(d2.surface_area_approx)
    
    # perturbed droplet
    d1 = droplets.SphericalDroplet([0, 0], R0)
    d2 = droplets.PerturbedDroplet2D([0, 0], R0, amplitudes=amplitudes) 
    assert d1.surface_area != pytest.approx(d2.surface_area)
    assert d2.surface_area == pytest.approx(d2.surface_area_approx, rel=1e-4)



def test_curvature():
    """ test interface curvature calculation """
    # spherical droplet
    for dim in range(1, 4):
        d = droplets.SphericalDroplet(np.zeros(dim),
                                      radius=np.random.uniform(1, 4))
        assert d.interface_curvature == pytest.approx(1 / d.radius)

    # perturbed 2d droplet        
    R0 = 3
    epsilon = 0.1
    amplitudes = epsilon * np.array([0.1, 0.2, 0.3, 0.4])

    def curvature_analytical(φ):
        """ analytical expression for curvature """
        radius = 3. * (
            5. * (40. + 27. * epsilon**2.) + epsilon *
            (40. * (4. * np.cos(2. * φ) + np.sin(φ)) + np.cos(φ) *
             (80. + 66. * epsilon + 240. * np.sin(φ)) - epsilon *
             (10. * np.cos(3. * φ) + 21. * np.cos(4. * φ) - 12. * np.
              sin(φ) + 20. * np.sin(3. * φ) + 72. * np.sin(4. * φ)))
        )**(3. / 2.) / (10. * np.sqrt(2.) * (
            200. + 60. * epsilon *
            (2. * np.cos(φ) + 8. * np.cos(2. * φ) + np.
             sin(φ) + 6. * np.sin(2. * φ)) + epsilon**2. *
            (345. + 165. * np.cos(φ) - 5. * np.cos(3. * φ) - 21. * np.
             cos(4. * φ) + 30. * np.sin(φ) - 10. * np.
             sin(3. * φ) - 72. * np.sin(4. * φ))))
        return 1 / radius

    d = droplets.PerturbedDroplet2D([0, 0], R0, amplitudes=amplitudes)
    φs = np.linspace(0, np.pi, 64)
    np.testing.assert_allclose(d.interface_curvature(φs),
                               curvature_analytical(φs), rtol=1e-1)

