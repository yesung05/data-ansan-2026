const stage = document.querySelector('three-d-stage');
const { THREE } = await stage.ready;

/* ---------- materials (named — they become usemtl / GLB material names) ---------- */
const M = {
  floor:      new THREE.MeshStandardMaterial({ name: 'floor_plate',   color: 0xe4e2e0, roughness: 0.9,  metalness: 0.0 }),
  stripe:     new THREE.MeshStandardMaterial({ name: 'floor_stripe',  color: 0xec3013, roughness: 0.7 }),
  panel:      new THREE.MeshStandardMaterial({ name: 'machine_panel', color: 0xd6d3d0, roughness: 0.55, metalness: 0.3 }),
  steel:      new THREE.MeshStandardMaterial({ name: 'steel_frame',   color: 0x8f8b87, roughness: 0.4,  metalness: 0.35 }),
  dark:       new THREE.MeshStandardMaterial({ name: 'dark_ink',      color: 0x201e1d, roughness: 0.6 }),
  belt:       new THREE.MeshStandardMaterial({ name: 'belt_rubber',   color: 0x35322f, roughness: 0.85 }),
  slat:       new THREE.MeshStandardMaterial({ name: 'belt_slat',     color: 0x4a4643, roughness: 0.8 }),
  accent:     new THREE.MeshStandardMaterial({ name: 'accent_red',    color: 0xec3013, roughness: 0.5 }),
  glass:      new THREE.MeshStandardMaterial({ name: 'glass_guard',   color: 0xbfc6c8, roughness: 0.15, metalness: 0.2, transparent: true, opacity: 0.28 }),
  piggy:      new THREE.MeshStandardMaterial({ name: 'piggy_glaze',   color: 0xcfcbc7, roughness: 0.45 }),
  piggyDark:  new THREE.MeshStandardMaterial({ name: 'piggy_detail',  color: 0x201e1d, roughness: 0.5 }),
  barFill:    new THREE.MeshStandardMaterial({ name: 'gauge_fill',    color: 0x201e1d, roughness: 0.5 }),
  lampOven:   new THREE.MeshStandardMaterial({ name: 'lamp_oven',     color: 0xffb59c, emissive: 0xff5a2a, emissiveIntensity: 0.35, roughness: 0.4 }),
  lampBeacon: new THREE.MeshStandardMaterial({ name: 'lamp_beacon',   color: 0xf0eeec, emissive: 0xec3013, emissiveIntensity: 0.05, roughness: 0.3 }),
  lampOk:     new THREE.MeshStandardMaterial({ name: 'lamp_status',   color: 0xe8e6e4, emissive: 0x201e1d, emissiveIntensity: 0.0, roughness: 0.3 }),
  laser:      new THREE.MeshStandardMaterial({ name: 'scan_beam',     color: 0xec3013, emissive: 0xec3013, emissiveIntensity: 0.8, transparent: true, opacity: 0.5, roughness: 0.4 }),
};

const model = new THREE.Group();
model.name = 'piggybank_factory_line';

const BELT_Y = 0.91;
const PIG_Y = BELT_Y + 0.22;

function box(name, w, h, d, mat, x, y, z, parent = model) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.name = name; m.position.set(x, y, z); parent.add(m); return m;
}
function cyl(name, rt, rb, h, mat, x, y, z, parent = model, seg = 32) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
  m.name = name; m.position.set(x, y, z); parent.add(m); return m;
}

/* ---------- floor ---------- */
box('floor_plate', 10.4, 0.08, 3.8, M.floor, 0, -0.04, 0);
box('floor_stripe_front', 10.4, 0.012, 0.07, M.stripe, 0, 0.005, 1.68);
box('floor_stripe_back', 10.4, 0.012, 0.07, M.stripe, 0, 0.005, -1.68);

/* ---------- conveyors ---------- */
const belts = [];
function conveyor(name, x0, x1) {
  const g = new THREE.Group(); g.name = name; model.add(g);
  const len = x1 - x0, cx = (x0 + x1) / 2;
  box(name + '_bed', len, 0.10, 0.72, M.belt, cx, BELT_Y - 0.05, 0, g);
  box(name + '_rail_a', len, 0.07, 0.035, M.steel, cx, BELT_Y + 0.03, 0.375, g);
  box(name + '_rail_b', len, 0.07, 0.035, M.steel, cx, BELT_Y + 0.03, -0.375, g);
  for (const lx of [x0 + 0.18, x1 - 0.18]) {
    for (const lz of [0.3, -0.3]) cyl(name + '_leg', 0.035, 0.035, BELT_Y - 0.1, M.steel, lx, (BELT_Y - 0.1) / 2, lz, g, 12);
    const r = cyl(name + '_roller', 0.075, 0.075, 0.7, M.steel, lx, BELT_Y - 0.05, 0, g, 24);
    r.rotation.x = Math.PI / 2;
  }
  const slats = [];
  const n = Math.max(4, Math.round(len / 0.22));
  for (let i = 0; i < n; i++) {
    slats.push(box(name + '_slat_' + i, 0.055, 0.022, 0.66, M.slat, x0 + (i + 0.5) * (len / n), BELT_Y + 0.005, 0, g));
  }
  belts.push({ slats, x0, x1, len });
  return g;
}
conveyor('conveyor_1', -2.95, -0.9);
conveyor('conveyor_2', -0.85, 0.8);
conveyor('conveyor_3', 0.85, 3.0);

/* ---------- 1. injection moulding press ---------- */
const press = (() => {
  const g = new THREE.Group(); g.name = 'moulding_press'; model.add(g);
  box('press_base', 1.85, 0.72, 1.35, M.panel, -3.85, 0.36, 0, g);
  box('press_base_skirt', 1.87, 0.10, 1.37, M.dark, -3.85, 0.06, 0, g);
  box('press_column_a', 0.22, 1.35, 1.15, M.panel, -4.55, 1.42, 0, g);
  box('press_column_b', 0.22, 1.35, 1.15, M.panel, -3.15, 1.42, 0, g);
  box('press_crown', 1.85, 0.26, 1.2, M.panel, -3.85, 2.22, 0, g);
  box('press_crown_band', 1.86, 0.06, 1.22, M.accent, -3.85, 2.05, 0, g);
  box('mould_die_lower', 0.86, 0.22, 0.82, M.steel, -3.85, 0.94, 0, g);
  const platen = box('mould_platen_upper', 0.86, 0.3, 0.82, M.steel, -3.85, 1.78, 0, g);
  cyl('press_ram', 0.09, 0.09, 0.5, M.dark, -3.85, 2.0, 0, g, 20);
  const hop = cyl('resin_hopper', 0.3, 0.11, 0.52, M.dark, -3.85, 2.66, 0.0, g, 24);
  cyl('hopper_neck', 0.07, 0.07, 0.3, M.steel, -3.85, 2.28, 0, g, 16);
  box('press_hmi', 0.42, 0.3, 0.05, M.dark, -3.4, 1.55, 0.62, g);
  const lamp = cyl('press_status_lamp', 0.055, 0.055, 0.07, M.lampOk, -3.85, 2.4, 0.5, g, 16);
  box('press_guard', 1.3, 0.9, 0.03, M.glass, -3.85, 1.5, 0.66, g);
  return { platen, lamp, hop };
})();

/* ---------- 2. glaze / drying tunnel ---------- */
const oven = (() => {
  const g = new THREE.Group(); g.name = 'glaze_oven'; model.add(g);
  box('oven_wall_a', 1.7, 0.72, 0.06, M.panel, -0.02, 1.32, 0.44, g);
  box('oven_wall_b', 1.7, 0.72, 0.06, M.panel, -0.02, 1.32, -0.44, g);
  box('oven_roof', 1.74, 0.1, 0.96, M.panel, -0.02, 1.73, 0, g);
  box('oven_roof_band', 1.76, 0.05, 0.98, M.accent, -0.02, 1.8, 0, g);
  box('oven_curtain_in', 0.05, 0.34, 0.9, M.dark, -0.86, 1.5, 0, g);
  box('oven_curtain_out', 0.05, 0.34, 0.9, M.dark, 0.82, 1.5, 0, g);
  const lamps = [];
  for (let i = 0; i < 4; i++) {
    const l = cyl('oven_lamp_' + i, 0.045, 0.045, 0.7, M.lampOven, -0.62 + i * 0.4, 1.62, 0, g, 16);
    l.rotation.x = Math.PI / 2; lamps.push(l);
  }
  const duct = cyl('oven_duct', 0.16, 0.16, 0.75, M.steel, 0.45, 2.15, 0, g, 20);
  box('oven_duct_box', 0.5, 0.3, 0.5, M.panel, 0.45, 1.95, 0, g);
  return { lamps, duct };
})();

/* ---------- 3. QC gantry: thickness gauge + hardness tester ---------- */
const qc = (() => {
  const g = new THREE.Group(); g.name = 'qc_gantry'; model.add(g);
  box('gantry_post_a', 0.1, 1.55, 0.1, M.steel, 1.85, 0.78, 0.56, g);
  box('gantry_post_b', 0.1, 1.55, 0.1, M.steel, 1.85, 0.78, -0.56, g);
  box('gantry_beam', 0.16, 0.14, 1.3, M.panel, 1.85, 1.62, 0, g);
  box('gantry_beam_band', 0.17, 0.05, 1.32, M.accent, 1.85, 1.7, 0, g);
  // thickness caliper
  box('thickness_head_upper', 0.2, 0.14, 0.34, M.dark, 1.6, 1.4, 0, g);
  box('thickness_head_lower', 0.2, 0.1, 0.34, M.dark, 1.6, BELT_Y + 0.06, 0.42, g);
  const beam = box('thickness_laser', 0.012, 0.42, 0.3, M.laser, 1.6, 1.2, 0, g);
  // hardness probe
  box('hardness_housing', 0.24, 0.3, 0.3, M.panel, 2.25, 1.42, 0, g);
  const probe = cyl('hardness_probe', 0.032, 0.02, 0.36, M.steel, 2.25, 1.28, 0, g, 16);
  const lamp = cyl('qc_status_lamp', 0.05, 0.05, 0.06, M.lampOk, 1.85, 1.78, 0, g, 16);
  // reject pusher
  const pusher = box('reject_pusher', 0.26, 0.14, 0.12, M.accent, 2.6, BELT_Y + 0.11, -0.52, g);
  box('reject_pusher_body', 0.3, 0.2, 0.24, M.dark, 2.6, BELT_Y + 0.11, -0.72, g);
  box('reject_bin', 0.6, 0.5, 0.5, M.dark, 2.6, 0.25, 1.15, g);
  box('reject_bin_band', 0.62, 0.06, 0.52, M.accent, 2.6, 0.47, 1.15, g);
  return { beam, probe, lamp, pusher };
})();

/* ---------- 4. packing station ---------- */
const pack = (() => {
  const g = new THREE.Group(); g.name = 'packing_station'; model.add(g);
  box('pack_table', 1.15, 0.09, 0.95, M.panel, 3.6, BELT_Y - 0.05, 0, g);
  for (const lx of [3.15, 4.05]) for (const lz of [0.35, -0.35]) cyl('pack_leg', 0.035, 0.035, 0.82, M.steel, lx, 0.41, lz, g, 12);
  cyl('robot_base', 0.16, 0.19, 0.16, M.dark, 4.35, 0.99, -0.55, g, 24);
  const arm = new THREE.Group(); arm.name = 'robot_arm'; arm.position.set(4.35, 1.07, -0.55); g.add(arm);
  box('arm_lower', 0.5, 0.11, 0.13, M.panel, -0.2, 0.16, 0, arm);
  box('arm_upper', 0.13, 0.34, 0.11, M.steel, -0.42, 0.0, 0, arm);
  box('arm_gripper', 0.1, 0.1, 0.16, M.dark, -0.42, -0.18, 0, arm);
  box('carton_a', 0.34, 0.3, 0.34, M.panel, 3.55, 1.06, -0.02, g);
  box('carton_a_band', 0.35, 0.05, 0.35, M.accent, 3.55, 0.94, -0.02, g);
  box('carton_stack_1', 0.34, 0.3, 0.34, M.panel, 4.4, 0.16, 0.75, g);
  box('carton_stack_2', 0.34, 0.3, 0.34, M.panel, 4.4, 0.47, 0.75, g);
  const lamp = cyl('pack_status_lamp', 0.06, 0.06, 0.07, M.lampOk, 3.15, 1.2, 0.42, g, 16);
  return { arm, lamp };
})();

/* ---------- control cabinet + beacon ---------- */
const beacon = (() => {
  const g = new THREE.Group(); g.name = 'control_post'; model.add(g);
  box('cabinet', 1.15, 1.6, 0.42, M.panel, 3.0, 0.8, -1.42);
  box('cabinet_screen', 0.8, 0.5, 0.04, M.dark, 3.0, 1.28, -1.2);
  box('cabinet_band', 1.17, 0.06, 0.44, M.accent, 3.0, 0.4, -1.42);
  cyl('beacon_post', 0.06, 0.06, 2.5, M.steel, -0.2, 1.25, -1.4, g, 16);
  const lamp = cyl('beacon_lamp', 0.19, 0.19, 0.3, M.lampBeacon, -0.2, 2.62, -1.4, g, 28);
  cyl('beacon_cap', 0.13, 0.19, 0.09, M.dark, -0.2, 2.81, -1.4, g, 28);
  box('beacon_horn', 0.2, 0.2, 0.24, M.dark, -0.2, 2.28, -1.4, g);
  return { lamp };
})();

/* ---------- sensor gauges (one bar per sensor, front row) ---------- */
const SENSORS = [
  { id: 'temp',      group: 1, label: '온도센서',        unit: '°C',   min: 150, max: 320, thr: 280, def: 214, x: -3.95 },
  { id: 'pressure',  group: 1, label: '압력센서',        unit: 'bar',  min: 40,  max: 160, thr: 132, def: 88,  x: -3.4 },
  { id: 'vibration', group: 1, label: '진동센서',        unit: 'mm/s', min: 0,   max: 20,  thr: 12,  def: 4.2, x: -2.1, dec: 1 },
  { id: 'humidity',  group: 1, label: '습도센서',        unit: '%RH',  min: 10,  max: 90,  thr: 68,  def: 37,  x: -0.55 },
  { id: 'cycle',     group: 1, label: '사이클타임 센서', unit: 's',    min: 8,   max: 40,  thr: 30,  def: 18,  x: 0.45, live: 0.5 },
  { id: 'thickness', group: 2, label: '두께 계측기',     unit: 'mm',   min: 1,   max: 6,   thr: 4.4, thrLow: 2.0, def: 2.9, x: 1.45, dec: 2 },
  { id: 'hardness',  group: 2, label: '경도 계측기',     unit: 'Shore D', min: 40, max: 100, thr: 88, def: 68, x: 2.05 },
  { id: 'power',     group: 3, label: '전력량계 센서',   unit: 'kW',   min: 0,   max: 120, thr: 96,  def: 54,  x: 3.15, live: 2 },
  { id: 'runtime',   group: 3, label: '가동/정지 타이머', unit: 'min', min: 0,   max: 600, thr: 480, def: 226, x: 3.7, ticks: true },
];
const GROUPS = {
  1: ['01', '실시간 공정 센서'],
  2: ['02', '품질 및 물성 계측 센서'],
  3: ['03', '설비 에너지 및 가동 계측기'],
};
const BAR_BOT = 0.82, BAR_H = 0.62;

for (const s of SENSORS) {
  const g = new THREE.Group(); g.name = 'gauge_' + s.id; model.add(g);
  box('gauge_post_' + s.id, 0.05, 0.78, 0.05, M.steel, s.x, 0.39, 0.95, g);
  box('gauge_track_' + s.id, 0.1, BAR_H, 0.05, M.dark, s.x, BAR_BOT + BAR_H / 2, 0.95, g);
  box('gauge_plate_' + s.id, 0.16, 0.07, 0.09, M.panel, s.x, BAR_BOT + BAR_H + 0.06, 0.95, g);
  s.fill = box('gauge_fill_' + s.id, 0.075, 1, 0.035, M.barFill.clone(), s.x, BAR_BOT, 0.972, g);
  s.fill.material.name = 'gauge_fill_' + s.id;
  const tick = (v, n) => box(n, 0.15, 0.014, 0.075, M.accent, s.x, BAR_BOT + BAR_H * ((v - s.min) / (s.max - s.min)), 0.958, g);
  tick(s.thr, 'gauge_limit_' + s.id);
  if (s.thrLow != null) tick(s.thrLow, 'gauge_limit_low_' + s.id);
  s.val = s.def;
}

/* ---------- the piggy bank ---------- */
function makePiggy(name) {
  const g = new THREE.Group(); g.name = name;
  const skin = M.piggy.clone(); skin.name = name + '_glaze';
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.17, 40, 28), skin);
  body.name = name + '_body'; body.scale.set(1.32, 1, 1.02); g.add(body);
  const snout = cyl(name + '_snout', 0.072, 0.078, 0.07, skin, 0.222, -0.01, 0, g, 28);
  snout.rotation.z = Math.PI / 2;
  for (const z of [0.026, -0.026]) {
    const n = cyl(name + '_nostril', 0.011, 0.011, 0.03, M.piggyDark, 0.252, -0.01, z, g, 10);
    n.rotation.z = Math.PI / 2;
  }
  for (const z of [0.075, -0.075]) {
    const ear = new THREE.Mesh(new THREE.ConeGeometry(0.048, 0.08, 18), skin);
    ear.name = name + '_ear'; ear.position.set(0.105, 0.15, z); ear.rotation.z = -0.35; g.add(ear);
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.018, 16, 12), M.piggyDark);
    eye.name = name + '_eye'; eye.position.set(0.163, 0.048, z * 0.95); g.add(eye);
  }
  for (const x of [0.115, -0.115]) for (const z of [0.082, -0.082]) {
    cyl(name + '_leg', 0.042, 0.038, 0.13, skin, x, -0.155, z, g, 18);
  }
  const tail = new THREE.Mesh(new THREE.TorusGeometry(0.038, 0.013, 10, 24, Math.PI * 1.6), skin);
  tail.name = name + '_tail'; tail.position.set(-0.222, 0.03, 0); tail.rotation.y = Math.PI / 2; g.add(tail);
  box(name + '_coin_slot', 0.11, 0.02, 0.032, M.piggyDark, 0, 0.166, 0, g);
  g.userData.skin = skin;
  return g;
}
const piggy = makePiggy('piggy_bank');
piggy.position.set(-3.85, PIG_Y, 0);
model.add(piggy);

stage.setObject(model);
// tighter three-quarter framing than the auto bounding-sphere fit
if (stage._camera && stage._controls) {
  stage._camera.position.set(6.2, 4.4, 9.2);
  stage._controls.target.set(-0.1, 0.85, 0);
  stage._controls.update();
}

/* ================= panel ================= */
const RAW = new THREE.Color(0xcfcbc7), GLAZE = new THREE.Color(0xffb0a0), ALARM = new THREE.Color(0xec3013);
const rows = {};
const panel = document.getElementById('sensors');
for (const key of ['1', '2', '3']) {
  const [num, title] = GROUPS[key];
  const sec = document.createElement('section');
  sec.className = 'grp';
  sec.innerHTML = `<div class="grp-h"><span class="grp-n">${num}</span><h2>${title}</h2></div>`;
  for (const s of SENSORS.filter((v) => String(v.group) === key)) {
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `
      <div class="row-top"><span class="row-label">${s.label}</span><span class="row-val"><b>—</b> <i>${s.unit}</i></span></div>
      <div class="bar"><div class="bar-fill"></div><div class="bar-tick"></div>${s.thrLow != null ? '<div class="bar-tick low"></div>' : ''}</div>
      <input type="range" min="${s.min}" max="${s.max}" step="${s.max - s.min > 60 ? 1 : 0.1}" value="${s.def}" aria-label="${s.label}">
      <div class="row-scale"><span>${s.min}</span><span class="lim">임계 ${s.thr}${s.thrLow != null ? ' / ' + s.thrLow : ''}</span><span>${s.max}</span></div>`;
    sec.appendChild(row);
    const tick = row.querySelector('.bar-tick');
    tick.style.left = pct(s, s.thr) + '%';
    const low = row.querySelector('.bar-tick.low');
    if (low) low.style.left = pct(s, s.thrLow) + '%';
    const input = row.querySelector('input');
    input.addEventListener('input', () => { s.val = parseFloat(input.value); paintSensor(s); evaluate(); });
    rows[s.id] = { row, input, fill: row.querySelector('.bar-fill'), val: row.querySelector('.row-val b') };
  }
  panel.appendChild(sec);
}
function pct(s, v) { return ((v - s.min) / (s.max - s.min)) * 100; }
function exceeded(s) { return s.val > s.thr || (s.thrLow != null && s.val < s.thrLow); }
function fmt(s) { return s.val.toFixed(s.dec || 0); }

function paintSensor(s) {
  const r = rows[s.id], bad = exceeded(s), f = Math.min(1, Math.max(0, (s.val - s.min) / (s.max - s.min)));
  r.val.textContent = fmt(s);
  r.fill.style.width = (f * 100).toFixed(1) + '%';
  r.row.classList.toggle('bad', bad);
  s.fill.scale.y = Math.max(0.001, BAR_H * f);
  s.fill.position.y = BAR_BOT + (BAR_H * f) / 2;
  s.fill.material.color.set(bad ? 0xec3013 : 0x201e1d);
  s.fill.material.emissive.set(bad ? 0x7c1405 : 0x000000);
  s.fill.material.emissiveIntensity = bad ? 0.6 : 0;
}

/* ================= run state ================= */
const S = { mode: 'idle', t: 0, alarmT: 0, cycle: 0, done: 0, reject: 0, cause: [], glaze: 0, beltPos: 0, rejected: false };
const el = {
  status: document.getElementById('status'),
  statusNote: document.getElementById('status-note'),
  phase: document.getElementById('phase'),
  done: document.getElementById('c-done'),
  cyc: document.getElementById('c-cycle'),
  rej: document.getElementById('c-reject'),
};

const KEYS = [[2.6, -3.85], [3.5, -2.8], [6.0, -0.9], [8.3, 0.8], [9.7, 1.6], [10.7, 1.6], [11.5, 2.25], [12.3, 2.25], [13.7, 3.55], [16.6, 3.55]];
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const seg = (t, a, b) => clamp01((t - a) / (b - a));
const ease = (p) => p * p * (3 - 2 * p);
function pathX(t) {
  if (t <= KEYS[0][0]) return KEYS[0][1];
  for (let i = 1; i < KEYS.length; i++) {
    if (t <= KEYS[i][0]) {
      const [t0, x0] = KEYS[i - 1], [t1, x1] = KEYS[i];
      return x0 + (x1 - x0) * ease(seg(t, t0, t1));
    }
  }
  return KEYS[KEYS.length - 1][1];
}

function setPhase(txt) { el.phase.textContent = txt; }
function phaseFor(t) {
  if (t < 2.4) return '사출 성형 — 금형 가압';
  if (t < 3.5) return '취출 · 컨베이어 이송';
  if (t < 6.0) return '1호 컨베이어 이송';
  if (t < 8.3) return '유약 도장 · 건조 터널';
  if (t < 10.7) return '두께 계측';
  if (t < 12.3) return '경도 계측';
  if (t < 13.7) return '포장 라인 이송';
  return '제품 완성 · 적재';
}

function start(scenario) {
  if (scenario === 'normal') reset(false);
  S.mode = 'run'; S.t = 0; S.scenario = scenario; S.rejected = false; S.glaze = 0; S.cause = [];
  S.cycle += 1; el.cyc.textContent = String(S.cycle);
  piggy.visible = true;
  document.body.classList.remove('alarm');
  paintStatus();
}
function reset(full = true) {
  clearTimeout(S.ovTimer);
  window.PLANT?.close();
  S.mode = 'idle'; S.t = 0; S.alarmT = 0; S.glaze = 0; S.rejected = false; S.cause = [];
  for (const s of SENSORS) { s.val = s.def; rows[s.id].input.value = s.def; paintSensor(s); }
  if (full) { S.cycle = 0; S.done = 0; S.reject = 0; el.cyc.textContent = '0'; el.done.textContent = '0'; el.rej.textContent = '0'; clearLog(); }
  piggy.visible = false;
  piggy.position.set(-3.85, PIG_Y, 0);
  piggy.rotation.set(0, 0, 0);
  piggy.scale.setScalar(1);
  piggy.userData.skin.color.copy(RAW);
  document.body.classList.remove('alarm');
  setPhase('대기 — 사이클 시작을 누르세요');
  paintStatus();
}
/* ================= 제품 생산 이력 =================
   제품이 하나 완성(또는 불량 배출)되는 순간의 센서 9종 값을 통째로 붙잡아 둔다.
   카운터만 올라가면 "그때 값이 얼마였는지"를 되짚을 수 없어서, 스냅샷을 남긴다. */
const LOG = [];
const LOG_MAX = 100;                       // 패널이 무한정 길어지지 않도록 최근 100건만 보관
const histList = document.getElementById('hist-list');
const histEmpty = document.getElementById('hist-empty');

function snapshot(result) {
  const now = new Date();
  const entry = {
    no: LOG.length + 1,
    result,                                // '양품' | '불량'
    cycle: S.cycle,
    time: now.toTimeString().slice(0, 8),
    sensors: SENSORS.map((s) => ({
      id: s.id, label: s.label, unit: s.unit,
      value: parseFloat(fmt(s)),           // 화면에 보이는 자릿수 그대로 기록
      threshold: s.thr, thresholdLow: s.thrLow ?? null,
      exceeded: exceeded(s),               // 이 제품이 만들어질 때 임계를 넘겨 있었는가
    })),
  };
  LOG.unshift(entry);                      // 최신이 위로
  if (LOG.length > LOG_MAX) LOG.length = LOG_MAX;
  renderLog();
  return entry;
}

function renderLog() {
  histEmpty.hidden = LOG.length > 0;
  histList.innerHTML = LOG.map((e) => `
    <article class="hist" data-result="${e.result}">
      <div class="hist-h">
        <span class="hist-no">#${e.no}</span>
        <span class="hist-tag">${e.result}</span>
        <span class="hist-time">사이클 ${e.cycle} · ${e.time}</span>
      </div>
      <dl class="hist-grid">
        ${e.sensors.map((s) => `
          <div${s.exceeded ? ' class="over"' : ''}>
            <dt>${s.label}</dt>
            <dd>${s.value}<i>${s.unit}</i></dd>
          </div>`).join('')}
      </dl>
    </article>`).join('');
}

function clearLog() { LOG.length = 0; renderLog(); }

/* 콘솔·자동화에서 그대로 꺼내 쓸 수 있게 열어 둔다. 사용법은 docs/사용법.md 참고. */
window.PLANT_LOG = () => LOG.map((e) => ({ ...e, sensors: e.sensors.map((s) => ({ ...s })) }));
window.PLANT_LOG_TSV = () => {
  const head = ['제품번호', '판정', '사이클', '시각', ...SENSORS.map((s) => `${s.label}(${s.unit})`)];
  const body = LOG.map((e) => [e.no, e.result, e.cycle, e.time, ...e.sensors.map((s) => s.value)]);
  return [head, ...body].map((r) => r.join('\t')).join('\n');
};

document.getElementById('btn-copy-log').addEventListener('click', async (ev) => {
  const btn = ev.currentTarget;
  if (!LOG.length) { btn.textContent = '이력 없음'; setTimeout(() => (btn.textContent = '이력 복사'), 1200); return; }
  try {
    await navigator.clipboard.writeText(window.PLANT_LOG_TSV());
    btn.textContent = `${LOG.length}건 복사됨`;
  } catch {
    btn.textContent = '복사 실패';   // file:// 등 클립보드가 막힌 환경
  }
  setTimeout(() => (btn.textContent = '이력 복사'), 1600);
});

window.PLANT_FEED = () => SENSORS.map((s) => ({ id: s.id, val: s.val }));
function raiseAlarm(cause) {
  if (S.mode === 'alarm') return;
  S.mode = 'alarm'; S.alarmT = 0; S.cause = cause;
  document.body.classList.add('alarm');
  setPhase('라인 정지 — 임계값 초과');
  paintStatus();
  // 경고 3초 후 공장 전경 관리 페이지가 오른쪽에서 슬라이드 인
  clearTimeout(S.ovTimer);
  S.ovTimer = setTimeout(() => {
    window.PLANT?.open({
      line: 'A',
      causes: cause.map((s) => ({ id: s.id, val: s.val })),
      sensors: window.PLANT_FEED(),
    });
  }, 3000);
}
function paintStatus() {
  const bad = SENSORS.filter(exceeded);
  const alarm = S.mode === 'alarm';
  el.status.textContent = alarm ? '경고 · 라인 정지' : S.mode === 'run' ? '정상 가동' : '대기';
  el.statusNote.textContent = alarm
    ? bad.map((s) => `${s.label} ${fmt(s)}${s.unit}`).join(' / ') + ' — 임계값 초과'
    : bad.length ? bad.map((s) => s.label).join(' / ') + ' 임계값 초과' : '전 센서 정상 범위';
}
function evaluate() {
  const bad = SENSORS.filter(exceeded);
  if (bad.length && S.mode !== 'alarm') raiseAlarm(bad);
  else paintStatus();
}

document.getElementById('btn-run').onclick = () => start('normal');
document.getElementById('btn-fault').onclick = () => { reset(false); start('fault'); };
document.getElementById('btn-reset').onclick = () => reset(true);

function spike(id, target, p) {
  const s = SENSORS.find((v) => v.id === id);
  s.val = s.def + (target - s.def) * p;
  rows[s.id].input.value = s.val;
  paintSensor(s);
}

/* ================= animation ================= */
let last = performance.now();
function frame(now) {
  const dt = Math.min(0.25, (now - last) / 1000); last = now;
  const running = S.mode === 'run';

  if (running) {
    S.t += dt;
    const t = S.t;
    setPhase(phaseFor(t));

    press.platen.position.y = 1.78 - 0.52 * (ease(seg(t, 0.2, 1.15)) - ease(seg(t, 1.9, 2.5)));
    piggy.visible = t > 0.85;
    piggy.scale.setScalar(ease(seg(t, 0.85, 1.9)) || 0.001);
    const x = pathX(t);
    const lift = Math.sin(Math.PI * seg(t, 2.6, 3.5)) * 0.22;
    piggy.position.set(x, (t < 2.6 ? 1.38 : PIG_Y + (1.38 - PIG_Y) * (1 - ease(seg(t, 2.6, 3.5)))) + lift, 0);
    S.glaze = ease(seg(t, 6.2, 8.1));
    piggy.userData.skin.color.copy(RAW).lerp(GLAZE, S.glaze);
    for (const l of oven.lamps) l.material.emissiveIntensity = 0.3 + 0.45 * Math.abs(Math.sin(now / 420)) * (t > 5.6 && t < 8.4 ? 1 : 0.3);
    qc.beam.visible = t > 9.4 && t < 10.9;
    qc.beam.material.opacity = 0.35 + 0.25 * Math.sin(now / 90) ** 2;
    qc.probe.position.y = 1.28 - 0.2 * Math.sin(Math.PI * seg(t, 11.5, 12.3));
    pack.arm.rotation.y = -0.5 * Math.sin(Math.PI * clamp01((t - 13.4) / 2.2));
    if (t > 13.7) piggy.rotation.y = (t - 13.7) * 1.6;
    pack.lamp.material.emissiveIntensity = t > 14.6 ? 0.9 : 0;
    pack.lamp.material.emissive.set(0x201e1d);
    press.hop.rotation.y = now / 4000;

    if (S.scenario === 'fault') {
      const p = ease(seg(t, 8.6, 9.7));
      if (p > 0) { spike('temp', 297, p); spike('vibration', 15.6, p); evaluate(); }
    }
    for (const s of SENSORS) {
      if (s.ticks) { s.val = Math.min(s.max, s.val + dt * 1.2); rows[s.id].input.value = s.val; paintSensor(s); }
      else if (s.live) {
        const j = s.def + Math.sin(now / (900 + s.live * 400)) * s.live;
        if (Math.abs(parseFloat(rows[s.id].input.value) - s.def) < 0.6) { s.val = j; paintSensor(s); }
      }
    }
    if (t > 14.9 && !S.counted) {
      S.counted = true; S.done += 1; el.done.textContent = String(S.done);
      snapshot('양품');            // 완성 순간의 센서 9종을 그대로 남긴다
    }
    if (t > 16.6) { S.counted = false; start('normal'); }
  }

  if (S.mode === 'alarm') {
    S.alarmT += dt;
    const pulse = Math.sin(S.alarmT * 9) > 0 ? 1 : 0.05;
    beacon.lamp.material.emissiveIntensity = 0.25 + pulse * 2.4;
    beacon.lamp.material.color.copy(ALARM);
    for (const l of [press.lamp, qc.lamp, pack.lamp]) {
      l.material.emissive.copy(ALARM);
      l.material.emissiveIntensity = pulse * 1.6;
    }
    for (const l of oven.lamps) l.material.emissiveIntensity = 0.15;
    qc.beam.visible = false;
    // reject sequence: pusher shoves the part off the line into the bin
    const p = ease(seg(S.alarmT, 1.4, 2.4));
    qc.pusher.position.z = -0.52 + 0.5 * p;
    if (p > 0.35 && !S.rejected) {
      S.rejected = true; S.reject += 1; el.rej.textContent = String(S.reject);
      snapshot('불량');           // 어떤 센서가 임계를 넘겨 걸러졌는지 함께 기록된다
    }
    const d = ease(seg(S.alarmT, 1.7, 3.1));
    if (d > 0) {
      piggy.position.z = 0 + 1.1 * d;
      piggy.position.y = PIG_Y - 0.62 * clamp01((d - 0.45) / 0.55);
      piggy.rotation.x = 1.4 * d;
      setPhase('불량 배출 — 리젝트 빈');
    }
  } else if (S.mode !== 'alarm') {
    beacon.lamp.material.emissiveIntensity = 0.06;
    beacon.lamp.material.color.set(0xf0eeec);
    qc.pusher.position.z = -0.52;
    press.lamp.material.emissiveIntensity = running ? 0.5 : 0;
    press.lamp.material.emissive.set(0x201e1d);
    qc.lamp.material.emissiveIntensity = running ? 0.5 : 0;
    qc.lamp.material.emissive.set(0x201e1d);
  }

  // belt slats + rollers
  if (running) {
    const v = 0.55 * dt;
    for (const b of belts) for (const s of b.slats) {
      s.position.x += v;
      if (s.position.x > b.x1) s.position.x -= b.len;
    }
    model.traverse((o) => { if (o.name && o.name.includes('_roller')) o.rotation.z += v * 4; });
  }
  requestAnimationFrame(frame);
}
for (const s of SENSORS) paintSensor(s);
reset(true);
requestAnimationFrame(frame);
