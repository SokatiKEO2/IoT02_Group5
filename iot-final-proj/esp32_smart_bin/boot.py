"""
Boot file for Smart Trash Bin ESP32
Runs before main.py
"""

import gc
import esp

# Disable debug output
esp.osdebug(None)

# Run garbage collection
gc.collect()
