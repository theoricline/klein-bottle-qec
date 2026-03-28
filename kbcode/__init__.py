"""
kbcode — Klein bottle stabilizer code library
===============================================
Klein bottle QEC · doi:10.5281/zenodo.19284050
"""
from .core import (
    klein_star, toric_star,
    predicted_pattern, compute_gsd,
    analyse_counts, capacity, all_capacities,
    build_H, gf2_rank,
    CodeResult, ParallelResult,
    KNOWN_BACKENDS,
)

__version__ = "0.1.0"
__author__  = "Leonardo Roma"
__doi__     = "10.5281/zenodo.19284050"
