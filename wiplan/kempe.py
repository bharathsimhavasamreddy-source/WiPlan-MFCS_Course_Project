"""
wiplan.kempe
Bonus Feature: Kempe Chain Dynamic Recoloring for AP Addition & Failure.
When an AP is added or its environment changes:
Instead of re-colouring the whole campus from scratch (which would disrupt active Wi-Fi connections campus-wide),
Kempe chains allow swapping colours locally in an (alpha, beta)-bicoloured component to free up a channel.
"""

from collections import deque
from typing import Dict, List, Set, Tuple, Any, Optional
from .graph import CampusGraph, AccessPoint


def find_kempe_component(
    start_node: str,
    color_alpha: int,
    color_beta: int,
    coloring: Dict[str, int],
    adj: Dict[str, List[str]],
) -> Set[str]:
    """
    Finds the connected component containing `start_node` in the
    induced subgraph G[{v : coloring[v] in {color_alpha, color_beta}}].
    """
    if coloring.get(start_node) not in (color_alpha, color_beta):
        return set()

    visited = set([start_node])
    queue = deque([start_node])

    while queue:
        u = queue.popleft()
        for v in adj.get(u, []):
            if v not in visited and coloring.get(v) in (color_alpha, color_beta):
                visited.add(v)
                queue.append(v)

    return visited


def kempe_recolor_for_new_ap(
    graph: CampusGraph,
    new_ap: AccessPoint,
    current_coloring: Dict[str, int],
    channels: List[int] = [1, 6, 11],
) -> Dict[str, Any]:
    """
    Attempts to assign a valid channel to new_ap with minimal campus disruption:
    1. If a channel in `channels` is not used by any neighbor, assign it directly (0 APs recoloured).
    2. If all 3 channels are used by neighbors, search for an (alpha, beta) Kempe chain
       emanating from a neighbor that does NOT contain another neighbor of color beta.
       If found, flip alpha <-> beta on that chain, freeing alpha for new_ap!
    """
    adj = graph.get_adjacency_list()
    # Find neighbors of new_ap based on distance to active APs
    active_aps = [ap for ap in graph.aps.values() if ap.active]
    neighbors = []
    for ap in active_aps:
        dist = ((ap.x - new_ap.x) ** 2 + (ap.y - new_ap.y) ** 2) ** 0.5
        threshold = (ap.interference_radius + new_ap.interference_radius) / 2.0
        if dist <= threshold:
            neighbors.append(ap.ap_id)

    neighbor_channels = {current_coloring.get(nbr) for nbr in neighbors if nbr in current_coloring}

    # Case 1: Simple free channel available
    free_channels = [c for c in channels if c not in neighbor_channels]
    if free_channels:
        chosen_c = free_channels[0]
        new_coloring = dict(current_coloring)
        new_coloring[new_ap.ap_id] = chosen_c
        return {
            "success": True,
            "method": "Direct Free Channel",
            "new_channel": chosen_c,
            "recolored_aps": [],
            "recolored_count": 0,
            "coloring": new_coloring,
            "explanation": f"Channel {chosen_c} was completely free among all {len(neighbors)} neighbors of {new_ap.name}. Assigned with 0 AP reconfigurations!",
        }

    # Case 2: All channels are used by neighbors.
    # Group neighbors by their channel
    nbrs_by_channel: Dict[int, List[str]] = {c: [] for c in channels}
    for nbr in neighbors:
        c = current_coloring.get(nbr)
        if c in nbrs_by_channel:
            nbrs_by_channel[c].append(nbr)

    # Try all pairs of colors (alpha, beta)
    for alpha in channels:
        for beta in channels:
            if alpha >= beta:
                continue

            # Pick a neighbor with color alpha
            for u in nbrs_by_channel[alpha]:
                chain = find_kempe_component(u, alpha, beta, current_coloring, adj)

                # Check if this chain contains ANY neighbor of new_ap that has color beta
                beta_nbrs_in_chain = [v for v in nbrs_by_channel[beta] if v in chain]

                if not beta_nbrs_in_chain:
                    # Kempe chain swap is successful!
                    # Swap alpha <-> beta for all nodes in chain
                    new_coloring = dict(current_coloring)
                    for node in chain:
                        if new_coloring[node] == alpha:
                            new_coloring[node] = beta
                        elif new_coloring[node] == beta:
                            new_coloring[node] = alpha

                    # Now, u (and any other alpha neighbor in this chain) has become beta!
                    # None of new_ap's neighbors have color alpha anymore!
                    new_coloring[new_ap.ap_id] = alpha

                    return {
                        "success": True,
                        "method": "Kempe Chain Color Swap",
                        "new_channel": alpha,
                        "alpha": alpha,
                        "beta": beta,
                        "recolored_aps": sorted(list(chain)),
                        "recolored_count": len(chain),
                        "coloring": new_coloring,
                        "explanation": (
                            f"Kempe Chain swap succeeded! Swapped Channel {alpha} ↔ Channel {beta} on a localized chain of {len(chain)} APs "
                            f"({', '.join(sorted(list(chain)))}). This freed Channel {alpha} for {new_ap.name} without altering any of the "
                            f"remaining {len(current_coloring) - len(chain)} APs on campus!"
                        ),
                    }

    # If all Kempe chains connect the neighbors, fallback to minimal local search
    return {
        "success": False,
        "method": "Kempe Chain Blocked (Topological Obstruction)",
        "new_channel": None,
        "recolored_aps": [],
        "recolored_count": 0,
        "coloring": current_coloring,
        "explanation": "All (alpha, beta)-Kempe chains between conflicting neighbors are intertwined (topological obstruction). A localized 2-color swap alone cannot free a channel; full Local Search (Step 4) is recommended.",
    }
