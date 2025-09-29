"""Configuration for camera PV performance tests.

This file mirrors the contents of `05_config.py` so that modules can
`import config` without renaming the original numbered file.

Edit CAMERA_PVS here (and optionally delete 05_config.py to avoid duplication).
"""

CAMERA_PVS = [
    "13ARV222:image1:ArrayData",
    "13ARV222:image2:ArrayData",
    "13ARV222:image3:ArrayData",
]

RESULTS_DIR = "results"
