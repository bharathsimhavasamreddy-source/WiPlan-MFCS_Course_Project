# 📡 WiPlan: Interference-Aware Campus Wi-Fi Planning
### Graph Colouring, DPLL SAT Solving, and Weighted Bipartite Matching

> **One-Line Summary:** WiPlan computes optimal, non-interfering Wi-Fi channel assignments for campus access points (APs) and connects students to the strongest APs using graph theory, exact SAT solving, and combinatorial optimization.

---

## 🎯 The Problem

Modern university campuses feature dozens of high-density Access Points (APs) placed across hostels, research laboratories, libraries, and student cafeterias. In the widely used **2.4 GHz ISM band**, there are only **3 clean, non-overlapping channels: 1, 6, and 11**.

If two nearby APs share the same frequency channel:
- Packet transmissions collide under CSMA/CA contention.
- Latency spikes and throughput drops dramatically for every connected student.
- WiPlan converts the campus network into an interference graph and computes mathematically optimal channel plans.

---

## 🔬 Mathematical Formulations & Course Topics

```
                          ┌─────────────────────────────┐
                          │   Campus Network Layout     │
                          │   G = (V, E), V = APs       │
                          └──────────────┬──────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      ┌─────────────────────────┐                 ┌─────────────────────────┐
      │   Step 1: 2 Channels?   │                 │ Step 3: Wi-Fi Spectrum  │
      │   König's Theorem BFS   │                 │ |c_u - c_v| >= 5 Rule   │
      │   Odd Cycle Certificate │                 │ Proof of {1, 6, 11}     │
      └────────────┬────────────┘                 └─────────────────────────┘
                   │
                   ▼ (Fails if odd cycle found)
      ┌─────────────────────────┐
      │  Step 2: DPLL 3-SAT     │
      │  CNF Clause Reduction   │
      │  Unit Prop & MOM's      │
      └────────────┬────────────┘
                   │
                   ├─────────────────► If UNSAT (chi >= 4)
                   │                   ┌─────────────────────────┐
                   │                   │ Step 4: Local Search    │
                   │                   │ Min-Conflicts Descent   │
                   │                   │ Conflicts <= |E|/3      │
                   │                   └─────────────────────────┘
                   ▼ (SAT Valid Plan)
      ┌─────────────────────────┐
      │  Step 5: Hungarian AP   │
      │  Bipartite Matching     │
      │  RSSI Max Optimization  │
      └────────────┬────────────┘
                   │
                   ▼ (Dynamic AP Changes)
      ┌─────────────────────────┐
      │  Bonus: Kempe Chains    │
      │  (alpha, beta) Swaps    │
      │  Zero Campus Disruption │
      └─────────────────────────┘
```

### 1. Step 1: 2-Channel Bipartiteness & Odd Cycle Certificate
- **Theorem (Dénes König, 1936):** A graph $G$ is 2-colourable if and only if $G$ is bipartite (contains no odd cycle).
- **Algorithm:** BFS traversal with tree depth and parent tracking.
- **Odd Cycle Extraction:** If an edge $(u, v)$ connects two vertices with the same colour, WiPlan backtracks to their Lowest Common Ancestor (LCA) in the BFS tree, reconstructing the exact cycle $u \to \dots \to \text{LCA} \to \dots \to v \to u$ of odd length $2k+1$.
- **Certificate:** Proves $\chi(G) \ge 3$, certifying that 2 channels are mathematically insufficient.

### 2. Step 2: Exact 3-Channel DPLL SAT Solver
Formulated in Propositional Logic CNF clauses:
1. **At-least-one channel per AP:**
   $$\bigvee_{c \in \{1, 6, 11\}} x_{u, c} \quad \forall u \in V$$
2. **At-most-one channel per AP:**
   $$(\neg x_{u, c} \lor \neg x_{u, c'}) \quad \forall u \in V, \, 1 \le c < c' \le 3$$
3. **Co-channel interference exclusion:**
   $$(\neg x_{u, c} \lor \neg x_{v, c}) \quad \forall (u, v) \in E, \, c \in \{1, 6, 11\}$$
- **Custom Pure Python DPLL Engine:** Implemented from scratch featuring Unit Propagation (Boolean Constraint Propagation), Pure Literal Elimination, MOM's (Maximum Occurrences in Minimum clauses) variable selection heuristic, and search-tree backtrack tracking.

### 3. Step 3: Realistic 802.11 Spectrum & Why Only {1, 6, 11}
- **Physical Spectrum:** 11 channels spaced 5 MHz apart ($f_c = 2412 + 5(c - 1) \text{ MHz}$), but each channel bandwidth is 22 MHz ($f_c \pm 11 \text{ MHz}$).
- **Non-Interference Rule:** Center frequencies must differ by at least 22 MHz:
  $$5 \cdot |c(u) - c(v)| \ge 22 \implies |c(u) - c(v)| \ge 5$$
- **Interval Packing / Pigeonhole Bound:**
  For any valid channel set $1 \le c_1 < c_2 < \dots < c_k \le 11$:
  $$c_k \ge c_1 + 5(k - 1) \ge 1 + 5(k - 1) = 5k - 4$$
  $$11 \ge 5k - 4 \implies 5k \le 15 \implies k \le 3$$
  Proves that at most 3 non-interfering channels can exist in the 2.4 GHz band.
- **Uniqueness Proof:**
  For $k = 3$, $c_1 = 1$ and $c_3 = 11$. Then $1 + 5 \le c_2 \le 11 - 5 \implies 6 \le c_2 \le 6 \implies c_2 = 6$.
  Thus, **$\{1, 6, 11\}$ is the UNIQUE valid 3-channel plan**.

### 4. Step 4: Local Search (Min-Conflicts) Interference Minimization
When $\chi(G) \ge 4$ (e.g. dense auditoriums), no 0-conflict 3-colouring exists.
- **Random Baseline Expectation:**
  If each AP chooses uniformly at random from $k=3$ channels:
  $$\mathbb{P}(c(u) = c(v)) = \frac{1}{3}$$
  By Linearity of Expectation:
  $$\mathbb{E}[\text{Conflicts}] = \sum_{e \in E} \mathbb{P}(c(u) = c(v)) = \frac{|E|}{3}$$
  Removes $2/3$ of all potential interference on average, but suffers from high random variance.
- **Local Search Deterministic Guarantee:**
  At any local minimum reached by greedily shifting APs to least-conflicted channels, each vertex $u$ has at most $\frac{d(u)}{3}$ neighbors of its channel (Pigeonhole Principle).
  Summing over all vertices by the Handshaking Lemma ($\sum d(u) = 2|E|$):
  $$2 \times \text{Conflicts} = \sum_{u \in V} n_{c(u)}(u) \le \sum_{u \in V} \frac{d(u)}{3} = \frac{2|E|}{3} \implies \text{Conflicts} \le \frac{|E|}{3}$$
  **Guarantees that at least $2/3$ of all interference is removed deterministically!**

### 5. Step 5: Capacity-Constrained Student-AP Matching (Hungarian Algorithm)
- **Model:** Students $S$ distributed across buildings; APs $A$ with capacity limits $C_j$.
- **Signal Quality:** Log-distance path loss RSSI (dBm) converted to positive connection utility.
- **Hungarian Formulation:** Each AP is expanded into $C_j$ virtual slots: $(a_j, 1), \dots, (a_j, C_j)$.
  Constructs an $N \times N$ bipartite matching solved via Kuhn-Munkres ($O(N^3)$), achieving the socially optimal matching while strictly respecting hardware capacities.

### 6. Bonus: Kempe Chains Dynamic Recoloring
- **Kempe's Lemma (1879):** In an $(\alpha, \beta)$-bicoloured component, swapping $\alpha \leftrightarrow \beta$ preserves colouring validity.
- **Dynamic Updates:** When an AP is added or fails, WiPlan swaps colours only along the localized $(\alpha, \beta)$ chain, freeing a channel with zero disruption to the rest of the campus.

---

## 🚀 Quick Start Guide

### 1. Launch the Interactive Web Application
```bash
python3 run.py
```
Open your browser to: **[http://localhost:8000](http://localhost:8000)**

### 2. Run the Terminal / CLI Demonstration
```bash
python3 run.py --cli
```

### 3. Run the Automated Unit Test Suite
```bash
python3 run.py --test
```

---

## 🖥️ Interactive Web Frontend Highlights

1. **Campus Network Map:**
   - Architectural building zones (Hostels, CS Labs, Central Library, Admin, Cafeteria, Quad).
   - Draggable AP nodes that dynamically re-evaluate interference edges in real time.
   - Flashing red edges for active co-channel interference.
   - Pulsing Crimson dashed loops for detected odd cycles.
   - Student nodes with dashed connection links and RSSI signal indicators.
2. **Step-by-Step Guided Navigation:**
   - Step 1: Bipartite BFS check & Odd Cycle certificate.
   - Step 2: DPLL 3-SAT solver with decision & backtrack statistics.
   - Step 3: Interactive RF Spectrum Analyzer & "Why 1, 6, 11" proof card.
   - Step 4: Local Search simulation & Monte Carlo 100-trial distribution.
   - Step 5: Student-AP Hungarian matching with capacity utilization meters.
   - Bonus: Kempe Chain bicolour swap animation.
   - Compare: Benchmark table of Greedy First-Fit vs Welsh-Powell vs DSatur vs Exact SAT vs Local Search.
3. **Built-in Presentation Mode:**
   - Full-screen slide deck with slide navigation, formulas, diagrams, and speaker notes.

---

## 📂 Project Structure

```
wifi/
├── wiplan/
│   ├── __init__.py           # Package exports
│   ├── graph.py              # AP, Student, Building, CampusGraph models
│   ├── bipartite.py          # Step 1: BFS 2-colouring & Odd Cycle extractor
│   ├── sat_solver.py         # Step 2: DPLL SAT solver from scratch & CNF reduction
│   ├── spectral.py           # Step 3: 802.11 spectrum model & Why {1,6,11} proof
│   ├── local_search.py       # Step 4: Min-conflicts local search & guarantees
│   ├── matching.py           # Step 5: Kuhn-Munkres Hungarian algorithm
│   ├── kempe.py              # Bonus: Kempe chain dynamic recoloring
│   ├── algorithms.py         # Greedy, Welsh-Powell, DSatur benchmark suite
│   ├── presets.py            # Main Campus, Auditorium, Corridor, Pentagon presets
│   └── server.py             # Zero-dependency Python HTTP API & file server
├── static/
│   ├── index.html            # Single Page Application frontend
│   ├── app.js                # Canvas map renderer & interactive workflows
│   └── styles.css            # Futuristic glassmorphism styling & animations
├── tests/
│   ├── __init__.py
│   └── test_all.py           # 10 comprehensive unit tests
├── run.py                    # Unified entrypoint (Web server, CLI, Tests)
├── presentation_guide.md     # Presentation script for viva/professors
└── README.md                 # Complete academic documentation
```
