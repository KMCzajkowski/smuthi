# -*- coding: utf-8 -*-

import argparse
import smuthi.read_input
import pkg_resources
import os

import pkgutil

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inputfile', nargs='?', default=None, type=str,
                        help='Input file containing the parameters of the simulations.'
                             'See https://gitlab.com/AmosEgel/smuthi for further information. '
                             'Default is the shipped example_input.dat')
    args = parser.parse_args()

    if args.inputfile is None:
        datadirname = os.path.abspath(pkg_resources.resource_filename('smuthi', 'data'))
        args.inputfile = datadirname + '/example_input.dat'

    simulation = smuthi.read_input.read_input_yaml(args.inputfile)
    simulation.run()


if __name__ == "__main__":
    main()
