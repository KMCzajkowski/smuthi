# -*- coding: utf-8 -*-
"""Provide routines for multiple scattering."""

import numpy as np
import scipy.special
import smuthi.index_conversion as idx
import smuthi.coordinates as coord
import smuthi.layers as lay
import smuthi.vector_wave_functions as vwf
import matplotlib.pyplot as plt


def layer_mediated_coupling_block(vacuum_wavelength, receiving_particle_position, emitting_particle_position,
                                  layer_system, index_specs, neff_contour, layerresponse_precision=None,
                                  show_integrand=False):
    """Return the layer-system mediated particle coupling matrix W^R for two particles. This routine is explicit, but
    slow.

    Input:
    vacuum_wavelength:              (length unit)
    receiving_particle_position:    In the format [x,y,z] (length unit)
    emitting_particle_position:     In the format [x,y,z] (length unit)
    layer_system:                   An instance of smuthi.layers.LayerSystem describing the stratified medium
    index_specs:                    A dictionary with the entries 'lmax', 'mmax' and 'index arrangement'
    neff_contour:                   An instance of smuthi.coordinates.ComplexContour to define the contour of the
                                    Sommerfeld integral
    layerresponse_precision:        Number of decimal digits (int). If specified, the layer-response is evaluated using
                                    mpmath multiple precision. Otherwise, standard numpy.
    show_integrand:                 If True, the norm of the integrand is plotted.
    """
    omega = coord.angular_frequency(vacuum_wavelength)

    # read out index specs
    lmax = index_specs['lmax']
    mmax = index_specs['mmax']
    if mmax is None:
        mmax = lmax
    index_arrangement = index_specs['index arrangement']
    blocksize = idx.block_size(lmax=lmax, mmax=mmax, index_arrangement=index_arrangement)

    # cylindrical coordinates of relative position vectors
    rs1 = np.array(receiving_particle_position)
    rs2 = np.array(emitting_particle_position)
    rs2s1 = rs1 - rs2
    rhos2s1 = np.linalg.norm(rs2s1[0:1])
    phis2s1 = np.arctan2(rs2s1[1], rs2s1[0])
    is1 = layer_system.layer_number(rs1[2])
    ziss1 = rs1[2] - layer_system.reference_z(is1)
    is2 = layer_system.layer_number(rs2[2])
    ziss2 = rs2[2] - layer_system.reference_z(is2)

    # wave numbers
    neff = neff_contour.neff()
    kpar = omega * neff
    kis2 = omega * layer_system.refractive_indices[is2]
    kzis1 = coord.k_z(n_effective=neff, vacuum_wavelength=vacuum_wavelength,
                      refractive_index=layer_system.refractive_indices[is1])
    kzis2 = coord.k_z(n_effective=neff, vacuum_wavelength=vacuum_wavelength,
                      refractive_index=layer_system.refractive_indices[is2])

    # phase factors
    ejkz = np.zeros((2, 2, len(neff)), dtype=complex)  # indices are: particle, plus/minus, kpar_idx
    ejkz[0, 0, :] = np.exp(1j * kzis1 * ziss1)
    ejkz[0, 1, :] = np.exp(- 1j * kzis1 * ziss1)
    ejkz[1, 0, :] = np.exp(1j * kzis2 * ziss2)
    ejkz[1, 1, :] = np.exp(- 1j * kzis2 * ziss2)

    # layer response
    L = np.zeros((2, 2, 2, len(neff)), dtype=complex)  # indices are: polarization, pl/mn1, pl/mn2, kpar_idx
    for pol in range(2):
        L[pol, :, :, :] = lay.layersystem_response_matrix(pol, layer_system.thicknesses,
                                                          layer_system.refractive_indices, kpar, omega, is2, is1,
                                                          layerresponse_precision)

    # transformation coefficients
    B = np.zeros((2, 2, 2, blocksize, len(neff)), dtype=complex)  # indices are: particle, pol, plus/minus, n, kpar_idx

    m_vec = np.zeros(blocksize, dtype=int)
    kz_tup = (kzis1, kzis2)
    plmn_tup = (1, -1)
    dagger_tup = (True, False)

    for tau in range(2):
        for m in range(-mmax, mmax + 1):
            for l in range(max(1, abs(m)), lmax + 1):
                n = idx.multi2single(tau, l, m, lmax, mmax, index_arrangement=index_arrangement)
                m_vec[n] = m
                for iprt in range(2):
                    for iplmn, plmn in enumerate(plmn_tup):
                        for pol in range(2):
                            B[iprt, pol, iplmn, n, :] = vwf.transformation_coefficients_VWF(tau, l, m, pol, kpar,
                                                                                            plmn * kz_tup[iprt],
                                                                                            dagger=dagger_tup[iprt])

    BeL = np.zeros((2, 2, blocksize, len(neff)), dtype=complex) # indices are: pol, plmn2, n1, kpar_idx
    for iplmn1 in range(2):
        for pol in range(2):
            BeL[pol, :, :, :] += (L[pol, iplmn1, :, np.newaxis, :] *
                                     B[0, pol, iplmn1, np.newaxis, :, :] * ejkz[0, iplmn1, :])
    BeLBe = np.zeros((blocksize, blocksize, len(neff)), dtype=complex) # indices are: n1, n2, kpar_idx
    for iplmn2 in range(2):
        for pol in range(2):
            BeLBe += BeL[pol, iplmn2, :, np.newaxis, :] * B[1, pol, iplmn2, :, :] * ejkz[1, 1 - iplmn2, :]

    # bessel function and jacobi factor
    bessel_list = []
    for dm in range(2 * lmax + 1):
        bessel_list.append(scipy.special.jv(dm, kpar * rhos2s1))
    bessel_full = np.array([[bessel_list[abs(m_vec[n1] - m_vec[n2])]
                                    for n1 in range(blocksize)] for n2 in range(blocksize)])
    jacobi_vector = kpar / (kzis2 * kis2)
    integrand = bessel_full * jacobi_vector * BeLBe
    integral = np.trapz(integrand, x=kpar, axis=-1)
    m2_minus_m1 = m_vec[np.newaxis].T - m_vec
    wr = 4 * (1j) ** abs(m2_minus_m1) * np.exp(1j * m2_minus_m1 * phis2s1) * integral

    if show_integrand:
        norm_integrand = np.zeros(len(neff))
        for i in range(len(neff)):
            norm_integrand[i] = 4 * np.linalg.norm(integrand[:, :, i])
        plt.plot(neff.real, norm_integrand)
        plt.show()

    return wr


def layer_mediated_coupling_matrix(vacuum_wavelength, particle_collection, layer_system, index_specs, neff_contour,
                                   layerresponse_precision=None):
    """Return the layer-system mediated particle coupling matrix W^R for a particle collection.
    This routine is explicit, but slow. It is thus suited for problems with few particles only.

    NOT TESTED

    Input:
    vacuum_wavelength:              (length unit)
    particle_collection:            An instance of  smuthi.particles.ParticleCollection describing the scattering
                                    particles
    layer_system:                   An instance of smuthi.layers.LayerSystem describing the stratified medium
    swe_idx_specs:                  A dictionary with the entries 'lmax', 'mmax' and 'index arrangement'
    neff_contour:                   An instance of smuthi.coordinates.ComplexContour to define the contour of the
                                    Sommerfeld integral
    layerresponse_precision:        Number of decimal digits (int). If specified, the layer-response is evaluated using
                                    mpmath multiple precision. Otherwise, standard numpy.
    """
    blocksize = idx.block_size(index_specs=index_specs)
    particle_number = particle_collection.particle_number()
    system_size = blocksize * particle_number
    wr = np.zeros((system_size, system_size), dtype=complex)

    if index_specs['index arrangement'][0] == 's':
        for s1, particle1 in enumerate(particle_collection.particles):
            rs1 = particle1['position']
            s1_start_idx = s1 * blocksize
            for s2, particle2 in enumerate(particle_collection.particles):
                rs2 = particle2['position']
                s2_start_idx = s2 * blocksize
                wrblock = layer_mediated_coupling_block(vacuum_wavelength, rs1, rs2, layer_system, index_specs,
                                                        neff_contour, layerresponse_precision)

                wr[s1_start_idx:(s1_start_idx + blocksize), s2_start_idx:(s2_start_idx + blocksize)] = wrblock
    else:
        raise ValueError('index arrangement other than "s..." are currently not implemented')

    return wr