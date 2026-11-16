"""
WiPlan: Interference-Aware Campus Wi-Fi Planning
Using Graph Colouring, SAT Solving and Bipartite Matching.
"""

from .graph import CampusGraph, AccessPoint, Student, BuildingZone
from .bipartite import check_bipartite
from .sat_solver import solve_3_channel_sat, DPLLSolver
from .spectral import Why1611Proof, solve_11_channel_spectral, generate_aci_matrix
from .local_search import local_search_min_conflicts, simulate_random_vs_local_search
from .matching import solve_student_ap_matching, HungarianSolver
from .kempe import kempe_recolor_for_new_ap
from .algorithms import run_all_benchmarks, dsatur, greedy_welsh_powell, greedy_first_fit
from .presets import load_preset, PRESET_MAP

__version__ = "1.0.0"
__all__ = [
    "CampusGraph",
    "AccessPoint",
    "Student",
    "BuildingZone",
    "check_bipartite",
    "solve_3_channel_sat",
    "DPLLSolver",
    "Why1611Proof",
    "solve_11_channel_spectral",
    "generate_aci_matrix",
    "local_search_min_conflicts",
    "simulate_random_vs_local_search",
    "solve_student_ap_matching",
    "HungarianSolver",
    "kempe_recolor_for_new_ap",
    "run_all_benchmarks",
    "dsatur",
    "greedy_welsh_powell",
    "greedy_first_fit",
    "load_preset",
    "PRESET_MAP",
]
