/* Local, ephemeral Q-method teaching panel. Full statistical results are precomputed.
 * Geometry preview changes only a displayed pair of axes, never downstream results. */
(function (global) {
'use strict';
const mounts = new WeakMap(), active = new Set(), historySnapshots = new Map();
const historySession = global.crypto?.randomUUID?.() || String(Date.now())+'-'+Math.random().toString(36).slice(2);
let serial = 0;
const STEPS = ['排序变成矩阵', '人与人的相关', '提取与旋转', '哪些排序定义因子', '每个人贡献多少', '总和变成因子数组', '两因子怎样区分', '回到论文三幅图'];
const escape = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (value, digits = 6) => Number.isFinite(Number(value)) ? (Math.abs(Number(value)) < 0.5 * 10 ** -digits ? 0 : Number(value)).toFixed(digits) : '未定义';
const sum = values => values.reduce((total, value) => total + value, 0);
const dot = (a, b) => sum(a.map((value, i) => value * b[i]));
const eq = text => '<p class="q-equation">' + text + '</p>';
const note = text => '<div class="q-note">' + text + '</div>';
const safeLink = value => typeof value === 'string' && (/^#\/[\w/.-]+$/.test(value) || /^https:\/\/[^\s<>"']+$/.test(value)) ? value : '';
const localImage = value => typeof value === 'string' && /^(?:resources\/)?library\/[A-Za-z0-9_./-]+\.(?:png|jpg|jpeg|webp)$/i.test(value) && !value.split('/').includes('..') ? value : '';
const link = (url, label) => safeLink(url) ? '<a href="' + escape(url) + '">' + escape(label) + '</a>' : escape(label);
function loadingLabels(markers) {
  // Conservative boxes for 12px system text: 8px Latin / 13px full-width,
  // with extra side bearings and 20px height. Only labels move, never markers.
  const bounds = {left:64, top:34, right:470, bottom:440}, height = 20;
  const overlaps = (a,b,gap=0) => a.x < b.x+b.width+gap && a.x+a.width+gap > b.x && a.y < b.y+b.height+gap && a.y+a.height+gap > b.y;
  const clamp = (v,min,max) => Math.max(min,Math.min(max,v));
  const obstacles = markers.map(m=>({x:m.x-m.radius-3,y:m.y-m.radius-3,width:2*(m.radius+3),height:2*(m.radius+3)}));
  const labels = markers.map((m,i)=>({...m,index:i,width:6+sum([...m.text].map(c=>c.charCodeAt(0)>255?13:8)),height}));
  const placed = [];
  // Reserve the longest selection/comparison labels first; participant order
  // resolves ties, so returning to the same controls reproduces the same plot.
  for (const label of [...labels].sort((a,b)=>b.width-a.width || a.index-b.index)) {
    let best = null, bestScore = Infinity;
    const consider = (left,top) => {
      const box = {x:clamp(left,bounds.left,bounds.right-label.width),y:clamp(top,bounds.top,bounds.bottom-height),width:label.width,height};
      if (obstacles.some(o=>overlaps(box,o)) || placed.some(o=>overlaps(box,o,4))) return;
      const endX = clamp(label.x,box.x,box.x+box.width), endY = clamp(label.y,box.y,box.y+height);
      const score = (endX-label.x)**2+(endY-label.y)**2;
      if (score < bestScore) { bestScore = score; best = {...box,endX,endY}; }
    };
    // Search nearby sides and diagonals, preferring short leader lines. Bounds
    // clamp candidates inward at the edge of the unchanged coordinate system.
    for (let gap=4;gap<=100;gap+=8) for (const [dx,dy] of [[1,0],[-1,0],[0,-1],[0,1],[1,-1],[-1,-1],[1,1],[-1,1]]) {
      consider(label.x+(dx>0?label.radius+gap:dx<0?-label.radius-gap-label.width:-label.width/2),label.y+(dy>0?label.radius+gap:dy<0?-label.radius-gap-height:-height/2));
    }
    // A bounded scan covers unusually crowded selections without allowing an
    // overlap as a fallback. The ten-participant plot has ample free space.
    if (!best) for (let top=bounds.top;top<=bounds.bottom-height;top+=8) for (let left=bounds.left;left<=bounds.right-label.width;left+=8) consider(left,top);
    if (!best) throw new Error('Q 载荷图没有足够的标签空间');
    label.box = best; placed.push(best);
  }
  return labels;
}
function mount(container) {
  if (!container || !container.ownerDocument || typeof container.append !== 'function') throw new TypeError('PaperQWalkthrough.mount 需要 DOM 容器');
  if (mounts.has(container)) return mounts.get(container);
  const config = global.PAPER_Q;
  if (!config || !Array.isArray(config.scenarios) || !config.scenarios.length) throw new TypeError('缺少 PAPER_Q.scenarios 预计算结果');
  for (const scenario of config.scenarios) {
    const r = scenario.result;
    if (!r || r.retained_factors !== 2 || !Array.isArray(r.data) || r.data.length !== r.nstat || r.participants.length !== r.npeople || r.data.some(row => row.length !== r.npeople)) throw new TypeError('Q 教学面板仅接受完整的两因子、陈述×人预计算结果');
  }
  const doc = container.ownerDocument, uid = 'paper-q-' + (++serial), mountedHash = global.location?.hash || '';
  const base = config.scenarios.find(s => s.id === 'baseline') || config.scenarios[0];
  const defaults = { step: 0, scenario: base.id, person: 'P01', other: 'P05', statement: 'S01', factor: 0, loadingView: 'varimax', angle: 0 };
  if (!base.result.participants.includes(defaults.person)) defaults.person = base.result.participants[0];
  if (!base.result.participants.includes(defaults.other)) defaults.other = base.result.participants[Math.min(1, base.result.npeople - 1)];
  if (!base.result.statements.some(s => s.id === defaults.statement)) defaults.statement = base.result.statements[0].id;
  // Only an opaque key enters history.state. Teaching choices stay in this tab's
  // memory; each history entry has its own snapshot, separate from private notes.
  const oldKey = global.history?.state?.paperQEntry, oldSnapshot = historySnapshots.get(oldKey);
  const restored = oldSnapshot?.hash === mountedHash ? oldSnapshot : null;
  const historyKey = restored ? oldKey : historySession+'-'+uid;
  const state = {...defaults, ...(restored?.state || {})}, source = config.source || {}, urls = new Set(), timers = new Set();
  const detailsByStep = {...(restored?.detailsByStep || {})};
  let mounted = true, invalid = '', observer, rendering = false, lastDownload = '';
  const panel = doc.createElement('section');
  panel.className = 'q-walkthrough'; panel.setAttribute('aria-label', 'Q 方法：同一合成数据的八步计算走读');
  panel.setAttribute('data-no-terms', 'true'); panel.setAttribute('tabindex', '0');
  const options = (items, selected) => items.map(([value, label]) => '<option value="' + escape(value) + '"' + (String(value) === String(selected) ? ' selected' : '') + '>' + escape(label) + '</option>').join('');
  const select = (key, label, items) => '<label class="q-control" data-control="' + key + '" for="' + uid + '-' + key + '"><span>' + label + '</span><select id="' + uid + '-' + key + '" data-field="' + key + '">' + options(items, state[key]) + '</select></label>';
  const nav = position => '<div class="q-navigation" aria-label="' + position + '步骤导航"><button type="button" data-action="previous">上一步</button><span class="q-position"></span><button type="button" data-action="next">下一步</button></div>';
  panel.innerHTML = '<header class="q-header"><p class="q-eyebrow">Q 方法 · 可逐项核对的合成教学</p><h2>跟着一份排序，走到一套观点</h2><p>20 条原创陈述 × 10 份合成排序。页面已有两套完整计算结果，无需安装；选择场景是切换已重算的数据，不是在线拟合任意新数据。</p><p class="q-boundary">这不是 Cheng 作者的327人原始数据，也不重现作者总体3因子及七组累计18观点。全部选择只留在本页内存，不改动笔记或阅读记录。</p></header>' +
    '<nav class="q-steps" aria-label="八步计算链">' + STEPS.map((label, i) => '<button type="button" data-step="' + i + '">' + (i + 1) + ' · ' + label + '</button>').join('') + '</nav>' +
    '<div class="q-controls">' + select('scenario', '计算场景', config.scenarios.map(s => [s.id, s.label])) + select('person', '跟踪这个人', base.result.participants.map(p => [p, p])) + select('other', '与这个人比较', base.result.participants.map(p => [p, p])) + select('statement', '跟踪这条陈述', base.result.statements.map(s => [s.id, s.id + ' · ' + s.text])) + select('factor', '查看因子／提取轴', [[0, 'F1 / 第1轴'], [1, 'F2 / 第2轴']]) + select('loadingView', '载荷图坐标', [['unrotated', 'PCA 未旋转'], ['varimax', '固定 varimax 结果'], ['geometry', '几何预览（不改后续计算）']]) +
    '<label class="q-control" data-control="angle" for="' + uid + '-angle"><span>几何预览角度（−180° 至180°）</span><input id="' + uid + '-angle" data-field="angle" type="number" value="0" min="-180" max="180" step="1" inputmode="decimal"></label><button type="button" data-action="reset">恢复 P01 / S01 基线</button></div>' +
    '<p class="q-status" role="status" aria-live="polite"></p><p class="q-error" role="alert" hidden></p><p class="q-navigation-help">切换步骤会定位新步骤标题；修改上面的选择不会跳走或移走焦点。只显示本步骤真正使用的控件。</p>' + nav('顶部') + '<div class="q-stage"></div>' + nav('底部') +
    '<details class="q-downloads"><summary>查看／运行完整计算与来源文件</summary><p>阅读无需运行代码。完整代码、CSV 和来源说明来自本站同一份文件；每步的短代码用于对应计算关系。运行前查看 q_method_readme.md 的 Python/NumPy 与 R 前提，q_method_sources.json 记录源码与核查边界。R 脚本可运行不等于已通过 R 一致性验证；实际状态以验证记录为准。</p><div class="q-download-buttons"></div><p class="q-download-status" role="status"></p></details>';
  container.append(panel);
  const q = selector => panel.querySelector(selector), stage = q('.q-stage');
  function remember() {
    if (!mounted || (global.location?.hash || '') !== mountedHash || !global.history?.replaceState) return;
    if (stage.dataset.renderedStep !== undefined) detailsByStep[stage.dataset.renderedStep] = [...stage.querySelectorAll('details')].map(item => !!item.open);
    historySnapshots.set(historyKey, {hash:mountedHash, state:{...state}, detailsByStep:{...detailsByStep}, downloadsOpen:!!q('.q-downloads').open});
    global.history.replaceState({...global.history.state, paperQEntry:historyKey}, '', global.location.href);
  }
  if (restored?.downloadsOpen) q('.q-downloads').open = true;
  q('[data-field="angle"]').value = String(state.angle);
  const D = () => config.scenarios.find(s => s.id === state.scenario).result;
  const indexes = r => ({p: r.participants.indexOf(state.person), o: r.participants.indexOf(state.other), s: r.statements.findIndex(st => st.id === state.statement), f: state.factor});
  const head = (title, text) => '<header class="q-stage-head"><p class="q-eyebrow">第 ' + (state.step + 1) + ' / 8 步</p><h3 tabindex="-1">' + title + '</h3><p>' + text + '</p></header>';
  function table(caption, headers, rows, attrs = {}) {
    return '<p class="q-scroll-hint">窄屏可在表格内左右滚动；每个图都有对应数值或文字。</p><div class="q-table-scroll" tabindex="0" role="region" aria-label="' + escape(caption) + '，可横向滚动"><table><caption>' + escape(caption) + '</caption><thead><tr>' + headers.map(h => '<th scope="col">' + escape(h) + '</th>').join('') + '</tr></thead><tbody>' + rows.map((row, i) => '<tr' + (attrs.row === i ? ' class="q-selected-row" aria-label="当前选择"' : '') + '>' + row.map((value, j) => (j === 0 ? '<th scope="row"' : '<td') + (attrs.row === i && attrs.col === j ? ' class="q-selected-cell"' : '') + '>' + escape(value) + (j === 0 ? '</th>' : '</td>')).join('') + '</tr>').join('') + '</tbody></table></div>';
  }
  function code(title, shape, text) { return '<details class="q-code"><summary>' + escape(title) + '</summary><p>' + escape(shape) + '</p><pre><code>' + escape(text) + '</code></pre></details>'; }
  function svg(name, desc, width, height, body) {
    const id = uid + '-plot-' + name;
    return '<figure class="q-figure"><p class="q-scroll-hint">窄屏可在图内左右滚动；下方有等价数值表。</p><div class="q-chart-scroll" tabindex="0" role="region" aria-label="' + escape(desc) + '，可横向滚动"><svg viewBox="0 0 ' + width + ' ' + height + '" role="img" aria-labelledby="' + id + '-title ' + id + '-desc"><title id="' + id + '-title">' + escape(desc) + '</title><desc id="' + id + '-desc">' + escape(desc) + '。当前选择由边框和文字标记，不只依赖颜色；完整数值见随后的表格。</desc>' + body + '</svg></div><figcaption>' + escape(desc) + '</figcaption></figure>';
  }
  function grid(r, values, selected, caption) {
    return '<p class="q-scroll-hint">窄屏可在五列网格内左右滚动；完整分数也在下方表格中。</p><div class="q-grid" tabindex="0" role="region" aria-label="' + escape(caption) + '，可横向滚动">' + r.grid_scores.map((score, k) => '<div class="q-grid-column"><h4>' + score + '分</h4><p>' + r.grid_counts[k] + '个位置</p>' + r.statements.map((st, i) => values[i] === score ? '<button type="button" data-statement="' + escape(st.id) + '" aria-pressed="' + (i === selected) + '" title="' + escape(st.text) + '">' + escape(st.id) + '<span>' + escape(st.text) + '</span></button>' : '').join('') + '</div>').join('') + '</div>';
  }
  function first(r, x) {
    const values = r.data.map(row => row[x.p]);
    return head('一份 Q-sort 是把所有陈述放进同一张网格', '每个人都比较同一组陈述。在这个例子里，1分表示相对低优先，5分表示相对高优先；中间不等于无所谓。固定每档容量让人表达取舍。') +
      eq(escape(state.person) + ' 的 ' + escape(state.statement) + '「' + escape(r.statements[x.s].text) + '」= ' + r.data[x.s][x.p] + '分<br>矩阵单元 D[' + escape(state.statement) + ', ' + escape(state.person) + '] = ' + r.data[x.s][x.p] + '；' + r.nstat + '行陈述 × ' + r.npeople + '列人') + grid(r, values, x.s, state.person + ' 的完整强制排序') +
      table('同一张输入矩阵：行是陈述，列是人', ['陈述', ...r.participants], r.statements.map((st, i) => [st.id + ' ' + st.text, ...r.data[i]]), {row:x.s,col:x.p + 1}) +
      note('每人均值为 ' + fmt(r.means[x.p], 2) + '，不是大家观点相同：谁把哪条放高才是后续比较的对象。强制网格为 ' + r.grid_counts.join('–') + '；它是本例设置，不能推定所有 Q 研究都用这个形状。') +
      code('代码对应：read_data / analyze，按列取得一个人', '输入 D: (' + r.nstat + ', ' + r.npeople + ')；D[:, p]: (' + r.nstat + ',)。Python 索引从0开始。', 'person_scores = D[:, p]\nselected_score = D[s, p]\n# 当前 p=' + x.p + ', s=' + x.s + '\n# selected_score = ' + r.data[x.s][x.p]);
  }
  function heatmap(r, x) {
    const left = 76, top = 52, cell = 45;
    let body = r.participants.map((id,i) => '<text x="' + (left + i*cell+cell/2) + '" y="34" text-anchor="middle">' + escape(id) + '</text><text x="66" y="' + (top+i*cell+29) + '" text-anchor="end">' + escape(id) + '</text>').join('');
    body += r.person_correlation.map((row,i) => row.map((v,j) => {const light = 97-Math.abs(v)*25;return '<g data-correlation="' + i + '-' + j + '"><rect x="' + (left+j*cell) + '" y="' + (top+i*cell) + '" width="44" height="44" fill="hsl(' + (v<0?28:195) + ' 60% ' + light + '%)" stroke="' + (i===x.p&&j===x.o?'#111827':'#d7dee5') + '" stroke-width="' + (i===x.p&&j===x.o?4:1) + '"/><text class="q-heat-ink" x="' + (left+j*cell+cell/2) + '" y="' + (top+i*cell+27) + '" text-anchor="middle">' + fmt(v,2) + '</text></g>';}).join('')).join('');
    return svg('correlation', state.person + ' × ' + state.other + ' 黑框单元：Pearson 相关；蓝为正、橙为负，数值也写在格内', 560,530,body);
  }
  function correlations(r, x) {
    const products = r.data.map(row => (row[x.p]-r.means[x.p]) * (row[x.o]-r.means[x.o])), numerator = sum(products), denominator = Math.sqrt(r.centered_sum_squares[x.p] * r.centered_sum_squares[x.o]);
    return head('比较两个人的整份排序，而不是比较陈述', '先把每个分数减去该人的均值，再把同一陈述的两个偏差相乘。相同方向增加相关，相反方向降低相关。20项相加后再除以两列的长度。') +
      eq(escape(state.statement) + ' 的一项：(' + r.data[x.s][x.p] + ' − ' + fmt(r.means[x.p],0) + ') × (' + r.data[x.s][x.o] + ' − ' + fmt(r.means[x.o],0) + ') = ' + fmt(products[x.s],2) + '<br>corr(' + escape(state.person) + ', ' + escape(state.other) + ') = Σ偏差乘积 / √(Σ偏差² × Σ偏差²)<br>= ' + fmt(numerator,2) + ' / √(' + fmt(r.centered_sum_squares[x.p],2) + ' × ' + fmt(r.centered_sum_squares[x.o],2) + ') = ' + fmt(numerator/denominator)) +
      heatmap(r,x) + table('相关矩阵：10个人 × 10个人', ['人', ...r.participants],r.person_correlation.map((row,i)=>[r.participants[i],...row.map(v=>fmt(v,3))]),{row:x.p,col:x.o+1}) +
      table('逐条看相关的分子：所选陈述突出显示', ['陈述',state.person+'分',state.other+'分',state.person+'偏差',state.other+'偏差','偏差乘积'],r.statements.map((st,i)=>[st.id+' '+st.text,r.data[i][x.p],r.data[i][x.o],fmt(r.data[i][x.p]-r.means[x.p],2),fmt(r.data[i][x.o]-r.means[x.o],2),fmt(products[i],2)]),{row:x.s}) +
      note('相关范围为−1至1。负相关表示整份排序倾向相反；0不证明两人毫无共同点。这里 sample SD = √[Σ偏差² / (20−1)] = '+fmt(r.sample_sd[x.p])+'，分母是 n−1。Pearson 公式中两边相同的 n−1 会约掉。') +
      code('代码对应：analyze 中的人相关 C', 'D: (20,10) → C: (10,10)。rowvar=False 告诉 NumPy 每列才是一个待比较对象。', 'centered = D - D.mean(axis=0)\nss = (centered**2).sum(axis=0)\nC = centered.T @ centered / np.sqrt(np.outer(ss, ss))\n# 等价于 np.corrcoef(D, rowvar=False)\nproducts = (D[:, p] - D[:, p].mean()) * (D[:, q] - D[:, q].mean())\n# C['+x.p+', '+x.o+'] = '+fmt(r.person_correlation[x.p][x.o]));
  }
  const membership = row => row[0] ? 'F1 定义排序' : row[1] ? 'F2 定义排序' : '未标记';
  function loadingPoints(r) {
    if (state.loadingView === 'varimax') return r.rotated_loadings;
    if (state.loadingView === 'unrotated') return r.unrotated_loadings;
    const a = state.angle*Math.PI/180, c = Math.cos(a), s = Math.sin(a);
    return r.unrotated_loadings.map(([v,w])=>[v*c-w*s,v*s+w*c]);
  }
  function loadingPlot(r,x,points) {
    const px = value => 62+(value+1.1)/2.2*410, py = value => 442-(value+1.1)/2.2*410;
    const markers = points.map((point,i)=>({id:r.participants[i],x:px(point[0]),y:py(point[1]),radius:i===x.p||i===x.o?13:8,text:r.participants[i]+(i===x.p?'（选）':i===x.o?'（比较）':'')}));
    const labels = loadingLabels(markers);
    let body = '<circle class="q-unit-circle" cx="'+px(0)+'" cy="'+py(0)+'" r="'+(410/2.2)+'"/><line class="q-axis" x1="62" x2="472" y1="'+py(0)+'" y2="'+py(0)+'"/><line class="q-axis" x1="'+px(0)+'" x2="'+px(0)+'" y1="32" y2="442"/>';
    body += [-1,0,1].map(v=>'<text x="'+px(v)+'" y="464" text-anchor="middle">'+v+'</text><text x="50" y="'+(py(v)+5)+'" text-anchor="end">'+v+'</text>').join('');
    // All leaders are behind all marker shapes and text, including other people.
    body += '<g class="q-point-leaders" aria-hidden="true">'+labels.map(label=>{
      const b=label.box,dx=b.endX-label.x,dy=b.endY-label.y,length=Math.hypot(dx,dy),offset=label.radius/length;
      return '<line class="q-point-leader" data-person-leader="'+escape(label.id)+'" x1="'+(label.x+dx*offset)+'" y1="'+(label.y+dy*offset)+'" x2="'+b.endX+'" y2="'+b.endY+'"/>';
    }).join('')+'</g>';
    body += labels.map((label,i)=>{
      const xp=label.x,yp=label.y,chosen=i===x.p,other=i===x.o,kind=r.flagged[i][0]?'one':r.flagged[i][1]?'two':'none',marker=' data-point-marker="'+escape(label.id)+'"',b=label.box;
      const shape=kind==='one'?'<circle'+marker+' cx="'+xp+'" cy="'+yp+'" r="6"/>':kind==='two'?'<rect'+marker+' x="'+(xp-5)+'" y="'+(yp-5)+'" width="10" height="10"/>':'<path'+marker+' d="M'+xp+','+(yp-7)+' l7,7 l-7,7 l-7,-7 Z"/>';
      return '<g class="q-point q-factor-'+kind+'" data-person="'+escape(label.id)+'">'+(chosen||other?'<circle class="q-selection-ring" cx="'+xp+'" cy="'+yp+'" r="11"/>':'')+shape+'<text class="q-point-label" data-person-label="'+escape(label.id)+'" x="'+(b.x+3)+'" y="'+(b.y+14)+'" text-anchor="start">'+escape(label.text)+'</text></g>';
    }).join('');
    body += '<text x="268" y="495" text-anchor="middle">'+(state.loadingView==='varimax'?'F1 载荷':'显示轴1')+'</text><text x="62" y="22">'+(state.loadingView==='varimax'?'F2 载荷':'显示轴2')+'</text>';
    return svg('loadings','一个点是一整份人的排序：圆=固定结果F1；方=固定结果F2；菱形=未标记。图形标签沿用固定 varimax 标记。细线仅将标签连回对应数据点，点的位置不变',560,510,body);
  }
  function extraction(r,x) {
    const k=x.f, eigen=r.all_eigenvalues[k], vectors=r.retained_eigenvectors, rowProducts=r.person_correlation[x.p].map((v,j)=>v*vectors[j][k]), norm=Math.sqrt(dot(r.unrotated_loadings[x.p],r.unrotated_loadings[x.p])), points=loadingPoints(r), retained=100*sum(r.all_eigenvalues.slice(0,2))/sum(r.all_eigenvalues);
    const approximation=dot(r.unrotated_loadings[x.p],r.unrotated_loadings[x.o]), rotated=dot(r.rotated_loadings[x.p],r.rotated_loadings[x.o]), preview=dot(points[x.p],points[x.o]);
    return head('先用两条轴压缩人与人关系，再转动这两条轴', '提取前有10个人彼此的关系；提取后，每人只留下两个坐标，称为载荷。轴的方向用特征向量 v 表示；λ 表示该方向承载多少相关结构。每个点仍然代表人，不是陈述。') +
      eq('C v'+(k+1)+' = λ'+(k+1)+' v'+(k+1)+'；v 每列长度为1（Σv²=1）<br>'+escape(state.person)+' 这一行：Σ C['+escape(state.person)+', j] v[j] = '+fmt(sum(rowProducts))+'<br>λ × v['+escape(state.person)+'] = '+fmt(eigen)+' × '+fmt(vectors[x.p][k])+' = '+fmt(eigen*vectors[x.p][k])+'<br>未旋转载荷 L['+escape(state.person)+', '+(k+1)+'] = '+fmt(vectors[x.p][k])+' × √'+fmt(eigen)+' = '+fmt(r.unrotated_loadings[x.p][k])) +
      '<details><summary>展开这行点积：10个人各贡献什么</summary>'+table('C v 中所选人的一行',['相乘对象 j','C['+state.person+',j]','v[j]','乘积'],r.participants.map((id,i)=>[id,fmt(r.person_correlation[x.p][i]),fmt(vectors[i][k]),fmt(rowProducts[i])]))+'</details>' +
      note('<strong>两轴共保留 '+fmt(retained)+'%</strong> = ('+fmt(r.all_eigenvalues[0])+' + '+fmt(r.all_eigenvalues[1])+') / '+fmt(sum(r.all_eigenvalues),0)+' ×100%。丢失的信息发生在只保留两轴时。第3个特征值 '+fmt(r.all_eigenvalues[2])+' 仍大于1，所以“两因子”是固定教学选择，不能说是 Kaiser>1 自动选出的结果。') +
      scree(r) + table('全部特征值与信息占比',['顺序','特征值 λ','占全部相关矩阵方差','本例保留？'],r.all_eigenvalues.map((v,i)=>[i+1,fmt(v),fmt(100*v/sum(r.all_eigenvalues),3)+'%',i<2?'是':'否'])) +
      '<h4>同一批人，观察旋转前后</h4>'+ (state.loadingView==='geometry'?note('<strong>GEOMETRY PREVIEW · 几何预览 '+fmt(state.angle,0)+'°</strong>：从未旋转 PCA 载荷转动；任意角度不是新的 varimax 最优解。下游标记、权重、z与因子数组始终读取所选场景的固定 varimax 结果。'):'') +
      loadingPlot(r,x,points) + table('载荷：未旋转、固定 varimax 与当前显示',['人','PCA轴1','PCA轴2','F1','F2','当前轴1','当前轴2','固定结果标记'],r.participants.map((id,i)=>[id,...r.unrotated_loadings[i].map(v=>fmt(v,4)),...r.rotated_loadings[i].map(v=>fmt(v,4)),...points[i].map(v=>fmt(v,4)),membership(r.flagged[i])]),{row:x.p}) +
      eq(escape(state.person)+' / '+escape(state.other)+'：原始相关 = '+fmt(r.person_correlation[x.p][x.o])+'<br>两轴近似 = Lp · Lq = Lp1Lq1 + Lp2Lq2<br>旋转前 '+fmt(approximation)+'；固定 varimax 后 '+fmt(rotated)+'；当前显示 '+fmt(preview)) +
      note('正交旋转保持这两轴内的点积与长度，未恢复省略轴的信息。特征值表属于PCA未旋转轴，不能把每个PCA特征值直接贴到混合后的F1/F2上。上面的两轴近似无需等于原始相关。Kaiser 行归一化：先按每个人保留载荷向量的长度缩放，再寻找旋转，最后还原；'+escape(state.person)+' 的长度 = √(L1²+L2²) = '+fmt(norm)+'。') +
      code('代码对应：analyze / varimax 的提取与旋转', 'C: (10,10) → V: (10,2) → L: (10,2)。下面是对应关系；完整迭代与符号对齐见下载代码。', 'eigenvalues, V = np.linalg.eigh(C)\norder = np.argsort(eigenvalues)[::-1]\neigenvalues, V = eigenvalues[order], V[:, order]\nL = V[:, :2] * np.sqrt(eigenvalues[:2])\nh = np.sqrt((L * L).sum(axis=1))\nB = L / h[:, None]  # Kaiser 行归一化\n# 找正交 T，使 Σ_k [Σ_i (BT)_ik^4 - (Σ_i (BT)_ik^2)^2/n] 增大\nL_rotated = (B @ T) * h[:, None]\n# 几何预览只做 L @ R(angle)，不重新拟合，也不回写 L_rotated');
  }
  function scree(r) {
    const top=30,left=58,w=470,h=160,max=Math.max(...r.all_eigenvalues);
    let body='<line class="q-axis" x1="'+left+'" x2="'+(left+w)+'" y1="'+(top+h)+'" y2="'+(top+h)+'"/>';
    body+=r.all_eigenvalues.map((v,i)=>{const x=left+i*47,y=top+h-v/max*h;return '<rect class="q-factor-'+(i<2?'one':'none')+'" x="'+x+'" y="'+y+'" width="29" height="'+(v/max*h)+'"/><text x="'+(x+14)+'" y="'+(y-7)+'" text-anchor="middle">'+fmt(v,2)+'</text><text x="'+(x+14)+'" y="212" text-anchor="middle">'+(i+1)+'</text>';}).join('');
    return svg('scree','特征值从大到小：只保留前两条，不代表第三条已没有信息',560,235,body);
  }
  function flagging(r,x) {
    const row=r.rotated_loadings[x.p], l=row[x.f], rival=sum(row.map((v,k)=>k===x.f?0:v*v)), significant=Math.abs(l)>r.loading_threshold, dominance=l*l>rival;
    return head('定义排序是被规则标记的整份排序', '本例对每个人、每个因子逐一检查两条严格条件：载荷绝对值超过门槛，并且该因子载荷平方大于其余因子载荷平方之和。两条都成立才标记；这不是给人贴永久类型。') +
      eq('门槛 = 1.96 / √'+r.nstat+' = '+fmt(r.loading_threshold)+'<br>'+escape(state.person)+' 对 F'+(x.f+1)+'：|'+fmt(l)+'| '+(significant?'&gt;':'≤')+' '+fmt(r.loading_threshold)+' → '+(significant?'通过':'不通过')+'<br>'+fmt(l*l)+' '+(dominance?'&gt;':'≤')+' '+fmt(rival)+' → '+(dominance?'通过':'不通过')+'<br>同时成立？'+(r.flagged[x.p][x.f]?'是，标记为定义排序':'否，不标记在该因子')) +
      table('固定 varimax 结果的标记账本',['人','F1载荷','F2载荷','F1满足两条？','F2满足两条？','结论'],r.participants.map((id,i)=>[id,...r.rotated_loadings[i].map(v=>fmt(v)),r.flagged[i][0]?'是':'否',r.flagged[i][1]?'是':'否',membership(r.flagged[i])]),{row:x.p}) +
      '<button type="button" data-person-select="P10">看 P10：两轴都很弱</button><button type="button" data-scenario-select="reverse-p03">看全链重算的 P03 反向案例</button>' +
      '<h4>规则小例子：不是额外受访者，也不混入主数据</h4><div class="q-rule-cards">'+
      note('<strong>两因子 (.60, .50)</strong><br>两者都超过0.438269，但 .60²=.36 &gt; .50²=.25，所以可标记 F1。“同时显著”不自动意味着剔除。')+
      note('<strong>两因子 (.50, .50)</strong><br>.25 不严格大于 .25，两边都不标记。等于门槛也不通过；所有比较均为严格 &gt;。')+
      note('<strong>三因子 (.65, .55, .50)：仅规则说明</strong><br>最大平方 .4225 ≤ .3025+.25=.5525，无一通过平方优势。这不是把当前主分析变为三因子。')+
      note('<strong>两因子 (−.80, .10)</strong><br>|−.80|通过门槛，.64&gt;.01，可定义 F1 的反向一极。带符号权重 −.80/(1−.64)=−2.222222；解释必须结合排序内容。')+'</div>' +
      note('P10只是本例“两轴都弱”的未标记案例，不能代表所有未归组原因。统计标记还需要研究者核查、访谈解释与命名；自动标记不自动生成观点名称。') +
      code('代码对应：automatic_flags 的两条严格条件', 'rotated_loadings: (10,2) → flagged: (10,2) 布尔矩阵。', 'significant = abs(L[i, f]) > 1.96 / np.sqrt(nstat)\ndominant = L[i, f]**2 > sum(L[i, k]**2 for k in other_factors)\nflagged[i, f] = significant and dominant');
  }
  function contributionPlot(r,x,values) {
    const max=Math.max(1,...values.map(Math.abs)),zero=280,span=170,top=30,row=31;
    let body='<line class="q-axis" x1="'+zero+'" x2="'+zero+'" y1="15" y2="'+(top+row*r.npeople)+'"/><text x="85" y="16">w × 原始分数</text>';
    body+=values.map((v,i)=>{const y=top+i*row,x1=v<0?zero+v/max*span:zero,width=Math.abs(v)/max*span;return '<g data-contribution="'+escape(r.participants[i])+'"><text x="72" y="'+(y+17)+'" text-anchor="end">'+escape(r.participants[i])+(i===x.p?' *':'')+'</text><rect x="'+x1+'" y="'+y+'" width="'+Math.max(width,1)+'" height="21" class="q-factor-'+(v<0?'negative':'one')+'"'+(i===x.p?' stroke="#111827" stroke-width="3"':'')+'/><text x="470" y="'+(y+17)+'">'+fmt(v,3)+'</text></g>';}).join('');
    return svg('contributions',state.statement+' 对 F'+(x.f+1)+' 的逐人贡献；* 与黑框为 '+state.person+'；负条向左，零权重不贡献',575,top+row*r.npeople+20,body);
  }
  function weighting(r,x) {
    const l=r.rotated_loadings[x.p][x.f],w=r.weights[x.p][x.f],values=r.weights.map((row,i)=>row[x.f]*r.data[x.s][i]),wsum=sum(r.weights.map(row=>row[x.f])),positive=r.weights.every(row=>row[x.f]>=0)&&wsum>0;
    const desc=r.flagged[x.p][x.f]?'已标记，保留载荷符号':'没有在这个因子被标记，因此权重置0';
    return head('先把载荷变成带符号权重，再逐人相加', '载荷越接近±1，公式给出的绝对权重增长越快。本例先对已标记的人计算 w=l/(1−l²)，未标记者在该因子贡献为0。随后同一条陈述的每个人分数乘各自权重。') +
      eq(escape(state.person)+' 对 F'+(x.f+1)+'：'+desc+'<br>w = '+(r.flagged[x.p][x.f]?fmt(l)+' / (1 − ('+fmt(l)+')²) = '+fmt(w):'0')+'<br>'+escape(state.statement)+' 当前人的一项 = '+fmt(w)+' × '+r.data[x.s][x.p]+' = '+fmt(values[x.p])+'<br>T['+escape(state.statement)+', F'+(x.f+1)+'] = Σ wᵢ × xᵢ = '+fmt(r.weighted_totals[x.s][x.f])) +
      contributionPlot(r,x,values) + table('所选陈述的逐人贡献：一行对应一个条形',['人','载荷','是否标记','带符号权重 w',state.statement+'原分','w×原分'],r.participants.map((id,i)=>[id,fmt(r.rotated_loadings[i][x.f]),r.flagged[i][x.f]?'是':'否',fmt(r.weights[i][x.f]),r.data[x.s][i],fmt(values[i])]),{row:x.p}) +
      (positive?note('<strong>当前因子的正权重等价关系（基线同样成立）：总和与加权平均为什么可给同一个 z？</strong><br>F'+(x.f+1)+' 权重和 W='+fmt(wsum)+'。当前陈述加权平均 A=T/W='+fmt(r.weighted_totals[x.s][x.f])+'/'+fmt(wsum)+'='+fmt(r.weighted_totals[x.s][x.f]/wsum)+'。20条 A 的均值='+fmt(r.weighted_total_means[x.f]/wsum)+'，样本SD='+fmt(r.weighted_total_sample_sd[x.f]/wsum)+'。标准化后 ('+fmt(r.weighted_totals[x.s][x.f]/wsum)+'−'+fmt(r.weighted_total_means[x.f]/wsum)+')/'+fmt(r.weighted_total_sample_sd[x.f]/wsum)+'='+fmt(r.statement_z[x.s][x.f])+'，与总和的 z 相同。'+escape(state.person)+' 的 w/W='+fmt(100*w/wsum,2)+'% 只表示这个合成因子内的权重份额。'):note('<strong>本场景含负定义权重</strong>，不要把带符号总和理解成普通的正权重平均。反向 P03 的 x′=6−x，w′=−w；w′x′=wx−6w，只给每条陈述的总和加同一个常数，随后跨陈述中心化抵消。完整重算后的 z 与因子数组可与基线核对。')) +
      note('这些 Q 权重只是构造观点因子数组的计算权重，不是农场优化目标权重、人口占比或采纳概率。非线性放大使高载荷排序影响更大，因此必须读清谁在定义因子。') +
      code('代码对应：postprocess，标记后再加权', 'weights: (10,2)；D: (20,10) → weighted_totals: (20,2)。', 'weights = np.where(flagged, L / (1 - L**2), 0)\nT = D @ weights\n# T['+x.s+', '+x.f+'] = '+fmt(r.weighted_totals[x.s][x.f])+'\n# 当前人的贡献 = '+fmt(w)+' * '+r.data[x.s][x.p]);
  }
  function arrays(r,x) {
    const f=x.f,mean=r.weighted_total_means[f],sd=r.weighted_total_sample_sd[f],z=r.statement_z[x.s][f],ties=r.exact_ties[f] || [];
    return head('标准化看相对位置，再按名次装回强制网格', '先在同一个因子的20条加权总和之间求均值和样本SD。z描述一条陈述相对于这20条陈述高或低多少个标准差。最后按 z 升序排名，再把排名映射到原网格位置。') +
      eq('F'+(f+1)+' 的均值 T̄='+fmt(mean)+'；样本SD s=√[Σ(T−T̄)²/(20−1)]='+fmt(sd)+'<br>'+escape(state.statement)+'：z=('+fmt(r.weighted_totals[x.s][f])+'−'+fmt(mean)+')/'+fmt(sd)+'='+fmt(z)+'<br>z='+fmt(z)+' → 升序名次 '+fmt(r.ranks[x.s][f],2)+' → 网格分数 '+r.factor_arrays[x.s][f]) +
      note(escape(state.statement)+' 比该因子的20条陈述均值'+(z<0?'低':'高')+'约 '+fmt(Math.abs(z),3)+' 个样本标准差。这不是 '+fmt(z*100,1)+'% 重要性，也不是可靠性。factor array 是多人的加权模式，不必等于任何一个真实人的排序。') +
      '<p>本例位置1–2映射1分，3–6映射2分，7–14映射3分，15–18映射4分，19–20映射5分。绝不是把 z 四舍五入成1–5分。</p>'+grid(r,r.factor_arrays.map(row=>row[f]),x.s,'F'+(f+1)+' 的因子数组') +
      table('同一陈述从 T 到最终分数',['陈述','加权总和 T','z','升序名次','factor score'],r.statements.map((st,i)=>[st.id+' '+st.text,fmt(r.weighted_totals[i][f]),fmt(r.statement_z[i][f]),fmt(r.ranks[i][f],2),r.factor_arrays[i][f]]),{row:x.s}) +
      '<details><summary>精确同分为什么需要单列说明</summary><p>本例同分采用平均名次，当前同分落在同一档内，最后仍为2–4–8–4–2。显示小数相同不意味着原值精确相同。若第2、第3位精确同分，平均名次2.5；按本参考实现的 R 索引规则截断取位置2，两条都可能取得1分，格数可能改变。不能偷偷用陈述ID打破同分。</p>'+table('当前因子的精确同分组',['陈述','平均名次','最终分数'],ties.map(t=>[t.statement_indices.map(i=>r.statements[i].id).join(', '),fmt(t.mean_rank,2),t.score]))+'</details>' +
      code('代码对应：postprocess / rank_to_grid 的标准化与映射', 'T: (20,2) → Z/ranks/factor_arrays: (20,2)。ddof=1 指样本SD。', 'Z = (T - T.mean(axis=0)) / T.std(axis=0, ddof=1)\nsorted_z = np.sort(Z[:, f])\nranks = np.array([np.flatnonzero(sorted_z == value).mean() + 1\n                  for value in Z[:, f]])\nslots = np.repeat(grid_scores, grid_counts)\narray = slots[np.trunc(ranks).astype(int) - 1]\n# '+state.statement+': '+fmt(z)+' → '+fmt(r.ranks[x.s][f],2)+' → '+r.factor_arrays[x.s][f]);
  }
  function differencePlot(r,x) {
    const max=Math.max(1,...r.statement_comparisons.map(c=>Math.abs(c.difference)))*1.12,px=v=>290+v/max*225,top=38,row=25,end=top+r.nstat*row,c=r.statement_comparisons[x.s];
    let body='<rect class="q-threshold-band" x="'+px(-c.threshold_p05)+'" y="22" width="'+(px(c.threshold_p05)-px(-c.threshold_p05))+'" height="'+(end-12)+'"/>';
    for(const [value,style]of [[-c.threshold_p01,'q-threshold-01'],[-c.threshold_p05,'q-threshold-05'],[0,'q-axis'],[c.threshold_p05,'q-threshold-05'],[c.threshold_p01,'q-threshold-01']])body+='<line class="'+style+'" x1="'+px(value)+'" x2="'+px(value)+'" y1="22" y2="'+(end+10)+'"/>';
    body+=r.statement_comparisons.map((v,i)=>{const y=top+i*row;return '<g data-difference="'+escape(r.statements[i].id)+'"><text x="58" y="'+(y+5)+'" text-anchor="end">'+escape(r.statements[i].id)+(i===x.s?' *':'')+'</text><line class="q-difference-stem" x1="'+px(0)+'" x2="'+px(v.difference)+'" y1="'+y+'" y2="'+y+'"/><circle class="q-difference-point" cx="'+px(v.difference)+'" cy="'+y+'" r="'+(i===x.s?7:4)+'"/><text x="532" y="'+(y+5)+'">'+fmt(v.difference,3)+'</text></g>';}).join('');
    body+='<text x="290" y="'+(end+34)+'" text-anchor="middle">左：F1更低 ← Δ = z₁ − z₂ → 右：F1更高</text>';
    return svg('difference','Δ与双侧门槛：浅色带内未过p<.05；实线±'+fmt(c.threshold_p05,3)+'；虚线±'+fmt(c.threshold_p01,3)+'。*为当前陈述',610,end+52,body);
  }
  function differences(r,x) {
    const c=r.statement_comparisons[x.s],a=r.assumed_individual_reliability;
    return head('同一条陈述，两个观点真的有可检出的差异吗？', '因子给分高低和因子之间的差异是两件事。软件在连续 z 分数上比较，不是只看最终1–5分是否不同。先由定义排序数量和可靠性假设得到差值的不确定性门槛。') +
      '<div class="q-example-actions"><button type="button" data-statement="S04">看 S04：网格分数不同，未检出差异</button><button type="button" data-statement="S12">看 S12：通过.05，未通过.01</button></div>' +
      eq('每份定义排序的平均可靠性 r='+fmt(a,1)+'：这是软件假设，不是本数据实测<br>m_f 是定义排序数量；R_f=m_f r/[1+(m_f−1)r] 是组合可靠性<br>SE_f=√(1−R_f)，因为每列 z 的样本SD=1<br>SED=√(SE₁²+SE₂²)='+fmt(r.SED)+'<br>p&lt;.05 门槛=1.96×SED='+fmt(c.threshold_p05)+'；p&lt;.01 门槛=2.576×SED='+fmt(c.threshold_p01)) +
      table('从定义排序数到标准误',['因子','m','假设 r','组合可靠性 R','标准误 SE'],[0,1].map(f=>['F'+(f+1),r.flagged_counts[f],a,fmt(r.composite_reliability[f]),fmt(r.factor_standard_errors[f])])) +
      eq(escape(state.statement)+'：两份网格分数='+r.factor_arrays[x.s][0]+' / '+r.factor_arrays[x.s][1]+'<br>Δ='+fmt(r.statement_z[x.s][0])+'−('+fmt(r.statement_z[x.s][1])+')='+fmt(c.difference)+'<br>|Δ|='+fmt(Math.abs(c.difference))+(c.distinguishing_p05?' &gt; ':' ≤ ')+fmt(c.threshold_p05)+' → p&lt;.05 '+(c.distinguishing_p05?'可区分':'未检出差异')+'<br>p&lt;.01 '+(c.distinguishing_p01?'可区分':'未检出差异')) +
      differencePlot(r,x) + table('连续差异与网格分数并排核对',['陈述','F1分','F2分','z₁','z₂','Δ','.05区分？','.01区分？'],r.statements.map((st,i)=>[st.id+' '+st.text,...r.factor_arrays[i],...r.statement_z[i].map(v=>fmt(v,4)),fmt(r.statement_comparisons[i].difference,4),r.statement_comparisons[i].distinguishing_p05?'是':'否',r.statement_comparisons[i].distinguishing_p01?'是':'否']),{row:x.s}) +
      note('<strong>把数字写成谨慎的观点描述。</strong>合成F1把S01稳定产品收入、S02增加粮食供给排5，把S06田边生境、S11野生生物空间排1，可暂称“收入与供给优先”；F2把S03节水、S07土壤肥力排5，可暂称“水与土壤维护优先”。仍须检查完整20条和共同高位S05（两边都4），并用S04/S12的连续检验约束描述。没有访谈理由，不能编造动机；低档只是这套陈述中的相对位置。这是合成模式的暂名，不是原作者观点名称或真实人口分类。') +
      note('本例仅比较F1/F2，未另作多重比较校正。Consensus 只是在这个检验下未检出差异，不代表人人赞同、不证明两观点等价，也不表示这条陈述都被评为高优先。作者三因子结果需要核查所有相关成对比较；不能把这个两因子流程静默扩成通用多因子检验。') +
      code('代码对应：postprocess 中两因子专用的差值判据', 'flagged_counts: (2,) → R/SE: (2,) → comparisons: 20条。完整实现须拒绝非两因子输入。', 'R = m * r / (1 + (m - 1) * r)\nSE = np.sqrt(1 - R)\nSED = np.sqrt(SE[0]**2 + SE[1]**2)\ndelta = Z[:, 0] - Z[:, 1]\ndistinguishing_p05 = abs(delta) > 1.96 * SED\ndistinguishing_p01 = abs(delta) > 2.576 * SED');
  }
  function sourceFigure(figure,i) {
    const path=localImage(figure.path),offline=global.location?.protocol==='file:';
    const size=Number.isInteger(figure.width)&&figure.width>0&&Number.isInteger(figure.height)&&figure.height>0?' width="'+figure.width+'" height="'+figure.height+'"':'';
    return '<section class="q-source-item"><h4>'+escape(figure.title || figure.id)+'</h4><p>'+escape(figure.meaning || '')+'</p>'+(path&&!offline?'<figure class="q-source-figure"><div class="q-source-scroll" tabindex="0" role="region" aria-label="'+escape(figure.title)+'原始图像，可横向滚动"><img data-source-image="'+i+'" src="'+escape(path)+'" alt="'+escape(figure.alt || figure.title)+'"'+size+' loading="lazy" decoding="async"></div><figcaption>'+escape(figure.caption || '')+'</figcaption><p class="q-image-status" data-image-status="'+i+'" hidden>原图未能加载。请从完整站点缓存或原文入口查看；合成图表和文字仍可阅读。</p></figure>':'<p class="q-image-status">'+(offline?'当前为单文件 file: 模式，原图未嵌入。':'本地原图路径未配置。')+'请使用完整站点缓存或原文入口；八步文字与合成图表可离线阅读。</p>')+'<p>'+link(figure.anchor,'打开这幅图的原文位置')+'</p>'+note(escape(figure.boundary || '保持原图，不用合成点覆盖作者图像。'))+'</section>';
  }
  function articleBridge() {
    const example=source.categoryExample || {},categories=example.categories || [],figures=source.figures || [];
    return head('同一个“点”，在三幅论文图里代表不同对象', '到这里，我们已解释合成排序怎样成为因子数组。论文图3还多了一步服务类别汇总与缩放；图4转为观点的定性优先关系；图5则是观点分组与属性的关联分析。它们不是同一张载荷图。') +
      '<p>'+link(source.original,'打开 Cheng 原文')+' · '+link(source.doi,'文章 DOI')+'</p>'+table('先确认一幅图的统计对象',['位置','一个图形对象是什么','后续运算／解释边界'],[['合成载荷图','一份人的完整排序','坐标为两个载荷'],['Cheng Fig.3','一个观点对一类服务的缩放分值','需类别汇总和0–100缩放；不是个人载荷'],['Cheng Fig.4','一个观点','三角形表达定性优先关系；距离不是倍数'],['Cheng Fig.5','观点分组与个人／农场属性的比较','含 Ungrouped；关联分析不是Q区分陈述检验，也不是因果证明']]) +
      '<h4>可核实的真实算术：'+escape(example.label || 'Farmer_1 的 Table 5 factor scores')+'</h4><p>作者 Table 2 确定成员类别，Table 5 给出已发表 factor scores。下面只计算这些已发表分数的和与算术均值，不把合成 S01 等陈述混进作者类别。</p>'+table('作者已发表 factor scores → 教学计算的类别均值',['类别','已发表分数','条数','分数和','算术均值'],categories.map(c=>[c.name,(c.scores || []).join(', '),c.count,sum(c.scores || []),fmt(c.mean)])) +
      '<p>'+link(example.sourceLink,'核对 Table 5 原文单元格')+' · '+link(example.membershipLink,'核对 Table 2 类别成员')+'</p>'+(categories.some(c=>Array.isArray(c.members))?'<details><summary>逐项核对：作者的服务名称、所属类别与 Farmer_1 分数</summary>'+table('Table 2 成员连接到 Table 5 已发表分数',['服务名称（保留原文）','类别','Farmer_1分数'],categories.flatMap(c=>(c.members||[]).map((member,i)=>[member,c.name,c.scores[i]])))+'<p>原表列序为2/7/4/7。Table 5 的 Natural hazards 与 Table 2 的 Natural hazard 用词差异保留在原文，不另造类别。</p></details>':'')+eq('类别成员 → Table 5 factor scores → 类别和／均值 → gₖ(类别平均；参考界限) → Fig.3 的0–100分值')+
      note('<strong>这里有一段尚未核实的变换。</strong>作者 §2.2.5 明示按类别汇总、缩放到0–100，并定义 &gt;50 为优先；补充材料尚未取得，精确缩放公式未确认。Table 5 的类别均值不等于图3缩放值，不能擅自补入 (均值−1)/4×100 并归因作者，也不能把图中粗读数说成精确重算。') +
      figures.map(sourceFigure).join('') +
      note('Fig.4 的 Village_2 / Farmer_3 可读出 C&gt;P 等定性关系，但不能读“距离两倍”，也不能叫 PCA 坐标。Fig.5 是分组后的独立属性比较，不证明年龄或其他属性导致某观点。作者“优先”“主要优先”“仅优先”的文字口径需分别保留，不能把数量合成一个数。') +
      '<details><summary>作者设置与仍待补齐的证据</summary>'+((source.authorSettings || []).length?'<ul>'+source.authorSettings.map(item=>'<li>'+escape(typeof item==='string'?item:JSON.stringify(item))+'</li>').join('')+'</ul>':'<p>作者原始排序、访谈理由、补充计算、软件精确版本与脚本仍须核对。</p>')+'<p>教学计算完成不等于作者结果复现。Q载荷、因子分数、可靠性和定义排序人数都不能自动变成优化目标权重或人口比例；研究迁移需另行解释映射与敏感性。</p></details>' +
      code('独立分支的代码关系：只计算已核对的均值', '每个类别只有 Table 5 已发表分数；不推定作者的0–100缩放算法。', 'category_mean = sum(published_factor_scores) / len(published_factor_scores)\n# scaled_score = author_scaling(category_mean, reference_bounds)\n# author_scaling 的精确实现尚未核实，因此不补造数值。');
  }
  const stages=[first,correlations,extraction,flagging,weighting,arrays,differences,articleBridge];
  const visibility={scenario:[0,1,2,3,4,5,6],person:[0,1,2,3,4],other:[1,2],statement:[0,1,4,5,6],factor:[2,3,4,5],loadingView:[2],angle:[2]};
  function render() {
    if(!mounted || rendering)return;
    rendering=true;
    try {
      const r=D(),x=indexes(r);
      panel.querySelectorAll('[data-control]').forEach(control=>{const key=control.getAttribute('data-control');control.hidden=!visibility[key].includes(state.step)||(key==='angle'&&state.loadingView!=='geometry');});
      panel.querySelectorAll('[data-step]').forEach(button=>{const selected=Number(button.getAttribute('data-step'))===state.step;button.setAttribute('aria-current',selected?'step':'false');});
      panel.querySelectorAll('[data-action="previous"]').forEach(button=>{button.disabled=state.step===0;});
      panel.querySelectorAll('[data-action="next"]').forEach(button=>{button.disabled=state.step===7;});
      panel.querySelectorAll('.q-position').forEach(el=>{el.textContent=(state.step+1)+' / 8';});
      const chosen=config.scenarios.find(s=>s.id===state.scenario);
      q('.q-status').textContent='第'+(state.step+1)+'步 · '+(state.step===7?'原论文证据':chosen.label+' · '+chosen.description)+(invalid?' · 无效输入未采用，保留上次有效结果':'');
      q('.q-error').textContent=invalid;q('.q-error').hidden=!invalid;
      q('[data-field="angle"]').setAttribute('aria-invalid',String(!!invalid));
      if(stage.dataset.renderedStep !== undefined) detailsByStep[stage.dataset.renderedStep]=[...stage.querySelectorAll('details')].map(item=>!!item.open);
      stage.innerHTML=stages[state.step](r,x);stage.dataset.renderedStep=String(state.step);
      stage.querySelectorAll('details').forEach((item,i)=>{item.open=!!detailsByStep[state.step]?.[i];});
      stage.querySelectorAll('[data-source-image]').forEach(img=>img.addEventListener('error',()=>{img.hidden=true;const status=stage.querySelector('[data-image-status="'+img.getAttribute('data-source-image')+'"]');if(status)status.hidden=false;},{once:true}));
      remember();
    } finally {rendering=false;}
  }
  function navigate(step) {
    if(!Number.isInteger(step)||step<0||step>7)return;
    state.step=step;render();
    const heading=stage.querySelector('h3');
    if(heading){if(typeof heading.focus==='function')heading.focus({preventScroll:true});if(typeof heading.scrollIntoView==='function')heading.scrollIntoView({block:'start',behavior:'auto'});}
  }
  function setControl(key,value) {state[key]=value;const input=q('[data-field="'+key+'"]');if(input)input.value=String(value);}
  function reset() {Object.keys(defaults).forEach(key=>setControl(key,defaults[key]));Object.keys(detailsByStep).forEach(key=>delete detailsByStep[key]);stage.querySelectorAll('details').forEach(item=>{item.open=false;});q('.q-downloads').open=false;invalid='';lastDownload='';q('.q-download-status').textContent='';render();}
  function change(event) {
    if(rendering||event.isComposing)return;
    const target=event.target,key=target.getAttribute&&target.getAttribute('data-field');if(!key)return;
    const raw=String(target.value),r=D(),wasInvalid=!!invalid;let value=raw;
    if(key==='angle') {
      value=Number(raw);
      if(!raw.trim()||!Number.isFinite(value)||value<-180||value>180||!Number.isInteger(value)){invalid='角度须为−180至180的整数；当前图保留上次有效角度 '+state.angle+'°。';render();return;}
      invalid='';
    }else if(key==='factor'){value=Number(raw);if(![0,1].includes(value))return;}
    else if(key==='person'||key==='other'){if(!r.participants.includes(raw))return;}
    else if(key==='statement'){if(!r.statements.some(s=>s.id===raw))return;}
    else if(key==='scenario'){if(!config.scenarios.some(s=>s.id===raw))return;}
    else if(key==='loadingView'){if(!['unrotated','varimax','geometry'].includes(raw))return;}
    else return;
    if(state[key]===value&&!invalid&&!wasInvalid)return;
    state[key]=value;render();
  }
  function download(name) {
    const files=global.PAPER_DATA?.files;
    if(!Array.isArray(config.downloads)||!config.downloads.includes(name)||!files||!Object.prototype.hasOwnProperty.call(files,name)||typeof files[name]!=='string') {q('.q-download-status').textContent='此文件未打包，无法下载：'+name;return;}
    if(!global.URL?.createObjectURL||!global.Blob){q('.q-download-status').textContent='当前环境不支持文件下载；请使用完整站点。';return;}
    const url=global.URL.createObjectURL(new global.Blob([files[name]],{type:'text/plain;charset=utf-8'}));urls.add(url);
    const anchor=doc.createElement('a');anchor.href=url;anchor.download=name;anchor.hidden=true;panel.append(anchor);anchor.click();anchor.remove();
    lastDownload=name;q('.q-download-status').textContent='已准备下载：'+name+'（本站打包的原文件）';
    const timer=global.setTimeout(()=>{global.URL.revokeObjectURL(url);urls.delete(url);timers.delete(timer);},1000);timers.add(timer);
  }
  function click(event) {
    if(event.target.closest?.('a'))remember();
    const button=event.target.closest&&event.target.closest('button');if(!button||!panel.contains(button)||button.disabled)return;
    const step=button.getAttribute('data-step'),action=button.getAttribute('data-action'),statement=button.getAttribute('data-statement'),person=button.getAttribute('data-person-select'),scenario=button.getAttribute('data-scenario-select'),file=button.getAttribute('data-q-download');
    if(step!==null)navigate(Number(step));
    else if(action==='next')navigate(state.step+1);
    else if(action==='previous')navigate(state.step-1);
    else if(action==='reset')reset();
    else if(statement!==null&&D().statements.some(s=>s.id===statement)){setControl('statement',statement);render();q('[data-field="statement"]').focus({preventScroll:true});}
    else if(person!==null&&D().participants.includes(person)){setControl('person',person);render();q('[data-field="person"]').focus({preventScroll:true});}
    else if(scenario!==null&&config.scenarios.some(s=>s.id===scenario)){setControl('scenario',scenario);setControl('person','P03');setControl('factor',0);render();q('[data-field="person"]').focus({preventScroll:true});}
    else if(file!==null)download(file);
  }
  function keydown(event) {
    if(event.target!==panel||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();navigate(event.key==='Home'?0:event.key==='End'?7:Math.max(0,Math.min(7,state.step+(event.key==='ArrowRight'?1:-1))));
  }
  function onRoute() {
    // Native Back/Forward: popstate may mount a new same-route panel before paired hashchange.
    // That new panel belongs to mountedHash and MUST survive the later history event.
    if((global.location?.hash||'')!==mountedHash||!container.isConnected)destroy();
  }
  function busy() {
    if(!mounted||!container.isConnected)return false;
    const focus=doc.activeElement,selection=typeof global.getSelection==='function'?global.getSelection():null;
    const selecting=!!selection&&!selection.isCollapsed&&panel.contains(selection.anchorNode);
    return !!invalid||selecting||urls.size>0||Object.keys(defaults).some(key=>state[key]!==defaults[key])||!!(focus&&panel.contains(focus)&&['INPUT','SELECT','TEXTAREA'].includes(focus.tagName));
  }
  function destroy() {
    if(!mounted)return;mounted=false;
    for(const [name,handler]of [['click',click],['input',change],['change',change],['keydown',keydown]])panel.removeEventListener(name,handler);
    global.removeEventListener('hashchange',onRoute);global.removeEventListener('popstate',onRoute);
    panel.removeEventListener('toggle',remember,true);
    if(observer)observer.disconnect();
    timers.forEach(timer=>global.clearTimeout(timer));timers.clear();urls.forEach(url=>global.URL.revokeObjectURL(url));urls.clear();
    panel.remove();active.delete(controller);mounts.delete(container);
  }
  const controller={destroy,reset,isBusy:busy,getState:()=>({...state,mounted,invalid:!!invalid,error:invalid,busy:busy(),pendingTimer:timers.size>0,lastDownload})};
  mounts.set(container,controller);active.add(controller);
  panel.addEventListener('click',click);panel.addEventListener('input',change);panel.addEventListener('change',change);panel.addEventListener('keydown',keydown);
  panel.addEventListener('toggle',remember,true);
  global.addEventListener('hashchange',onRoute);global.addEventListener('popstate',onRoute);
  if(global.MutationObserver){observer=new global.MutationObserver(()=>{if(!container.isConnected||!panel.isConnected)destroy();});observer.observe(doc.documentElement,{childList:true,subtree:true});}
  q('.q-download-buttons').innerHTML=(config.downloads||[]).map(name=>'<button type="button" data-q-download="'+escape(name)+'"'+(typeof global.PAPER_DATA?.files?.[name]==='string'?'':' disabled')+'>'+escape(name)+'</button>').join('');
  render();return controller;
}
global.PaperQWalkthrough={mount,isBusy:()=>[...active].some(controller=>controller.isBusy())};
})(window);
