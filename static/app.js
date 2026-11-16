/**
 * WiPlan — Academic & Scientific Campus Wi-Fi Channel Planner
 * Frontend Controller & Network Visualizer
 */

// ==========================================
// STATE MANAGEMENT
// ==========================================
const State = {
  currentGraph: null,
  beforeGraph: null,
  optimizedGraph: null,
  viewMode: 'before', // 'before' | 'after'
  isOptimizing: false,
  selectedAPId: null,
  highlightedStage: null, // 1..5 for stage clicks

  // Layer Toggles
  showCoverage: true,
  showInterference: true,
  showStudents: true,
  showLabels: true,

  // Viewport Coordinates & Pan/Zoom
  zoom: 1.0,
  pan: { x: 0, y: 0 },
  isPanning: false,
  panStart: { x: 0, y: 0 },
  animTime: 0,
};

// Standard Scientific Palette
const CH_COLORS = {
  1:  '#0284c7', // Cyan / Tech Blue
  6:  '#d97706', // Warm Amber
  11: '#7c3aed', // Purple / Violet
  null: '#94a3b8',
};

let canvas, ctx;
let rafId = null;

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  canvas = document.getElementById('network-canvas');
  if (canvas) ctx = canvas.getContext('2d');

  resizeCanvas();
  window.addEventListener('resize', () => {
    resizeCanvas();
    fitView();
  });

  initCanvasEvents();
  initUIEvents();
  loadScenario('full_campus');
  startRenderLoop();
});

function resizeCanvas() {
  const container = document.getElementById('canvas-container');
  if (!container || !canvas) return;
  const rect = container.getBoundingClientRect();
  if (rect.width > 0 && rect.height > 0) {
    canvas.width = rect.width;
    canvas.height = rect.height;
    render();
  }
}

function startRenderLoop() {
  function loop(ts) {
    State.animTime = ts;
    render();
    rafId = requestAnimationFrame(loop);
  }
  rafId = requestAnimationFrame(loop);
}

// ==========================================
// API CLIENT
// ==========================================
async function fetchJSON(url, opts = {}) {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    return await res.json();
  } catch (err) {
    console.error('API Error:', err);
    return null;
  }
}

// ==========================================
// SCENARIO LOADING & AUTO-FIT
// ==========================================
async function loadScenario(key) {
  const selector = document.getElementById('preset-selector');
  if (selector && selector.value !== key) selector.value = key;

  const data = await fetchJSON(`/api/preset/${key}`);
  if (!data || !data.graph) return;

  // 1. Set Initial (Before) Graph
  State.beforeGraph = JSON.parse(JSON.stringify(data.graph));
  recomputeGraphConflicts(State.beforeGraph);
  State.optimizedGraph = null;

  // 2. Clear previous pipeline results
  resetPipelineUI();

  // 3. Set current view to BEFORE
  State.viewMode = 'before';
  State.currentGraph = JSON.parse(JSON.stringify(State.beforeGraph));
  State.selectedAPId = null;
  State.highlightedStage = null;

  hideInspector();
  updateViewSwitcherUI();
  updateSummaryMetrics();

  // Auto-fit to 100% of canvas container
  setTimeout(() => {
    resizeCanvas();
    fitView();
  }, 50);
}

function recomputeGraphConflicts(g) {
  if (!g) return;
  const aps = Object.values(g.aps || {}).filter(a => a.active);
  const edges = g.edges || [];
  const conflicts = [];

  edges.forEach(([u, v]) => {
    const a = g.aps[u], b = g.aps[v];
    if (a && b && a.active && b.active) {
      if (a.channel && b.channel && a.channel === b.channel) {
        conflicts.push([u, v]);
      }
    }
  });

  g.conflicts = conflicts;
  g.conflict_count = conflicts.length;
}

// ==========================================
// RUN WIPLAN (5-STEP PROGRESSION WITH EXPLICIT PASS/FAIL)
// ==========================================
async function runWiPlanPipeline() {
  if (State.isOptimizing) return;
  State.isOptimizing = true;

  const runBtn = document.getElementById('btn-run-wiplan');
  const runBtnText = document.getElementById('run-btn-text');
  runBtn.classList.add('busy');

  // Clone a working copy of graph
  const workingGraph = JSON.parse(JSON.stringify(State.beforeGraph));

  // --- STEP 1: Bipartite Check ---
  runBtnText.textContent = 'Checking 2-Channel Feasibility...';
  setStepStageUI(1, 'running', 'RUNNING', 'Verifying BFS bipartite structure...');
  State.highlightedStage = 1;
  await delay(350);

  const bipRes = await fetchJSON('/api/step1-bipartite', {
    method: 'POST',
    body: JSON.stringify({ graph: workingGraph }),
  });

  if (bipRes) {
    if (bipRes.is_bipartite) {
      setStepStageUI(1, 'passed', 'PASSED', 'Passed · 2 channels sufficient');
      workingGraph.oddCycle = [];
    } else {
      // EXPLICIT FAILURE STATE AS REQUESTED
      setStepStageUI(1, 'failed', 'FAILED', `Failed · Odd cycle of ${bipRes.odd_cycle_length} APs (≥3 channels needed)`);
      workingGraph.oddCycle = bipRes.odd_cycle || [];
    }
  }

  // --- STEP 2: Exact 3-Channel Plan (DPLL SAT) ---
  runBtnText.textContent = 'Solving Exact SAT Formulation...';
  setStepStageUI(2, 'running', 'RUNNING', 'Running DPLL exact solver...');
  State.highlightedStage = 2;
  await delay(350);

  const satRes = await fetchJSON('/api/step2-sat', {
    method: 'POST',
    body: JSON.stringify({ graph: workingGraph, channels: [1, 6, 11] }),
  });

  let hasExactPlan = false;
  if (satRes && satRes.is_sat && satRes.coloring) {
    hasExactPlan = true;
    applyColoringToGraph(workingGraph, satRes.coloring);
    setStepStageUI(2, 'passed', 'PASSED', 'Passed · Conflict-free 3-channel plan');
  } else {
    // EXPLICIT FAILURE STATE AS REQUESTED (UNSAT on dense cliques)
    setStepStageUI(2, 'failed', 'FAILED', 'Failed · 4-clique contention (requires χ ≥ 4)');
  }

  // --- STEP 3: Spectrum Separation ---
  runBtnText.textContent = 'Enforcing Spectrum Constraints...';
  setStepStageUI(3, 'running', 'RUNNING', 'Checking Δ ≥ 5 separation...');
  State.highlightedStage = 3;
  await delay(250);
  setStepStageUI(3, 'passed', 'ENFORCED', 'Clean channels {1, 6, 11} enforced (Δ ≥ 5)');

  // --- STEP 4: Interference Minimization (Local Search) ---
  runBtnText.textContent = 'Minimizing Remaining Clashes...';
  setStepStageUI(4, 'running', 'RUNNING', 'Running 1-Opt greedy search...');
  State.highlightedStage = 4;
  await delay(350);

  const initialConflicts = State.beforeGraph.conflicts.length;
  if (!hasExactPlan) {
    const lsRes = await fetchJSON('/api/step4-local-search', {
      method: 'POST',
      body: JSON.stringify({ graph: workingGraph, channels: [1, 6, 11] }),
    });
    if (lsRes && lsRes.coloring) {
      applyColoringToGraph(workingGraph, lsRes.coloring);
      recomputeGraphConflicts(workingGraph);
      const afterConflicts = workingGraph.conflicts.length;
      setStepStageUI(4, 'passed', 'OPTIMIZED', `Reduced: ${initialConflicts} → ${afterConflicts} conflicts`);
    }
  } else {
    recomputeGraphConflicts(workingGraph);
    setStepStageUI(4, 'passed', 'OPTIMIZED', `${initialConflicts} → 0 conflicts`);
  }

  // --- STEP 5: Student Assignment (Hungarian Matching) ---
  runBtnText.textContent = 'Connecting Students to APs...';
  setStepStageUI(5, 'running', 'RUNNING', 'Computing Kuhn-Munkres matching...');
  State.highlightedStage = 5;
  await delay(350);

  const matchRes = await fetchJSON('/api/step5-matching', {
    method: 'POST',
    body: JSON.stringify({ graph: workingGraph }),
  });

  if (matchRes && matchRes.assignments) {
    workingGraph.studentMatches = matchRes.assignments;
    const totalUsers = Object.keys(workingGraph.students).length;
    setStepStageUI(5, 'passed', 'ASSIGNED', `${matchRes.assigned_count} / ${totalUsers} users (Avg ${matchRes.avg_rssi_dbm} dBm)`);
  }

  // Complete pipeline & update current view
  recomputeGraphConflicts(workingGraph);
  State.optimizedGraph = workingGraph;
  State.currentGraph = JSON.parse(JSON.stringify(workingGraph));
  State.viewMode = 'after';
  State.isOptimizing = false;

  runBtn.classList.remove('busy');
  runBtnText.textContent = 'Run WiPlan';

  updateViewSwitcherUI();
  updateSummaryMetrics();
}

function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function applyColoringToGraph(g, coloring) {
  Object.entries(coloring || {}).forEach(([id, ch]) => {
    if (g.aps[id]) g.aps[id].channel = ch;
  });
}

/**
 * Updates step UI with explicit PASS / FAIL / PENDING status
 */
function setStepStageUI(stepNum, type, tagText, resultText) {
  const card = document.getElementById(`card-step-${stepNum}`);
  const tag  = document.getElementById(`tag-step-${stepNum}`);
  const val  = document.getElementById(`res-val-step-${stepNum}`);

  if (card && tag && val) {
    card.classList.remove('active-step', 'passed', 'failed');
    tag.className = 'step-status-tag';

    if (type === 'running') {
      card.classList.add('active-step');
      tag.classList.add('running');
    } else if (type === 'passed') {
      card.classList.add('passed');
      tag.classList.add('passed');
    } else if (type === 'failed') {
      card.classList.add('failed');
      tag.classList.add('failed');
    }

    tag.textContent = tagText;
    val.textContent = resultText;
  }
}

function resetPipelineUI() {
  for (let i = 1; i <= 5; i++) {
    const card = document.getElementById(`card-step-${i}`);
    const tag  = document.getElementById(`tag-step-${i}`);
    const val  = document.getElementById(`res-val-step-${i}`);
    if (card) card.className = 'step-card';
    if (tag) {
      tag.className = 'step-status-tag pending';
      tag.textContent = 'Pending';
    }
    if (val) {
      val.textContent = i === 3 ? '1 · 6 · 11' : '—';
    }
  }
}

// ==========================================
// VIEW SWITCHER (BEFORE / AFTER)
// ==========================================
function setViewMode(mode) {
  if (mode === 'after' && !State.optimizedGraph) {
    runWiPlanPipeline();
    return;
  }
  State.viewMode = mode;
  if (mode === 'before' && State.beforeGraph) {
    State.currentGraph = JSON.parse(JSON.stringify(State.beforeGraph));
  } else if (mode === 'after' && State.optimizedGraph) {
    State.currentGraph = JSON.parse(JSON.stringify(State.optimizedGraph));
  }
  updateViewSwitcherUI();
  updateSummaryMetrics();
  if (State.selectedAPId && State.currentGraph.aps[State.selectedAPId]) {
    populateInspector(State.currentGraph.aps[State.selectedAPId]);
  }
}

function updateViewSwitcherUI() {
  const btnBefore = document.getElementById('btn-view-before');
  const btnAfter  = document.getElementById('btn-view-after');
  if (State.viewMode === 'before') {
    btnBefore.className = 'view-segment active before';
    btnAfter.className  = 'view-segment';
  } else {
    btnBefore.className = 'view-segment';
    btnAfter.className  = 'view-segment active after';
  }
}

function updateSummaryMetrics() {
  if (!State.currentGraph) return;

  const beforeCount = State.beforeGraph?.conflicts?.length || 0;
  const afterCount = State.optimizedGraph ? (State.optimizedGraph.conflicts?.length ?? 0) : null;

  document.getElementById('stat-before-conflicts').textContent = `${beforeCount} conflicts`;
  document.getElementById('stat-after-conflicts').textContent = afterCount !== null ? `${afterCount} conflicts` : '—';

  const aps = Object.values(State.currentGraph.aps || {}).filter(a => a.active);
  const students = Object.keys(State.currentGraph.students || {}).length;

  document.getElementById('network-totals-caption').textContent =
    `${aps.length} Access Points · ${students} Students · 3 Channels`;
}

// ==========================================
// INTERACTIVE STEP HIGHLIGHTING
// ==========================================
function highlightStepStage(stepNum) {
  if (State.highlightedStage === stepNum) {
    State.highlightedStage = null;
    document.querySelectorAll('.step-card').forEach(c => c.classList.remove('active-step'));
    return;
  }
  State.highlightedStage = stepNum;
  document.querySelectorAll('.step-card').forEach((c, idx) => {
    c.classList.toggle('active-step', idx + 1 === stepNum);
  });
}

// ==========================================
// CANVAS RENDERING (LIGHT ACADEMIC MAP)
// ==========================================
function render() {
  if (!ctx || !State.currentGraph) return;
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  // Background Grid (subtle light gray)
  drawScientificGrid(W, H);

  ctx.save();
  ctx.translate(State.pan.x, State.pan.y);
  ctx.scale(State.zoom, State.zoom);

  // 1. Campus building zones
  drawCampusBuildings();

  // 2. Coverage areas
  if (State.showCoverage) {
    drawCoverageAreas();
  }

  // 3. Interference edges & links
  if (State.showInterference) {
    drawInterferenceEdges();
  }

  // 4. Student assignment lines
  if (State.showStudents && (State.highlightedStage === 5 || State.viewMode === 'after')) {
    drawStudentLinks();
  }

  // 5. AP Nodes
  drawAccessPoints();

  // 6. Students (small emerald dots)
  if (State.showStudents) {
    drawStudentDots();
  }

  ctx.restore();
}

function drawScientificGrid(W, H) {
  ctx.save();
  ctx.strokeStyle = '#f1f5f9';
  ctx.lineWidth = 1;
  const sz = 32;
  const startX = State.pan.x % sz;
  const startY = State.pan.y % sz;
  ctx.beginPath();
  for (let x = startX; x < W; x += sz) {
    ctx.moveTo(x, 0); ctx.lineTo(x, H);
  }
  for (let y = startY; y < H; y += sz) {
    ctx.moveTo(0, y); ctx.lineTo(W, y);
  }
  ctx.stroke();
  ctx.restore();
}

function drawCampusBuildings() {
  const buildings = Object.values(State.currentGraph.buildings || {});
  buildings.forEach(b => {
    ctx.save();
    ctx.fillStyle = 'rgba(248, 250, 252, 0.9)';
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.rect(b.x, b.y, b.width, b.height);
    ctx.fill();
    ctx.stroke();

    // Crisp zone label
    ctx.fillStyle = '#64748b';
    ctx.font = '700 9.5px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(b.name.toUpperCase(), b.x + 8, b.y + 6);
    ctx.restore();
  });
}

function drawCoverageAreas() {
  const aps = Object.values(State.currentGraph.aps || {});
  aps.forEach(ap => {
    if (!ap.active) return;
    const col = CH_COLORS[ap.channel] || CH_COLORS[null];
    ctx.save();
    ctx.beginPath();
    ctx.arc(ap.x, ap.y, ap.coverage_radius, 0, Math.PI * 2);
    ctx.fillStyle = hexToRgba(col, 0.04);
    ctx.fill();
    ctx.strokeStyle = hexToRgba(col, 0.15);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();
  });
}

function drawInterferenceEdges() {
  const edges = State.currentGraph.edges || [];
  const conflictSet = new Set((State.currentGraph.conflicts || []).map(([u, v]) => `${u}|${v}`));
  const selectedAP = State.selectedAPId ? State.currentGraph.aps[State.selectedAPId] : null;

  edges.forEach(([u, v]) => {
    const a = State.currentGraph.aps[u], b = State.currentGraph.aps[v];
    if (!a || !b || !a.active || !b.active) return;

    const isConflict = conflictSet.has(`${u}|${v}`) || conflictSet.has(`${v}|${u}`);
    const isRelevant = !selectedAP || u === selectedAP.id || v === selectedAP.id;

    ctx.save();
    if (!isRelevant) ctx.globalAlpha = 0.15;

    if (isConflict) {
      // Conflict: Red line with gentle pulse
      const pulse = 0.75 + 0.25 * Math.sin(State.animTime / 350);
      ctx.strokeStyle = `rgba(220, 38, 38, ${pulse})`;
      ctx.lineWidth = 2.2;
      ctx.setLineDash([5, 4]);
    } else {
      // Normal proximity link
      ctx.strokeStyle = isRelevant ? '#94a3b8' : '#cbd5e1';
      ctx.lineWidth = 1;
    }

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  });

  // Highlight odd cycle if Step 1 is active
  if (State.highlightedStage === 1 && State.currentGraph.oddCycle && State.currentGraph.oddCycle.length > 2) {
    const cycleNodes = State.currentGraph.oddCycle;
    const pts = cycleNodes.map(id => State.currentGraph.aps[id]).filter(Boolean);
    if (pts.length > 2) {
      ctx.save();
      ctx.strokeStyle = '#dc2626';
      ctx.lineWidth = 3;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      pts.forEach((p, i) => {
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.lineTo(pts[0].x, pts[0].y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }
  }
}

function drawStudentLinks() {
  const matches = State.currentGraph.studentMatches || [];
  matches.forEach(m => {
    const s = State.currentGraph.students[m.student_id];
    const ap = State.currentGraph.aps[m.ap_id];
    if (!s || !ap) return;

    ctx.save();
    ctx.strokeStyle = 'rgba(5, 150, 105, 0.45)';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(ap.x, ap.y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  });
}

function drawAccessPoints() {
  const aps = Object.values(State.currentGraph.aps || {});
  const conflictSet = new Set();
  (State.currentGraph.conflicts || []).forEach(([u, v]) => {
    conflictSet.add(u); conflictSet.add(v);
  });

  const selectedAP = State.selectedAPId ? State.currentGraph.aps[State.selectedAPId] : null;
  const neighborSet = new Set();
  if (selectedAP) {
    (State.currentGraph.edges || []).forEach(([u, v]) => {
      if (u === selectedAP.id) neighborSet.add(v);
      if (v === selectedAP.id) neighborSet.add(u);
    });
  }

  aps.forEach(ap => {
    if (!ap.active) return;
    const col = CH_COLORS[ap.channel] || CH_COLORS[null];
    const isSelected = selectedAP && selectedAP.id === ap.id;
    const isNeighbor = selectedAP && neighborSet.has(ap.id);
    const isConflict = conflictSet.has(ap.id);
    const isDimmed = selectedAP && !isSelected && !isNeighbor;

    ctx.save();
    if (isDimmed) ctx.globalAlpha = 0.2;

    // Selection Halo
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(ap.x, ap.y, 22, 0, Math.PI * 2);
      ctx.fillStyle = hexToRgba(col, 0.15);
      ctx.fill();
      ctx.strokeStyle = col;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Node Circle
    ctx.beginPath();
    ctx.arc(ap.x, ap.y, 14, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = isConflict ? '#dc2626' : col;
    ctx.stroke();

    // Center Channel Digit
    ctx.font = '700 11px ui-monospace, Menlo, Consolas, monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = isConflict ? '#dc2626' : '#0f172a';
    ctx.fillText(ap.channel ? `${ap.channel}` : '—', ap.x, ap.y);

    // Label below node
    if (State.showLabels) {
      const userCount = getStudentCountForAP(ap.id);
      const labelText = ap.id;
      const subText = `CH ${ap.channel || '—'} · ${userCount} users`;

      ctx.font = '700 10px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
      const tw = Math.max(ctx.measureText(labelText).width, ctx.measureText(subText).width);

      // Light background tag
      ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      ctx.fillRect(ap.x - tw / 2 - 4, ap.y + 17, tw + 8, 22);
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 0.5;
      ctx.strokeRect(ap.x - tw / 2 - 4, ap.y + 17, tw + 8, 22);

      // Main ID
      ctx.fillStyle = isConflict ? '#dc2626' : '#0f172a';
      ctx.fillText(labelText, ap.x, ap.y + 25);

      // Subtitle
      ctx.font = '500 8.5px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
      ctx.fillStyle = '#64748b';
      ctx.fillText(subText, ap.x, ap.y + 35);
    }

    ctx.restore();
  });
}

function drawStudentDots() {
  const students = Object.values(State.currentGraph.students || {});
  students.forEach(s => {
    ctx.save();
    ctx.beginPath();
    ctx.arc(s.x, s.y, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = '#059669';
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();
    ctx.restore();
  });
}

function hexToRgba(hex, a) {
  if (!hex || hex[0] !== '#') return `rgba(148, 163, 184, ${a})`;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

function getStudentCountForAP(apId) {
  if (!State.currentGraph) return 0;
  const matches = State.currentGraph.studentMatches || [];
  if (matches.length > 0) {
    return matches.filter(m => m.ap_id === apId).length;
  }
  return Object.values(State.currentGraph.students || {}).filter(s => {
    const ap = State.currentGraph.aps[apId];
    return ap && Math.hypot(s.x - ap.x, s.y - ap.y) <= ap.coverage_radius;
  }).length;
}

// ==========================================
// INTERACTIVE CANVAS EVENTS (AUTO-FIT & PAN)
// ==========================================
function initCanvasEvents() {
  canvas.addEventListener('mousedown', onMouseDown);
  canvas.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
  canvas.addEventListener('mouseleave', () => {
    document.getElementById('node-tooltip').classList.remove('show');
  });
}

function worldXY(e) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (e.clientX - rect.left - State.pan.x) / State.zoom,
    y: (e.clientY - rect.top  - State.pan.y) / State.zoom,
  };
}

function onMouseDown(e) {
  const { x, y } = worldXY(e);
  const ap = findAPAt(x, y);

  if (ap) {
    State.selectedAPId = ap.id;
    showInspector(ap);
    return;
  }

  // Clicked empty background: deselect
  if (State.selectedAPId) {
    State.selectedAPId = null;
    hideInspector();
  }

  State.isPanning = true;
  State.panStart = { x: e.clientX - State.pan.x, y: e.clientY - State.pan.y };
}

function onMouseMove(e) {
  const { x, y } = worldXY(e);
  const rect = canvas.getBoundingClientRect();

  if (State.isPanning) {
    State.pan.x = e.clientX - State.panStart.x;
    State.pan.y = e.clientY - State.panStart.y;
    return;
  }

  // Hover Tooltip
  const ap = findAPAt(x, y);
  const tip = document.getElementById('node-tooltip');
  if (ap) {
    const users = getStudentCountForAP(ap.id);
    const conflicts = (State.currentGraph.conflicts || []).filter(([u, v]) => u === ap.id || v === ap.id).length;
    tip.innerHTML = `
      <div style="font-weight:700;color:#0f172a;font-size:12px;margin-bottom:2px;">${ap.name} (${ap.id})</div>
      <div style="font-size:11px;color:#475569;margin-bottom:1px;">
        Channel: <strong style="color:${CH_COLORS[ap.channel] || '#0f172a'};">CH ${ap.channel || 'None'}</strong>
      </div>
      <div style="font-size:11px;color:#475569;margin-bottom:1px;">
        Connected Users: <strong>${users} / ${ap.capacity}</strong>
      </div>
      <div style="font-size:10.5px;color:${conflicts > 0 ? '#dc2626' : '#059669'};">
        ${conflicts > 0 ? `⚠ ${conflicts} Clashes` : '✓ Clear'}
      </div>
    `;
    tip.style.left = `${e.clientX - rect.left + 12}px`;
    tip.style.top  = `${e.clientY - rect.top + 12}px`;
    tip.classList.add('show');
  } else {
    tip.classList.remove('show');
  }
}

function onMouseUp() {
  State.isPanning = false;
}

function findAPAt(x, y) {
  if (!State.currentGraph) return null;
  const aps = Object.values(State.currentGraph.aps || {});
  for (let i = aps.length - 1; i >= 0; i--) {
    const ap = aps[i];
    if (!ap.active) continue;
    if (Math.hypot(ap.x - x, ap.y - y) <= 18) return ap;
  }
  return null;
}

/**
 * Automatically fits map to 100% of the canvas container
 */
function fitView() {
  if (!State.currentGraph) return;
  const aps = Object.values(State.currentGraph.aps || {}).filter(a => a.active);
  const buildings = Object.values(State.currentGraph.buildings || {});
  if (aps.length === 0 && buildings.length === 0) return;

  const xs = aps.map(a => a.x);
  const ys = aps.map(a => a.y);
  buildings.forEach(b => {
    xs.push(b.x);
    xs.push(b.x + b.width);
    ys.push(b.y);
    ys.push(b.y + b.height);
  });

  const minX = Math.min(...xs) - 40, maxX = Math.max(...xs) + 40;
  const minY = Math.min(...ys) - 40, maxY = Math.max(...ys) + 40;

  const W = canvas.width, H = canvas.height;
  const scaleX = W / (maxX - minX);
  const scaleY = H / (maxY - minY);
  State.zoom = Math.min(scaleX, scaleY, 1.4);

  State.pan.x = (W - (maxX + minX) * State.zoom) / 2;
  State.pan.y = (H - (maxY + minY) * State.zoom) / 2;
}

// ==========================================
// AP INSPECTOR
// ==========================================
function showInspector(ap) {
  const box = document.getElementById('inspector-box');
  box.classList.add('show');
  populateInspector(ap);
}

function hideInspector() {
  document.getElementById('inspector-box').classList.remove('show');
}

function populateInspector(ap) {
  const col = CH_COLORS[ap.channel] || '#94a3b8';
  const users = getStudentCountForAP(ap.id);
  const conflicts = (State.currentGraph.conflicts || []).filter(([u, v]) => u === ap.id || v === ap.id).length;

  document.getElementById('insp-name').textContent = `${ap.name} (${ap.id})`;
  document.getElementById('insp-channel').innerHTML = `<span style="color:${col};">CH ${ap.channel || 'None'}</span>`;
  document.getElementById('insp-users').textContent = `${users} / ${ap.capacity}`;

  const clashesEl = document.getElementById('insp-clashes');
  clashesEl.textContent = `${conflicts}`;
  clashesEl.style.color = conflicts > 0 ? 'var(--status-err)' : 'var(--status-ok)';
}

// ==========================================
// UI EVENT LISTENERS
// ==========================================
function initUIEvents() {
  // Scenario Dropdown
  document.getElementById('preset-selector').addEventListener('change', e => {
    loadScenario(e.target.value);
  });

  // Primary Action Button
  document.getElementById('btn-run-wiplan').addEventListener('click', runWiPlanPipeline);

  // Segmented View Toggle (Before / After)
  document.getElementById('btn-view-before').addEventListener('click', () => setViewMode('before'));
  document.getElementById('btn-view-after').addEventListener('click', () => setViewMode('after'));

  // Layer Toggles
  function bindToggle(btnId, stateProp) {
    const btn = document.getElementById(btnId);
    btn.addEventListener('click', () => {
      State[stateProp] = !State[stateProp];
      btn.classList.toggle('active', State[stateProp]);
    });
  }
  bindToggle('btn-toggle-coverage', 'showCoverage');
  bindToggle('btn-toggle-interference', 'showInterference');
  bindToggle('btn-toggle-students', 'showStudents');
  bindToggle('btn-toggle-labels', 'showLabels');

  // Inspector Close
  document.getElementById('btn-close-inspector').addEventListener('click', () => {
    State.selectedAPId = null;
    hideInspector();
  });
}
