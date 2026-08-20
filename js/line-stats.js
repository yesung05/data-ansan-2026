/* 라인 통계 그래프 — 엔지니어 콘솔에서 라인을 고르면 열리는 통계 패널.
 *
 * 7일 / 30일 생산 통계를 그래프로 보여주고, PDF 저장과 주간 이메일 구독을 제공한다.
 *
 * ⚠ 이 페이지에는 이력 데이터베이스가 없다. 아래 이력은 라인 ID를 시드로 한
 *   결정적 난수로 만들어 낸 **시뮬레이션 값**이다. 같은 라인은 언제 열어도 같은
 *   그래프가 나오고, 7일 구간은 30일 구간의 뒷부분과 정확히 일치한다.
 *   단, 오늘 자 실적만은 현재 세션의 실제 생산 이력(PLANT_LOG)을 얹는다.
 */
(function () {
  'use strict';

  /* ================= 시뮬레이션 이력 ================= */

  // mulberry32 — 시드가 같으면 항상 같은 수열이 나온다
  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const seedOf = (s) => { let h = 2166136261; for (const c of s) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return h >>> 0; };

  const DAY = 86400000;
  const dayKey = (d) => `${d.getMonth() + 1}/${d.getDate()}`;
  const isWeekend = (d) => d.getDay() === 0 || d.getDay() === 6;

  let SENSORS = [];          // plant-overview 가 넘겨준 센서 정의
  const cache = new Map();   // lineId -> 30일 이력 (한 번만 만든다)

  function history(line) {
    if (cache.has(line.id)) return cache.get(line.id);
    const r = rng(seedOf(line.id));
    const util0 = parseFloat(line.util) || 93;
    const out = [];
    const today = new Date(); today.setHours(0, 0, 0, 0);

    for (let i = 29; i >= 0; i--) {
      const date = new Date(today.getTime() - i * DAY);
      const wk = isWeekend(date);
      const util = Math.max(72, Math.min(99, util0 + (r() - 0.5) * 6 - (wk ? 9 : 0)));
      const prod = Math.round((wk ? 430 : 780) * (util / 100) * (0.9 + r() * 0.2));

      // 라인의 현재 센서값이 임계에 가까울수록 불량률이 높게 나오도록 묶어 둔다
      let stress = 0;
      for (const s of SENSORS) {
        const v = line.vals[s.id];
        if (v == null) continue;
        stress += Math.max(0, v / s.thr - 0.7);
      }
      const base = 0.028 + stress * 0.012;
      const rate = Math.max(0.004, base + (r() - 0.45) * 0.025);
      const reject = Math.min(prod, Math.round(prod * rate));

      // 임계 초과 건수 — 현재 값이 임계에 근접한 센서에서 더 자주 발생
      const exceed = {};
      for (const s of SENSORS) {
        const v = line.vals[s.id];
        if (v == null) continue;
        const near = Math.max(0, v / s.thr - 0.72);
        exceed[s.id] = r() < near * 1.6 ? 1 + Math.floor(r() * near * 9) : 0;
      }

      out.push({
        date, key: dayKey(date), weekend: wk,
        prod, reject, good: prod - reject,
        rate: reject / prod,
        util: +util.toFixed(1),
        exceed,
      });
    }

    // 오늘 자에는 이번 세션의 실제 생산 이력을 얹는다 (있을 때만)
    const log = typeof window.PLANT_LOG === 'function' ? window.PLANT_LOG() : [];
    if (log.length) {
      const t = out[out.length - 1];
      const good = log.filter((e) => e.result === '양품').length;
      const rej = log.filter((e) => e.result === '불량').length;
      t.good += good; t.reject += rej; t.prod += good + rej;
      t.rate = t.reject / t.prod;
      t.live = true;                       // 표에 '실측 반영' 으로 표시
    }

    cache.set(line.id, out);
    return out;
  }

  /* ================= SVG 차트 ================= */

  const NS = 'http://www.w3.org/2000/svg';
  const C_GOOD = '#7d7979';   // 양품 — 정상 상태(중립)
  const C_BAD = '#ec3013';    // 불량 — 페이지 전역에서 경고를 뜻하는 강조색
  const el = (n, a) => { const e = document.createElementNS(NS, n); for (const k in a) if (a[k] != null) e.setAttribute(k, a[k]); return e; };
  const txt = (x, y, s, a) => { const t = el('text', a); t.setAttribute('x', x); t.setAttribute('y', y); t.textContent = s; return t; };
  const nf = (n) => n.toLocaleString('ko-KR');

  let tipEl = null;
  function tip(host, target, html) {
    target.addEventListener('mousemove', (ev) => {
      const r = host.getBoundingClientRect();
      tipEl.innerHTML = html;
      tipEl.style.left = Math.max(70, Math.min(r.width - 70, ev.clientX - r.left)) + 'px';
      tipEl.style.top = (ev.clientY - r.top) + 'px';
      tipEl.style.opacity = '1';
    });
    target.addEventListener('mouseleave', () => { tipEl.style.opacity = '0'; });
  }

  /* 일별 생산량 — 양품/불량 누적 막대 */
  function chartProduction(host, rows) {
    const W = 900, H = 260, L = 52, R = 16, T = 26, B = 34;
    const max = Math.max(...rows.map((d) => d.prod)) * 1.08;
    const iw = W - L - R, ih = H - T - B;
    const bw = Math.max(3, Math.min(26, (iw / rows.length) - (rows.length > 14 ? 3 : 6)));
    const x = (i) => L + (i + 0.5) * (iw / rows.length);
    const y = (v) => T + ih - (v / max) * ih;
    const s = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': `일별 생산량. ${rows.length}일간 총 ${nf(rows.reduce((a, d) => a + d.prod, 0))}개 생산.` });

    for (let g = 0; g <= 4; g++) {
      const v = (max / 4) * g;
      s.appendChild(el('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: 'g-grid' }));
      s.appendChild(txt(L - 9, y(v) + 4, nf(Math.round(v)), { class: 'g-tick', 'text-anchor': 'end' }));
    }

    const peak = rows.reduce((a, d, i) => (d.reject > rows[a].reject ? i : a), 0);
    rows.forEach((d, i) => {
      const hGood = (d.good / max) * ih, hBad = (d.reject / max) * ih;
      // 불량을 위에, 양품을 아래에. 두 채움 사이에 2px 표면 간격을 둔다.
      s.appendChild(el('rect', { x: x(i) - bw / 2, y: y(d.good), width: bw, height: Math.max(1, hGood), rx: 0, fill: C_GOOD }));
      if (d.reject > 0) {
        s.appendChild(el('rect', { x: x(i) - bw / 2, y: y(d.prod), width: bw, height: Math.max(1.5, hBad - 2), rx: 4, fill: C_BAD }));
      }
      if (rows.length <= 10 || i % Math.ceil(rows.length / 8) === 0) {
        s.appendChild(txt(x(i), H - 12, d.key, { class: 'g-tick', 'text-anchor': 'middle' }));
      }
      const hit = el('rect', { x: x(i) - (iw / rows.length) / 2, y: T - 6, width: iw / rows.length, height: ih + 12, fill: 'transparent' });
      tip(host, hit, `<b>${d.key}</b>${d.live ? ' · 실측 반영' : ''}<br>생산 ${nf(d.prod)} · 양품 ${nf(d.good)} · 불량 ${nf(d.reject)}<br>불량률 ${(d.rate * 100).toFixed(2)}% · 가동률 ${d.util}%`);
      s.appendChild(hit);
    });
    // 불량이 가장 많았던 날만 직접 라벨 (모든 점에 숫자를 붙이지 않는다)
    s.appendChild(txt(x(peak), y(rows[peak].prod) - 8, `불량 ${rows[peak].reject}`, { class: 'g-note', 'text-anchor': 'middle' }));
    host.appendChild(s);
  }

  /* 불량률 추이 — 선 그래프 + 목표선 */
  function chartRate(host, rows) {
    const W = 900, H = 210, L = 52, R = 16, T = 24, B = 34;
    const vals = rows.map((d) => d.rate * 100);
    const max = Math.max(5, Math.max(...vals) * 1.2), min = 0;
    const iw = W - L - R, ih = H - T - B;
    const x = (i) => L + (rows.length === 1 ? iw / 2 : (i / (rows.length - 1)) * iw);
    const y = (v) => T + ih - ((v - min) / (max - min)) * ih;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    const s = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': `불량률 추이. 평균 ${avg.toFixed(2)} 퍼센트.` });

    for (let g = 0; g <= 4; g++) {
      const v = (max / 4) * g;
      s.appendChild(el('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: 'g-grid' }));
      s.appendChild(txt(L - 9, y(v) + 4, v.toFixed(1) + '%', { class: 'g-tick', 'text-anchor': 'end' }));
    }
    // 목표선 3%
    s.appendChild(el('line', { x1: L, x2: W - R, y1: y(3), y2: y(3), class: 'g-target' }));
    s.appendChild(txt(W - R, y(3) - 6, '목표 3.0%', { class: 'g-note', 'text-anchor': 'end' }));

    s.appendChild(el('path', { d: vals.map((v, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1)).join(' '), class: 'g-line' }));
    vals.forEach((v, i) => {
      const over = v > 3;
      s.appendChild(el('circle', { cx: x(i), cy: y(v), r: rows.length > 14 ? 4 : 5, fill: over ? C_BAD : C_GOOD, class: 'g-dot' }));
      if (rows.length <= 10 || i % Math.ceil(rows.length / 8) === 0) {
        s.appendChild(txt(x(i), H - 12, rows[i].key, { class: 'g-tick', 'text-anchor': 'middle' }));
      }
      const hw = iw / rows.length;
      const hit = el('rect', { x: x(i) - hw / 2, y: T - 6, width: hw, height: ih + 12, fill: 'transparent' });
      tip(host, hit, `<b>${rows[i].key}</b><br>불량률 ${v.toFixed(2)}%${over ? ' — 목표 초과' : ''}<br>불량 ${nf(rows[i].reject)} / 생산 ${nf(rows[i].prod)}`);
      s.appendChild(hit);
    });
    host.appendChild(s);
  }

  /* 센서별 임계 초과 횟수 — 단일 계열 가로 막대 */
  function chartExceed(host, rows) {
    const tot = SENSORS.map((s) => ({
      label: s.label,
      n: rows.reduce((a, d) => a + (d.exceed[s.id] || 0), 0),
    })).sort((a, b) => b.n - a.n);
    const max = Math.max(1, ...tot.map((t) => t.n));
    const W = 900, L = 132, R = 56, T = 12, rowH = 26, H = T + tot.length * rowH + 10;
    const x = (v) => L + (v / max) * (W - L - R);
    const s = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': `센서별 임계 초과 횟수. 최다 ${tot[0].label} ${tot[0].n}회.` });

    tot.forEach((t, i) => {
      const yy = T + i * rowH;
      s.appendChild(txt(L - 10, yy + 15, t.label, { class: 'g-tick', 'text-anchor': 'end' }));
      s.appendChild(el('rect', { x: L, y: yy + 4, width: Math.max(1, x(t.n) - L), height: 15, rx: 4, fill: t.n ? C_BAD : C_GOOD, opacity: t.n ? 1 : 0.28 }));
      s.appendChild(txt(x(t.n) + 8, yy + 16, t.n + '회', { class: 'g-val' }));
      const hit = el('rect', { x: L, y: yy, width: W - L - R, height: rowH, fill: 'transparent' });
      tip(host, hit, `<b>${t.label}</b><br>임계 초과 ${t.n}회 / ${rows.length}일`);
      s.appendChild(hit);
    });
    host.appendChild(s);
  }

  /* ================= AI 요약 ================= */

  const AI_KEY = (lineId, weekLabel) => `piggy.ai.${lineId}.${weekLabel}`;

  function isoWeek(d) {
    // YYYY-Www 형식 (ISO 8601 주차)
    const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = date.getUTCDay() || 7;
    date.setUTCDate(date.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
    const week = Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
    return `${date.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
  }

  function loadAiCache(lineId, weekLabel) {
    try { return JSON.parse(localStorage.getItem(AI_KEY(lineId, weekLabel))); } catch { return null; }
  }
  function saveAiCache(lineId, weekLabel, data) {
    try { localStorage.setItem(AI_KEY(lineId, weekLabel), JSON.stringify(data)); } catch { /* noop */ }
  }

  async function fetchAiSummary(lineId, weekLabel, statsData) {
    const resp = await fetch(`http://${location.hostname}:8001/api/ai-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ line_id: lineId, week_label: weekLabel, stats: statsData }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
  }

  function renderAi(el, lineId, weekLabel, statsData) {
    const cached = loadAiCache(lineId, weekLabel);
    if (cached) {
      showAi(el, cached);
      return;
    }
    el.innerHTML = `<div class="ovg-ai-loading">AI 요약 생성 중…</div>`;
    fetchAiSummary(lineId, weekLabel, statsData)
      .then((data) => { saveAiCache(lineId, weekLabel, data); showAi(el, data); })
      .catch((err) => { el.innerHTML = `<div class="ovg-ai-err">AI 요약을 불러오지 못했습니다 — ${err.message}</div>`; });
  }

  function showAi(el, data) {
    const imps = (data.improvements || []).map((s) => `<li>${s}</li>`).join('');
    const ts = data.generated_at ? new Date(data.generated_at).toLocaleString('ko-KR', { hour12: false }) : '';
    el.innerHTML = `
      <div class="ovg-ai-badge">AI 분석</div>
      <p class="ovg-ai-summary">${data.summary || ''}</p>
      ${imps ? `<ul class="ovg-ai-imps">${imps}</ul>` : ''}
      ${ts ? `<p class="ovg-ai-ts">생성 시각: ${ts}</p>` : ''}`;
  }

  /* ================= 주간 이메일 구독 ================= */

  const SUB_KEY = 'piggy.weeklyReport';
  const loadSub = () => { try { return JSON.parse(localStorage.getItem(SUB_KEY)) || {}; } catch { return {}; } };
  const saveSub = (v) => { try { localStorage.setItem(SUB_KEY, JSON.stringify(v)); } catch { /* 저장 불가 환경 */ } };
  const validEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

  /* ================= 패널 ================= */

  let root = null, line = null, days = 7, subOpen = false;

  function stats(rows) {
    const prod = rows.reduce((a, d) => a + d.prod, 0);
    const rej = rows.reduce((a, d) => a + d.reject, 0);
    const util = rows.reduce((a, d) => a + d.util, 0) / rows.length;
    const exc = rows.reduce((a, d) => a + Object.values(d.exceed).reduce((x, y) => x + y, 0), 0);
    return { prod, rej, good: prod - rej, rate: prod ? rej / prod : 0, util, exc };
  }

  function tableHTML(rows) {
    return `<table class="ovg-table">
      <caption>일별 실적 표 — 위 그래프와 같은 데이터입니다</caption>
      <thead><tr><th scope="col">일자</th><th scope="col">생산</th><th scope="col">양품</th><th scope="col">불량</th><th scope="col">불량률</th><th scope="col">가동률</th></tr></thead>
      <tbody>${rows.slice().reverse().map((d) => `<tr${d.live ? ' class="live"' : ''}>
        <th scope="row">${d.key}${d.live ? ' <i>실측</i>' : ''}</th>
        <td>${nf(d.prod)}</td><td>${nf(d.good)}</td><td>${nf(d.reject)}</td>
        <td>${(d.rate * 100).toFixed(2)}%</td><td>${d.util}%</td></tr>`).join('')}</tbody>
    </table>`;
  }

  function render() {
    const rows = history(line).slice(-days);
    const k = stats(rows);
    const sub = loadSub();
    const on = !!sub.email && sub.lines && sub.lines.includes(line.id);

    root.querySelector('.ovg-title').textContent = `LINE ${line.id} — 생산 통계`;
    root.querySelector('.ovg-sub').textContent = `${line.note} · 가동률 ${line.util}%`;
    root.querySelectorAll('.ovg-tab').forEach((b) => {
      const onTab = Number(b.dataset.days) === days;
      b.classList.toggle('on', onTab);
      b.setAttribute('aria-selected', onTab ? 'true' : 'false');
    });

    root.querySelector('.ovg-kpis').innerHTML = [
      ['총 생산', nf(k.prod), '개'],
      ['양품률', (100 - k.rate * 100).toFixed(2), '%'],
      ['불량', nf(k.rej), '개'],
      ['평균 가동률', k.util.toFixed(1), '%'],
      ['임계 초과', nf(k.exc), '회'],
    ].map(([a, b, c]) => `<div class="ovg-kpi"><span>${a}</span><b>${b}<i>${c}</i></b></div>`).join('');

    const body = root.querySelector('.ovg-body');
    body.innerHTML = `
      <div class="ovg-ai" hidden></div>
      <section class="ovg-c">
        <h3>일별 생산량</h3>
        <p class="ovg-legend"><span><i style="background:${C_GOOD}"></i>양품</span><span><i style="background:${C_BAD}"></i>불량</span></p>
        <div class="ovg-plot" data-plot="prod"></div>
      </section>
      <section class="ovg-c">
        <h3>불량률 추이</h3>
        <p class="ovg-legend"><span><i style="background:${C_GOOD}"></i>목표 이내</span><span><i style="background:${C_BAD}"></i>목표 초과</span></p>
        <div class="ovg-plot" data-plot="rate"></div>
      </section>
      <section class="ovg-c">
        <h3>센서별 임계 초과 횟수</h3>
        <div class="ovg-plot" data-plot="exceed"></div>
      </section>
      <details class="ovg-details"><summary>데이터 표로 보기</summary>${tableHTML(rows)}</details>
      <p class="ovg-disclaimer">이 페이지에는 이력 데이터베이스가 없습니다. 위 통계는 라인별로 고정된 시드에서 만들어 낸 <b>시뮬레이션 값</b>이며, 오늘 자 실적에만 현재 세션의 실제 생산 이력이 더해집니다.</p>`;

    chartProduction(body.querySelector('[data-plot="prod"]'), rows);
    chartRate(body.querySelector('[data-plot="rate"]'), rows);
    chartExceed(body.querySelector('[data-plot="exceed"]'), rows);

    // AI 주간 요약 (7일 탭일 때만 표시)
    const aiEl = body.querySelector('.ovg-ai');
    if (aiEl) {
      if (days === 7) {
        const wk = isoWeek(new Date());
        const weekLabel = `${new Date().getFullYear()}년 ${wk.split('-')[1]}주차`;
        renderAi(aiEl, line.id, wk, k);
        aiEl.hidden = false;
      } else {
        aiEl.hidden = true;
      }
    }

    const mailBtn = root.querySelector('.ovg-mail');
    mailBtn.classList.toggle('on', on);
    mailBtn.textContent = on ? `주간 이메일 수신 중 · ${sub.email}` : '주간 이메일 받기';
    mailBtn.setAttribute('aria-expanded', subOpen ? 'true' : 'false');
    root.querySelector('.ovg-sub-panel').hidden = !subOpen;
    if (subOpen) renderSubPanel();

    root.querySelector('.ovg-print-period').textContent = days === 7 ? '최근 7일' : '최근 30일';
  }

  function renderSubPanel() {
    const sub = loadSub();
    const p = root.querySelector('.ovg-sub-panel');
    p.innerHTML = `
      <div class="ovg-field">
        <label for="ovg-email">받을 이메일 주소</label>
        <input id="ovg-email" type="email" inputmode="email" autocomplete="email"
               placeholder="name@company.com" value="${sub.email || ''}">
      </div>
      <div class="ovg-field">
        <label for="ovg-day">발송 요일</label>
        <select id="ovg-day">${['월', '화', '수', '목', '금', '토', '일']
          .map((d, i) => `<option value="${i}"${Number(sub.day ?? 0) === i ? ' selected' : ''}>${d}요일 오전 9시</option>`).join('')}</select>
      </div>
      <p class="ovg-field-n">LINE ${line.id} 의 주간 생산 통계를 매주 정해진 시각에 보냅니다.</p>
      <div class="ovg-sub-a">
        <button type="button" class="ovg-sub-save">구독 저장</button>
        ${sub.email ? '<button type="button" class="ovg-sub-off">구독 해지</button>' : ''}
      </div>
      <p class="ovg-sub-msg" role="status" aria-live="polite"></p>
      <p class="ovg-disclaimer">구독 설정은 이 브라우저에만 저장됩니다. 실제 발송에는 메일 서버가 필요합니다 — 아직 연결되어 있지 않습니다.</p>`;

    p.querySelector('.ovg-sub-save').onclick = () => {
      const email = p.querySelector('#ovg-email').value.trim();
      const msg = p.querySelector('.ovg-sub-msg');
      if (!validEmail(email)) { msg.textContent = '이메일 주소 형식을 확인해 주세요.'; msg.className = 'ovg-sub-msg bad'; return; }
      const cur = loadSub();
      const lines = new Set(cur.lines || []); lines.add(line.id);
      saveSub({ email, day: Number(p.querySelector('#ovg-day').value), lines: [...lines], savedAt: new Date().toISOString() });
      const dn = ['월', '화', '수', '목', '금', '토', '일'][Number(p.querySelector('#ovg-day').value)];
      msg.textContent = `구독을 저장했습니다 — 매주 ${dn}요일 오전 9시, ${email} 로 LINE ${line.id} 통계를 보냅니다.`;
      msg.className = 'ovg-sub-msg ok';
      render();
      p.querySelector('.ovg-sub-msg').textContent = msg.textContent;
      p.querySelector('.ovg-sub-msg').className = 'ovg-sub-msg ok';
    };
    const off = p.querySelector('.ovg-sub-off');
    if (off) off.onclick = () => {
      const cur = loadSub();
      const lines = (cur.lines || []).filter((x) => x !== line.id);
      if (lines.length) saveSub({ ...cur, lines }); else { try { localStorage.removeItem(SUB_KEY); } catch { /* noop */ } }
      render();
      const msg = root.querySelector('.ovg-sub-msg');
      if (msg) { msg.textContent = `LINE ${line.id} 구독을 해지했습니다.`; msg.className = 'ovg-sub-msg ok'; }
    };
  }

  function build() {
    root = document.createElement('div');
    root.className = 'ovg';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-labelledby', 'ovg-title');
    root.hidden = true;
    root.innerHTML = `
      <div class="ovg-card">
        <header class="ovg-head">
          <div>
            <h2 class="ovg-title" id="ovg-title">LINE</h2>
            <p class="ovg-sub"></p>
          </div>
          <div class="ovg-tabs" role="tablist" aria-label="통계 기간">
            <button class="ovg-tab" type="button" role="tab" data-days="7">7일</button>
            <button class="ovg-tab" type="button" role="tab" data-days="30">30일</button>
          </div>
          <button class="ovg-x" type="button" aria-label="통계 닫기">✕</button>
        </header>
        <p class="ovg-print-h">LINE <span class="ovg-print-line"></span> 생산 통계 · <span class="ovg-print-period"></span> · <span class="ovg-print-date"></span></p>
        <div class="ovg-kpis"></div>
        <div class="ovg-scroll"><div class="ovg-body"></div><div class="ovg-tip"></div></div>
        <footer class="ovg-foot">
          <button class="ovg-pdf" type="button">PDF로 저장</button>
          <button class="ovg-mail" type="button" aria-expanded="false">주간 이메일 받기</button>
          <div class="ovg-sub-panel" hidden></div>
        </footer>
      </div>`;
    document.body.appendChild(root);
    tipEl = root.querySelector('.ovg-tip');
    tipEl.className = 'ovg-tip';

    root.querySelector('.ovg-tabs').addEventListener('click', (e) => {
      const b = e.target.closest('.ovg-tab');
      if (!b) return;
      days = Number(b.dataset.days);
      render();
    });
    root.querySelector('.ovg-x').onclick = API.close;
    root.addEventListener('click', (e) => { if (e.target === root) API.close(); });
    root.querySelector('.ovg-pdf').onclick = () => {
      root.querySelector('.ovg-print-date').textContent = new Date().toLocaleString('ko-KR', { hour12: false });
      const d = root.querySelector('.ovg-details');
      const wasOpen = d.open; d.open = true;              // 표까지 인쇄에 포함
      document.body.classList.add('printing-stats');
      const restore = () => { document.body.classList.remove('printing-stats'); d.open = wasOpen; window.removeEventListener('afterprint', restore); };
      window.addEventListener('afterprint', restore);
      window.print();
      setTimeout(restore, 1500);                          // afterprint 미지원 대비
    };
    root.querySelector('.ovg-mail').onclick = () => { subOpen = !subOpen; render(); };
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !root.hidden) API.close(); });
  }

  const API = {
    /** @param {object} l 라인 정보 {id,label,note,util,vals}  @param {Array} sensors 센서 정의 */
    open(l, sensors) {
      if (sensors) SENSORS = sensors;
      if (!root) build();
      line = l; days = 7; subOpen = false;
      root.querySelector('.ovg-print-line').textContent = l.id;
      root.hidden = false;
      document.body.classList.add('ovg-on');
      render();
      root.querySelector('.ovg-x').focus();
    },
    close() {
      if (!root || root.hidden) return;
      root.hidden = true;
      document.body.classList.remove('ovg-on');
      const back = document.querySelector('.ov-line.on .ov-graph');
      if (back) back.focus();
    },
    isOpen: () => !!root && !root.hidden,
  };
  window.LINE_STATS = API;
})();
