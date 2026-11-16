"""
tests/test_all.py
Comprehensive unit tests for all WiPlan algorithmic modules:
- Bipartite BFS & Odd Cycle Extraction
- DPLL SAT Solver & 3-Coloring CNF Reduction
- Spectral 11-Channel Rules & Proof
- Local Search Min-Conflicts & Guarantee
- Hungarian Matching & AP Capacities
- Kempe Chains Dynamic Recoloring
"""

import unittest
from wiplan.graph import CampusGraph, AccessPoint, Student
from wiplan.bipartite import check_bipartite
from wiplan.sat_solver import DPLLSolver, solve_3_channel_sat
from wiplan.spectral import (
    Why1611Proof,
    get_channel_center_freq,
    calculate_spectral_overlap_ratio,
    solve_11_channel_spectral,
)
from wiplan.local_search import local_search_min_conflicts, count_conflicts
from wiplan.matching import HungarianSolver, solve_student_ap_matching
from wiplan.kempe import kempe_recolor_for_new_ap, find_kempe_component
from wiplan.presets import (
    get_preset_campus_main,
    get_preset_bipartite_corridor,
    get_preset_odd_cycle_pentagon,
    get_preset_dense_auditorium,
    get_preset_grotzsch_graph,
)


class TestWiPlan(unittest.TestCase):

    def test_bipartite_corridor(self):
        """Corridor graph has no odd cycles and must be 2-colourable."""
        g = get_preset_bipartite_corridor()
        res = check_bipartite(g)
        self.assertTrue(res.is_bipartite)
        self.assertEqual(len(res.odd_cycle), 0)
        self.assertTrue(len(res.coloring) > 0)
        # Check no co-channel interference
        for u, v in g.get_interference_edges():
            self.assertNotEqual(res.coloring[u], res.coloring[v])

    def test_odd_cycle_pentagon(self):
        """C5 pentagon must be identified as non-bipartite with odd cycle length 5."""
        g = get_preset_odd_cycle_pentagon()
        res = check_bipartite(g)
        self.assertFalse(res.is_bipartite)
        self.assertEqual(len(res.odd_cycle), 5)
        self.assertIn("INSUFFICIENT", res.proof_explanation)

    def test_dpll_core(self):
        """Test DPLL solver on small CNF problems."""
        solver = DPLLSolver()
        # Formula: (x1 v x2) & (~x1 v x2) & (~x2) -> UNSAT
        clauses = [[1, 2], [-1, 2], [-2]]
        sat, _ = solver.solve(clauses, {1, 2})
        self.assertFalse(sat)

        # Formula: (x1 v x2) & (~x1 v ~x2) -> SAT
        clauses2 = [[1, 2], [-1, -2]]
        sat2, assign = solver.solve(clauses2, {1, 2})
        self.assertTrue(sat2)
        self.assertIsNotNone(assign)

    def test_sat_3_coloring_campus_main(self):
        """Main campus must be satisfiable with 3 channels."""
        g = get_preset_campus_main()
        res = solve_3_channel_sat(g, channels=[1, 6, 11])
        self.assertTrue(res.is_sat)
        for u, v in g.get_interference_edges():
            self.assertNotEqual(res.coloring[u], res.coloring[v])

    def test_sat_3_coloring_dense_auditorium_unsat(self):
        """Dense auditorium has a 4-clique and must be proved UNSAT for 3 channels."""
        g = get_preset_dense_auditorium()
        res = solve_3_channel_sat(g, channels=[1, 6, 11])
        self.assertFalse(res.is_sat)
        self.assertIn("UNSATISFIABLE", res.explanation)

    def test_sat_grotzsch_graph_unsat(self):
        """Grötzsch graph is triangle-free but 4-chromatic; must be UNSAT for 3 channels."""
        g = get_preset_grotzsch_graph()
        res = solve_3_channel_sat(g, channels=[1, 6, 11])
        self.assertFalse(res.is_sat)

    def test_spectral_proof_and_overlap(self):
        """Check 802.11 spectrum math and ACI calculation."""
        self.assertEqual(get_channel_center_freq(1), 2412.0)
        self.assertEqual(get_channel_center_freq(6), 2437.0)
        self.assertEqual(get_channel_center_freq(11), 2462.0)

        # Distance >= 5 channels -> zero overlap
        self.assertEqual(calculate_spectral_overlap_ratio(1, 6), 0.0)
        self.assertEqual(calculate_spectral_overlap_ratio(6, 11), 0.0)
        self.assertEqual(calculate_spectral_overlap_ratio(1, 11), 0.0)

        # Distance < 5 channels -> overlap > 0
        self.assertGreater(calculate_spectral_overlap_ratio(1, 2), 0.5)
        self.assertEqual(calculate_spectral_overlap_ratio(1, 1), 1.0)

        proof = Why1611Proof.get_formal_proof()
        self.assertIn("unique", proof["step_2_uniqueness"]["title"].lower())

    def test_local_search_guarantee(self):
        """Verify that local search achieves conflicts <= |E|/3 on dense graphs."""
        g = get_preset_dense_auditorium()
        res = local_search_min_conflicts(g, channels=[1, 6, 11])
        self.assertLessEqual(res.final_conflicts, res.theoretical_bound)
        self.assertLessEqual(res.final_conflicts, res.initial_conflicts)

    def test_hungarian_matching(self):
        """Verify Hungarian algorithm finds optimal matching respecting capacities."""
        # Test basic Kuhn-Munkres on 3x3
        weights = [
            [10.0, 5.0, 1.0],
            [2.0, 8.0, 4.0],
            [1.0, 3.0, 9.0],
        ]
        solver = HungarianSolver(weights)
        match, total_w, _, _ = solver.solve_max_weight()
        self.assertEqual(match, [0, 1, 2])
        self.assertEqual(total_w, 27.0)

        # Test on campus network
        g = get_preset_campus_main()
        match_res = solve_student_ap_matching(g)
        self.assertEqual(match_res.assigned_count, len(g.students))
        # Ensure capacities are never exceeded
        for ap_id, util in match_res.ap_utilization.items():
            self.assertLessEqual(util["connected_count"], util["capacity"])

    def test_kempe_chain(self):
        """Verify Kempe chain recoloring when a new AP is introduced."""
        g = get_preset_bipartite_corridor()
        # Initialize coloring
        cur_coloring = {ap.ap_id: (1 if "N" in ap.ap_id else 6) for ap in g.aps.values()}
        # Add new AP in between
        new_ap = AccessPoint("AP-NEW", "Corridor Kiosk", 240, 220, capacity=4)
        res = kempe_recolor_for_new_ap(g, new_ap, cur_coloring, channels=[1, 6, 11])
        self.assertTrue(res["success"])
        self.assertIn(res["new_channel"], [1, 6, 11])


if __name__ == "__main__":
    unittest.main()
