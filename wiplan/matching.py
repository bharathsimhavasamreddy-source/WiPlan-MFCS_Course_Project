"""
wiplan.matching
Step 5: Connect Students to APs via Weighted Bipartite Matching.
Solves capacity-constrained student-to-AP assignment to maximize total signal strength (RSSI).
Implemented using the Kuhn-Munkres (Hungarian) Algorithm from scratch.
"""

import math
from typing import Dict, List, Tuple, Any, Optional
from .graph import CampusGraph, Student, AccessPoint


class HungarianSolver:
    """
    Kuhn-Munkres (Hungarian) Algorithm for Maximum Weight Bipartite Matching.
    Solves on an N x N weight matrix. Complexity O(N^3).
    """

    def __init__(self, weights: List[List[float]]):
        self.raw_weights = weights
        self.rows = len(weights)
        self.cols = len(weights[0]) if self.rows > 0 else 0
        self.n = max(self.rows, self.cols)

        # Pad into square N x N matrix
        self.w = [[0.0] * self.n for _ in range(self.n)]
        for i in range(self.rows):
            for j in range(self.cols):
                self.w[i][j] = float(weights[i][j])

    def solve_max_weight(self) -> Tuple[List[int], float, List[float], List[float]]:
        """
        Computes maximum weight matching.
        Returns:
        - match_row: list of length 'rows', where match_row[i] is the matched column (or -1 if unmatched)
        - total_weight: total matched weight
        - u: row dual variables
        - v: column dual variables
        """
        n = self.n
        if n == 0:
            return [], 0.0, [], []

        # Dual potentials: u_i and v_j such that u_i + v_j >= w_{ij}
        u = [0.0] * n
        v = [0.0] * n

        # Initial feasible duals: u_i = max_j w_{ij}, v_j = 0
        for i in range(n):
            u[i] = max(self.w[i]) if self.w[i] else 0.0

        # match_col[j] is the row matched to column j, or -1
        # match_row[i] is the column matched to row i, or -1
        match_col = [-1] * n
        match_row = [-1] * n

        # Augment matching for each row i
        for cur_row in range(n):
            links = [-1] * n
            mins = [float("inf")] * n
            visited_col = [False] * n
            marked_row = cur_row
            marked_col = -1

            while True:
                # Update mins for unvisited columns from marked_row
                for j in range(n):
                    if not visited_col[j]:
                        slack = u[marked_row] + v[j] - self.w[marked_row][j]
                        if slack < mins[j]:
                            mins[j] = slack
                            links[j] = marked_row

                # Find column with minimum slack
                delta = float("inf")
                next_col = -1
                for j in range(n):
                    if not visited_col[j] and mins[j] < delta:
                        delta = mins[j]
                        next_col = j

                # Update dual variables
                u[cur_row] -= delta
                for j in range(n):
                    if visited_col[j]:
                        u[match_col[j]] -= delta
                        v[j] += delta
                    else:
                        mins[j] -= delta

                visited_col[next_col] = True
                marked_col = next_col
                marked_row = match_col[next_col]

                if marked_row == -1:
                    # Found augmenting path!
                    break

            # Trace back augmenting path
            while marked_col != -1:
                prev_row = links[marked_col]
                prev_col = match_row[prev_row]
                match_col[marked_col] = prev_row
                match_row[prev_row] = marked_col
                marked_col = prev_col

        # Filter back to original dimensions
        res_matches = []
        total_weight = 0.0
        for i in range(self.rows):
            c = match_row[i]
            if c < self.cols and self.raw_weights[i][c] > 0.0:
                res_matches.append(c)
                total_weight += self.raw_weights[i][c]
            else:
                res_matches.append(-1)

        return res_matches, total_weight, u[:self.rows], v[:self.cols]


class MatchingResult:
    def __init__(
        self,
        assignments: List[Dict[str, Any]],
        unassigned_students: List[str],
        ap_utilization: Dict[str, Dict[str, Any]],
        total_signal_score: float,
        avg_rssi_dbm: float,
        dual_potentials: Dict[str, Any],
        explanation: str,
    ):
        self.assignments = assignments
        self.unassigned_students = unassigned_students
        self.ap_utilization = ap_utilization
        self.total_signal_score = total_signal_score
        self.avg_rssi_dbm = avg_rssi_dbm
        self.dual_potentials = dual_potentials
        self.explanation = explanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assignments": self.assignments,
            "assigned_count": len(self.assignments),
            "unassigned_students": self.unassigned_students,
            "unassigned_count": len(self.unassigned_students),
            "ap_utilization": self.ap_utilization,
            "total_signal_score": round(self.total_signal_score, 2),
            "avg_rssi_dbm": round(self.avg_rssi_dbm, 1),
            "dual_potentials": self.dual_potentials,
            "explanation": self.explanation,
        }

    @property
    def assigned_count(self) -> int:
        return len(self.assignments)

    @property
    def unassigned_count(self) -> int:
        return len(self.unassigned_students)


def solve_student_ap_matching(
    graph: CampusGraph,
    min_rssi_cutoff: float = -90.0,
) -> MatchingResult:
    """
    Builds the bipartite matching between Students and AP capacity slots.
    Weights correspond to received signal strength indicator (RSSI).
    Uses Hungarian algorithm to find the socially optimal matching.
    """
    students = list(graph.students.values())
    active_aps = [ap for ap in graph.aps.values() if ap.active]

    if not students or not active_aps:
        return MatchingResult(
            assignments=[],
            unassigned_students=[s.student_id for s in students],
            ap_utilization={},
            total_signal_score=0.0,
            avg_rssi_dbm=-100.0,
            dual_potentials={},
            explanation="No active students or access points to match.",
        )

    # Expand APs into capacity slots
    # slot_info: list of (ap_id, slot_idx)
    slots: List[Tuple[str, int]] = []
    for ap in active_aps:
        for slot_idx in range(ap.capacity):
            slots.append((ap.ap_id, slot_idx))

    n_students = len(students)
    n_slots = len(slots)

    # Construct weight matrix: students x slots
    # Convert RSSI (e.g. -40 to -90 dBm) to a positive utility score in [0, 100]
    weights: List[List[float]] = []
    rssi_matrix: List[List[float]] = []

    for s in students:
        row_w = []
        row_rssi = []
        for ap_id, _ in slots:
            rssi = graph.calculate_rssi(s.student_id, ap_id)
            row_rssi.append(rssi)
            if rssi >= min_rssi_cutoff:
                # Score from 10 to 100: (-90 dBm -> 10, -30 dBm -> 100)
                score = (rssi - (-100.0)) * (100.0 / 70.0)
                row_w.append(max(0.1, score))
            else:
                row_w.append(0.0)  # Cannot connect due to weak signal
        weights.append(row_w)
        rssi_matrix.append(row_rssi)

    solver = HungarianSolver(weights)
    matched_slots, total_score, u_duals, v_duals = solver.solve_max_weight()

    assignments: List[Dict[str, Any]] = []
    unassigned: List[str] = []
    ap_student_count: Dict[str, int] = {ap.ap_id: 0 for ap in active_aps}
    matched_rssis: List[float] = []

    for i, s in enumerate(students):
        slot_idx = matched_slots[i]
        if slot_idx != -1 and weights[i][slot_idx] > 0.0:
            ap_id, s_slot = slots[slot_idx]
            ap = graph.aps[ap_id]
            rssi = rssi_matrix[i][slot_idx]
            dist = graph.student_ap_distance(s.student_id, ap_id)

            quality = "Excellent" if rssi >= -55 else ("Good" if rssi >= -70 else "Fair")
            assignments.append({
                "student_id": s.student_id,
                "student_name": s.name,
                "student_building": s.building,
                "ap_id": ap_id,
                "ap_name": ap.name,
                "ap_channel": ap.channel,
                "distance_m": round(dist, 1),
                "rssi_dbm": round(rssi, 1),
                "quality": quality,
                "score": round(weights[i][slot_idx], 2),
            })
            s.assigned_ap = ap_id
            ap_student_count[ap_id] += 1
            matched_rssis.append(rssi)
        else:
            unassigned.append(s.student_id)
            s.assigned_ap = None

    avg_rssi = (sum(matched_rssis) / len(matched_rssis)) if matched_rssis else -100.0

    ap_util = {}
    for ap in active_aps:
        cnt = ap_student_count[ap.ap_id]
        pct = round(cnt / max(ap.capacity, 1) * 100.0, 1)
        ap_util[ap.ap_id] = {
            "name": ap.name,
            "building": ap.building,
            "connected_count": cnt,
            "capacity": ap.capacity,
            "utilization_pct": pct,
        }

    explanation = (
        f"Kuhn-Munkres Hungarian Algorithm matched {len(assignments)}/{len(students)} students "
        f"across {len(active_aps)} active APs (total capacity = {n_slots} slots). "
        f"Average received signal strength is {round(avg_rssi, 1)} dBm with a total campus utility of {round(total_score, 1)}. "
        f"Strict capacity constraints were respected for all APs while maximizing aggregate connection quality."
    )

    return MatchingResult(
        assignments=assignments,
        unassigned_students=unassigned,
        ap_utilization=ap_util,
        total_signal_score=total_score,
        avg_rssi_dbm=avg_rssi,
        dual_potentials={"students_count": len(u_duals), "slots_count": len(v_duals)},
        explanation=explanation,
    )
