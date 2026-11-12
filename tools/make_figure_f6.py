#!/usr/bin/env python3
"""Reproduce figure F6 and its full-precision provenance."""
import sys
from make_figures_v6 import main
if __name__ == '__main__':
    sys.argv[1:1] = ['--figure','F6']
    main()
