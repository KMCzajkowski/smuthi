# -*- coding: utf-8 -*-

import numpy as np
import smuthi.coordinates as coord
import smuthi.field_expansion as fldex


class InitialField:
    """Base class for initial field classes"""
    def __init__(self, vacuum_wavelength):
        self.vacuum_wavelength = vacuum_wavelength

    def spherical_wave_expansion(self, particle, layer_system):
        """Virtual method to be overwritten."""
        pass

    def plane_wave_expansion(self, layer_system, i):
        """Virtual method to be overwritten."""
        pass

    def piecewise_field_expansion(self, layer_system):
        """Virtual method to be overwritten."""
        pass
    
    def angular_frequency(self):
        """Angular frequency.
        
        Returns:
            Angular frequency (float) according to the vacuum wavelength in units of c=1.
        """
        return coord.angular_frequency(self.vacuum_wavelength)


class InitialPropagatingWave(InitialField):
    """Base class for plane waves and Gaussian beams

    Args:
        vacuum_wavelength (float):
        polar_angle (float):            polar propagation angle (0 means, parallel to z-axis)
        azimuthal_angle (float):        azimuthal propagation angle (0 means, in x-z plane)
        polarization (int):             0 for TE/s, 1 for TM/p
        amplitude (float or complex):   Electric field amplitude
        reference_point (list):         Location where electric field of incoming wave equals amplitude
    """
    def __init__(self, vacuum_wavelength, polar_angle, azimuthal_angle, polarization, amplitude=1,
                 reference_point=None):
        assert (polarization == 0 or polarization == 1)
        InitialField.__init__(self, vacuum_wavelength)
        self.polar_angle = polar_angle
        self.azimuthal_angle = azimuthal_angle
        self.polarization = polarization
        self.amplitude = amplitude
        if reference_point:
            self.reference_point = reference_point
        else:
            self.reference_point = [0, 0, 0]
            
    def spherical_wave_expansion(self, particle, layer_system):
        """Regular spherical wave expansion of the wave including layer system response, at the locations of the
        particles.
        """
        # todo: doc
        i = layer_system.layer_number(particle.position[2])
        pwe_up, pwe_down = self.plane_wave_expansion(layer_system, i)
        return (fldex.pwe_to_swe_conversion(pwe_up, particle.l_max, particle.m_max, particle.position)
                + fldex.pwe_to_swe_conversion(pwe_down, particle.l_max, particle.m_max, particle.position))

    def piecewise_field_expansion(self, layer_system):
        # todo: doc
        pfe = fldex.PiecewiseFieldExpansion()
        for i in range(layer_system.number_of_layers()):
            pwe_up, pwe_down = self.plane_wave_expansion(layer_system, i)
            pfe.expansion_list.append(pwe_up)
            pfe.expansion_list.append(pwe_down)
        return pfe

    def electric_field(self, x, y, z, layer_system):
        """Evaluate the complex electric field corresponding to the wave.

        Args:
            x (array like):     Array of x-values where to evaluate the field (length unit)
            y (array like):     Array of y-values where to evaluate the field (length unit)
            z (array like):     Array of z-values where to evaluate the field (length unit)
            layer_system (smuthi.layer.LayerSystem):    Stratified medium

        Returns
            Tuple (E_x, E_y, E_z) of electric field values
        """

        pfe = self.piecewise_field_expansion(layer_system=layer_system)
        return pfe.electric_field(x, y, z)

    
class GaussianBeam(InitialPropagatingWave):
    """Class for the representation of a Gaussian beam as initial field."""
    def __init__(self, vacuum_wavelength, polar_angle, azimuthal_angle, polarization, beam_waist, k_parallel_array,
                 azimuthal_angles_array, amplitude=1, reference_point=None):
        InitialPropagatingWave.__init__(self, vacuum_wavelength, polar_angle, azimuthal_angle, polarization, amplitude,
                                        reference_point)
        self.beam_waist = beam_waist
        self.k_parallel_array = k_parallel_array
        self.azimuthal_angles_array = azimuthal_angles_array
        
    def plane_wave_expansion(self, layer_system, i, k_parallel_array=None, azimuthal_angles_array=None):
        
        if k_parallel_array is None:
            k_parallel_array = self.k_parallel_array
        if azimuthal_angles_array is None:
            azimuthal_angles_array = self.azimuthal_angles_array

        if np.cos(self.polar_angle) > 0:
            iG = 0  # excitation layer number
            kind = 'upgoing'
        else:
            iG = layer_system.number_of_layers() - 1
            kind = 'downgoing'

        niG = layer_system.refractive_indices[iG]  # refractive index in excitation layer
        k_iG = niG * self.angular_frequency()
        z_iG = layer_system.reference_z(iG)
        loz = layer_system.lower_zlimit(iG)
        upz = layer_system.upper_zlimit(iG)
        pwe_exc = fldex.PlaneWaveExpansion(k=k_iG, k_parallel=k_parallel_array, azimuthal_angles=azimuthal_angles_array, 
                                           kind=kind, reference_point=[0, 0, z_iG], lower_z=loz, upper_z=upz)

        k_Gx = k_iG * np.sin(self.polar_angle) * np.cos(self.azimuthal_angle)
        k_Gy = k_iG * np.sin(self.polar_angle) * np.sin(self.azimuthal_angle)

        kp = pwe_exc.k_parallel_grid()
        al = pwe_exc.azimuthal_angle_grid()

        kx = kp * np.cos(al)
        ky = kp * np.sin(al)
        kz = pwe_exc.k_z_grid()

        w = self.beam_waist
        r_G = self.reference_point

        g = (self.amplitude * w**2 / (4 * np.pi) * np.exp(-w**2 / 4 * ((kx - k_Gx)**2 + (ky - k_Gy)**2))
             * np.exp(-1j * (kx * r_G[0] + ky * r_G[1] + kz * (r_G[2] - z_iG))) )

        pwe_exc.coefficients[0, :, :] = g * np.cos(al - self.azimuthal_angle + self.polarization * np.pi/2)
        if np.cos(self.polar_angle) > 0:
            pwe_exc.coefficients[1, :, :] = g * np.sin(al - self.azimuthal_angle + self.polarization * np.pi/2)
        else:
            pwe_exc.coefficients[1, :, :] = - g * np.sin(al - self.azimuthal_angle + self.polarization * np.pi/2)

        pwe_up, pwe_down = layer_system.response(pwe_exc, from_layer=iG, to_layer=i)
        if iG == i:
            if kind == 'upgoing':
                pwe_up = pwe_up + pwe_exc
            elif kind == 'downgoing':
                pwe_down = pwe_down + pwe_exc

        return pwe_up, pwe_down

    def propagated_far_field(self, layer_system):
        """Evaluate the far field intensity of the reflected / transmitted initial field.

        Args:
            layer_system (smuthi.layers.LayerSystem):           Stratified medium

        Returns:
            A tuple of smuthi.field_evaluation.FarField objects, one for forward (i.e., into the top hemisphere) and one
            for backward propagation (bottom hemisphere).
        """
        i_top = layer_system.number_of_layers() - 1
        top_ff = fldex.pwe_to_ff_conversion(vacuum_wavelength=self.vacuum_wavelength,
                                            plane_wave_expansion=self.plane_wave_expansion(layer_system, i_top)[0])
        bottom_ff = fldex.pwe_to_ff_conversion(vacuum_wavelength=self.vacuum_wavelength,
                                               plane_wave_expansion=self.plane_wave_expansion(layer_system, 0)[1])

        return top_ff, bottom_ff

    def initial_intensity(self, layer_system):
        """Evaluate the incoming intensity of the initial field.

        Args:
            layer_system (smuthi.layers.LayerSystem):           Stratified medium

        Returns:
            A smuthi.field_evaluation.FarField object holding the initial intensity information.
        """
        if np.cos(self.polar_angle) > 0:  # bottom illumination
            ff = fldex.pwe_to_ff_conversion(vacuum_wavelength=self.vacuum_wavelength,
                                            plane_wave_expansion=self.plane_wave_expansion(layer_system, 0)[0])
        else:  # top illumination
            i_top = layer_system.number_of_layers() - 1
            ff = fldex.pwe_to_ff_conversion(vacuum_wavelength=self.vacuum_wavelength,
                                            plane_wave_expansion=self.plane_wave_expansion(layer_system, i_top)[1])
        return ff


class PlaneWave(InitialPropagatingWave):
    """Class for the representation of a plane wave as initial field.

    Args:
        vacuum_wavelength (float):
        polar_angle (float):            polar angle of k-vector (0 means, k is parallel to z-axis)
        azimuthal_angle (float):        azimuthal angle of k-vector (0 means, k is in x-z plane)
        polarization (int):             0 for TE/s, 1 for TM/p
        amplitude (float or complex):   Plane wave amplitude at reference point
        reference_point (list):         Location where electric field of incoming wave equals amplitude
    """
        
    def plane_wave_expansion(self, layer_system, i):
        """Plane wave expansion for the plane wave including its layer system response. As it already is a plane wave,
        the plane wave expansion is somehow trivial (containing only one partial wave, i.e., a discrete plane wave
        expansion).

        Args:
            layer_system (smuthi.layers.LayerSystem): Layer system object
            i (int): layer number in which the plane wave expansion is valid

        Returns:
            Tuple of smuthi.field_expansion.PlaneWaveExpansion objects. The first element is an upgoing PWE, whereas the
            second element is a downgoing PWE.
        """
        if np.cos(self.polar_angle) > 0:
            iP = 0
            kind = 'upgoing'
        else:
            iP = layer_system.number_of_layers() - 1
            kind = 'downgoing'

        niP = layer_system.refractive_indices[iP]
        neff = np.sin([self.polar_angle]) * niP
        alpha = np.array([self.azimuthal_angle])

        angular_frequency = coord.angular_frequency(self.vacuum_wavelength)
        k_iP = niP * angular_frequency
        k_Px = k_iP * np.sin(self.polar_angle) * np.cos(self.azimuthal_angle)
        k_Py = k_iP * np.sin(self.polar_angle) * np.sin(self.azimuthal_angle)
        k_Pz = k_iP * np.cos(self.polar_angle)
        z_iP = layer_system.reference_z(iP)
        amplitude_iP = self.amplitude * np.exp(-1j * (k_Px * self.reference_point[0] + k_Py * self.reference_point[1]
                                                      + k_Pz * (self.reference_point[2] - z_iP)))
        loz = layer_system.lower_zlimit(iP)
        upz = layer_system.upper_zlimit(iP)
        pwe_exc = fldex.PlaneWaveExpansion(k=k_iP, k_parallel=neff*angular_frequency, azimuthal_angles=alpha, kind=kind,
                                           reference_point=[0, 0, z_iP], lower_z=loz, upper_z=upz)
        pwe_exc.coefficients[self.polarization, 0, 0] = amplitude_iP
        pwe_up, pwe_down = layer_system.response(pwe_exc, from_layer=iP, to_layer=i)
        if iP == i:
            if kind == 'upgoing':
                pwe_up = pwe_up + pwe_exc
            elif kind == 'downgoing':
                pwe_down = pwe_down + pwe_exc

        return pwe_up, pwe_down
