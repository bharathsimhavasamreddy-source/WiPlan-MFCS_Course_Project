"""
wiplan.spectral
Step 3: Realistic Wi-Fi Rules & The "Why 1, 6, 11" Mathematical Proof.
Encodes the physical 802.11 2.4 GHz spectrum rules:
- 11 channels, spaced 5 MHz apart (2412 MHz to 2462 MHz)
- Channel bandwidth = 22 MHz
- Rule: Nearby APs must have |c(u) - c(v)| >= 5 to prevent spectral overlap.
- Proves mathematically why ONLY {1, 6, 11} form the unique maximal non-interfering 3-channel set.
- Adjacent Channel Interference (ACI) penalty matrix and full 11-channel solver.
"""

import math
from typing import Dict, List, Tuple, Any, Optional
from .graph import CampusGraph


def get_channel_center_freq(channel: int) -> float:
    """Returns center frequency in MHz for 2.4 GHz 802.11 channel 1..11."""
    return 2412.0 + 5.0 * (channel - 1)


def get_channel_bounds(channel: int) -> Tuple[float, float]:
    """Returns (f_min, f_max) in MHz for 22 MHz channel bandwidth."""
    fc = get_channel_center_freq(channel)
    return fc - 11.0, fc + 11.0


def calculate_spectral_overlap_ratio(c1: int, c2: int) -> float:
    """
    Computes spectral overlap ratio between channel c1 and c2 in [0.0, 1.0].
    Based on triangular/trapezoidal spectral power mask convolution.
    """
    diff = abs(c1 - c2)
    if diff >= 5:
        return 0.0
    # Overlap drops linearly from 1.0 (co-channel) to 0.0 at diff >= 5
    # diff 0 -> 1.0, diff 1 -> 0.8, diff 2 -> 0.6, diff 3 -> 0.4, diff 4 -> 0.2
    return max(0.0, (5.0 - diff) / 5.0)


def generate_aci_matrix() -> List[List[float]]:
    """
    Generates 11x11 Adjacent Channel Interference (ACI) matrix.
    Rows and columns are channels 1..11 (indices 0..10).
    """
    matrix = []
    for c1 in range(1, 12):
        row = []
        for c2 in range(1, 12):
            row.append(round(calculate_spectral_overlap_ratio(c1, c2), 2))
        matrix.append(row)
    return matrix


class Why1611Proof:
    """
    Mathematical demonstration of why {1, 6, 11} is the unique maximal non-overlapping set.
    """

    @staticmethod
    def get_formal_proof() -> Dict[str, Any]:
        return {
            "theorem": "In the 2.4 GHz Wi-Fi band {1, 2, ..., 11}, the maximum number of mutually non-interfering channels (differing by at least 5) is 3, and the unique maximal symmetric triple spanning the band is {1, 6, 11}.",
            "premises": [
                "1. Center frequency fc(c) = 2412 + 5(c - 1) MHz for c in {1, ..., 11}.",
                "2. 802.11b/g/n signal mask width W = 22 MHz (spans fc ± 11 MHz).",
                "3. To avoid Adjacent Channel Interference (ACI), center frequencies must satisfy |fc(c1) - fc(c2)| >= 22 MHz.",
                "4. Since channels are spaced by 5 MHz, 5 * |c1 - c2| >= 22 => |c1 - c2| >= ceil(22/5) = 5.",
            ],
            "step_1_upper_bound": {
                "title": "Proof that at most 3 non-interfering channels can exist",
                "details": (
                    "Let S = {c_1, c_2, ..., c_k} be any valid subset of channels sorted in ascending order: "
                    "1 <= c_1 < c_2 < ... < c_k <= 11.\n"
                    "Because each adjacent pair must satisfy c_{i+1} - c_i >= 5:\n"
                    "  c_2 >= c_1 + 5\n"
                    "  c_3 >= c_2 + 5 >= c_1 + 10\n"
                    "  ...\n"
                    "  c_k >= c_1 + 5*(k - 1).\n"
                    "Since c_1 >= 1 and c_k <= 11:\n"
                    "  11 >= c_k >= 1 + 5*(k - 1) = 5*k - 4\n"
                    "  => 5*k <= 15\n"
                    "  => k <= 3.\n"
                    "Hence, it is mathematically IMPOSSIBLE to choose 4 or more mutually non-interfering channels."
                ),
            },
            "step_2_uniqueness": {
                "title": "Proof that {1, 6, 11} is the unique optimal configuration",
                "details": (
                    "To achieve the maximum k = 3 channels:\n"
                    "  1 <= c_1 and c_3 <= 11 and c_3 >= c_1 + 10.\n"
                    "The only way this inequality holds is if c_1 = 1 and c_3 = 11!\n"
                    "Now for the middle channel c_2:\n"
                    "  c_2 >= c_1 + 5 = 1 + 5 = 6,\n"
                    "  c_3 >= c_2 + 5 => 11 >= c_2 + 5 => c_2 <= 6.\n"
                    "Since 6 <= c_2 <= 6, we must have c_2 = 6.\n"
                    "Therefore, S = {1, 6, 11} is the UNIQUE 3-channel non-interfering plan in the North American / Indian 11-channel band."
                ),
            },
            "channel_details": [
                {"channel": 1, "center_mhz": 2412, "range_mhz": "2401 - 2423"},
                {"channel": 6, "center_mhz": 2437, "range_mhz": "2426 - 2448"},
                {"channel": 11, "center_mhz": 2462, "range_mhz": "2451 - 2473"},
            ],
        }


def solve_11_channel_spectral(
    graph: CampusGraph, min_separation: int = 5
) -> Dict[str, Any]:
    """
    Assigns channels from {1..11} such that for every interference edge (u, v),
    |c(u) - c(v)| >= min_separation.
    Uses backtracking search with minimum remaining values (MRV) heuristic.
    """
    adj = graph.get_adjacency_list()
    active_nodes = sorted(list(adj.keys()), key=lambda n: len(adj[n]), reverse=True)

    if not active_nodes:
        return {"success": True, "coloring": {}, "message": "No active APs."}

    # Available domains: 1..11 (or {1, 6, 11} if min_separation == 5)
    domain = list(range(1, 12))
    assignment: Dict[str, int] = {}

    def is_valid(node: str, ch: int) -> bool:
        for neighbor in adj[node]:
            if neighbor in assignment:
                if abs(ch - assignment[neighbor]) < min_separation:
                    return False
        return True

    def backtrack(idx: int) -> bool:
        if idx == len(active_nodes):
            return True

        node = active_nodes[idx]
        # Try preferred channels first: 1, 6, 11, then others
        ordered_domain = [1, 6, 11] + [c for c in domain if c not in (1, 6, 11)]

        for ch in ordered_domain:
            if is_valid(node, ch):
                assignment[node] = ch
                if backtrack(idx + 1):
                    return True
                del assignment[node]

        return False

    success = backtrack(0)
    conflicts = []
    if success:
        # Calculate residual ACI
        for u, v in graph.get_interference_edges():
            c_u = assignment[u]
            c_v = assignment[v]
            overlap = calculate_spectral_overlap_ratio(c_u, c_v)
            if overlap > 0:
                conflicts.append({"u": u, "v": v, "overlap": overlap})

        return {
            "success": True,
            "coloring": assignment,
            "min_separation": min_separation,
            "residual_conflicts": conflicts,
            "message": f"Successfully planned campus channels adhering to |c(u) - c(v)| >= {min_separation}.",
        }
    else:
        return {
            "success": False,
            "coloring": {},
            "min_separation": min_separation,
            "message": f"Cannot satisfy strict channel separation of {min_separation} across all APs in the 11-channel band. Use Local Search (Step 4) to minimize total interference.",
        }
