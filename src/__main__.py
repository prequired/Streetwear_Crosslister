#!/usr/bin/env python3
"""
Streetwear Inventory Cross-Listing CLI
Main entry point for the application
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cli.commands import inventory

if __name__ == '__main__':
    inventory()