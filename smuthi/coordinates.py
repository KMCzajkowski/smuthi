# -*- coding: utf-8 -*-
import numpy as np


class ComplexContour:
    """Trajectory of :math:`n_\mathrm{eff} = \kappa / \omega` in the complex plane for the evaluation of Sommerfeld
    integrals.

    Args:
        neff_waypoints (numpy ndarray):         complex :math:`n_\mathrm{eff}` waypoints, that is, points through which
                                                the contour goes (linear between them).
        neff_discretization (float or list):    Distance between adjacent :math:`n_\mathrm{eff}` values in the contour.
                                                Either as a list of floats (for different discretization in different
                                                linear segments) or as a scalar float (uniform for all segments)
    """
    def __init__(self, neff_waypoints=[0, 1], neff_discretization=1e-2):
        self.neff_waypoints = neff_waypoints
        self.neff_discretization = neff_discretization

    def neff(self):
        """
        Returns:
            numpy-array of :math:`n_\mathrm{eff}` values that define the contour
        """
        neff_segments = []
        for i in range(len(self.neff_waypoints)-1):
            if hasattr(self.neff_discretization, "__len__"):
                npoints = abs(self.neff_waypoints[i+1] - self.neff_waypoints[i]) / self.neff_discretization[i] + 1
            else:
                npoints = abs(self.neff_waypoints[i + 1] - self.neff_waypoints[i]) / self.neff_discretization + 1
            neff_segments.append(self.neff_waypoints[i] + np.linspace(0, 1, num=npoints, endpoint=True, dtype=complex) *
                                 (self.neff_waypoints[i + 1] - self.neff_waypoints[i]))
        return np.concatenate(neff_segments)


def k_z(k_parallel=None, n_effective=None, k=None, omega=None, vacuum_wavelength=None, refractive_index=None):
    """z-component :math:`k_z=\sqrt{k^2-\kappa^2}` of the wavevector. The branch cut is defined such that the imaginary
    part is not negative. Not all of the arguments need to be specified.

    Args:
        k_parallel (numpy ndarray):     In-plane wavenumber :math:`\kappa` (inverse length)
        n_effective (numpy ndarray):    Effective refractive index :math:`n_\mathrm{eff}`
        k (float):                      Wavenumber (inverse length)
        omega (float):                  Angular frequency :math:`\omega` or vacuum wavenumber (inverse length, c=1)
        vacuum_wavelength (float):      Vacuum wavelength :math:`\lambda` (length)
        refractive_index (complex):     Refractive index :math:`n_i` of material

    Returns:
        z-component :math:`k_z` of wavenumber with non-negative imaginary part (inverse length)
    """
    if k_parallel is None:
        if omega is None:
            omega = angular_frequency(vacuum_wavelength)
        k_parallel = n_effective * omega

    if k is None:
        if omega is None:
            omega = angular_frequency(vacuum_wavelength)
        k = refractive_index * omega

    kz = np.sqrt(k ** 2 - k_parallel ** 2 + 0j)
    kz = (kz.imag >= 0) * kz + (kz.imag < 0) * (-kz)  # Branch cut such to prohibit negative imaginary
    return kz


def angular_frequency(vacuum_wavelength):
    """Angular frequency :math:`\omega = 2\pi c / \lambda`

    Args:
        vacuum_wavelength (float): Vacuum wavelength in length unit

    Returns:
        Angular frequency in the units of c=1 (time units=length units). This is at the same time the vacuum wavenumber.
    """
    return 2 * np.pi / vacuum_wavelength
