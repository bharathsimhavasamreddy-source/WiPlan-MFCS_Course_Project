#!/usr/bin/env python3
"""
WiPlan Main Entrypoint:
Run as local web server or command-line analysis tool.
Usage:
  python3 run.py               # Starts web server at http://localhost:8000
  python3 run.py --port 8080   # Custom port
  python3 run.py --test        # Runs all unit tests
  python3 run.py --cli         # Interactive CLI runner
"""

import sys
import os
import argparse
import unittest

# Ensure wiplan package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from wiplan.server import run_server
from wiplan.presets import load_preset, PRESET_MAP
from wiplan.bipartite import check_bipartite
from wiplan.sat_solver import solve_3_channel_sat
from wiplan.local_search import local_search_min_conflicts
from wiplan.matching import solve_student_ap_matching
from wiplan.algorithms import run_all_benchmarks
from wiplan.spectral import Why1611Proof


def run_cli_demo(preset_name: str = "campus_main"):
    print("=" * 70)
    print("🛰️  WiPlan: Interference-Aware Campus Wi-Fi Planning")
    print("=" * 70)
    print(f"Loading preset: {preset_name}...\n")
    g = load_preset(preset_name)

    print(f"Graph: {g.name}")
    print(f"Active APs: {len(g.aps)}")
    edges = g.get_interference_edges()
    print(f"Interference Edges: {len(edges)}")
    print(f"Students on campus: {len(g.students)}\n")

    print("-" * 70)
    print("STEP 1: Check whether 2 channels are enough (Bipartite & Odd Cycle)")
    print("-" * 70)
    res_bip = check_bipartite(g)
    print(f"Is Bipartite? {res_bip.is_bipartite}")
    print(f"Explanation: {res_bip.proof_explanation}\n")

    print("-" * 70)
    print("STEP 2: Exact 3-Channel DPLL SAT Solver")
    print("-" * 70)
    res_sat = solve_3_channel_sat(g)
    print(f"3-Channel SAT Status: {'SATISFIABLE' if res_sat.is_sat else 'UNSATISFIABLE'}")
    print(f"CNF Clauses Generated: {res_sat.cnf_clause_count}")
    print(f"DPLL Decisions: {res_sat.stats.get('decisions')}, Backtracks: {res_sat.stats.get('backtracks')}")
    print(f"Solve Time: {res_sat.stats.get('time_ms')} ms")
    print(f"Explanation: {res_sat.explanation}\n")

    print("-" * 70)
    print("STEP 3: Realistic Wi-Fi Rules & Why {1, 6, 11}")
    print("-" * 70)
    proof = Why1611Proof.get_formal_proof()
    print(f"Theorem: {proof['theorem']}")
    print(f"{proof['step_1_upper_bound']['details']}\n")

    print("-" * 70)
    print("STEP 4: Local Search Interference Minimization")
    print("-" * 70)
    res_ls = local_search_min_conflicts(g)
    print(f"Initial Conflicts: {res_ls.initial_conflicts}")
    print(f"Final Conflicts: {res_ls.final_conflicts}")
    print(f"Theoretical Upper Bound: <= {round(res_ls.theoretical_bound, 2)}")
    print(f"Iterations: {res_ls.iterations}")
    print(f"Conflict Reduction: {res_ls.to_dict()['conflict_reduction_pct']}%\n")

    print("-" * 70)
    print("STEP 5: Student-to-AP Weighted Bipartite Matching (Hungarian Algorithm)")
    print("-" * 70)
    res_match = solve_student_ap_matching(g)
    print(f"Matched Students: {res_match.assigned_count}/{len(g.students)}")
    print(f"Average RSSI: {round(res_match.avg_rssi_dbm, 1)} dBm")
    print(f"Total Campus Utility Score: {round(res_match.total_signal_score, 1)}")
    print(f"Explanation: {res_match.explanation}\n")

    print("-" * 70)
    print("ALGORITHM BENCHMARK SUMMARY")
    print("-" * 70)
    bench = run_all_benchmarks(g)
    for alg in bench["algorithms"]:
        print(f"• {alg['algorithm']:<30} | Channels: {str(alg['channels_used']):<12} | Conflicts: {str(alg['conflicts']):<8} | Time: {alg['time_ms']} ms")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="WiPlan: Campus Wi-Fi Planning")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server (default 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address (default 0.0.0.0)")
    parser.add_argument("--test", action="store_true", help="Run unit test suite")
    parser.add_argument("--cli", action="store_true", help="Run terminal demo")
    parser.add_argument("--preset", type=str, default="campus_main", choices=list(PRESET_MAP.keys()), help="Preset to analyze in CLI")
    args = parser.parse_args()

    if args.test:
        suite = unittest.defaultTestLoader.discover("tests")
        runner = unittest.TextTestRunner(verbosity=2)
        res = runner.run(suite)
        sys.exit(0 if res.wasSuccessful() else 1)
    elif args.cli:
        run_cli_demo(args.preset)
    else:
        run_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()
