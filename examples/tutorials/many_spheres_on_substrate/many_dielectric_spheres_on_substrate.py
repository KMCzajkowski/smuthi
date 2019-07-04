#*****************************************************************************#
# This is a simple example script for Smuthi v0.8.6.                          #
# It evaluates the differential scattering cross section of a large number of #
# glass spheres on a glass substrate, excited by a plane wave under normal    #
# incidence.                                                                  #
#*****************************************************************************#

import time
import numpy as np
import smuthi.simulation
import smuthi.initial_field
import smuthi.layers
import smuthi.particles
import smuthi.scattered_field
import smuthi.graphical_output
import smuthi.coordinates as coord
import smuthi.cuda_sources as cu
import matplotlib.pyplot as plt

# In this file, all lengths are given in nanometers

coord.set_default_k_parallel(vacuum_wavelength=550, 
                         neff_resolution=5e-3, 
                         neff_max=2.5, 
                         neff_imag=1e-2)

def simulate_N_spheres(number_of_spheres=100,
                       direct_inversion=True,
                       use_gpu=False,
                       solver_tolerance=5e-4,
                       lookup_resolution=5,
                       interpolation_order='linear'):
    
    # Initialize the layer system: substrate (glass) and ambient (air)
    two_layers = smuthi.layers.LayerSystem(thicknesses=[0, 0],
                                           refractive_indices=[1.52, 1])
    
    # Initial field
    plane_wave = smuthi.initial_field.PlaneWave(vacuum_wavelength=550,
                                                polar_angle=np.pi,  # from top
                                                azimuthal_angle=0,
                                                polarization=0)  # 0=TE 1=TM
    
    # Scattering particles (Vogel spiral)
    spheres_list = []
    for i in range(1, number_of_spheres):
        r = 200 * np.sqrt(i)
        theta = i * 137.508 * np.pi/180
        spheres_list.append(smuthi.particles.Sphere(position=[r*np.cos(theta),
                                                               r*np.sin(theta),
                                                               100],
                                                    refractive_index=1.52,
                                                    radius=100,
                                                    l_max=3))
    
    # Initialize and run simulation
    cu.enable_gpu(use_gpu)
    if use_gpu and not cu.use_gpu:
        print("Failed to load pycuda, skipping simulation")
        return [0, 0, 0]
   
    preparation_time = 0
    solution_time = 0

    if direct_inversion:
        simulation = smuthi.simulation.Simulation(layer_system=two_layers,
                                              particle_list=spheres_list,
                                              initial_field=plane_wave)
        # We run the simulation manually to measure the time of each step
	# instead, we could just simulation.run()
        start = time.time()
        simulation.initialize_linear_system()
        simulation.linear_system.prepare()
        end = time.time()
        preparation_time = end - start
 
        start = time.time()
        simulation.linear_system.solve()
        end = time.time()
        solution_time = end - start

    else:
        simulation = smuthi.simulation.Simulation(layer_system=two_layers,
                                                  particle_list=spheres_list,
                                                  initial_field=plane_wave,
                                                  solver_type='gmres', 
                                                  solver_tolerance=solver_tolerance, 
                                                  store_coupling_matrix=False,
                                                  coupling_matrix_lookup_resolution=lookup_resolution, 
                                                  coupling_matrix_interpolator_kind=interpolation_order)

        start = time.time()
        simulation.initialize_linear_system()
        simulation.linear_system.prepare()
        end = time.time()
        preparation_time = end - start
 
        start = time.time()
        simulation.linear_system.solve()
        end = time.time()
        solution_time = end - start

    
    # compute cross section
    ecs = smuthi.scattered_field.extinction_cross_section(initial_field=plane_wave,
                                                          particle_list=spheres_list,
                                                          layer_system=two_layers)

    return [(ecs["top"] + ecs["bottom"]).real, preparation_time, solution_time]
    

# launch a series of simulations:

# iterative solution on GPU
gpu_iterative_particle_numbers = [5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
gpu_iterative_times = []
gpu_iterative_preptimes = []
gpu_iterative_ecs = []
for particle_number in gpu_iterative_particle_numbers:
    print("\n----------------------------------------------------------")
    print("Simulating %i particles on GPU with iterative solver."%particle_number)
    results = simulate_N_spheres(number_of_spheres=particle_number,
                                 direct_inversion=False,
                                 use_gpu=True)
    gpu_iterative_times.append(results[1]+results[2])
    gpu_iterative_preptimes.append(results[1])
    gpu_iterative_ecs.append(results[0])

# direct solution on CPU
cpu_direct_particle_numbers = [5, 10, 20, 50]
cpu_direct_times = []
cpu_direct_preptimes = []
cpu_direct_ecs = []
for particle_number in cpu_direct_particle_numbers:
    print("\n----------------------------------------------------------")
    print("Simulating %i particles on CPU with direct inversion."%particle_number)
    results = simulate_N_spheres(number_of_spheres=particle_number,
                                 direct_inversion=True,
                                 use_gpu=False)
    cpu_direct_times.append(results[1]+results[2])
    cpu_direct_preptimes.append(results[1])
    cpu_direct_ecs.append(results[0])

# iterative solution on CPU
cpu_iterative_particle_numbers = [5, 10, 20, 50, 100, 200]
cpu_iterative_times = []
cpu_iterative_preptimes = []
cpu_iterative_ecs = []
for particle_number in cpu_iterative_particle_numbers:
    print("\n----------------------------------------------------------")
    print("Simulating %i particles on CPU with iterative solver."%particle_number)
    results = simulate_N_spheres(number_of_spheres=particle_number,
                                 direct_inversion=False,
                                 use_gpu=False)
    cpu_iterative_times.append(results[1]+results[2])
    cpu_iterative_preptimes.append(results[1])
    cpu_iterative_ecs.append(results[0])

      
# get GPU device name
import pycuda.driver as drv
drv.init()
device_name = drv.Device(0).name()   
   
plt.figure()
plt.xlabel("Number of spheres")
plt.ylabel("Solver time")
plt.loglog(cpu_direct_particle_numbers, cpu_direct_times, '-bx')
plt.loglog(cpu_direct_particle_numbers, cpu_direct_preptimes, '--bx')
plt.loglog(cpu_iterative_particle_numbers, cpu_iterative_times, '-ro')
plt.loglog(cpu_iterative_particle_numbers, cpu_iterative_preptimes, '--ro')
plt.loglog(gpu_iterative_particle_numbers, gpu_iterative_times, '-gd')
plt.loglog(gpu_iterative_particle_numbers, gpu_iterative_preptimes, '--gd')
plt.legend(["direct, CPU, total", "direct, CPU, prep.", "iter., CPU, total", "iter., CPU, prep.", "iter., GPU, total", "iter., GPU, prep."])
plt.grid()
plt.savefig("runtime.png")

plt.figure()
plt.xlabel("Number of spheres")
plt.ylabel("Extinction cross section [nm^2]")
plt.loglog(cpu_direct_particle_numbers, cpu_direct_ecs, '-bx')
plt.loglog(cpu_iterative_particle_numbers, cpu_iterative_ecs, '-ro')
plt.loglog(gpu_iterative_particle_numbers, gpu_iterative_ecs, '-gd')
plt.legend(["Direct solution on CPU", "Iterative solution on CPU", "Iterative solution on " + device_name])
plt.grid()
plt.savefig("cross_section.png")

plt.show()
