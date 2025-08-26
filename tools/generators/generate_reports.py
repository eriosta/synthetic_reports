#!/usr/bin/env python3

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import synthrad.generator

if __name__ == "__main__":
    synthrad.generator.main()
