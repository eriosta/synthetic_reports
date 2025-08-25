#!/usr/bin/env python3

"""
Entry point for running synthrad.generator as a module.
This avoids the circular import issues with __init__.py
"""

from .generator import main

if __name__ == "__main__":
    main()
