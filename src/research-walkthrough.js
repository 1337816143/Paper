/* Isolated, offline research explanation. No storage, network, grading, or source-block edits. */
(function (global) {
  'use strict';
  const VERSION = '1.0.0';
  const DEFAULTS = Object.freeze({ crop1: 10000, crop2: 20000, crop3: 30000, manure1: 5, manure2: 7,
    wheat: 6, maize: 8, irrigation: 300, area: 0.6, laborCap: 100, marginA: 100, waterA: 30, costAW: 1000, costAM: 900, waterAW: 300, waterAM: 150, laborAW: 45.5, laborAM: 28.5 });
  const LIMITS = Object.freeze({ crop1: [0, 100000], crop2: [0, 100000], crop3: [0, 100000],
    manure1: [0, 100], manure2: [0, 100], wheat: [0, 15], maize: [0, 20], irrigation: [0, 600],
    area: [0.1, 10], laborCap: [0, 160], marginA: [0, 240], waterA: [0, 80], costAW: [0, 2000], costAM: [0, 2000], waterAW: [0, 600], waterAM: [0, 600], laborAW: [0, 120], laborAM: [0, 120] });
  function finite(value, label) { if (!Number.isFinite(value)) throw new TypeError(label + ' 必须是有限数字'); return value; }
  function validate(values) {
    const result = { ...DEFAULTS, ...values };
    Object.entries(LIMITS).forEach(([key, [min, max]]) => {
      finite(result[key], key); if (result[key] < min || result[key] > max) throw new RangeError(key + ' 超出教学输入范围');
    });
    return result;
  }
  function aggregate(cropKg, manureMg) {
    if (!cropKg.length || !manureMg.length) throw new RangeError('示例表不能为空');
    [...cropKg, ...manureMg].forEach(v => { finite(v, '质量'); if (v < 0) throw new RangeError('质量不能为负'); });
    const crops = cropKg.map(v => v / 1000);
    const wrong = crops.flatMap((crop, i) => manureMg.map((manure, j) => ({ crop, manure, cropId: i + 1, manureId: j + 1 })));
    return { crops, wrong, correctCrop: crops.reduce((a, b) => a + b, 0), correctManure: manureMg.reduce((a, b) => a + b, 0),
      wrongCrop: wrong.reduce((s, row) => s + row.crop, 0), wrongManure: wrong.reduce((s, row) => s + row.manure, 0) };
  }
  function indicators(values) {
    const v = validate(values), revenueWheat = v.wheat * 300, revenueMaize = v.maize * 250;
    const revenue = revenueWheat + revenueMaize, gm = revenue - 1900, energyWheat = v.wheat * 3.17, energyMaize = v.maize * 3.35;
    const irrigation = v.irrigation + 150, recharge = 0.2 * (500 + irrigation), gwd = irrigation - recharge;
    return { revenueWheat, revenueMaize, revenue, gm, gmTotal: gm * v.area,
      energyWheat, energyMaize, dey: energyWheat + energyMaize, deyTotal: (energyWheat + energyMaize) * v.area,
      wheatLabor: 45.5, maizeLabor: 28.5, labor: 74, laborTotal: 74 * v.area,
      irrigation, recharge, gwd, gwdVolume: gwd * 10 * v.area,
      wheatN: 47, maizeN: 36.5, nitrogen: 83.5, nitrogenTotal: 83.5 * v.area,
      emissions: 4, sequestration: 1.5, ghg: 2.5, ghgTotal: 2.5 * v.area,
      insecticide: 3, herbicide: 2, fungicide: 1, pesticide: 6 };
  }
  function dominates(a, b) { return a.margin >= b.margin && a.water <= b.water && (a.margin > b.margin || a.water < b.water); }
  function fronts(rows) {
    let remaining = rows.slice(); const result = [];
    while (remaining.length) {
      const front = remaining.filter(row => !remaining.some(other => dominates(other, row)));
      if (!front.length) throw new Error('无法建立前沿');
      result.push(front.map(row => row.id)); const ids = new Set(front.map(row => row.id));
      remaining = remaining.filter(row => !ids.has(row.id));
    }
    return result;
  }
  function distance(point, ideal, ranges) {
    if (!point.length || point.length !== ideal.length || point.length !== ranges.length) throw new RangeError('距离向量维数不一致');
    [...point, ...ideal, ...ranges].forEach(v => finite(v, '距离输入'));
    if (ranges.some(v => v < 0)) throw new RangeError('范围不能为负');
    const d = point.map((v, i) => {
      if (!ranges[i] && v !== ideal[i]) throw new RangeError('常数列的值必须等于理想值');
      return ranges[i] ? Math.abs(v - ideal[i]) / ranges[i] : 0;
    });
    const mean = d.reduce((s, v) => s + v, 0) / d.length;
    return { d, mean, MIDIP: Math.sqrt(d.reduce((s, v) => s + v * v, 0)),
      HDIP: d.length > 1 ? Math.sqrt(d.reduce((s, v) => s + (v - mean) ** 2, 0) / (d.length - 1)) : null };
  }
  function decision(values) {
    const v = validate(values), rows = [{ id: 'A', margin: v.marginA, water: v.waterA, labor: 80 },
      { id: 'B', margin: 80, water: 40, labor: 85 }, { id: 'C', margin: 120, water: 50, labor: 90 }, { id: 'D', margin: 200, water: 10, labor: 140 }];
    const feasible = rows.filter(row => row.labor <= v.laborCap), excluded = rows.filter(row => row.labor > v.laborCap);
    if (!feasible.length) return { rows, feasible, excluded, fronts: [], ideal: null, ranges: null, distances: {} };
    const ideal = [Math.max(...feasible.map(r => r.margin)), Math.min(...feasible.map(r => r.water))];
    const ranges = [Math.max(...feasible.map(r => r.margin)) - Math.min(...feasible.map(r => r.margin)), Math.max(...feasible.map(r => r.water)) - Math.min(...feasible.map(r => r.water))];
    const distances = Object.fromEntries(feasible.map(r => [r.id, distance([r.margin, r.water], ideal, ranges)]));
    return { rows, feasible, excluded, fronts: fronts(feasible), ideal, ranges, distances };
  }
  function farmPipeline(values) {
    const v = validate(values);
    const sourceRows = [
      { id: 'A', costs: [v.costAW, v.costAM], irrigation: [v.waterAW, v.waterAM], labor: [v.laborAW, v.laborAM] },
      { id: 'B', costs: [1100, 1000], irrigation: [315, 160], labor: [50, 30] },
      { id: 'C', costs: [850, 750], irrigation: [330, 170], labor: [55, 30] },
      { id: 'D', costs: [650, 550], irrigation: [230, 120], labor: [90, 50] }
    ];
    const rows = sourceRows.map(r => {
      const harvestKg = [6000, 8000], area = 1, yieldMgHa = harvestKg.map(kg => kg / 1000 / area), prices = [300, 250];
      const revenue = yieldMgHa.reduce((sum, y, i) => sum + y * prices[i], 0);
      const cost = r.costs.reduce((a, b) => a + b, 0), irrigation = r.irrigation.reduce((a, b) => a + b, 0), recharge = 0.2 * (500 + irrigation);
      return { id: r.id, source: r, harvestKg, area, yieldMgHa, prices, revenue, cost, irrigation, recharge,
        margin: revenue - cost, water: irrigation - recharge, labor: r.labor.reduce((a, b) => a + b, 0) };
    });
    const feasible = rows.filter(r => r.labor <= v.laborCap), excluded = rows.filter(r => r.labor > v.laborCap), observedFronts = fronts(rows);
    if (!feasible.length) return { rows, feasible, excluded, fronts: [], observedFronts, ideal: null, ranges: null, distances: {} };
    const ideal = [Math.max(...feasible.map(r => r.margin)), Math.min(...feasible.map(r => r.water))];
    const ranges = [Math.max(...feasible.map(r => r.margin)) - Math.min(...feasible.map(r => r.margin)), Math.max(...feasible.map(r => r.water)) - Math.min(...feasible.map(r => r.water))];
    return { rows, feasible, excluded, observedFronts, fronts: fronts(feasible), ideal, ranges,
      distances: Object.fromEntries(feasible.map(r => [r.id, distance([r.margin, r.water], ideal, ranges)])) };
  }
  function calculate(values) { const v = validate(values); return { values: v, join: aggregate([v.crop1, v.crop2, v.crop3], [v.manure1, v.manure2]), indicators: indicators(v), decision: farmPipeline(v) }; }
  const STEP_NAMES = ['原始记录', '汇总与单位', '算出指标', '可行性扩展', 'Pareto 比较', '距离与解释'];
  const METRICS = [['gm', '毛利 ↑'], ['dey', '食物能量 ↑'], ['labor', '劳动 ↓'], ['gwd', '地下水 ↓'], ['nl', '氮损失 ↓'], ['ghg', '净温室气体 ↓'], ['pu', '农药次数 ↓']];
  const ESC = value => String(value).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const fmt = (v, places = 3) => Number(v.toFixed(places)).toLocaleString('en-US', { maximumFractionDigits: places });
  const badge = (type, text) => `<span class="rw-badge rw-${type}">${ESC(text)}</span>`;
  const source = (label, route) => `<a href="#/${route}">${label} →</a>`;
  function table(caption, headers, rows) { return `<div class="rw-table-wrap" tabindex="0" role="region" aria-label="${ESC(caption)}，必要时可横向滚动"><table><caption>${caption}</caption><thead><tr>${headers.map(h => `<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map((v, i) => i ? `<td>${v}</td>` : `<th scope="row">${v}</th>`).join('')}</tr>`).join('')}</tbody></table></div>`; }
  function chain(items, label) { return `<div class="rw-chain" role="group" aria-label="${ESC(label)}">${items.map((item, i) => `${i ? '<span class="rw-arrow" aria-hidden="true">→</span>' : ''}<div class="rw-chain-node"><span>${ESC(item[0])}</span><strong>${ESC(item[1])}</strong><small>${ESC(item[2] || '')}</small></div>`).join('')}</div>`; }
  function lesson(prerequisite, why, action) { return `<dl class="rw-reason"><div><dt>先知道</dt><dd>${prerequisite}</dd></div><div><dt>为什么</dt><dd>${why}</dd></div><div><dt>现在做</dt><dd>${action}</dd></div></dl>`; }
  function outcome(title, body) { return `<div class="rw-outcome"><h4>${title}</h4><p>${body}</p></div>`; }
  let serial = 0;
  const mounted = new WeakMap();
  const activeControllers = new Set();
  function mount(container) {
    if (!container || !container.ownerDocument) throw new TypeError('需要一个独立的挂载容器');
    if (mounted.has(container)) return mounted.get(container);
    const doc = container.ownerDocument, win = doc.defaultView, uid = `rw-${++serial}`, mq = win.matchMedia('(prefers-reduced-motion: reduce)');
    let state = { values: { ...DEFAULTS }, step: 0, metric: 'gm', joinWrong: false, selected: 'A', playing: false, speed: 12000 };
    let timer = null, destroyed = false, routeInactive = false, invalid = new Set();
    const element = doc.createElement('div'); element.className = 'paper-walkthrough'; element.tabIndex = -1;
    element.setAttribute('role', 'region'); element.setAttribute('aria-labelledby', `${uid}-title`);
    element.innerHTML = `<header class="rw-header"><span class="rw-kicker">看一遍数据怎样变成结论</span><h2 id="${uid}-title">从一张记录表，走到一个有边界的判断</h2><p>不用先学会编程。看表、改数字、逐步跟随计算；每一步都能直接打开。</p></header>
      <div class="rw-evidence"><p>${badge('source', '作者依据')} 梁2022：调查案例 → 七指标 → Pareto 前沿 → 聚类 → 群组距离与比较。</p><p>${badge('toy', '合成讲解')} 主流程始终跟随同一张A–D四农场表：两季收获、价格、成本、灌溉和劳动 → 年度指标 → 候选集 → 前沿 → 距离。所有农场记录为<strong>合成输入，不是作者数据复现</strong>。</p><p>${badge('extension', '研究迁移扩展')} 第4步资源约束为教学补充；原论文是观测案例识别。第6步只用单点演示群组中心距离，没有重做原文聚类。</p></div>
      <nav class="rw-steps" aria-label="自由选择解释步骤">${STEP_NAMES.map((name, i) => `<button type="button" data-step="${i}" aria-controls="${uid}-stage"><span aria-hidden="true">${String(i + 1).padStart(2, '0')}</span>${name}</button>`).join('')}</nav>
      <div class="rw-controls" role="group" aria-label="演示控制"><button type="button" data-action="previous" aria-label="上一步">← 上一步</button><button type="button" data-action="play" aria-pressed="false">播放流程</button><button type="button" data-action="next" aria-label="单步到下一步">下一步 →</button><label for="${uid}-speed">每步停留 <select id="${uid}-speed" data-action="speed"><option value="12000">12秒</option><option value="20000">20秒</option><option value="30000">30秒</option></select></label><button type="button" data-action="reset">重置示例</button></div>
      <p class="rw-play-help">默认不播放。播放只按顺序切换步骤；可随时暂停、改数或单步。键盘在此面板的非输入区域可用 ← / → 换步，空格播放或暂停。</p>
      <p class="rw-motion-note" ${mq.matches ? '' : 'hidden'}>已遵循系统“减少动态效果”：不播放动画，仍可手动换步。</p>
      <p class="rw-status" role="status" aria-live="polite" aria-atomic="true"></p>
      <section class="rw-stage" id="${uid}-stage" aria-label="当前步骤"></section>
      <details class="rw-side-lessons"><summary>可选放大镜：错误连接与其余指标怎么计算？</summary><p>以下是另外的独立算术例，不是上方A–D农场的输入或输出；不改变主流程的前沿。</p><details class="rw-side-join"><summary>3×2明细连接为何把60/12变成120/36？</summary><div class="rw-side-join-body"></div></details><details class="rw-side-metrics"><summary>七个指标分别怎样代入、换单位？</summary><div class="rw-side-metric-body"></div></details></details>
      <details class="rw-source-detail"><summary>原文依据、没有复现的部分与可运行核算</summary><p>原文：Liang et al. (2022), Agricultural Systems 201, 103471，方法 §2.4–2.7，正文式1–8。主文明确给出的能量系数3.17 / 3.35 GCal/Mg与地下水补给系数0.2在示例中保留；它们不能自动移用于海南。</p><p>缺少完整作者原始记录、价格与作业参数表、补充电量→灌溉 / 施氮→损失 / 排放与土壤碳关系。83.5 kg N 和2.5 Mg CO₂-eq只是独立合成算术结果，不能互相反推。</p><p>本例未重现344案例、56个第一前沿案例、9个典型群组成员；未执行HCA或证明管理措施的因果效果。</p><div class="rw-links">${source('原文获取与边界', 'original/liang-2022')} ${source('七项完整公式与代入', 'liang-indicator-audit')} ${source('数据结构详解', 'data-schema')} ${source('理想点详解', 'ideal-distance')} ${source('下载本例代码与CSV', 'offline')}</div><p>主流程的同一套四农场数字由离线包 examples/farm_walkthrough.py 与 farm_walkthrough_synthetic.csv 核算。另两个脚本 research_pipeline_walkthrough.py / seven_indicators_worked.py 只核算独立的连接、100/30目标表和七项算术放大镜，不能用来验证主流程1900/260结果。本面板不联网、不读写个人记录。</p></details>`;
    container.append(element);
    const stage = element.querySelector('.rw-stage'), status = element.querySelector('.rw-status');
    const q = selector => element.querySelector(selector);
    function say(text) { status.textContent = text; }
    function heading(kicker, title, text) { return `<header class="rw-stage-head"><span class="rw-kicker">${kicker}</span><h3>${title}</h3><p>${text}</p></header>`; }
    function field(key, label, unit, type = 'number', step = '1') {
      const [min, max] = LIMITS[key], id = `${uid}-${key}`;
      return `<div class="rw-field"><label for="${id}">${label} <span>(${unit})</span></label><div><input id="${id}" data-field="${key}" type="${type}" min="${min}" max="${max}" step="${step}" value="${state.values[key]}" aria-describedby="${id}-help ${id}-error"/><output data-for="${key}" for="${id}">${fmt(state.values[key])}</output></div><small id="${id}-help">合成输入；范围 ${min}–${max} ${unit}</small><span class="rw-error" id="${id}-error" role="alert"></span></div>`;
    }
    function controls() {
      element.classList.toggle('rw-playing', state.playing && !mq.matches);
      element.querySelectorAll('[data-step]').forEach(button => { const active = +button.dataset.step === state.step; button.setAttribute('aria-current', active ? 'step' : 'false'); });
      q('[data-action="previous"]').disabled = state.step === 0;
      q('[data-action="next"]').disabled = state.step === STEP_NAMES.length - 1;
      const play = q('[data-action="play"]'); play.textContent = state.playing ? '暂停流程' : state.step === 5 ? '从头播放' : '播放流程'; play.setAttribute('aria-pressed', String(state.playing)); play.disabled = mq.matches || invalid.size > 0;
      q('[data-action="speed"]').disabled = mq.matches;
    }
    function stop(message) { state.playing = false; if (timer !== null) win.clearTimeout(timer); timer = null; controls(); if (message) say(message); }
    function schedule() {
      if (timer !== null) win.clearTimeout(timer);
      timer = win.setTimeout(() => { timer = null; if (destroyed || !element.isConnected || doc.hidden) { stop(); return; }
        if (state.step >= 5) { stop('已到距离解释。可以回看任意一步，或修改输入。'); return; }
        show(state.step + 1, false); if (state.step === 5) stop('已到第6步。播放已停止，留在结果供你阅读。'); else schedule();
      }, state.speed);
    }
    function play() { if (mq.matches || invalid.size) return; if (state.playing) { stop('已暂停；当前数字和步骤保留。'); return; }
      if (state.step === 5) show(0, false); state.playing = true; controls(); say(`正在演示，每步停留${state.speed / 1000}秒；可随时暂停。`); schedule(); }
    function renderStage() {
      invalid.clear();
      const headings = [
        heading('01 / 同一张四农场表 · 所有农户记录均为合成', '先看记录：一行是一个农场的一个作物季', 'A、B、C、D都用同一块1 ha土地，一年依次种小麦和玉米。八行原始记录将一路变成四行年度结果。'),
        heading('02 / 延续A–D的八行记录', '统一单位，再把同一农场的两季合并', '先收获kg÷1,000÷面积ha得到Mg/ha；再按农场与年份，把对应的两季收入、成本、灌溉和劳动归到同一年度账。'),
        heading('03 / 从同一批记录算出年度指标', '收入减成本；取水减补给；两季劳动相加', '每个结果都能追溯到前两步的一行记录。为看清整条链，主流程只比较毛利和地下水消耗，劳动另作迁移约束；不是原文完整七目标分析。'),
        heading('04 / A–D决策表 · 研究迁移扩展', '先问“做得到吗”，再问“表现好不好”', '继续使用刚算出的A–D结果。两个绩效目标是毛利提高、净地下水消耗降低；劳动在这里另作硬约束。'),
        heading('05 / 继续使用同一张A–D表', 'Pareto：有没有另一方案全面不差？', '只比较上一步可行的方案。支配需要“每个目标都不差，至少一个更好”；不先把两个目标加成一个总分。'),
        heading('06 / 继续使用同一张A–D表', '先消掉单位，再看离理想点多远', '把每列当前可行集合的最好值拼成理想点。它可能并不是任何真实可行方案。这里只把一个方案当单点群组来演示距离；原文还要先聚类并求群组中心。')
      ];
      let fields = '';
      if (state.step === 0) fields = `<div class="rw-inputs">${field('costAW', 'A的小麦季可变成本', 'USD/ha', 'number', '10')}${field('costAM', 'A的玉米季可变成本', 'USD/ha', 'number', '10')}</div>`;
      if (state.step === 1) fields = `<div class="rw-inputs">${field('waterAW', 'A的小麦季地下水灌溉', 'mm', 'range', '5')}${field('waterAM', 'A的玉米季地下水灌溉', 'mm', 'range', '5')}</div>`;
      if (state.step === 2) fields = `<div class="rw-switch" role="group" aria-label="追踪一个农场的计算">${['A','B','C','D'].map(id=>`<button type="button" data-select="${id}" aria-pressed="${state.selected===id}">跟随农场 ${id}</button>`).join('')}</div>`;
      if (state.step === 3) fields = `<div class="rw-inputs">${field('laborCap', '全场可用年度劳动上限', 'h/year（本例1 ha）', 'range')}</div>`;
      if (state.step === 4) fields = `<div class="rw-inputs">${field('costAW', '改变A的小麦季成本', 'USD/ha', 'range', '10')}${field('waterAW', '改变A的小麦季灌溉', 'mm', 'range', '5')}</div>`;
      stage.innerHTML = headings[state.step] + fields + '<div class="rw-result"></div>';
      renderResult(); controls();
    }
    function farmRaw(model) {
      const rows = model.decision.rows.flatMap(r => ['小麦','玉米'].map((crop, i) => [r.id+' / '+crop, fmt(r.harvestKg[i]), fmt(r.prices[i]), fmt(r.source.costs[i]), fmt(r.source.irrigation[i]), fmt(r.source.labor[i])]));
      return lesson('一行有一个明确对象：某农场、某年、某作物季。这个示例的记录键是农场×年份×作物季。', '产量、成本、灌溉与劳动必须对应同一季、同一面积，不能把重复行当作新投入。', '读下表的单位。可先改A的成本，后续毛利、前沿与距离会用同一处修改重算。') +
        table('同一年、同一块1 ha地；每行的记录与单位明确', ['农场 / 作物季','总收获 (kg)','销售价 (USD/Mg)','可变成本 (USD/ha)','地下水灌溉 (mm)','劳动 (h/ha)'], rows) +
        `<p class="rw-boundary">${badge('toy','共同假设')} 四个农场都用合成收获6,000/8,000kg、价格300/250USD/Mg、1ha面积、年降水500mm。成本、灌溉和劳动因农场不同。劳动是已给定的合成季总人时，不声称由真实作业日志估计。</p>` +
        outcome('接下来具体交出什么？','八条带单位、带键的季记录。下一步不换数据：只换质量单位、生成每公顷单产，再将每个农场两季归入同一年。') +
        `<p class="rw-boundary">多个明细表不能只按农场ID直接连接。页面下方“可选放大镜”另用60/12例解释3×2重复；它不是本表的收获或粪肥。</p>`;
    }
    function farmAggregate(model) {
      const a = model.decision.rows[0];
      return lesson('1Mg=1吨=1,000kg；单产=收获质量÷面积。两季共用同一块地，年度土地分母仍是1ha。', '先换对单位，才能与USD/Mg价格相乘。分季成本相加一次；年降水500mm不能每季各加一遍。', '按A的记录先核算；B/C/D用相同规则，保持原来的成本、灌溉和劳动差异。') +
        chain([['A小麦：质量→单产','6,000÷1,000÷1 = 6 Mg/ha','乘300USD/Mg → 1,800USD/ha'],['A玉米：质量→单产','8,000÷1,000÷1 = 8 Mg/ha','乘250USD/Mg → 2,000USD/ha'],['合并同一年度收入','1,800+2,000 = 3,800','USD/ha/year，不是3,800Mg']], '从原始收获到同一年度收入') +
        table('同一张输入表的年度归集结果（尚未扣成本或补给）',['农场','收入 (USD/ha/year)','成本 (USD/ha/year)','灌溉 (mm/year)','劳动 (h/ha/year)'],model.decision.rows.map(r=>[r.id,fmt(r.revenue),r.source.costs.map(n=>fmt(n)).join('+')+'='+fmt(r.cost),r.source.irrigation.map(n=>fmt(n)).join('+')+'='+fmt(r.irrigation),r.source.labor.map(n=>fmt(n)).join('+')+'='+fmt(r.labor)])) +
        outcome('这一层产物还不是最终绩效',`A现在有收入${fmt(a.revenue)}、成本${fmt(a.cost)}、灌溉${fmt(a.irrigation)}、劳动${fmt(a.labor)}。下一步用相同数值计算毛利与净地下水消耗；灌溉量不能直接改名为净消耗。`);
    }
    function farmMetrics(model) {
      const r=model.decision.rows.find(row=>row.id===state.selected)||model.decision.rows[0], s=r.source;
      return lesson('毛利是销售收入减可变成本；地下水消耗是取用量减估计补给；劳动是人时。', '算指标的目的是把明确问题转成可比较的列，不是把数据任意加出一个总分。', `现在逐笔跟随${r.id}；点击上方A/B/C/D可查看同一计算规则如何产生不同结果。`) +
        `<p>${badge('source','正文式1、3、4–5')}${badge('toy','全部农场输入为合成')} 补给系数0.2是梁2022文中给定的当地值。输入已是灌溉深度；未补电量→灌溉关系。</p>` +
        chain([['毛利 GM',`3,800−(${fmt(s.costs[0])}+${fmt(s.costs[1])}) = ${fmt(r.margin)}`,'USD/ha/year；本文成本边界下的余额'],['净地下水消耗 GWD',`${fmt(r.irrigation)}−0.2×(500+${fmt(r.irrigation)}) = ${fmt(r.water)}` ,`mm/year；估计补给${fmt(r.recharge)}mm`],['年度劳动 LU',`${fmt(s.labor[0])}+${fmt(s.labor[1])} = ${fmt(r.labor)}`,'h/ha/year；人时，不是劳动人数']], `${r.id}从输入到三列输出`) +
        table('得到4行年度绩效矩阵：下一步仍用这些数字',['农场','毛利 ↑ (USD/ha/year)','净地下水消耗 ↓ (mm/year)','劳动 (h/ha/year)'],model.decision.rows.map(row=>[row.id,fmt(row.margin),fmt(row.water),fmt(row.labor)])) +
        outcome('为什么不把四列排成一个单榜？',`毛利越高、净地下水消耗越低是本例两个改善方向。还没有给偏好权重；先把劳动资源门槛说清，再作逐对比较。当前若不加资源门槛，第一前沿为{${model.decision.observedFronts[0].join(', ')}}。`) +
        `<p class="rw-boundary">主流程没有捏造氮损失或温室气体输入响应系数。其余指标在下方“七个指标”放大镜中作为独立算术解释；不能把那里83.5kg N或2.5Mg CO₂-eq塞进这张4农场表。</p>`;
    }
    function raw(model) {
      const v = model.values;
      return lesson('主键像记录的身份证；连接键像用来配对的门牌号。这里只保留示例所需字段。', '两张表都写F01，不代表每条收获要和每条粪肥配成一个新的事实。', '先在表头读“每行是什么”和单位，再改一项数量观察合计。') +
        `<div class="rw-two">${table('收获表：每行是一条收获记录', ['记录键', '农场 / 年', '收获质量 (kg)'], [1, 2, 3].map(i => [`H0${i}`, 'F01 / 同一年', fmt(v['crop' + i])]))}${table('粪肥表：每行是一条入场记录', ['记录键', '农场 / 年', '粪肥质量 (Mg)'], [1, 2].map(i => [`M0${i}`, 'F01 / 同一年', fmt(v['manure' + i])]))}</div>` +
        chain([['先统一质量单位', '1 Mg = 1 t = 1,000 kg', 'Mg是兆克，不是mg毫克'], ['再选汇总粒度', '一行 = 农场 × 年', '不能直接把明细连接后相加']], '从明细到年度记录的准备') +
        outcome('这一层交给下一步什么？', `3条收获与2条粪肥明细，以及明确的农场/年份键。收获合计应为 ${fmt(model.join.correctCrop)} Mg；粪肥应为 ${fmt(model.join.correctManure)} Mg。还没有单产、成本或氮含量，不能直接计算七指标。`);
    }
    function joined(model) {
      const j = model.join;
      let rows = state.joinWrong ? table('错误做法：两张明细表只按农场/年份直接配对', ['收获 × 粪肥', '收获 (Mg)', '粪肥 (Mg)'], j.wrong.map(r => [`H0${r.cropId} × M0${r.manureId}`, fmt(r.crop), fmt(r.manure)])) :
        table('正确做法：先在每张表内按农场/年份求和，再连接', ['农场 / 年', '年度收获 (Mg)', '年度粪肥 (Mg)'], [['F01 / 同一年', fmt(j.correctCrop), fmt(j.correctManure)]]);
      return lesson('粒度就是“一行代表什么”。Σ只是把指定的数相加。', '3条记录 × 2条记录会生成6行：每笔收获重复2遍，每笔粪肥重复3遍。', '对照下面的行数与合计；“直接连接”与“先汇总”不是同一种数据。') +
        chain([['收获单位转换', `${j.crops.map(v => fmt(v)).join(' + ')} = ${fmt(j.correctCrop)} Mg`, '每笔kg先除以1,000'], ['粪肥独立求和', `${fmt(model.values.manure1)} + ${fmt(model.values.manure2)} = ${fmt(j.correctManure)} Mg`, '不因为收获条数而重复'], ['目标年度表', '1行 F01 × 同一年', '每张汇总表的键必须唯一']], '分别聚合再连接') + rows +
        `<div class="rw-totals ${state.joinWrong ? 'rw-warning' : ''}"><span>${state.joinWrong ? '错误连接：6行' : '正确连接：1行'}</span><strong>收获 ${fmt(state.joinWrong ? j.wrongCrop : j.correctCrop)} Mg · 粪肥 ${fmt(state.joinWrong ? j.wrongManure : j.correctManure)} Mg</strong></div>` +
        outcome('同一批原始数据，错误只来自整理方式', `直接连接会得到 ${fmt(j.wrongCrop)} / ${fmt(j.wrongManure)} Mg；正确总量是 ${fmt(j.correctCrop)} / ${fmt(j.correctManure)} Mg。默认值正是120/36与60/12的差别。下一步若要算“每ha”，还必须有对应面积；如果已是每ha，不再除一次。`) + source('查看完整键与数据字典解释', 'data-schema');
    }
    function metric(model) {
      const v = model.values, m = model.indicators, area = fmt(v.area);
      const common = `<p class="rw-boundary">${badge('toy', '独立算术例')} 同一块1 ha地先种小麦、再种玉米，一年仍是1 ha·year；两季不是2 ha。面积调节只改变可加总的总量，不改变每ha强度。</p>`;
      const scenarios = {
        gm: { title: '毛利 GM', ref: '正文式1 · §2.4.1', why: '卖得多还不够；还要扣掉生产所需的可变成本。', before: '单产是每公顷产量；价格与产量质量单位必须一致。', action: '先单产×价格算收入，再减对应可变成本，最后把两季相加。', formula: 'GM = (小麦单产×价格−成本) + (玉米单产×价格−成本)',
          rows: [['小麦', `${fmt(v.wheat)} Mg/ha × 300 USD/Mg`, `${fmt(m.revenueWheat)} − 1,000 = ${fmt(m.revenueWheat - 1000)}`], ['玉米', `${fmt(v.maize)} Mg/ha × 250 USD/Mg`, `${fmt(m.revenueMaize)} − 900 = ${fmt(m.revenueMaize - 900)}`]], heads: ['作物季', '收入 (USD/ha)', '收入−成本 (USD/ha)'],
          chain: [['合成收入', `${fmt(m.revenue)} USD/ha/year`, '价格300 / 250为合成值'], ['扣可变成本', '−1,900 USD/ha/year', '1,000 + 900，均为合成'], ['年度毛利', `${fmt(m.gm)} USD/ha/year`, `${area} ha合计 ${fmt(m.gmTotal)} USD/year`]],
          result: `GM=${fmt(m.gm)} USD/ha/year。${area} ha总毛利是${fmt(m.gm)}×${area}=${fmt(m.gmTotal)} USD/year。它没有自动扣掉固定资本和全部家庭劳动机会成本，不能改称净利润。`, limit: 'Table S2原价未纳入。本例改单产时价格和成本不变，只展示公式敏感性，不声称真实增产无需追加投入。' },
        dey: { title: '膳食能量 DEY', ref: '正文式2 · §2.4.2.1', why: '把两种谷物的产量变为共同的食物能量单位，表示食物生产潜力。', before: '每Mg谷物含多少GCal，就是能量系数；它不是产量。', action: '各作物单产乘自己的系数，再合并两季。', formula: 'DEY = 小麦单产×3.17 + 玉米单产×3.35',
          rows: [['小麦', `${fmt(v.wheat)} × 3.17`, `${fmt(m.energyWheat)} GCal/ha`], ['玉米', `${fmt(v.maize)} × 3.35`, `${fmt(m.energyMaize)} GCal/ha`]], heads: ['作物季', 'Mg/ha × GCal/Mg', '这一季能量'],
          chain: [['原文系数', '3.17 / 3.35 GCal/Mg', '分别是小麦 / 玉米'], ['两季相加', `${fmt(m.energyWheat)} + ${fmt(m.energyMaize)}`, '同一地块的一年'], ['年度能量', `${fmt(m.dey)} GCal/ha/year`, `${area} ha合计 ${fmt(m.deyTotal)} GCal/year`]],
          result: `${fmt(m.dey)} GCal/ha/year = ${fmt(m.dey * 1e6)} kcal/ha/year。1 GCal=1,000,000 kcal。结果是生产潜力，不是居民实际摄入。`, limit: '单产是合成输入；3.17和3.35是原文明示系数。出售、饲用、加工、损失与分配不由此式追踪。' },
        labor: { title: '劳动 LU', ref: '正文式3 · §2.4.2.2', why: '劳动短缺时，需要知道活动会占用多少人时。', before: '2个人各做3小时=6人时；次数×每次单位面积人时才能相加。', action: '先逐项次数×工时，再合计作物季、最后合计全年。', formula: 'LU = Σ作物季 Σ作业 (次数 × 每次人时/ha)',
          rows: [['化肥', '2×3=6', '1×3=3'], ['粪肥', '1×8=8', '0×8=0'], ['施药', '3×1.5=4.5', '3×1.5=4.5'], ['灌溉', '3×4=12', '1×4=4'], ['除草', '1×5=5', '1×5=5'], ['手工收获', '1×10=10', '1×12=12']], heads: ['作业（工时均为合成）', '小麦 (h/ha)', '玉米 (h/ha)'],
          chain: [['小麦合计', '45.5 h/ha', '6+8+4.5+12+5+10'], ['玉米合计', '28.5 h/ha', '3+0+4.5+4+5+12'], ['年度需求', '74 h/ha/year', `${area} ha合计 ${fmt(m.laborTotal)} h/year`]],
          result: `年度需求74×${area}=${fmt(m.laborTotal)} h/year。年度够用不保证收获周够用；例如一周需12h、只能提供8h，仍短缺4h。`, limit: '这些工时不是Table S3。原文部分活动使用报告农户的平均单位工时；缺失记录不能按0处理。此例其他手工作业假设为0。' },
        gwd: { title: '地下水净消耗 GWD', ref: '正文式4–5 · §2.4.3.1', why: '抽走的水有一部分估计回补；净消耗需要同时记借出与回流。', before: 'mm是按面积表达的水深；1mm×1ha=10m³。补给系数α=0.2没有单位。', action: '先加两季地下水灌溉，再用α×(降水+灌溉)估补给，最后相减。', formula: 'GWD = IR − D；D = 0.2 × (P + IR)',
          rows: [['灌溉IR', `${fmt(v.irrigation)} + 150`, `${fmt(m.irrigation)} mm`], ['估计补给D', `0.2 × (500 + ${fmt(m.irrigation)})`, `${fmt(m.recharge)} mm/year`], ['净消耗GWD', `${fmt(m.irrigation)} − ${fmt(m.recharge)}`, `${fmt(m.gwd)} mm/year`]], heads: ['步骤', '代入', '结果'],
          chain: [['地下水取用', `${fmt(m.irrigation)} mm`, '小麦可调；玉米固定150'], ['模型估计回补', `${fmt(m.recharge)} mm/year`, '降水500为合成，α0.2来自原文'], ['净消耗', `${fmt(m.gwd)} mm/year`, `×10×${area} = ${fmt(m.gwdVolume)} m³/year`]],
          result: `本例净消耗${fmt(m.gwd)}mm/year；${area}ha对应${fmt(m.gwdVolume)}m³/year。${m.gwd < 0 ? '负值只表示这个经验账下净回补，不能自动断言实测水位上升。' : '它不等于灌溉总量，也不等于直接测得的地下水位下降。'}`, limit: '从给定灌溉深度开始；未补电量→灌溉的补充关系。0.2是本文区域参数，不自动适用于海南。' },
        nl: { title: '氮损失 NL', ref: '正文式6 · §2.4.3.2', why: '把三条纳入的氮损失通道汇为一个年度指标。', before: '相加的是氮元素质量kg N；不是把NH₃气体、NO₃离子与N₂O气体质量直接混加。', action: '以下路径值已经是假设的估算输出：先按季相加，再合计两季。', formula: 'NL = Σ作物季 (NH₃-N + NO₃-N + N₂O-N)',
          rows: [['小麦', '20 + 25 + 2', '47'], ['玉米', '15 + 20 + 1.5', '36.5']], heads: ['作物季', '三路径 (kg N/ha/season)', '季总和 (kg N/ha)'],
          chain: [['缺口：投入→路径', '参数未补齐', '不能擅自设一个损失率'], ['从合成路径输出开始', '47 + 36.5 kg N/ha', '不是作者实测值'], ['年度合计', '83.5 kg N/ha/year', `${area} ha合计 ${fmt(m.nitrogenTotal)} kg N/year`]],
          result: `83.5×${area}=${fmt(m.nitrogenTotal)}kg N/year。它不是自动等于“氮输入−作物带走量”的氮盈余，也未包括所有可能的损失通道。`, limit: '补充§1.2完整输入响应系数缺失。没有它，施N200不能忠实推出三条路径。4.4kg N₂O×28/44=2.8kg N是另一个单位例，不再加进83.5。' },
        ghg: { title: '净温室气体 GHG', ref: '正文式7 · §2.4.3.3', why: '在同一核算边界下，比较排放与土壤碳固存抵消后的气候影响。', before: 'CO₂-eq是共同影响单位；不能直接把kg C从Mg CO₂-eq里减掉。', action: '本例各组分已假设换算成CO₂-eq；先加排放，再减土壤碳固存项。', formula: 'GHGnet = GHGemi − QSOC',
          rows: [['前端投入', '2.0'], ['直接N₂O', '0.8'], ['间接N₂O', '0.2'], ['SOC分解', '1.0'], ['另给固存QSOC', '1.5（从合计排放扣除）']], heads: ['独立合成已换算组分', 'Mg CO₂-eq/ha/year'],
          chain: [['合计排放', '2+0.8+0.2+1 = 4', 'Mg CO₂-eq/ha/year'], ['扣固存项', '−1.5', '同单位且不重复扣减'], ['净排放', '2.5 Mg CO₂-eq/ha/year', `${area} ha合计 ${fmt(m.ghgTotal)} Mg/year`]],
          result: `2.5Mg=2,500kg CO₂-eq/ha/year；${area}ha对应${fmt(m.ghgTotal)}Mg CO₂-eq/year。排放4.0和净值2.5不能互换；碳输入不等于永久固存。`, limit: '完整排放因子、GWP版本、SOC经验参数未补齐。这些气候组分不由上一张氮损失例反推；两例不是联立校准的农场。' },
        pu: { title: '农药标准剂量 PU', ref: '正文式8 · §2.4.3.4', why: '成分与用量回忆不可靠时，用标准剂量施用次数表示对农药的依赖代理。', before: '次数、药液体积、有效成分质量与毒性是不同的量。', action: '本例假设每次全面积、标签全剂量；先合计每类两季次数，再合并类别。', formula: 'PU = 杀虫剂标准剂量 + 除草剂标准剂量 + 杀菌剂标准剂量',
          rows: [['杀虫剂', '2 + 1', '3'], ['除草剂', '1 + 1', '2'], ['杀菌剂', '1 + 0', '1']], heads: ['类别', '小麦 + 玉米', '年度标准剂量次数'],
          chain: [['杀虫 + 除草 + 杀菌', '3 + 2 + 1', '全剂量、同一完整评价面积'], ['年度指标', '6 doses/year', '不是6kg，也不是6L'], ['改面积也不相乘', '仍为6次', `${area} ha不把次数改成${fmt(6 * v.area)}`]],
          result: '6降低到4，只能说明本代理减少，不能据此说毒性风险同比降低。20L/亩×15亩/ha=300L/ha算的是药液体积，没有浓度仍不知道有效成分质量。', limit: '非标准剂量、混配或只喷部分面积需要补充§1.5与具体记录；不能用桶数自行替换标准剂量定义。' }
      };
      const s = scenarios[state.metric];
      return `<div class="rw-metric-heading">${badge('source', s.ref)}<h4>${s.title}</h4></div>` + common + lesson(s.before, s.why, s.action) + `<p class="rw-formula">${s.formula}</p>` + table('输入与逐项代入', s.heads, s.rows) + chain(s.chain, `${s.title}的计算链`) + outcome('得到的数字怎样读', s.result) + `<p class="rw-boundary"><strong>边界：</strong>${s.limit}</p>`;
    }
    function decisionTable(model, withStatus) {
      const m = model.decision, v = model.values;
      return table('合成方案矩阵：每行同为1 ha、同一年', ['方案', '毛利 ↑ (USD/ha/year)', '净地下水消耗 ↓ (mm/year)', '劳动 (h/ha/year)', withStatus ? '可行性' : '前沿'], m.rows.map(r => [r.id, fmt(r.margin), fmt(r.water), fmt(r.labor), r.labor > v.laborCap ? `不可行：超${fmt(r.labor - v.laborCap)}h` : withStatus ? '可行' : 'F' + (m.fronts.findIndex(f => f.includes(r.id)) + 1)]));
    }
    function feasible(model) {
      const m = model.decision, v = model.values;
      return lesson('硬约束是“必须满足”的门槛；目标是满足门槛以后想改善的方向。', 'D默认利润高且耗水低，但需要140h，超过100h的劳动上限；图上漂亮仍可能无法实施。', '把劳动需求逐行与上限比较。可调整上限，让同一方案进入或离开候选集。') +
        `<p class="rw-boundary">${badge('extension', '不是梁2022原文步骤')} 原论文从已有观测系统做非支配排序。本处为了研究迁移，增加一个明确的资源门槛；这里仅检查年度劳动，不表示土地、现金、季节峰值等都已可行。</p>` +
        `<div class="rw-cap-bars" role="group" aria-label="劳动需求与当前上限">${m.rows.map(r => `<div><span>${r.id}：${r.labor} h</span><div class="rw-meter"><span style="width:${r.labor / 160 * 100}%"></span><i style="left:${v.laborCap / 160 * 100}%" aria-hidden="true"></i></div><strong>${r.labor <= v.laborCap ? '通过年度门槛' : '超出上限'}</strong></div>`).join('')}<p>竖线是上限 ${fmt(v.laborCap)} h/year（每个农场固定1 ha）；状态也以文字标明。</p></div>` + decisionTable(model, true) +
        outcome('交给Pareto比较的集合', m.feasible.length ? `保留 ${m.feasible.map(r => r.id).join('、')}；排除 ${m.excluded.length ? m.excluded.map(r => r.id).join('、') : '无'}。下一步只在保留集合里比较绩效。改变上限会改变候选集合与后面的标准化范围。` : '当前没有可行方案。后续不能编造一个“最佳方案”，也不能对空集合计算理想点；请查看资源上限与方案需求。');
    }
    function plot(model, withIdeal) {
      const m = model.decision, all = m.rows, minMargin = Math.min(0, ...all.map(r => r.margin)), maxMargin = Math.max(3000, ...all.map(r => r.margin));
      const minWater = Math.min(0, ...all.map(r=>r.water)), maxWater = Math.max(400, ...all.map(r=>r.water));
      const x = water => 70 + (water-minWater) / (maxWater-minWater) * 390, y = margin => 252 - (margin - minMargin) / (maxMargin - minMargin) * 205;
      const selected = m.rows.find(r => r.id === state.selected), selectedDistance = m.distances[state.selected];
      let marks = all.map(r => {
        const excluded = !m.feasible.some(a => a.id === r.id), front = !excluded && m.fronts[0].includes(r.id), cx = x(r.water), cy = y(r.margin);
        return `<g class="${excluded ? 'rw-dot-excluded' : front ? 'rw-dot-front' : 'rw-dot-other'}">${excluded ? `<path d="M${cx - 6},${cy - 6}l12,12m-12,0l12,-12"/>` : `<circle cx="${cx}" cy="${cy}" r="7"/>`}<text x="${cx + 12}" y="${cy + (r.id === 'A' ? -9 : 5)}">${r.id}${excluded ? ' 不可行' : front ? ' F1' : ' F2+'}</text></g>`;
      }).join('');
      if (withIdeal && m.ideal) {
        const ix = x(m.ideal[1]), iy = y(m.ideal[0]);
        const segments = selectedDistance ? `<path class="rw-distance-line" d="M${x(selected.water)},${y(selected.margin)}L${ix},${y(selected.margin)}L${ix},${iy}"/>` : '';
        marks = segments + marks + `<g class="rw-ideal"><path d="M${ix},${iy - 9}l9,9l-9,9l-9,-9z"/><text x="${Math.min(ix + 13, 430)}" y="${iy - 13}">理想点 q</text></g>`;
      }
      return `<figure class="rw-plot"><div class="rw-chart-scroll" tabindex="0" role="region" aria-label="二维绩效图；窄屏可横向滚动"><svg viewBox="0 0 570 310" role="img" aria-labelledby="${uid}-plot-title ${uid}-plot-desc"><title id="${uid}-plot-title">毛利与净地下水消耗：左上方向更好</title><desc id="${uid}-plot-desc">横轴净地下水消耗越低越好，纵轴毛利越高越好。${m.feasible.length ? '当前第一前沿是' + m.fronts[0].join('、') : '当前没有可行方案'}。叉号表示不可行；圆点的文字标记前沿。精确数字见同页表格。${withIdeal && m.ideal ? '理想点毛利' + fmt(m.ideal[0]) + '，净地下水消耗' + fmt(m.ideal[1]) + '。折线只分解两列的差，不是MIDIP的原单位距离。' : ''}</desc><path class="rw-axis" d="M70,35V252H520"/><text x="76" y="21">毛利 ↑（USD/ha/year）</text><text x="138" y="296">净地下水消耗（mm/year），← 越少越好</text>${[minWater, minWater+(maxWater-minWater)/4, minWater+(maxWater-minWater)/2, minWater+3*(maxWater-minWater)/4, maxWater].map(w => `<text class="rw-tick" x="${x(w)}" y="274" text-anchor="middle">${fmt(w)}</text>`).join('')}${[minMargin, minMargin+(maxMargin-minMargin)/3, minMargin+2*(maxMargin-minMargin)/3, maxMargin].map(p => `<text class="rw-tick" x="60" y="${y(p) + 4}" text-anchor="end">${fmt(p)}</text>`).join('')}<text class="rw-better" x="85" y="53">↖ 希望靠近的方向</text>${marks}</svg></div><figcaption>窄屏可横向滑动图形，或直接读下方数值表。文字、形状和表格共同表达状态；图中位置是原始单位，距离指标还需标准化。</figcaption></figure>`;
    }
    function pareto(model) {
      const m = model.decision;
      let explanation = '';
      if (m.feasible.length) {
        explanation = m.feasible.map(row => {
          const beat = m.feasible.filter(other => dominates(other, row));
          return `<li><strong>${row.id}</strong>：${beat.length ? `${beat.map(r => r.id).join('、')} 在两项上都不差且至少一项更好，所以${row.id}不在第一前沿。` : '没有其他可行方案在两项上都不差且至少一项更好，所以位于第一前沿。'}</li>`;
        }).join('');
      }
      const a = m.rows[0], c = m.rows[2], both = m.feasible.includes(a) && m.feasible.includes(c);
      let contrast = '';
      if (both) contrast = dominates(a, c) ? '当前A支配C；改动输入后不要继续沿用默认A/C并列的结论。' : dominates(c, a) ? '当前C支配A；改动输入后不要继续沿用默认A/C并列的结论。' : `A毛利${fmt(a.margin)}、耗水${fmt(a.water)}；C毛利${fmt(c.margin)}、耗水${fmt(c.water)}。两者都没有全面胜过对方，所以不能只凭一个目标挑冠军。`;
      return lesson('“≥ / ≤”表示不差；“至少一项严格更好”排除把自己或完全相同方案算作支配者。', '不同目标可能冲突。保留取舍后，才有资格讨论偏好和进一步证据。', '对每个可行方案找“是否存在一个全面不差的对手”。移除第一前沿后，对剩余集合重复。') + plot(model, false) + decisionTable(model, false) + `<ol class="rw-comparisons">${explanation || '<li>没有可行候选，停止比较。</li>'}</ol>` +
        outcome('前沿不是唯一最优答案', m.fronts.length ? `${m.fronts.map((f, i) => `F${i + 1}={${f.join(', ')}}`).join('；')}。${contrast} 默认A支配B：1,900≥1,700且260≤280；A/C互有取舍，D先因劳动排除。` : '可行集合为空；不存在本次可报告的前沿。') + `<p class="rw-boundary">${badge('toy', '仅2个目标')} 原文比较7指标；本例为看清支配关系仅留2列，不重现原文56案例前沿。改变A的成本或灌溉，会重新计算本流程的毛利和净地下水消耗；未建模的产量响应、劳动响应和其他环境效应不会自动生成。</p>`;
    }
    function ideal(model) {
      const m = model.decision;
      if (!m.feasible.length) return outcome('当前不能计算距离', '没有可行方案，所以没有可计算的最好值、范围或理想点。回第4步核对劳动资源；空白不是0分。');
      if (!m.distances[state.selected]) state.selected = m.feasible[0].id;
      const row = m.feasible.find(r => r.id === state.selected), d = m.distances[row.id], [qGM, qWater] = m.ideal, [rGM, rWater] = m.ranges;
      const rangeRows = [['毛利（提高）', fmt(qGM), fmt(rGM), rGM ? `|${fmt(row.margin)}−${fmt(qGM)}| ÷ ${fmt(rGM)} = ${fmt(d.d[0], 6)}` : '所有值相同 → 距离贡献为0'], ['地下水（降低）', fmt(qWater), fmt(rWater), rWater ? `|${fmt(row.water)}−${fmt(qWater)}| ÷ ${fmt(rWater)} = ${fmt(d.d[1], 6)}` : '所有值相同 → 距离贡献为0']];
      const squared = d.d.map(x => (x - d.mean) ** 2);
      return lesson('量纲不同不能直接相加：美元与毫米先各除以本列范围，变成无单位距离。', 'MIDIP看整体离理想点多远；HDIP看这些距离是否均匀，两者回答不同问题。', '先确定比较集合、最好值与范围，再对所选方案逐列标准化，最后平方求和与样本标准差。') +
        `<p class="rw-boundary">${badge('toy', '本例的比较基准')} 理想点与范围均取当前全部可行A–D行，包括被支配行。原文使用其观测数据与聚类中心；本例改门槛后基准也会变，前后距离不能脱离参照集合直接排名。</p>` +
        `<div class="rw-switch" role="group" aria-label="选择距离计算方案">${m.feasible.map(r => `<button type="button" data-select="${r.id}" aria-pressed="${state.selected === r.id}">方案 ${r.id}</button>`).join('')}</div>` + plot(model, true) +
        table(`方案${row.id}：d = |当前值−理想值| ÷ (最大值−最小值)`, ['指标', '理想值 q', '范围 R', '标准化距离 d（无单位）'], rangeRows) +
        chain([['先求平均距离', `(${fmt(d.d[0], 6)}+${fmt(d.d[1], 6)})÷2 = ${fmt(d.mean, 6)}`, '此平均数不是MIDIP'], ['MIDIP：整体远近', `√(${fmt(d.d[0] ** 2, 6)}+${fmt(d.d[1] ** 2, 6)}) = ${fmt(d.MIDIP, 6)}`, '先平方、求和、再开根'], ['HDIP：距离是否均匀', `√[(${fmt(squared[0], 6)}+${fmt(squared[1], 6)})÷(2−1)] = ${fmt(d.HDIP, 6)}`, '平方项来自(d−平均d)²；K=2']], '逐步算出MIDIP与HDIP') +
        table('同一参照集合下的计算结果', ['方案', '毛利距离', '地下水距离', 'MIDIP', 'HDIP'], m.feasible.map(r => { const x = m.distances[r.id]; return [r.id, fmt(x.d[0], 6), fmt(x.d[1], 6), fmt(x.MIDIP, 6), fmt(x.HDIP, 6)]; })) +
        outcome('把两个数翻译回研究判断', `方案${row.id}的MIDIP=${fmt(d.MIDIP, 6)}、HDIP=${fmt(d.HDIP, 6)}。在当前相同基准下，MIDIP较小表示整体较接近理想；HDIP小只表示距离均匀，不能独自证明“好”。例如(0.8,0.8)的HDIP=0，但MIDIP≈1.131。`) +
        `<details class="rw-explain"><summary>还差哪些步骤，才能回到原论文与自己的研究？</summary><p>原文还要对第一前沿案例做层次聚类并计算群组中心。这个两维、单点教学例没有实现HCA，不能从A/C推出原文9个典型案例。</p><p>常数列的范围为0时不能除以0。本演示保留两列并明确把同值列贡献设为0；若只有一列实际变化，或整个集合只有一个案例，HDIP不构成多维均衡性的证据。</p><p>最后回到管理与背景：同土壤、同资源条件下是否还表现突出？投入记录和估算参数是否共享误差？观察到的优势需要试验或其他可信设计检验，不能直接改写为措施的因果效果。</p></details>`;
    }
    function renderResult() { const model = calculate(state.values); const renderers = [farmRaw, farmAggregate, farmMetrics, feasible, pareto, ideal]; stage.querySelector('.rw-result').innerHTML = renderers[state.step](model); }
    function renderSideMetric() {
      q('.rw-side-metric-body').innerHTML=`<nav class="rw-metrics" aria-label="选择独立解释的指标">${METRICS.map(([key,label])=>`<button type="button" data-metric="${key}" aria-pressed="${state.metric===key}">${label}</button>`).join('')}</nav><div class="rw-inputs">${['gm','dey'].includes(state.metric)?field('wheat','独立例：小麦单产','Mg/ha','range','0.5')+field('maize','独立例：玉米单产','Mg/ha','range','0.5'):state.metric==='gwd'?field('irrigation','独立例：小麦灌溉','mm','range','10'):''}${field('area','独立例：同一地块面积','ha','range','0.1')}</div><div class="rw-side-metric-result"></div>`;
      q('.rw-side-metric-result').innerHTML=metric(calculate(state.values));
    }
    function renderSideJoin() {
      q('.rw-side-join-body').innerHTML=`<div class="rw-inputs">${field('crop3','独立例：第三条收获','kg')}${field('manure2','独立例：第二条粪肥','Mg','number','0.5')}</div><div class="rw-switch" role="group" aria-label="独立连接例的方法"><button type="button" data-join="correct" aria-pressed="${!state.joinWrong}">先汇总再连接</button><button type="button" data-join="wrong" aria-pressed="${state.joinWrong}">看看直接连接会怎样</button></div><div class="rw-side-join-result"></div>`;
      q('.rw-side-join-result').innerHTML=raw(calculate(state.values))+joined(calculate(state.values));
    }
    function show(step, pause = true) { if (pause) stop(); state.step = Math.max(0, Math.min(5, step)); renderStage(); say(`第${state.step + 1}步，共6步：${STEP_NAMES[state.step]}。`); }
    function onClick(event) {
      routeInactive = false; const b = event.target.closest('button'); if (!b || !element.contains(b) || b.disabled) return;
      if (b.dataset.step !== undefined) { show(+b.dataset.step); return; }
      if (b.dataset.metric) { stop(); state.metric = b.dataset.metric; renderSideMetric(); q(`[data-metric="${state.metric}"]`).focus(); say(`已展开${METRICS.find(r => r[0] === state.metric)[1]}，合成输入与公式如下。`); return; }
      if (b.dataset.join) { state.joinWrong = b.dataset.join === 'wrong'; stop(); renderSideJoin(); q(`[data-join="${b.dataset.join}"]`).focus(); say(state.joinWrong ? '已展开直接连接的6行，注意数量被重复。' : '已展开各自汇总后的1行。'); return; }
      if (b.dataset.select) { state.selected = b.dataset.select; stop(); if(state.step===2) renderStage(); else renderResult(); q(`[data-select="${state.selected}"]`).focus(); say(`已计算方案${state.selected}到当前理想点的距离。`); return; }
      if (b.dataset.action === 'previous') show(state.step - 1);
      if (b.dataset.action === 'next') show(state.step + 1);
      if (b.dataset.action === 'play') play();
      if (b.dataset.action === 'reset') { stop(); invalid.clear(); state = { values: { ...DEFAULTS }, step: 0, metric: 'gm', joinWrong: false, selected: 'A', playing: false, speed: 12000 }; q('[data-action="speed"]').value = '12000'; renderStage(); renderSideJoin(); renderSideMetric(); say('已恢复全部合成默认值，并回到原始记录；没有改动个人笔记。'); }
    }
    function onInput(event) {
      routeInactive = false; const input = event.target, key = input.dataset.field; if (!key || !LIMITS[key]) return;
      stop(); const n = input.value.trim() === '' ? NaN : Number(input.value), [min, max] = LIMITS[key]; const valid = Number.isFinite(n) && n >= min && n <= max;
      input.setAttribute('aria-invalid', String(!valid)); q(`#${input.id}-error`).textContent = valid ? '' : `请输入${min}到${max}之间的数字；下方结果仍使用上一次有效值。`;
      if (!valid) { invalid.add(key); controls(); say('输入暂时无效，计算未采用这一改动。'); return; }
      invalid.delete(key); state.values[key] = n; q(`[data-for="${key}"]`).textContent = fmt(n); renderResult(); q('.rw-side-join-result').innerHTML=raw(calculate(state.values))+joined(calculate(state.values)); q('.rw-side-metric-result').innerHTML=metric(calculate(state.values)); controls(); say('已按有效输入重算下方数字；播放已暂停。');
    }
    function onChange(event) { if (event.target.dataset.action === 'speed') { state.speed = +event.target.value; if (state.playing) schedule(); } }
    function onKey(event) {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.target.closest('input,select,textarea,button,a,summary,.rw-chart-scroll,.rw-table-wrap,[contenteditable="true"]')) return;
      if (event.key === 'ArrowRight') { event.preventDefault(); show(state.step + 1); }
      else if (event.key === 'ArrowLeft') { event.preventDefault(); show(state.step - 1); }
      else if (event.key === ' ') { event.preventDefault(); play(); }
    }
    function onHidden() { if (doc.hidden) stop('页面已隐藏，演示已暂停。'); }
    function onRoute() { stop(); routeInactive = true; }
    function onMotion() { q('.rw-motion-note').hidden = !mq.matches; if (mq.matches) stop('系统已减少动态效果；可手动换步。'); controls(); }
    function destroy() { if (destroyed) return; stop(); destroyed = true; observer.disconnect(); element.removeEventListener('click', onClick); element.removeEventListener('input', onInput); element.removeEventListener('change', onChange); element.removeEventListener('keydown', onKey); doc.removeEventListener('visibilitychange', onHidden); win.removeEventListener('hashchange', onRoute); mq.removeEventListener('change', onMotion); mounted.delete(container); activeControllers.delete(controller); element.remove(); }
    element.addEventListener('click', onClick); element.addEventListener('input', onInput); element.addEventListener('change', onChange); element.addEventListener('keydown', onKey); doc.addEventListener('visibilitychange', onHidden); win.addEventListener('hashchange', onRoute); mq.addEventListener('change', onMotion);
    const observer = new win.MutationObserver(() => { if (!element.isConnected) destroy(); }); observer.observe(doc.documentElement, { childList: true, subtree: true });
    const controller = { destroy, pause: () => stop(), isBusy: () => !destroyed && !routeInactive && (state.playing || state.step !== 0 || state.metric !== 'gm' || state.joinWrong || state.selected !== 'A' || invalid.size > 0 || Object.keys(DEFAULTS).some(key => state.values[key] !== DEFAULTS[key])), getState: () => ({ ...state, values: { ...state.values }, mounted: !destroyed, pendingTimer: timer !== null }) };
    mounted.set(container, controller); activeControllers.add(controller); renderStage(); renderSideJoin(); renderSideMetric(); say('第1步，共6步：原始记录。未自动播放。'); return controller;
  }
  const API = { version: VERSION, mount, isBusy: () => [...activeControllers].some(controller => controller.isBusy()), model: { defaults: DEFAULTS, limits: LIMITS, validate, aggregate, indicators, dominates, fronts, distance, decision, farmPipeline, calculate } };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  if (global) global.PaperWalkthrough = API;
})(typeof window !== 'undefined' ? window : null);
