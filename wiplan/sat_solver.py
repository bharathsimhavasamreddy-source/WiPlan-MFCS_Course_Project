"""
wiplan.sat_solver
Step 2: DPLL SAT Solver & Exact 3-Channel Wi-Fi Planning.
Converts graph colouring into Propositional Logic CNF clauses:
1. At-least-one channel per AP: (x_{u,1} ∨ x_{u,2} ∨ x_{u,3})
2. At-most-one channel per AP: (¬x_{u,c} ∨ ¬x_{u,c'})
3. Interference constraint: (¬x_{u,c} ∨ ¬x_{v,c}) for (u, v) in E

Implements a pure Python DPLL SAT solver from scratch featuring:
- Unit Propagation (Boolean Constraint Propagation)
- Pure Literal Elimination
- MOM's / DLIS variable selection heuristic
- Search tree tracing and statistics
- Certificate of SAT (valid channel plan) or UNSAT (proof of non-3-colourability).
"""

import time
from typing import Dict, List, Set, Tuple, Optional, Any
from .graph import CampusGraph


class DPLLSolver:
    """
    Pure Python DPLL (Davis-Putnam-Logemann-Loveland) SAT solver.
    """

    def __init__(self):
        self.decisions = 0
        self.unit_propagations = 0
        self.pure_literals = 0
        self.backtracks = 0
        self.max_depth = 0
        self.trace_steps: List[Dict[str, Any]] = []

    def solve(
        self,
        clauses: List[List[int]],
        all_vars: Set[int],
        timeout_sec: float = 10.0,
    ) -> Tuple[bool, Optional[Dict[int, bool]]]:
        """
        Solves CNF formula.
        Returns (is_sat, assignment_dict).
        assignment_dict maps var_id -> True/False.
        """
        self.decisions = 0
        self.unit_propagations = 0
        self.pure_literals = 0
        self.backtracks = 0
        self.max_depth = 0
        self.trace_steps = []
        self.start_time = time.perf_counter()
        self.timeout_sec = timeout_sec

        # Standardize clauses into list of frozensets
        initial_clauses = [frozenset(c) for c in clauses if c]
        # Check if empty clause exists initially
        if any(len(c) == 0 for c in clauses):
            return False, None

        sat, assignment = self._dpll(initial_clauses, {}, all_vars, depth=0)
        return sat, assignment

    def _simplify(
        self, clauses: List[frozenset], lit: int
    ) -> Optional[List[frozenset]]:
        """
        Given that literal `lit` is assigned True:
        - Remove all clauses containing `lit` (satisfied).
        - Remove `-lit` from all remaining clauses (cannot satisfy them).
        - If any clause becomes empty, return None (conflict / falsified).
        """
        neg_lit = -lit
        new_clauses = []
        for c in clauses:
            if lit in c:
                continue  # Clause satisfied
            if neg_lit in c:
                filtered = c - {neg_lit}
                if not filtered:
                    return None  # Empty clause -> conflict!
                new_clauses.append(filtered)
            else:
                new_clauses.append(c)
        return new_clauses

    def _dpll(
        self,
        clauses: List[frozenset],
        assignment: Dict[int, bool],
        all_vars: Set[int],
        depth: int,
    ) -> Tuple[bool, Optional[Dict[int, bool]]]:
        if time.perf_counter() - self.start_time > self.timeout_sec:
            raise TimeoutError("DPLL solver exceeded time limit.")

        self.max_depth = max(self.max_depth, depth)

        # 1. Base cases
        if not clauses:
            # All clauses satisfied! Fill unassigned variables with True
            full_assignment = dict(assignment)
            for v in all_vars:
                if v not in full_assignment:
                    full_assignment[v] = True
            return True, full_assignment

        if any(len(c) == 0 for c in clauses):
            return False, None

        # 2. Unit Propagation
        unit_clause = None
        for c in clauses:
            if len(c) == 1:
                unit_clause = next(iter(c))
                break

        if unit_clause is not None:
            self.unit_propagations += 1
            lit = unit_clause
            var = abs(lit)
            val = (lit > 0)
            new_assign = dict(assignment)
            new_assign[var] = val
            simpler = self._simplify(clauses, lit)
            if simpler is None:
                self.backtracks += 1
                return False, None
            return self._dpll(simpler, new_assign, all_vars, depth + 1)

        # 3. Pure Literal Elimination
        literals_present = set()
        for c in clauses:
            literals_present.update(c)

        for lit in list(literals_present):
            if -lit not in literals_present:
                self.pure_literals += 1
                var = abs(lit)
                val = (lit > 0)
                new_assign = dict(assignment)
                new_assign[var] = val
                simpler = self._simplify(clauses, lit)
                if simpler is None:
                    self.backtracks += 1
                    return False, None
                return self._dpll(simpler, new_assign, all_vars, depth + 1)

        # 4. Variable Selection Heuristic (MOM's - Maximum Occurrences in Minimum clauses)
        # Find minimum clause length
        min_len = min(len(c) for c in clauses)
        counts: Dict[int, int] = {}
        for c in clauses:
            if len(c) == min_len:
                for lit in c:
                    counts[lit] = counts.get(lit, 0) + 1

        # Pick literal with highest count in minimum clauses
        best_lit = max(counts.keys(), key=lambda l: counts[l])
        chosen_var = abs(best_lit)

        self.decisions += 1
        if len(self.trace_steps) < 50:
            self.trace_steps.append({
                "decision": self.decisions,
                "depth": depth,
                "chosen_var": chosen_var,
                "try_literal": best_lit,
            })

        # Branch 1: Try best_lit
        val1 = (best_lit > 0)
        branch1_assign = dict(assignment)
        branch1_assign[chosen_var] = val1
        simpler1 = self._simplify(clauses, best_lit)
        if simpler1 is not None:
            sat, res = self._dpll(simpler1, branch1_assign, all_vars, depth + 1)
            if sat:
                return True, res

        # Branch 2: Backtrack and try -best_lit
        self.backtracks += 1
        val2 = not val1
        branch2_assign = dict(assignment)
        branch2_assign[chosen_var] = val2
        simpler2 = self._simplify(clauses, -best_lit)
        if simpler2 is not None:
            sat, res = self._dpll(simpler2, branch2_assign, all_vars, depth + 1)
            if sat:
                return True, res

        return False, None


class SATColoringResult:
    def __init__(
        self,
        is_sat: bool,
        coloring: Optional[Dict[str, int]] = None,
        cnf_clause_count: int = 0,
        variable_count: int = 0,
        sample_clauses: Optional[List[str]] = None,
        stats: Optional[Dict[str, Any]] = None,
        explanation: str = "",
    ):
        self.is_sat = is_sat
        self.coloring = coloring or {}
        self.cnf_clause_count = cnf_clause_count
        self.variable_count = variable_count
        self.sample_clauses = sample_clauses or []
        self.stats = stats or {}
        self.explanation = explanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_sat": self.is_sat,
            "three_channels_sufficient": self.is_sat,
            "coloring": self.coloring,
            "cnf_clause_count": self.cnf_clause_count,
            "variable_count": self.variable_count,
            "sample_clauses": self.sample_clauses,
            "stats": self.stats,
            "explanation": self.explanation,
        }


def solve_3_channel_sat(
    graph: CampusGraph,
    channels: List[int] = [1, 6, 11],
    timeout_sec: float = 10.0,
) -> SATColoringResult:
    """
    Formulates 3-channel planning as SAT in CNF, solves with DPLL,
    and returns solution or UNSAT proof.
    """
    adj = graph.get_adjacency_list()
    active_nodes = sorted(list(adj.keys()))
    edges = graph.get_interference_edges()

    if not active_nodes:
        return SATColoringResult(
            is_sat=True,
            coloring={},
            explanation="Graph has no active APs.",
        )

    # 1. Variable mapping:
    # Var x_{u, c}: AP u is assigned channel index c (0, 1, 2)
    # Variable ID is positive integer: 1 .. n * k
    k = len(channels)
    node_to_idx = {node: i for i, node in enumerate(active_nodes)}
    idx_to_node = {i: node for i, node in enumerate(active_nodes)}

    def var_id(u: str, c_idx: int) -> int:
        return node_to_idx[u] * k + c_idx + 1

    def parse_var(var: int) -> Tuple[str, int]:
        idx = (var - 1) // k
        c_idx = (var - 1) % k
        return idx_to_node[idx], channels[c_idx]

    all_vars = set(range(1, len(active_nodes) * k + 1))
    clauses: List[List[int]] = []
    readable_samples: List[str] = []

    # Clause Type 1: At-least-one channel per vertex
    # (x_{u, 1} v x_{u, 2} v x_{u, 3})
    for u in active_nodes:
        clause = [var_id(u, c_idx) for c_idx in range(k)]
        clauses.append(clause)
        if len(readable_samples) < 3:
            var_names = [f"x({u}, Ch{channels[c]})" for c in range(k)]
            readable_samples.append(f"At-least-one: ({' ∨ '.join(var_names)})")

    # Clause Type 2: At-most-one channel per vertex
    # (not x_{u, c} v not x_{u, c'})
    for u in active_nodes:
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-var_id(u, c1), -var_id(u, c2)])
                if len(readable_samples) < 6:
                    readable_samples.append(
                        f"At-most-one: (¬x({u}, Ch{channels[c1]}) ∨ ¬x({u}, Ch{channels[c2]}))"
                    )

    # Clause Type 3: Interference constraint (no two adjacent APs share channel)
    # (not x_{u, c} v not x_{v, c}) for (u, v) in E
    for u, v in edges:
        if u in node_to_idx and v in node_to_idx:
            for c_idx in range(k):
                clauses.append([-var_id(u, c_idx), -var_id(v, c_idx)])
                if len(readable_samples) < 10:
                    readable_samples.append(
                        f"Interference: (¬x({u}, Ch{channels[c_idx]}) ∨ ¬x({v}, Ch{channels[c_idx]}))"
                    )

    solver = DPLLSolver()
    start_t = time.perf_counter()
    try:
        is_sat, assignment = solver.solve(clauses, all_vars, timeout_sec=timeout_sec)
    except TimeoutError:
        return SATColoringResult(
            is_sat=False,
            cnf_clause_count=len(clauses),
            variable_count=len(all_vars),
            sample_clauses=readable_samples,
            explanation="DPLL solver timed out before finding a solution.",
        )
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    stats = {
        "decisions": solver.decisions,
        "unit_propagations": solver.unit_propagations,
        "pure_literals": solver.pure_literals,
        "backtracks": solver.backtracks,
        "max_depth": solver.max_depth,
        "time_ms": round(elapsed_ms, 3),
        "trace": solver.trace_steps,
    }

    if is_sat and assignment:
        coloring = {}
        for var, val in assignment.items():
            if val and 1 <= var <= len(active_nodes) * k:
                node, ch = parse_var(var)
                coloring[node] = ch

        # Verify all nodes received a channel
        for u in active_nodes:
            if u not in coloring:
                # Default to first channel if unassigned (due to base case fill)
                coloring[u] = channels[0]

        explanation = (
            f"SATISFIABLE (SAT)! DPLL found a valid interference-free 3-channel plan in {stats['time_ms']} ms "
            f"with {stats['decisions']} decisions, {stats['unit_propagations']} unit propagations, "
            f"and {stats['backtracks']} backtracks. All {len(edges)} interference edges have different channels assigned."
        )
        return SATColoringResult(
            is_sat=True,
            coloring=coloring,
            cnf_clause_count=len(clauses),
            variable_count=len(all_vars),
            sample_clauses=readable_samples,
            stats=stats,
            explanation=explanation,
        )
    else:
        explanation = (
            f"UNSATISFIABLE (UNSAT)! Proved by DPLL exhaustively exploring the search space "
            f"({stats['decisions']} decisions, {stats['backtracks']} backtracks, {stats['time_ms']} ms): "
            f"No valid assignment can satisfy the {len(clauses)} CNF clauses. "
            f"Therefore, the interference graph G is not 3-colourable (χ(G) ≥ 4). "
            f"Campus Wi-Fi requires either more channels (e.g. 5 GHz band) or local search conflict minimization (Step 4)."
        )
        return SATColoringResult(
            is_sat=False,
            cnf_clause_count=len(clauses),
            variable_count=len(all_vars),
            sample_clauses=readable_samples,
            stats=stats,
            explanation=explanation,
        )
