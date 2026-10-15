const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = { time: 54, playing: false, sensorFault: false, uf: 13.4, duration: 4, bloodFlow: 320, selected: 'optimized', role: 'nephrologist' };
const API_URL = window.NADI_HD_API_URL || window.NEPHRON_API_URL || 'http://127.0.0.1:8000';
const scenarios = [
  { id: 'current', name: 'Planned prescription', note: '13.4 UF · 4.0 h', risk: 72, ktv: 1.31, urr: 68, x: 219, y: 119 },
  { id: 'optimized', name: 'Stability optimized', note: '9.2 UF · 4.75 h', risk: 24, ktv: 1.34, urr: 70, x: 238, y: 50 },
  { id: 'balanced', name: 'Balanced alternative', note: '10.4 UF · 4.5 h', risk: 33, ktv: 1.38, urr: 72, x: 258, y: 65 }
];

function riskFromSettings() {
  const ufEffect = (state.uf - 8.2) * 8.4;
  const durationEffect = (state.duration - 4) * -13;
  const flowEffect = Math.abs(state.bloodFlow - 320) * .025;
  return Math.max(12, Math.min(91, Math.round(28 + ufEffect + durationEffect + flowEffect)));
}

function ktvFromSettings() {
  const flow = state.bloodFlow / 320;
  const time = state.duration / 4;
  return Math.max(.7, Math.min(1.8, 1.31 * Math.pow(flow, .42) * Math.pow(time, .78)));
}

function setRangeFill(input) {
  const value = ((input.value - input.min) / (input.max - input.min)) * 100;
  input.style.setProperty('--range', `${value}%`);
}

function bpSeries(risk = riskFromSettings()) {
  const points = [];
  const severity = (risk - 18) / 74;
  for (let t = 0; t <= 240; t += 8) {
    const baseline = 132 - t * .055;
    const dip = Math.exp(-Math.pow((t - 145) / 43, 2)) * (8 + severity * 30);
    const ripple = Math.sin(t / 19) * 1.7;
    points.push({ t, bp: baseline - dip + ripple });
  }
  return points;
}

function pathFor(points, offset = 0) {
  return points.map((p, i) => `${i ? 'L' : 'M'} ${48 + p.t / 240 * 660} ${212 - ((p.bp + offset) - 80) / 60 * 190}`).join(' ');
}

function renderChart(risk = riskFromSettings()) {
  const points = bpSeries(risk);
  const currentIndex = Math.floor(state.time / 8);
  const observed = points.slice(0, currentIndex + 1);
  $('#bp-path').setAttribute('d', pathFor(points));
  $('#observed-path').setAttribute('d', pathFor(observed));
  const upper = points.map(p => ({ ...p, bp: p.bp + (state.sensorFault ? 9 : 5) }));
  const lower = [...points].reverse().map(p => ({ ...p, bp: p.bp - (state.sensorFault ? 9 : 5) }));
  $('#confidence-area').setAttribute('d', `${pathFor(upper)} ${pathFor(lower).replace(/^M/, 'L')} Z`);
  const now = points[Math.min(currentIndex, points.length - 1)];
  const x = 48 + state.time / 240 * 660;
  const y = 212 - (now.bp - 80) / 60 * 190;
  $('#playhead').setAttribute('x1', x); $('#playhead').setAttribute('x2', x);
  $('#playhead-dot').setAttribute('cx', x); $('#playhead-dot').setAttribute('cy', y);
  $('#live-bp').innerHTML = `${Math.round(now.bp)} <small>mmHg</small>`;
}

function renderGrid() {
  $('#bp-chart .grid-lines').innerHTML = [22, 85, 148, 211].map(y => `<path d="M48 ${y}H708"/>`).join('');
}

function renderTime() {
  const h = Math.floor(state.time / 60).toString().padStart(2, '0');
  const m = Math.round(state.time % 60).toString().padStart(2, '0');
  $('#time-value').textContent = `${h}:${m} / 04:00`;
  $('#time-scrubber').value = state.time;
  $('#plasma-value').textContent = `−${(state.time / 11.25).toFixed(1)}%`;
  $('#uf-removed').textContent = `${(state.uf * 64.8 * state.time / 60000).toFixed(2)} L`;
  $('#cardiac-output').textContent = `${Math.max(3.1, 4.7 - state.time * .009).toFixed(1)} L/min`;
  renderChart();
}

function renderScenarios() {
  $('#scenario-points').innerHTML = scenarios.map(s => `<circle class="scenario-point ${s.id} ${state.selected === s.id ? 'optimal' : ''}" data-scenario="${s.id}" cx="${s.x}" cy="${s.y}" r="6"><title>${s.name}: ${s.risk}% risk</title></circle>`).join('');
  $('#scenario-list').innerHTML = scenarios.map(s => `<button class="scenario-item ${s.id} ${state.selected === s.id ? 'selected' : ''}" data-scenario="${s.id}"><i></i><div><b>${s.name}</b><span>${s.note} · Kt/V ${s.ktv.toFixed(2)}</span></div><strong>${s.risk}%</strong></button>`).join('');
  $$('[data-scenario]').forEach(el => el.addEventListener('click', () => selectScenario(el.dataset.scenario)));
}

function selectScenario(id) {
  state.selected = id;
  const scenario = scenarios.find(s => s.id === id);
  if (id === 'optimized') { state.uf = 9.2; state.duration = 4.75; state.bloodFlow = 330; }
  if (id === 'balanced') { state.uf = 10.4; state.duration = 4.5; state.bloodFlow = 350; }
  if (id === 'current') { state.uf = 13.4; state.duration = 4; state.bloodFlow = 320; }
  syncControls();
  updateResults(scenario.risk, scenario.ktv, scenario.urr);
  renderScenarios();
  showToast('Future selected', `${scenario.name} loaded into the twin`);
}

function syncControls() {
  $('#uf-rate').value = state.uf; $('#duration').value = state.duration; $('#blood-flow').value = state.bloodFlow;
  $('#uf-output').innerHTML = `${state.uf.toFixed(1)} <small>mL/kg/h</small>`;
  $('#duration-output').textContent = `${state.duration.toFixed(2).replace(/0$/, '')} h`;
  $('#blood-output').textContent = state.bloodFlow;
  $$('input[type=range]').forEach(setRangeFill);
}

function updateResults(forcedRisk, forcedKtv, forcedUrr) {
  const risk = forcedRisk ?? riskFromSettings();
  const ktv = forcedKtv ?? ktvFromSettings();
  const urr = forcedUrr ?? Math.round((1 - Math.exp(-ktv * .92)) * 100);
  $('#risk-score').textContent = risk;
  $('#risk-time').textContent = risk > 55 ? '47 min' : risk > 30 ? '86 min' : 'low likelihood';
  $('#ktv-value').textContent = ktv.toFixed(2);
  $('#urr-value').textContent = `${urr}%`;
  $('#fluid-target-text').textContent = `${(state.uf * 64.8 * state.duration / 1000).toFixed(1)} L / ${state.duration.toFixed(1)} h`;
  $('#fluid-bar').style.width = `${Math.min(100, state.uf / 14 * 100)}%`;
  $('#risk-explanation').textContent = risk > 55
    ? `The planned UF rate exceeds Meera's learned tolerance envelope while systolic pressure is falling faster than her 18-session baseline.`
    : `This profile remains inside Meera's personalized tolerance envelope while preserving the modeled adequacy target.`;
  renderChart(risk);
}

function simulate() {
  const button = $('#simulate-button');
  button.classList.add('running');
  button.innerHTML = '<span>Simulating physiological futures…</span><small>physics + learned response</small>';
  $('#simulation-status').innerHTML = '<span></span><b>24 futures running</b><small>constraints active</small>';
  setTimeout(() => {
    const risk = riskFromSettings();
    const ktv = ktvFromSettings();
    updateResults(risk, ktv);
    button.classList.remove('running');
    button.innerHTML = '<span>Run parallel futures</span><small>24 scenarios · 0.8 sec</small>';
    $('#simulation-status').innerHTML = '<span></span><b>24 futures completed</b><small>7 rejected · 3 retained</small>';
    scenarios[0].risk = risk; scenarios[0].ktv = ktv; scenarios[0].note = `${state.uf.toFixed(1)} UF · ${state.duration.toFixed(2)} h`;
    state.selected = 'current'; renderScenarios();
    showToast('Simulation complete', '3 clinician-reviewable futures found');
  }, 900);
}

function showToast(title, detail) {
  const toast = $('#toast');
  $('b', toast).textContent = title; $('small', toast).textContent = detail;
  toast.classList.add('show'); clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 3000);
}

function openDrawer() {
  $('#decision-drawer').classList.add('open'); $('#drawer-backdrop').classList.add('open'); $('#decision-drawer').setAttribute('aria-hidden', 'false');
}
function closeDrawer() {
  $('#decision-drawer').classList.remove('open'); $('#drawer-backdrop').classList.remove('open'); $('#decision-drawer').setAttribute('aria-hidden', 'true');
}
function openModal(content) {
  $('#modal-content').innerHTML = content; $('#modal').classList.add('open'); $('#modal').setAttribute('aria-hidden', 'false');
}
function closeModal() { $('#modal').classList.remove('open'); $('#modal').setAttribute('aria-hidden', 'true'); }

function systemsModal() {
  openModal(`<span class="eyebrow">LONGITUDINAL TWIN</span><h2>Multisystem interdependence</h2><p>This map separates measured signals from modeled trends. Selective connections help clinicians inspect how renal failure, dialysis, anemia, mineral balance, and cardiovascular load interact over time.</p><div class="system-map"><div class="system-node k"><div><b>Kidney</b><small>ESKD · origin</small></div></div><div class="system-node h"><div><b>Heart</b><small>LVH burden +18%</small></div></div><div class="system-node b"><div><b>Blood</b><small>Hb 9.4 g/dL</small></div></div><div class="system-node bo"><div><b>Bone</b><small>PTH 486 pg/mL</small></div></div><div class="system-node d"><div><b>Dialysis</b><small>Kt/V 1.31</small></div></div></div>`);
}

function validationModal() {
  openModal(`<span class="eyebrow">FROZEN MODEL CARD / HEMOBP V3 TEST PARTITION</span><h2>Validation, without inflated claims.</h2><p>These are the repository's untouched patient-level test results for the pre-session BP-proxy model. Warning lead time has not yet been measured and is not estimated here.</p><div class="modal-grid"><div class="modal-metric"><span>AUROC</span><b>0.862</b></div><div class="modal-metric"><span>AUPRC</span><b>0.329</b></div><div class="modal-metric"><span>WARNING LEAD TIME</span><b>Not measured</b></div><div class="modal-metric"><span>SENSITIVITY</span><b>83.1%</b></div><div class="modal-metric"><span>FALSE ALERTS / 100</span><b>24.54</b></div><div class="modal-metric"><span>BRIER SCORE</span><b>0.048</b></div></div><div class="safety-note" style="margin-top:16px"><b>Prototype limitation</b><p>Single-centre retrospective Taiwanese cohort; the target is a BP-only proxy because symptoms and interventions are unavailable. Precision is 17.1%, so this model must not drive a disruptive clinical alarm. Prospective multicentre validation is required.</p></div>`);
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $('#theme-toggle').setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
  $('#theme-toggle span').textContent = theme === 'dark' ? '☼' : '◐';
  localStorage.setItem('nadi-hd-theme', theme);
}

function toggleRole() {
  state.role = state.role === 'nephrologist' ? 'nurse' : 'nephrologist';
  document.body.dataset.role = state.role;
  $('#role-toggle').textContent = state.role === 'nurse' ? 'Nephrologist view' : 'Nurse view';
  $('#role-toggle').setAttribute('aria-pressed', state.role === 'nurse' ? 'true' : 'false');
  localStorage.setItem('nadi-hd-role', state.role);
  showToast(`${state.role === 'nurse' ? 'Nurse' : 'Nephrologist'} view`, state.role === 'nurse' ? 'Immediate session signals prioritized' : 'Full planning evidence restored');
}

function aboutModal() {
  openModal(`<span class="eyebrow">NADI—HD</span><h2>Test tomorrow's dialysis, today.</h2><p>NADI-HD is a patient-specific hemodialysis rehearsal system that fuses historical context with live session signals. Its hybrid twin models clearance and hemodynamic response, forecasts instability, and compares constrained counterfactual prescriptions for clinician review.</p><div class="modal-grid"><div class="modal-metric"><span>TWIN LAYERS</span><b>4</b></div><div class="modal-metric"><span>STREAMS</span><b>10</b></div><div class="modal-metric"><span>FUTURES / RUN</span><b>24</b></div></div>`);
}

function sensorFault() {
  state.sensorFault = !state.sensorFault; document.body.classList.toggle('sensor-fault', state.sensorFault);
  $('#quality-value').textContent = state.sensorFault ? '8 / 10 streams' : '9 / 10 streams';
  renderChart();
  showToast(state.sensorFault ? 'BP stream delayed' : 'BP stream restored', state.sensorFault ? 'Confidence widened · conservative mode active' : 'Twin confidence returned to baseline');
}

async function hydrateFromApi() {
  const status = $('#api-status');
  try {
    const response = await fetch(`${API_URL}/api/v1/demo`, {
      signal: AbortSignal.timeout(1800)
    });
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const demo = await response.json();
    const apiForecast = demo.forecast;
    const apiScenarios = demo.parallel_futures.filter(item => item.feasible).slice(0, 3);
    status.textContent = 'LIVE TWIN API';
    status.previousElementSibling.classList.add('connected');
    if (apiForecast?.adequacy) {
      $('#ktv-value').textContent = Number(apiForecast.adequacy.sp_kt_v).toFixed(2);
      $('#urr-value').textContent = `${Math.round(apiForecast.adequacy.urr_pct)}%`;
    }
    apiScenarios.forEach((candidate, index) => {
      if (!scenarios[index]) return;
      scenarios[index].name = candidate.candidate_id.replaceAll('-', ' ');
      scenarios[index].risk = Math.round(candidate.forecast.peak_idh_risk * 100);
      scenarios[index].ktv = candidate.forecast.adequacy.sp_kt_v;
      scenarios[index].note = `${candidate.prescription.duration_minutes} min · ${candidate.prescription.blood_flow_ml_min} Qb`;
    });
    if (apiScenarios.length) renderScenarios();
  } catch {
    try {
      const fallback = await fetch('./demo-fixture.json');
      if (!fallback.ok) throw new Error('Fixture unavailable');
      const demo = await fallback.json();
      const apiScenarios = demo.parallel_futures.filter(item => item.feasible).slice(0, 3);
      apiScenarios.forEach((candidate, index) => {
        if (!scenarios[index]) return;
        scenarios[index].name = candidate.candidate_id.replaceAll('-', ' ');
        scenarios[index].risk = Math.round(candidate.forecast.peak_idh_risk * 100);
        scenarios[index].ktv = candidate.forecast.adequacy.sp_kt_v;
      });
      renderScenarios();
      status.textContent = 'VERIFIED OFFLINE FIXTURE';
      status.title = 'Deterministic fixture generated from the NADI-HD API';
    } catch {
      status.textContent = 'LOCAL DEMO ONLY';
      status.title = 'Static fallback values are active';
    }
  }
}

$('#uf-rate').addEventListener('input', e => { state.uf = +e.target.value; state.selected = ''; syncControls(); updateResults(); });
$('#duration').addEventListener('input', e => { state.duration = +e.target.value; state.selected = ''; syncControls(); updateResults(); });
$('#blood-flow').addEventListener('input', e => { state.bloodFlow = +e.target.value; state.selected = ''; syncControls(); updateResults(); });
$('#time-scrubber').addEventListener('input', e => { state.time = +e.target.value; renderTime(); });
$('#play-button').addEventListener('click', () => {
  state.playing = !state.playing; $('#play-button span').textContent = state.playing ? '❚❚' : '▶';
  if (state.playing) play();
});
function play() { if (!state.playing) return; state.time = state.time >= 240 ? 0 : state.time + 2; renderTime(); setTimeout(play, 80); }
$('#simulate-button').addEventListener('click', simulate);
$('#open-trace').addEventListener('click', openDrawer); $('#explain-button').addEventListener('click', openDrawer);
$('#close-drawer').addEventListener('click', closeDrawer); $('#drawer-backdrop').addEventListener('click', closeDrawer);
$('#modal-close').addEventListener('click', closeModal); $('#modal').addEventListener('click', e => { if (e.target === $('#modal')) closeModal(); });
$('#toggle-uncertainty').addEventListener('click', sensorFault); $('#view-systems').addEventListener('click', systemsModal); $('#open-about').addEventListener('click', aboutModal);
$('#theme-toggle').addEventListener('click', () => applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light'));
$('#role-toggle').addEventListener('click', toggleRole);
$('#expand-frontier').addEventListener('click', () => openModal(`<span class="eyebrow">COUNTERFACTUAL SEARCH</span><h2>Safety–clearance frontier</h2><p>Each point represents a simulated prescription. The frontier retains scenarios that improve cardiovascular stability without violating the modeled adequacy constraint.</p><div class="modal-grid"><div class="modal-metric"><span>SIMULATED</span><b>24</b></div><div class="modal-metric"><span>REJECTED</span><b>7</b></div><div class="modal-metric"><span>RETAINED</span><b>3</b></div></div>`));
$$('.rail-button[data-view]').forEach(button => button.addEventListener('click', () => {
  $$('.rail-button').forEach(b => b.classList.remove('active')); button.classList.add('active');
  if (button.dataset.view === 'systems') systemsModal();
  if (button.dataset.view === 'validation') validationModal();
  if (button.dataset.view === 'history') showToast('Session memory', '18 prior sessions loaded into the twin');
}));
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeDrawer(); closeModal(); } });

applyTheme(localStorage.getItem('nadi-hd-theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'));
state.role = localStorage.getItem('nadi-hd-role') === 'nurse' ? 'nurse' : 'nephrologist';
document.body.dataset.role = state.role;
$('#role-toggle').textContent = state.role === 'nurse' ? 'Nephrologist view' : 'Nurse view';
$('#role-toggle').setAttribute('aria-pressed', state.role === 'nurse' ? 'true' : 'false');
renderGrid(); syncControls(); renderScenarios(); renderTime(); updateResults(72, 1.31, 68); hydrateFromApi();
