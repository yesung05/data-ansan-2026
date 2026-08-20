/* 공장 전경 관리 페이지 — 경고 발생 3초 후 오른쪽에서 슬라이드 인 */
(function () {
  const S = [
    { id: 'temp',      g: 1, st: 0, label: '온도센서',         unit: '°C',      min: 150, max: 320, thr: 280, def: 214 },
    { id: 'pressure',  g: 1, st: 0, label: '압력센서',         unit: 'bar',     min: 40,  max: 160, thr: 132, def: 88 },
    { id: 'vibration', g: 1, st: 0, label: '진동센서',         unit: 'mm/s',    min: 0,   max: 20,  thr: 12,  def: 4.2, dec: 1 },
    { id: 'humidity',  g: 1, st: 1, label: '습도센서',         unit: '%RH',     min: 10,  max: 90,  thr: 68,  def: 37 },
    { id: 'cycle',     g: 1, st: 0, label: '사이클타임 센서',  unit: 's',       min: 8,   max: 40,  thr: 30,  def: 18 },
    { id: 'thickness', g: 2, st: 2, label: '두께 계측기',      unit: 'mm',      min: 1,   max: 6,   thr: 4.4, thrLow: 2.0, def: 2.9, dec: 2 },
    { id: 'hardness',  g: 2, st: 2, label: '경도 계측기',      unit: 'Shore D', min: 40,  max: 100, thr: 88,  def: 68 },
    { id: 'power',     g: 3, st: 3, label: '전력량계 센서',    unit: 'kW',      min: 0,   max: 120, thr: 96,  def: 54 },
    { id: 'runtime',   g: 3, st: 3, label: '가동/정지 타이머', unit: 'min',     min: 0,   max: 600, thr: 480, def: 226 },
  ];
  const GROUPS = { 1: ['01', '실시간 공정 센서'], 2: ['02', '품질 및 물성 계측 센서'], 3: ['03', '설비 에너지 및 가동 계측기'] };
  const STATIONS = [
    { code: 'ST-01', name: '사출 성형기' },
    { code: 'ST-02', name: '유약 · 건조 터널' },
    { code: 'ST-03', name: 'QC 계측 게이트' },
    { code: 'ST-04', name: '포장 · 적재' },
  ];
  const byId = (id) => S.find((s) => s.id === id);
  const LINES = [
    { id: 'A', label: 'A 라인', note: '3D 모니터 대상 · 주력 라인', util: '94.2', vals: Object.fromEntries(S.map((s) => [s.id, s.def])) },
    { id: 'B', label: 'B 라인', note: '동형 설비 · 소형 저금통', util: '96.8',
      vals: { temp: 208, pressure: 91, vibration: 3.8, humidity: 41, cycle: 19, thickness: 3.05, hardness: 71, power: 58, runtime: 305 } },
    { id: 'C', label: 'C 라인', note: '시험 생산 · 신규 금형', util: '91.5',
      vals: { temp: 231, pressure: 104, vibration: 6.1, humidity: 52, cycle: 21, thickness: 2.6, hardness: 64, power: 66, runtime: 118 } },
  ];

  const fmt = (s, v) => Number(v).toFixed(s.dec || 0);
  const frac = (s, v) => Math.min(1, Math.max(0, (v - s.min) / (s.max - s.min)));
  const bad = (s, v) => v > s.thr || (s.thrLow != null && v < s.thrLow);

  let root, planEl, navEl, alertEl, sel = 'A', alarm = null, poll = 0;

  /* ---------- 전경도 ---------- */
  function plan() {
    const T = [];
    T.push('<svg viewBox="0 0 1000 700" role="img" aria-label="공장 전경도">');
    T.push('<rect x="40" y="40" width="920" height="620" fill="none" stroke="var(--color-text)" stroke-width="2"/>');
    for (const x of [180, 820]) T.push(`<line x1="${x}" y1="40" x2="${x}" y2="660" stroke="var(--color-text)" stroke-width="2"/>`);
    for (const y of [90, 260, 440, 612]) T.push(`<line x1="180" y1="${y}" x2="820" y2="${y}" stroke="var(--color-divider)" stroke-width="1"/>`);
    T.push('<text class="zone" x="110" y="350" transform="rotate(-90 110 350)">자재 창고 · 원료 투입</text>');
    T.push('<text class="zone" x="890" y="350" transform="rotate(-90 890 350)">검수 · 출하장</text>');
    T.push('<text class="strip" x="192" y="70">생산관리 사무동</text>');
    T.push('<text class="strip" x="192" y="642">유틸리티 · 컴프레서 · 집진</text>');

    LINES.forEach((L, i) => {
      const top = 90 + i * 180, cy = top + 80;
      T.push(`<g class="line" data-line="${L.id}">`);
      // 밴드 자체가 라인 선택 대상 — 설비 아이콘 밖을 눌러도 라인이 잡힌다
      T.push(`<rect class="band" x="180" y="${top}" width="640" height="170" fill="transparent"/>`);
      T.push(`<text class="ln" x="196" y="${top + 30}">LINE ${L.id}</text>`);
      T.push(`<text class="lnote" x="196" y="${top + 46}">가동률 ${L.util}%</text>`);
      // 선택된 라인에만 나타나는 그래프 버튼 (CSS 로 표시/숨김)
      T.push(`<g class="gbtn" data-graph="${L.id}" tabindex="0" role="button" aria-label="LINE ${L.id} 통계 그래프 열기">`);
      T.push(`<rect x="196" y="${top + 56}" width="104" height="26" rx="0"/>`);
      T.push(`<text x="248" y="${top + 73}">통계 그래프</text>`);
      T.push('</g>');
      T.push(`<rect class="belt" x="248" y="${cy - 3}" width="510" height="6"/>`);
      STATIONS.forEach((st, j) => {
        const cx = 288 + j * 152;
        T.push(`<g class="st" data-line="${L.id}" data-st="${j}" tabindex="0" role="button" aria-label="LINE ${L.id} ${st.name}">`);
        T.push(`<rect class="ring" x="${cx - 48}" y="${cy - 48}" width="96" height="96" fill="none"/>`);
        T.push(`<rect class="box" x="${cx - 38}" y="${cy - 38}" width="76" height="76"/>`);
        T.push(`<text class="code" x="${cx}" y="${cy + 5}">${st.code}</text>`);
        T.push(`<text class="sname" x="${cx}" y="${cy + 58}">${st.name}</text>`);
        S.filter((s) => s.st === j).forEach((s, k, arr) => {
          const w = 10, gap = 4, tot = arr.length * w + (arr.length - 1) * gap;
          T.push(`<rect class="pip" data-sensor="${s.id}" data-line="${L.id}" x="${cx - tot / 2 + k * (w + gap)}" y="${cy - 58}" width="${w}" height="6"/>`);
        });
        T.push('</g>');
      });
      T.push(`<path class="flow" d="M 760 ${cy} L 800 ${cy}"/>`);
      T.push('</g>');
    });
    T.push('</svg>');
    return T.join('');
  }

  /* ---------- 네비게이션 바 ---------- */
  function nav() {
    const T = [];
    T.push('<div class="ov-lines">');
    for (const L of LINES) {
      T.push(`<div class="ov-line" data-line="${L.id}">
        <button class="ov-line-b" data-line="${L.id}" aria-label="LINE ${L.id} 선택">
          <span class="ov-line-h"><b>LINE ${L.id}</b><i class="ov-chip">정상</i></span>
          <span class="ov-line-n">${L.note}</span>
        </button>
        <button class="ov-graph" data-graph="${L.id}" hidden>통계 그래프 보기</button>
      </div>`);
    }
    T.push('</div>');
    T.push('<div class="ov-sensors">');
    for (const k of ['1', '2', '3']) {
      const [num, title] = GROUPS[k];
      T.push(`<section class="grp"><div class="grp-h"><span class="grp-n">${num}</span><h2>${title}</h2></div>`);
      for (const s of S.filter((v) => String(v.g) === k)) {
        T.push(`<div class="row" data-row="${s.id}">
          <div class="row-top"><span class="row-label">${s.label}</span><span class="row-val"><b>—</b> <i>${s.unit}</i></span></div>
          <div class="bar"><div class="bar-fill"></div><div class="bar-tick"></div>${s.thrLow != null ? '<div class="bar-tick low"></div>' : ''}</div>
          <div class="row-scale"><span>${STATIONS[s.st].code}</span><span class="lim">임계 ${s.thr}${s.thrLow != null ? ' / ' + s.thrLow : ''}</span><span>${s.max}</span></div>
        </div>`);
      }
      T.push('</section>');
    }
    T.push('</div>');
    return T.join('');
  }

  function openGraph(id) {
    const L = LINES.find((l) => l.id === id);
    if (L && window.LINE_STATS) window.LINE_STATS.open(L, S);
  }

  function paint() {
    const L = LINES.find((l) => l.id === sel);
    navEl.querySelectorAll('.ov-line').forEach((b) => {
      const id = b.dataset.line;
      b.classList.toggle('on', id === sel);
      const alarmed = alarm && alarm.line === id;
      b.classList.toggle('alarm', !!alarmed);
      b.querySelector('.ov-chip').textContent = alarmed ? '경고' : '정상';
      b.querySelector('.ov-graph').hidden = id !== sel;   // 고른 라인에만 그래프 버튼
    });
    for (const s of S) {
      const v = L.vals[s.id], row = navEl.querySelector(`[data-row="${s.id}"]`);
      const isBad = bad(s, v);
      row.classList.toggle('bad', isBad);
      row.querySelector('.row-val b').textContent = fmt(s, v);
      row.querySelector('.bar-fill').style.width = (frac(s, v) * 100).toFixed(1) + '%';
      row.querySelector('.bar-tick').style.left = (frac(s, s.thr) * 100) + '%';
      const low = row.querySelector('.bar-tick.low');
      if (low) low.style.left = (frac(s, s.thrLow) * 100) + '%';
    }
    planEl.querySelectorAll('.line').forEach((g) => {
      g.classList.toggle('sel', g.dataset.line === sel);
      g.classList.toggle('alarm', !!alarm && alarm.line === g.dataset.line);
    });
    planEl.querySelectorAll('.st').forEach((g) => {
      const hit = alarm && alarm.line === g.dataset.line && alarm.stations.includes(Number(g.dataset.st));
      g.classList.toggle('alarm', !!hit);
    });
    planEl.querySelectorAll('.pip').forEach((p) => {
      const line = LINES.find((l) => l.id === p.dataset.line);
      const s = byId(p.dataset.sensor);
      p.classList.toggle('bad', bad(s, line.vals[s.id]));
    });
  }

  function paintAlert() {
    alertEl.style.left = ''; alertEl.style.top = ''; alertEl.style.right = ''; alertEl.style.bottom = '';
    if (!alarm) { alertEl.innerHTML = ''; return; }
    // 경고 라인을 가리지 않는 모서리에서 시작 (마지막 라인이면 위쪽)
    const last = LINES[LINES.length - 1].id === alarm.line;
    if (last) { alertEl.style.top = '52px'; alertEl.style.bottom = 'auto'; }
    const rows = alarm.causes.map((c) => {
      const s = byId(c.id);
      return `<div class="ov-alert-row"><span>${s.label}</span><b>${fmt(s, c.val)} ${s.unit}</b><i>임계 ${s.thr}</i></div>`;
    }).join('');
    alertEl.innerHTML = `<div class="ov-alert">
      <div class="ov-alert-k">
        <div class="ov-alert-h"><span class="ov-dot"></span>경고 · 임계값 초과<span class="ov-alert-t">${alarm.time}</span></div>
        <div class="ov-alert-line">LINE ${alarm.line} — ${STATIONS[alarm.stations[0]].name}</div>
      </div>
      <div class="ov-alert-rows">${rows}</div>
      <div class="ov-alert-a"><button data-act="go">3D 라인 뷰</button><button data-act="ack">확인</button></div>
    </div>`;
  }

  function build() {
    root = document.createElement('div');
    root.className = 'overview';
    root.id = 'overview';
    root.innerHTML = `
      <header class="ov-head">
        <div><h1>공장 전경 · 통합 관리</h1><div class="sub">Plant overview · engineer console</div></div>
        <div class="spacer"></div>
        <div class="ov-meta"><span>주간 A조</span><b id="ov-clock">--:--:--</b></div>
        <button class="ov-back" id="ov-back">← 3D 라인 뷰</button>
      </header>
      <div class="ov-plan"><div class="ov-plan-t">전경도 — PLANT LAYOUT</div><div class="ov-alerts"></div><div class="ov-svg"></div>
        <div class="ov-legend"><span class="lg lg-ok"></span>정상 센서<span class="lg lg-bad"></span>임계 초과<span class="lg lg-belt"></span>컨베이어 라인</div>
      </div>
      <aside class="ov-nav"></aside>`;
    document.body.appendChild(root);
    if (!document.querySelector('.ov-peek')) {
      const peek = document.createElement('div');
      peek.className = 'ov-peek';
      peek.innerHTML = '<span>3D 라인 뷰 뒤에서 계속 가동</span>';
      document.body.appendChild(peek);
    }
    planEl = root.querySelector('.ov-svg');
    navEl = root.querySelector('.ov-nav');
    alertEl = root.querySelector('.ov-alerts');
    planEl.innerHTML = plan();
    navEl.innerHTML = nav();

    navEl.addEventListener('click', (e) => {
      const gb = e.target.closest('.ov-graph');
      if (gb) { openGraph(gb.dataset.graph); return; }
      const b = e.target.closest('.ov-line-b');
      if (b) { sel = b.dataset.line; paint(); }
    });
    planEl.addEventListener('click', (e) => {
      const gb = e.target.closest('.gbtn');
      if (gb) { sel = gb.dataset.graph; paint(); openGraph(gb.dataset.graph); return; }
      // 설비 아이콘이든 라인 밴드 어디든 — 누른 라인을 고른다
      const g = e.target.closest('.st') || e.target.closest('.line');
      if (g) { sel = g.dataset.line || g.dataset.st; paint(); }
    });
    planEl.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const gb = e.target.closest('.gbtn');
      if (gb) { e.preventDefault(); sel = gb.dataset.graph; paint(); openGraph(gb.dataset.graph); return; }
      const g = e.target.closest('.st');
      if (g) { e.preventDefault(); sel = g.dataset.line; paint(); }
    });
    alertEl.addEventListener('click', (e) => {
      const a = e.target.closest('button');
      if (!a) return;
      if (a.dataset.act === 'ack') { alertEl.innerHTML = ''; }
      else API.close();
    });
    root.querySelector('#ov-back').onclick = () => API.close();
    dragCard();
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && root.classList.contains('open')) API.close(); });

    const clock = root.querySelector('#ov-clock');
    setInterval(() => { clock.textContent = new Date().toLocaleTimeString('ko-KR', { hour12: false }); }, 1000);
    clock.textContent = new Date().toLocaleTimeString('ko-KR', { hour12: false });
    paint();
  }

  /* 경고 카드 드래그 — 도면을 가리면 자유롭게 이동 */
  function dragCard() {
    let sx = 0, sy = 0, ox = 0, oy = 0, card = null;
    alertEl.addEventListener('pointerdown', (e) => {
      const k = e.target.closest('.ov-alert-k');
      if (!k) return;
      card = k.closest('.ov-alert');
      const host = alertEl.parentElement.getBoundingClientRect();
      const r = alertEl.getBoundingClientRect();
      ox = r.left - host.left; oy = r.top - host.top;
      sx = e.clientX; sy = e.clientY;
      alertEl.style.right = 'auto';
      alertEl.style.bottom = 'auto';
      alertEl.style.left = ox + 'px';
      alertEl.style.top = oy + 'px';
      card.classList.add('dragging');
      alertEl.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    alertEl.addEventListener('pointermove', (e) => {
      if (!card) return;
      const host = alertEl.parentElement.getBoundingClientRect();
      const w = alertEl.offsetWidth, h = alertEl.offsetHeight;
      const nx = Math.min(host.width - w, Math.max(0, ox + e.clientX - sx));
      const ny = Math.min(host.height - h, Math.max(0, oy + e.clientY - sy));
      alertEl.style.left = nx + 'px';
      alertEl.style.top = ny + 'px';
    });
    const end = () => { if (card) { card.classList.remove('dragging'); card = null; } };
    alertEl.addEventListener('pointerup', end);
    alertEl.addEventListener('pointercancel', end);
  }

  const API = {
    open(o) {
      if (!root) build();
      const causes = (o.causes || []).map((c) => ({ id: c.id, val: c.val }));
      alarm = {
        line: o.line || 'A',
        causes,
        stations: [...new Set(causes.map((c) => byId(c.id).st))].sort(),
        time: new Date().toLocaleTimeString('ko-KR', { hour12: false }),
      };
      if (!alarm.stations.length) alarm.stations = [0];
      sel = alarm.line;
      API.sync(o.sensors);
      paintAlert();
      paint();
      requestAnimationFrame(() => root.classList.add('open'));
      document.body.classList.add('overview-on');
      clearInterval(poll);
      poll = setInterval(() => {
        if (typeof window.PLANT_FEED === 'function') { API.sync(window.PLANT_FEED()); paint(); }
      }, 500);
    },
    close() {
      if (!root) return;
      root.classList.remove('open');
      document.body.classList.remove('overview-on');
      clearInterval(poll); poll = 0;
    },
    sync(list) {
      if (!Array.isArray(list)) return;
      const L = LINES.find((l) => l.id === (alarm ? alarm.line : 'A'));
      for (const v of list) if (v && v.id in L.vals) L.vals[v.id] = v.val;
    },
    isOpen() { return !!root && root.classList.contains('open'); },
  };
  window.PLANT = API;
})();
