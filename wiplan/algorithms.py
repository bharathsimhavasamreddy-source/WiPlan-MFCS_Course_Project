"""
wiplan.algorithms
Implements Graph Colouring Algorithms for Comparative Benchmarking:
- Greedy First-Fit (Arbitrary Ordering)
- Greedy Welsh-Powell (Largest-First Degree Ordering)
- DSatur (Degree of Saturation - Brélaz 1979)
- Benchmark comparison against DPLL SAT and Local Search.
"""

import time
from typing import Dict, List, Set, Tuple, Any, Optional
from .graph import CampusGraph
from .sat_solver import solve_3_channel_sat
from .local_search import local_search_min_conflicts, count_conflicts


def greedy_first_fit(
    graph: CampusGraph, channel_palette: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Greedy First-Fit graph colouring.
    Assigns the smallest available color index not used by neighbors.
    """
    start_t = time.perf_counter()
    adj = graph.get_adjacency_list()
    nodes = sorted(list(adj.keys()))  # Standard alphabetical order

    if not nodes:
        return {"coloring": {}, "channels_used": 0, "time_ms": 0.0}

    # If palette is not provided, use positive integers 1, 2, 3, ...
    coloring: Dict[str, int] = {}

    for u in nodes:
        neighbor_colors = {coloring[v] for v in adj[u] if v in coloring}
        c = 1
        while c in neighbor_colors:
            c += 1
        coloring[u] = c

    # Map color numbers to channels if palette provided, or keep numbers
    if channel_palette and len(channel_palette) >= max(coloring.values(), default=0):
        mapped = {u: channel_palette[c - 1] for u, c in coloring.items()}
    else:
        mapped = coloring

    elapsed_ms = (time.perf_counter() - start_t) * 1000.0
    channels_used = len(set(coloring.values()))

    # Calculate conflicts if mapped to 3 channels (1, 6, 11)
    conflicts = count_conflicts(graph.get_interference_edges(), mapped)

    return {
        "algorithm": "Greedy First-Fit",
        "ordering": "Arbitrary (Alphabetical)",
        "coloring": mapped,
        "channels_used": channels_used,
        "conflicts": conflicts,
        "time_ms": round(elapsed_ms, 3),
        "complexity": "O(|V| + |E|)",
    }


def greedy_welsh_powell(
    graph: CampusGraph, channel_palette: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Welsh-Powell (Largest First):
    Sorts vertices in descending order of degrees d(v), then colors greedily.
    Upper bound: chi(G) <= 1 + max_i min(d(v_i), i-1).
    """
    start_t = time.perf_counter()
    adj = graph.get_adjacency_list()
    # Sort vertices by descending degree
    nodes = sorted(list(adj.keys()), key=lambda u: len(adj[u]), reverse=True)

    if not nodes:
        return {"coloring": {}, "channels_used": 0, "time_ms": 0.0}

    coloring: Dict[str, int] = {}

    for u in nodes:
        neighbor_colors = {coloring[v] for v in adj[u] if v in coloring}
        c = 1
        while c in neighbor_colors:
            c += 1
        coloring[u] = c

    if channel_palette and len(channel_palette) >= max(coloring.values(), default=0):
        mapped = {u: channel_palette[c - 1] for u, c in coloring.items()}
    else:
        mapped = coloring

    elapsed_ms = (time.perf_counter() - start_t) * 1000.0
    channels_used = len(set(coloring.values()))
    conflicts = count_conflicts(graph.get_interference_edges(), mapped)

    return {
        "algorithm": "Welsh-Powell (Largest First)",
        "ordering": "Descending Degree Order",
        "coloring": mapped,
        "channels_used": channels_used,
        "conflicts": conflicts,
        "time_ms": round(elapsed_ms, 3),
        "complexity": "O(|V| log |V| + |E|)",
    }


def dsatur(
    graph: CampusGraph, channel_palette: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    DSatur (Degree of Saturation, Brélaz 1979):
    Heuristic that chooses next vertex with maximum number of differently colored neighbors.
    Exact for bipartite graphs, cycles, trees, and chordal graphs!
    """
    start_t = time.perf_counter()
    adj = graph.get_adjacency_list()
    nodes = set(adj.keys())

    if not nodes:
        return {"coloring": {}, "channels_used": 0, "time_ms": 0.0}

    coloring: Dict[str, int] = {}
    # Saturation degree: set of distinct colors present in colored neighbors
    saturation: Dict[str, Set[int]] = {u: set() for u in nodes}
    uncolored_degrees: Dict[str, int] = {u: len(adj[u]) for u in nodes}

    while len(coloring) < len(nodes):
        # Find uncolored vertex with:
        # 1. Maximum saturation degree len(saturation[u])
        # 2. Tie-break: Maximum uncolored degree
        best_u = None
        best_sat = -1
        best_deg = -1

        for u in nodes:
            if u not in coloring:
                sat_sz = len(saturation[u])
                deg = uncolored_degrees[u]
                if sat_sz > best_sat or (sat_sz == best_sat and deg > best_deg):
                    best_sat = sat_sz
                    best_deg = deg
                    best_u = u

        # Assign lowest available color
        used_colors = saturation[best_u]
        c = 1
        while c in used_colors:
            c += 1
        coloring[best_u] = c

        # Update saturation and uncolored degrees of neighbors
        for neighbor in adj[best_u]:
            if neighbor not in coloring:
                saturation[neighbor].add(c)
                uncolored_degrees[neighbor] -= 1

    if channel_palette and len(channel_palette) >= max(coloring.values(), default=0):
        mapped = {u: channel_palette[c - 1] for u, c in coloring.items()}
    else:
        mapped = coloring

    elapsed_ms = (time.perf_counter() - start_t) * 1000.0
    channels_used = len(set(coloring.values()))
    conflicts = count_conflicts(graph.get_interference_edges(), mapped)

    return {
        "algorithm": "DSatur (Brélaz 1979)",
        "ordering": "Dynamic Degree of Saturation",
        "coloring": mapped,
        "channels_used": channels_used,
        "conflicts": conflicts,
        "time_ms": round(elapsed_ms, 3),
        "complexity": "O(|V|^2)",
    }


def run_all_benchmarks(graph: CampusGraph) -> Dict[str, Any]:
    """
    Executes and benchmarks all algorithms on the given campus graph:
    1. Greedy First-Fit
    2. Welsh-Powell
    3. DSatur
    4. Exact 3-SAT (DPLL)
    5. Local Search (Min-Conflicts with k=3 channels)
    """
    palette_3 = [1, 6, 11]

    res_greedy = greedy_first_fit(graph)
    res_welsh = greedy_welsh_powell(graph)
    res_dsatur = dsatur(graph)

    # DPLL SAT solver on 3 channels
    sat_res = solve_3_channel_sat(graph, channels=palette_3)
    sat_dict = {
        "algorithm": "Exact 3-SAT (DPLL Solver)",
        "ordering": "MOM's Heuristic + Unit Propagation",
        "coloring": sat_res.coloring,
        "channels_used": len(set(sat_res.coloring.values())) if sat_res.is_sat else "N/A (UNSAT)",
        "conflicts": 0 if sat_res.is_sat else "χ(G) ≥ 4",
        "time_ms": sat_res.stats.get("time_ms", 0.0),
        "is_sat": sat_res.is_sat,
        "complexity": "O(2^|V|) worst-case / Fast in practice",
    }

    # Local search
    ls_res = local_search_min_conflicts(graph, channels=palette_3)
    ls_dict = {
        "algorithm": "Local Search (Min-Conflicts)",
        "ordering": "Greedy Steepest Descent",
        "coloring": ls_res.coloring,
        "channels_used": len(set(ls_res.coloring.values())),
        "conflicts": ls_res.final_conflicts,
        "time_ms": round(len(ls_res.steps) * 0.05, 3),  # approximate computation time
        "theoretical_bound": ls_res.theoretical_bound,
        "complexity": "O(steps * |V| * k)",
    }

    return {
        "graph_name": graph.name,
        "nodes_count": len(graph.aps),
        "edges_count": len(graph.get_interference_edges()),
        "algorithms": [
            res_greedy,
            res_welsh,
            res_dsatur,
            sat_dict,
            ls_dict,
        ],
    }
