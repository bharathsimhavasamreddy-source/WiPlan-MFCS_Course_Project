"""
wiplan.bipartite
Step 1: Check whether 2 channels are enough.
A graph is 2-colourable if and only if it is bipartite (contains no odd cycle).
If bipartite: returns the exact 2-colouring (Channels 1 and 6).
If not bipartite: extracts an odd cycle C_{2k+1} as a formal mathematical certificate.
"""

from collections import deque
from typing import Dict, List, Tuple, Optional, Any
from .graph import CampusGraph


class BipartiteResult:
    def __init__(
        self,
        is_bipartite: bool,
        coloring: Optional[Dict[str, int]] = None,
        odd_cycle: Optional[List[str]] = None,
        partitions: Optional[Tuple[List[str], List[str]]] = None,
        proof_explanation: str = "",
        bfs_tree_edges: Optional[List[Tuple[str, str]]] = None,
    ):
        self.is_bipartite = is_bipartite
        self.coloring = coloring or {}
        self.odd_cycle = odd_cycle or []
        self.partitions = partitions or ([], [])
        self.proof_explanation = proof_explanation
        self.bfs_tree_edges = bfs_tree_edges or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_bipartite": self.is_bipartite,
            "two_channels_sufficient": self.is_bipartite,
            "coloring": self.coloring,
            "odd_cycle": self.odd_cycle,
            "odd_cycle_length": len(self.odd_cycle),
            "partitions": {
                "set_A": self.partitions[0],
                "set_B": self.partitions[1],
            },
            "proof_explanation": self.proof_explanation,
            "bfs_tree_edges": self.bfs_tree_edges,
        }


def check_bipartite(graph: CampusGraph) -> BipartiteResult:
    """
    Checks if the active AP interference graph is bipartite.
    Uses BFS with parent pointers and depth tracking to find an odd cycle if one exists.
    """
    adj = graph.get_adjacency_list()
    active_nodes = sorted(list(adj.keys()))

    if not active_nodes:
        return BipartiteResult(
            is_bipartite=True,
            coloring={},
            partitions=([], []),
            proof_explanation="The graph has no active access points, vacuously 2-colourable.",
        )

    color: Dict[str, int] = {}  # 1 or 2
    parent: Dict[str, Optional[str]] = {}
    depth: Dict[str, int] = {}
    bfs_tree_edges: List[Tuple[str, str]] = []

    for root in active_nodes:
        if root in color:
            continue

        color[root] = 1
        parent[root] = None
        depth[root] = 0
        queue = deque([root])

        while queue:
            u = queue.popleft()

            for v in adj[u]:
                if v not in color:
                    color[v] = 3 - color[u]  # Toggle between 1 and 2
                    parent[v] = u
                    depth[v] = depth[u] + 1
                    bfs_tree_edges.append((u, v))
                    queue.append(v)
                elif color[v] == color[u]:
                    # Conflict found! color[v] == color[u] implies an odd cycle.
                    # Trace paths back to lowest common ancestor (LCA).
                    path_u = []
                    curr = u
                    while curr is not None:
                        path_u.append(curr)
                        curr = parent.get(curr)

                    path_v = []
                    curr = v
                    while curr is not None:
                        path_v.append(curr)
                        curr = parent.get(curr)

                    # Find LCA
                    set_u = set(path_u)
                    lca = None
                    for ancestor in path_v:
                        if ancestor in set_u:
                            lca = ancestor
                            break

                    # Construct cycle: LCA -> ... -> u -> v -> ... -> LCA
                    u_to_lca = []
                    for node in path_u:
                        u_to_lca.append(node)
                        if node == lca:
                            break

                    v_to_lca = []
                    for node in path_v:
                        v_to_lca.append(node)
                        if node == lca:
                            break

                    # Cycle order: LCA -> u_to_lca (reversed, excluding LCA) -> v_to_lca
                    cycle = list(reversed(u_to_lca)) + v_to_lca[:-1]
                    # Verify cycle length is odd
                    cycle_len = len(cycle)

                    explanation = (
                        f"2 channels are INSUFFICIENT. Found an odd cycle of length {cycle_len}: "
                        f"{' -> '.join(cycle)} -> {cycle[0]}. "
                        f"By Theorem (König, 1936), a graph is 2-colourable if and only if it contains no odd cycle. "
                        f"In an odd cycle of length {cycle_len}, alternating between 2 channels forces the terminal "
                        f"vertices ({u} and {v}) to share the same channel ({color[u]}), creating inevitable co-channel interference. "
                        f"Therefore, chromatic number χ(G) ≥ 3."
                    )

                    return BipartiteResult(
                        is_bipartite=False,
                        odd_cycle=cycle,
                        proof_explanation=explanation,
                        bfs_tree_edges=bfs_tree_edges,
                    )

    # If no conflicts found, the graph is bipartite!
    set_a = [node for node, c in color.items() if c == 1]
    set_b = [node for node, c in color.items() if c == 2]

    # Map colors 1 and 2 to standard Wi-Fi channels 1 and 6
    channel_plan = {node: (1 if c == 1 else 6) for node, c in color.items()}

    explanation = (
        f"2 channels (Channel 1 and Channel 6) are SUFFICIENT! The interference graph is bipartite (contains zero odd cycles). "
        f"The campus APs partition cleanly into Set A ({len(set_a)} APs on Channel 1) and "
        f"Set B ({len(set_b)} APs on Channel 6) with zero co-channel interference edges."
    )

    return BipartiteResult(
        is_bipartite=True,
        coloring=channel_plan,
        partitions=(set_a, set_b),
        proof_explanation=explanation,
        bfs_tree_edges=bfs_tree_edges,
    )
