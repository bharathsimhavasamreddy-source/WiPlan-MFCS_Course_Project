# 🎤 WiPlan: Presentation & Viva Guide

Use this guide when presenting WiPlan to professors, teaching assistants, or project evaluators.

---

## ⏱️ Recommended 10-Minute Presentation Outline

| Time | Slide / Topic | What to Say / Demonstrate |
|---|---|---|
| **0:00 - 1:30** | **Slide 1: Problem Overview** | Explain campus Wi-Fi interference in 2.4 GHz. Show how APs map to vertices, physical interference distance maps to edges, and channels map to colors. |
| **1:30 - 3:00** | **Slide 2 & Step 1: Bipartite Test** | Explain König's theorem (1936). Click "Run BFS Check" on Main Campus to show the odd cycle $C_3$ in the CS Lab. Switch preset to "Pentagon Plaza" to show $C_5$. Emphasize that the odd cycle is a *formal certificate* that 2 channels are insufficient! |
| **3:00 - 4:30** | **Slide 3 & Step 2: Exact DPLL SAT** | Explain the 3 CNF clause types (At-least-one, At-most-one, Conflict exclusion). Click "Solve DPLL SAT" to show the solver running with decisions, unit propagations, and backtracks in under 1 ms! Then switch to "Dense Auditorium" ($K_4$) to show the DPLL solver proving **UNSAT**! |
| **4:30 - 5:45** | **Slide 4 & Step 3: Why 1, 6, 11** | Walk through the interval packing math: $11 \ge 1 + 5(k - 1) \implies k \le 3$. Show the uniqueness of $\{1, 6, 11\}$ with the interactive spectrum visualizer. |
| **5:45 - 7:00** | **Slide 5 & Step 4: Local Search** | Explain what happens when a graph is dense ($\chi \ge 4$). Compare Random assignment expectation ($\mathbb{E} = |E|/3$) with the Local Search deterministic guarantee ($\le |E|/3$). Run the 100-trial Monte Carlo simulation to demonstrate that Local Search achieves superior conflict reduction! |
| **7:00 - 8:15** | **Slide 6 & Step 5: Hungarian Matching** | Show how students are assigned to APs. Explain that each AP is split into $C_j$ virtual capacity slots to convert the problem into an $N \times N$ Maximum Weight Bipartite Matching solved by Kuhn-Munkres. Point out the RSSI values and AP capacity meters. |
| **8:15 - 9:00** | **Slide 7 & Bonus: Kempe Chains** | Click "Add AP" or "Simulate Kempe Swap". Show how flipping an $(\alpha, \beta)$ Kempe chain frees a channel locally without disturbing any other APs on campus! |
| **9:00 - 10:00** | **Slide 8 & Benchmark Summary** | Show the comparison table of Greedy vs Welsh-Powell vs DSatur vs Exact DPLL SAT vs Local Search. Take questions from examiners. |

---

## 🎯 Likely Viva Questions & Model Answers

### Q1: Why not just use Greedy Colouring for everything?
> **Answer:** Greedy colouring is order-sensitive. Depending on vertex ordering, it can use significantly more channels than the chromatic number $\chi(G)$ (up to $|V|/2$ in worst-case bipartite crowns). While Welsh-Powell and DSatur improve performance using degree heuristics, only exact SAT solving (DPLL) can guarantee minimum channel usage and formally certify non-colourability (UNSAT) when 3 channels are insufficient.

### Q2: How does your DPLL SAT solver work without third-party libraries?
> **Answer:** We implemented DPLL from scratch in pure Python standard library. It encodes the graph colouring as CNF clauses and uses:
> 1. **Boolean Constraint Propagation (Unit Propagation):** Forcing single-literal clauses.
> 2. **Pure Literal Elimination:** Assigning variables that only appear in one polarity.
> 3. **MOM's Heuristic:** Choosing variables that appear most frequently in minimum-sized clauses to accelerate conflict discovery.

### Q3: Why is {1, 6, 11} unique in 2.4 GHz?
> **Answer:** Channels are spaced 5 MHz apart, but 802.11 signals have 22 MHz bandwidth. Therefore, $|c_u - c_v| \ge \lceil 22/5 \rceil = 5$. In $\{1, \dots, 11\}$, the maximum independent set of channels with spacing $\ge 5$ satisfies $11 \ge 1 + 5(k - 1) \implies 5k \le 15 \implies k \le 3$. For $k=3$, $c_1$ must be 1 and $c_3$ must be 11. Then $1 + 5 \le c_2 \le 11 - 5 \implies 6 \le c_2 \le 6 \implies c_2 = 6$. Hence, $\{1, 6, 11\}$ is unique.

### Q4: How does Local Search guarantee $\le |E|/3$ conflicts?
> **Answer:** At any local optimum, each vertex $u$ is on the channel that minimizes neighbor conflicts. By the Pigeonhole Principle, dividing its $d(u)$ neighbors across 3 channels means at most $\lfloor d(u)/3 \rfloor$ neighbors share its channel. Summing over all vertices by the Handshaking Lemma ($\sum d(u) = 2|E|$):
> $$2 \times \text{Conflicts} \le \sum_{u} \frac{d(u)}{3} = \frac{2|E|}{3} \implies \text{Conflicts} \le \frac{|E|}{3}$$

### Q5: How did you handle AP capacities in the Hungarian Algorithm?
> **Answer:** The Hungarian algorithm operates on a 1-to-1 bipartite matching. To accommodate an AP $a_j$ that can serve up to $C_j$ students, we expand $a_j$ into $C_j$ distinct virtual slots: $(a_j, 1), (a_j, 2), \dots, (a_j, C_j)$. The edge weight between student $s_i$ and each slot of $a_j$ is the received signal strength (RSSI). We then solve the $N \times N$ assignment problem in $O(N^3)$ time using Kuhn-Munkres.

---

## 🚀 Live Demo Checklist Before You Present

1. Open your terminal:
   ```bash
   cd /Users/bh4r4th/wifi
   python3 run.py
   ```
2. Open your browser: **`http://localhost:8000`**
3. Maximize the browser window for the presentation.
4. Click **"📽️ Presentation Mode"** in the top right to start the slide deck!
5. Use keyboard **`→`** and **`←`** arrows to advance slides, or close it to show live canvas dragging and real-time algorithm executions!
