"""Shared fixtures for Flwr test suite."""

import sys
import os

# Add the Flwr root to sys.path so that imports like
# `from server.contribution import ...` work from within tests.
_flwr_root = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.insert(0, os.path.abspath(_flwr_root))
