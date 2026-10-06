/* Original annual N ledger: manual explanation, one calculation, local memory only. */
(function (global) {
  'use strict';
  const mounts = new WeakMap(), active = new Set(), snapshots = new Map();
  const documentKey = global.crypto?.randomUUID?.() ||
    ('page-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2));
  let serial = 0;
  const STEPS = ['定边界与单位', '收获和饲料', '动物与粪肥链', '土壤这一笔', '合并整座农场', '保留后再减投入'];
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const fmt = value => (Math.abs(value) < 0.000000001 ? 0 : value).toFixed(2);
  const eq = text => '<p class="annual-equation">' + text + '</p>';
  const NOTE = '全部系数由本站编写，仅解释年度守恒；不是作者数据、FarmDESIGN/FarmM3复现、排放因子或施肥处方。';
  const ZERO = '饲料浪费、固氮、垫料、粪肥进口、粪肥外运和存量变化均设为0；多余饲草明确出口。';
  const LIMIT = '产量和产品N固定；没有检验有效N、季节供应、土壤、天气或产量响应，也没有能量/蛋白日粮、温室气体、有机质或经济模块。';
  const FIELDS = [
    ['cashArea', '商品作物面积', '10 − 饲草面积'],
    ['forageHarvest', '全部饲草收获', '饲草面积 × 6'],
    ['feedDemand', '动物饲料需求', '动物数 × 5'],
    ['feedConsumed', '自产饲草实际饲用', 'min(全部收获, 需求)'],
    ['feedImported', '外购饲料', 'max(需求 − 收获, 0)'],
    ['feedExported', '多余饲草出口', 'max(收获 − 需求, 0)'],
    ['forageHarvestNitrogen', '全部收获饲草N', '全部饲草收获 × 25；从土壤账全部扣除'],
    ['feedNitrogenConsumed', '自产饲草实际饲用N', '自产实际饲用 × 25；仅这部分进入动物'],
    ['feedNitrogenImported', '外购饲料N', '外购饲料 × 25'],
    ['feedNitrogenExported', '多余饲草出口N', '多余饲草出口 × 25'],
    ['cashProductNitrogen', '商品作物出口N', '商品作物面积 × 60'],
    ['animalProductNitrogen', '动物产品出口N', '动物数 × 20'],
    ['manureExcretedNitrogen', '排泄N', '自产饲用N + 外购饲料N − 动物产品N'],
    ['chainLoss', '粪肥链N损失', '排泄N × 链条损失比例'],
    ['manureToSoil', '返回土壤的粪肥N', '排泄N − 粪肥链N损失'],
    ['baseMineralNitrogen', '参考矿质N投入', '饲草面积 × 100 + 商品作物面积 × 80'],
    ['retainedNitrogen', '相对比例0.20多保留的N', '(0.20 − 当前比例) × 排泄N'],
    ['mineralNitrogen', '实际矿质N投入', '勾选替代时：参考投入 − 多保留N；否则仍用参考投入'],
    ['depositionNitrogen', '外部沉降N', '总面积10 × 10'],
    ['soilResidual', '土壤N残差', '矿质N + 沉降N + 返回粪肥N − 全部收获饲草N − 商品作物N'],
    ['farmInputs', '全场外部N输入', '矿质N + 外购饲料N + 沉降N'],
    ['farmOutputs', '全场N产品出口', '商品作物N + 动物产品N + 多余饲草出口N'],
    ['farmSurplus', '全场N盈余', '全场外部N输入 − 全场N产品出口'],
    ['checkError', '守恒核对差额', '全场N盈余 − 粪肥链N损失 − 土壤N残差']
  ];
  const PARAMS = [
    ['totalArea', '农场总面积', 'ha'], ['forageYield', '目标饲草产量', 'Mg DM/(ha·year)'],
    ['feedPerAnimal', '每头年饲料需求', 'Mg DM/(头·year)'],
    ['feedNitrogenConcentration', '所有饲料统一N浓度', 'kg N/Mg DM'],
    ['forageMineralRate', '饲草地参考矿质N', 'kg N/(ha·year)'],
    ['cashMineralRate', '商品作物地参考矿质N', 'kg N/(ha·year)'],
    ['depositionRate', '外部沉降N', 'kg N/(ha·year)'],
    ['cashProductRate', '商品作物目标出口N', 'kg N/(ha·year)'],
    ['animalProductRate', '每头目标动物产品N', 'kg N/(头·year)'],
    ['feedImportCap', '外购饲料上限', 'Mg DM/year'],
    ['referenceLossFraction', '比较用参考链条损失比例', '比例']
  ];
  function table(caption, headers, rows) {
    return '<div class="annual-table-scroll" tabindex="0" role="region" aria-label="' + escape(caption) + '；窄屏可横向滚动"><table><caption>' + escape(caption) + '</caption><thead><tr>' + headers.map(x => '<th scope="col">' + escape(x) + '</th>').join('') + '</tr></thead><tbody>' + rows.map(row => '<tr>' + row.map((cell, i) => (i ? '<td>' : '<th scope="row">') + escape(cell) + (i ? '</td>' : '</th>')).join('') + '</tr>').join('') + '</tbody></table></div>';
  }
  function mount(container) {
    if (!container || !container.ownerDocument || typeof container.append !== 'function') throw new TypeError('PaperAnnualBalance.mount需要DOM容器');
    if (mounts.has(container)) return mounts.get(container);
    const model = global.PaperAnnualBalanceModel;
    if (!model || typeof model.calculate !== 'function') throw new TypeError('请先加载annual-balance-model.js');
    const doc = container.ownerDocument, uid = 'paper-annual-' + (++serial), mountedHash = global.location?.hash || '';
    const priorKey = global.history?.state?.paperAnnualEntry, prior = snapshots.get(priorKey);
    const restored = prior?.hash === mountedHash ? prior : null;
    const historyKey = restored ? priorKey : documentKey + ':' + uid;
    let inputs = {...(restored?.inputs || model.defaults)}, result = model.calculate(inputs), step = restored?.step || 0;
    let mounted = true, errors = [], observer, lastDownload = '', printDetails = null;
    const urls = new Set(), timers = new Set();
    const panel = doc.createElement('section');
    panel.className = 'annual-walkthrough';
    panel.setAttribute('aria-label', '同一合成农场的一年：氮收支六步带读');
    panel.setAttribute('data-no-terms', 'true'); panel.setAttribute('tabindex', '0');
    const field = (name, label, help) => '<div class="annual-field"><label for="' + uid + '-' + name + '">' + label + '</label><input id="' + uid + '-' + name + '" data-annual-field="' + name + '" type="number" inputmode="' + (name === 'herd' ? 'numeric' : 'decimal') + '" min="' + model.domain[name].min + '" max="' + model.domain[name].max + '" step="' + model.domain[name].step + '" aria-describedby="' + uid + '-' + name + '-help ' + uid + '-error"><small id="' + uid + '-' + name + '-help">' + help + '</small></div>';
    panel.innerHTML = '<header class="annual-header"><p class="annual-eyebrow">原创合成模型 · 一座10 ha农场 · 一整年</p><h2>这份氮，从哪里来，到哪里去？</h2><p>从饲料、动物和粪肥走到土壤，再合并成一张全场账。四个输入同时驱动流程图、公式、表格和约束；按自己的顺序阅读。</p><p class="annual-boundary">' + NOTE + '</p></header>' +
      '<fieldset class="annual-controls"><legend>先选这座合成农场的配置</legend>' + field('herd', '动物数（等价头数）', '0–20头；每次1头，无年龄结构') + field('forageArea', '饲草面积（ha）', '0–10 ha；每次0.5 ha；其余为商品作物') + field('lossFraction', '粪肥链损失比例', '0–0.20；每次0.05；0.20即20%') +
      '<div class="annual-replace"><label for="' + uid + '-replace"><input id="' + uid + '-replace" data-annual-field="replaceRetained" type="checkbox">把相对0.20多保留的N，等量替代矿质N</label><small>这是单独的投入调整假设；勾选后才减少矿质N。产量仍按固定目标计算，尚未验证田间可行性。</small></div></fieldset>' +
      '<div class="annual-toolbar"><button type="button" data-annual-action="reset">恢复8头／6 ha／0.20，不替代</button></div><p class="annual-error" id="' + uid + '-error" role="alert" hidden></p><p class="annual-status" role="status" aria-live="polite"></p>' +
      '<nav class="annual-steps" aria-label="六步收支带读">' + STEPS.map((label, i) => '<button type="button" data-annual-stage="' + i + '"><span>' + (i + 1) + '</span>' + label + '</button>').join('') + '</nav><section class="annual-stage"></section>' +
      '<div class="annual-nav"><button type="button" data-annual-action="previous">上一步</button><span class="annual-position"></span><button type="button" data-annual-action="next">下一步</button></div>' +
      '<div class="annual-metrics"></div><div class="annual-constraints"></div><figure class="annual-figure"><div class="annual-figure-heading"><h3>同一份N的流向</h3><p class="annual-scroll-hint">图中所有数值：kg N/年。窄屏可在图内左右滚动；下方表格提供完整文字替代。</p></div><div class="annual-chart-scroll" tabindex="0" role="region" aria-label="年度N流向图，可左右滚动"></div><figcaption class="annual-figure-caption"></figcaption></figure>' +
      '<div class="annual-gate-table"></div><details class="annual-ledger"><summary>逐项核对：输入、固定参数、全部中间值和公式</summary><p>显示值保留两位小数；下载保留原始精度。Mg是公吨（1000 kg），DM是干物质，kg N是氮元素质量；它们不能混用。</p><div class="annual-input-table"></div><div class="annual-parameter-table"></div><div class="annual-all-table"></div><p>' + ZERO + '</p></details>' +
      '<aside class="annual-caveat"><h3>算得闭合，还不能直接用于田间</h3><p>正土壤残差是需要解释的去向，不是校准污染量；负残差表示N供应赤字或目标不相容，不能当作环境收益。</p><p>' + LIMIT + '</p></aside>' +
      '<section class="annual-downloads" aria-label="下载与打印"><h3>带走当前这份合成账本</h3><div class="annual-toolbar"><button type="button" data-annual-download="inputs">输入CSV</button><button type="button" data-annual-download="json">完整结果JSON</button><button type="button" data-annual-download="csv">完整账本CSV</button><button type="button" data-annual-action="print">打印当前账本</button></div><p>输入CSV只有四列，可交给配套Python的 --input；完整账本CSV是带单位的长表，不是该命令的输入。无效输入期间暂停下载，请先修正或恢复默认。</p><p class="annual-download-status" role="status"></p></section><footer class="annual-footnote">概念连接：<a href="#/farmdesign-2012-balance-walkthrough">FarmDESIGN年度收支带读</a> · <a href="#/qu-2025-chain-walkthrough">Qu粪肥链带读</a>。本图和数字由本站原创，不是论文原图或作者情景结果。选择仅存在本页会话内存中。</footer>';
    container.append(panel);
    const q = selector => panel.querySelector(selector), qa = selector => [...panel.querySelectorAll(selector)];
    function writeControls(raw) {
      for (const name of ['herd', 'forageArea', 'lossFraction']) q('[data-annual-field="' + name + '"]').value = raw ? raw[name] : String(inputs[name]);
      q('[data-annual-field="replaceRetained"]').checked = raw ? raw.replaceRetained : inputs.replaceRetained;
    }
    function rawControls() {
      return Object.fromEntries(Object.keys(model.defaults).map(name => [name, name === 'replaceRetained' ? q('[data-annual-field="' + name + '"]').checked : q('[data-annual-field="' + name + '"]').value]));
    }
    function remember() {
      if (!mounted || (global.location?.hash || '') !== mountedHash) return;
      snapshots.set(historyKey, {hash: mountedHash, inputs: {...inputs}, raw: rawControls(), step, ledgerOpen: q('.annual-ledger').open});
      // Only an opaque entry key is placed in existing history state. No inputs,
      // notes or private data are put in web storage or sent anywhere.
      if (global.history?.replaceState) global.history.replaceState({...global.history.state, paperAnnualEntry: historyKey}, '', global.location.href);
    }
    function head(title, text) {
      return '<p class="annual-eyebrow">第 ' + (step + 1) + ' / 6 步 · 可随时跳转</p><h3 tabindex="-1">' + title + '</h3><p>' + text + '</p>';
    }
    function stageContent() {
      const r = result, i = inputs, f = fmt;
      if (step === 0) return head('先圈出边界，再开始加减', '把作物、动物和粪肥链都放进农场的边界；比较的是同一整年的流量。内部来回传递的N不能重复算作外部投入。') +
        eq('总面积：' + f(model.constants.totalArea) + ' ha = 饲草 ' + f(i.forageArea) + ' ha + 商品作物 ' + f(r.cashArea) + ' ha') +
        '<p>kg N/年表示这整座农场一年通过的氮元素质量；kg N/(ha·年)才是单位面积投入。6 Mg DM/(ha·年)先乘面积才成为年收获量，再乘25 kg N/Mg DM才成为N流量。</p><p>' + ZERO + '</p><p>这些教学范围合计4,410种配置，其中也包含不满足约束的配置；可选到不等于可实施。</p>';
      if (step === 1) return head('收获、吃掉、购入、出口是四个量', '先算干物质（Mg DM/年）。所有饲草都离开土壤，但只有实际饲用的部分进入动物；多余部分直接出口。') +
        eq('收获 = ' + f(i.forageArea) + ' ha × 6 Mg DM/(ha·年) = ' + f(r.forageHarvest) + ' Mg DM/年<br>需求 = ' + f(i.herd) + ' 头 × 5 Mg DM/(头·年) = ' + f(r.feedDemand) + ' Mg DM/年') +
        eq('自产实际饲用 = min(' + f(r.forageHarvest) + ', ' + f(r.feedDemand) + ') = ' + f(r.feedConsumed) + '<br>外购 = max(' + f(r.feedDemand) + ' − ' + f(r.forageHarvest) + ', 0) = ' + f(r.feedImported) + '<br>多余出口 = max(' + f(r.forageHarvest) + ' − ' + f(r.feedDemand) + ', 0) = ' + f(r.feedExported) + '<br>以上三项单位均为 Mg DM/年') +
        eq('动物采食N = (' + f(r.feedConsumed) + ' + ' + f(r.feedImported) + ') Mg DM/年 × 25 kg N/Mg DM = ' + f(r.feedNitrogenConsumed + r.feedNitrogenImported) + ' kg N/年') +
        '<p>外购上限为10 Mg DM/年。这只检查干物质数量；统一N浓度是教学简化，并未验证蛋白、能量、结构或季节饲料供应。</p>';
      if (step === 2) return head('动物留下产品，其余N进入粪肥链', '这里没有体重、畜群或物料库存净增加，也没有垫料。排泄N在整条链上分成损失和返回土壤两部分。') +
        eq('动物产品N = ' + f(i.herd) + ' × 20 = ' + f(r.animalProductNitrogen) + ' kg N/年<br>排泄N = 自产饲用N ' + f(r.feedNitrogenConsumed) + ' + 购料N ' + f(r.feedNitrogenImported) + ' − 产品N ' + f(r.animalProductNitrogen) + ' = ' + f(r.manureExcretedNitrogen) + ' kg N/年') +
        eq('链条损失 = ' + f(r.manureExcretedNitrogen) + ' × ' + f(i.lossFraction) + ' = ' + f(r.chainLoss) + ' kg N/年<br>返回土壤 = ' + f(r.manureExcretedNitrogen) + ' − ' + f(r.chainLoss) + ' = ' + f(r.manureToSoil) + ' kg N/年') +
        '<p>损失比例把收集、储存、处理和施用合为一个自编参数；它不是某项真实技术的排放因子。返回土壤的N也不等于当季全部可被作物吸收的有效N。</p>';
      if (step === 3) return head('土壤扣除的是全部收获', '土壤边界接收矿质N、外部沉降和返回的粪肥N；输出包括全部收获饲草和商品作物的N。') +
        eq('参考矿质N = ' + f(i.forageArea) + ' × 100 + ' + f(r.cashArea) + ' × 80 = ' + f(r.baseMineralNitrogen) + ' kg N/年<br>当前实际矿质N = ' + f(r.baseMineralNitrogen) + ' − ' + f(i.replaceRetained ? r.retainedNitrogen : 0) + ' = ' + f(r.mineralNitrogen) + ' kg N/年') +
        eq('土壤N残差 = ' + f(r.mineralNitrogen) + ' + ' + f(r.depositionNitrogen) + ' + ' + f(r.manureToSoil) + ' − ' + f(r.forageHarvestNitrogen) + ' − ' + f(r.cashProductNitrogen) + ' = ' + f(r.soilResidual) + ' kg N/年') +
        '<p>收获饲草N ' + f(r.forageHarvestNitrogen) + ' = 场内饲用 ' + f(r.feedNitrogenConsumed) + ' + 出口 ' + f(r.feedNitrogenExported) + ' kg N/年。若只扣饲用部分，会漏掉已经运出农场的N。</p><p>' + (r.flags.soilSupplyDeficit ? '当前为负残差：供应不足以支撑给定输出，配置不通过。它不是“负污染”。' : '当前非负残差仍需解释。这个数没有区分淋溶、反硝化、径流等过程，不是校准过的污染预测。') + '</p>';
      if (step === 4) return head('把内部传递划掉，只看跨边界的流', '自产饲草、排泄和返回粪肥在内部一个模块的输出，正好是另一个模块的输入；合并后抵消。') +
        eq('全场外部N输入 = 矿质 ' + f(r.mineralNitrogen) + ' + 购料 ' + f(r.feedNitrogenImported) + ' + 沉降 ' + f(r.depositionNitrogen) + ' = ' + f(r.farmInputs) + ' kg N/年<br>全场N出口 = 商品作物 ' + f(r.cashProductNitrogen) + ' + 动物产品 ' + f(r.animalProductNitrogen) + ' + 多余饲草 ' + f(r.feedNitrogenExported) + ' = ' + f(r.farmOutputs) + ' kg N/年') +
        eq('全场N盈余 = ' + f(r.farmInputs) + ' − ' + f(r.farmOutputs) + ' = ' + f(r.farmSurplus) + ' kg N/年<br>同一个数 = 链条损失 ' + f(r.chainLoss) + ' + 土壤残差 (' + f(r.soilResidual) + ') = ' + f(r.chainLoss + r.soilResidual) + ' kg N/年') +
        table('相加时抵消的三条内部流', ['内部流', '上一模块输出', '下一模块输入', '进入全场外部投入？'], [['自产实际饲用N', f(r.feedNitrogenConsumed), f(r.feedNitrogenConsumed), '否'], ['排泄N', f(r.manureExcretedNitrogen), f(r.manureExcretedNitrogen), '否'], ['返回粪肥N', f(r.manureToSoil), f(r.manureToSoil), '否']]) +
        '<p>上表数值单位为kg N/年。检查误差容限为1×10⁻⁹ kg N/年；算术守恒通过只验证这套记账一致，不能替代现实数据验证。</p>';
      const reference = model.calculate({...i, lossFraction: 0.20, replaceRetained: false});
      const kept = model.calculate({...i, replaceRetained: false});
      const replaced = model.calculate({...i, replaceRetained: true});
      return head('少在链条损失，不会自动减少全场盈余', '下表固定当前动物数、面积、产量和产品目标。先改链条比例，再明确调整矿质N；额外保留量大于0时，第三行才减少外部投入。') +
        '<div class="annual-scenarios"><button type="button" data-annual-scenario="reference">① 比例0.20，不替代</button><button type="button" data-annual-scenario="retain">② 比例0.10，只多保留</button><button type="button" data-annual-scenario="replace">③ 比例0.10，再减矿质N</button></div><p>这三个按钮只改变链条比例和替代选择，保留当前动物数与面积。下面第二、三行使用控件中当前比例 ' + f(i.lossFraction) + '。</p>' +
        table('同一配置的三种记账比较（所有N列：kg N/年）', ['情景', '比例', '矿质N', '链条损失', '土壤残差', '全场N盈余'], [['参考链条，不替代', '0.20', f(reference.mineralNitrogen), f(reference.chainLoss), f(reference.soilResidual), f(reference.farmSurplus)], ['当前比例，只多保留', f(i.lossFraction), f(kept.mineralNitrogen), f(kept.chainLoss), f(kept.soilResidual), f(kept.farmSurplus)], ['当前比例，再等量替代', f(i.lossFraction), f(replaced.mineralNitrogen), f(replaced.chainLoss), f(replaced.soilResidual), f(replaced.farmSurplus)]]) +
        eq('相对0.20多保留N = (0.20 − ' + f(i.lossFraction) + ') × ' + f(r.manureExcretedNitrogen) + ' = ' + f(r.retainedNitrogen) + ' kg N/年<br>明确替代时矿质N = ' + f(r.baseMineralNitrogen) + ' − ' + f(r.retainedNitrogen) + ' = ' + f(replaced.mineralNitrogen) + ' kg N/年') +
        '<p>只保留时：土壤残差增加 ' + f(r.retainedNitrogen) + '，全场盈余不变。等量替代时：全场盈余减少 ' + f(r.retainedNitrogen) + '。这来自固定产出和无库存变化的约定，不表示现实中保留N一定当年流失，也不证明真实作物能够承受这个减肥量。</p>';
    }
    function diagram() {
      const r = result, f = fmt;
      const label = (x, y, title, value, key, anchor) => '<g class="annual-flow-label"><text x="' + x + '" y="' + y + '" text-anchor="' + (anchor || 'middle') + '">' + title + '</text><text class="annual-flow-value" data-annual-diagram="' + key + '" x="' + x + '" y="' + (y + 23) + '" text-anchor="' + (anchor || 'middle') + '">' + f(value) + '</text></g>';
      const arrow = (d, kind) => '<path class="annual-flow ' + (kind || '') + '" d="' + d + '" marker-end="url(#' + uid + '-arrow)"></path>';
      return '<svg viewBox="0 0 980 650" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="' + uid + '-svg-title ' + uid + '-svg-desc"><title id="' + uid + '-svg-title">同一合成农场的年度氮流向</title><desc id="' + uid + '-svg-desc">所有数值单位kg N/年。外部输入' + f(r.farmInputs) + '，产品出口' + f(r.farmOutputs) + '，链条损失' + f(r.chainLoss) + '，土壤残差' + f(r.soilResidual) + '。自产饲用和粪肥返回是内部传递。下方逐项表格列出每条流量。</desc><defs><marker id="' + uid + '-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L8,4 L0,8 Z" class="annual-arrow-head"></path></marker></defs>' +
        '<rect class="annual-farm-boundary" x="210" y="125" width="575" height="395" rx="18"></rect><text class="annual-boundary-title" x="230" y="151">农场边界 · 10 ha · 一整年</text>' +
        arrow('M160 280 H250') + arrow('M160 340 H250') + arrow('M665 94 V220') +
        arrow('M340 270 V182 H600 V220', 'annual-internal') + arrow('M665 310 V400', 'annual-internal') + arrow('M580 445 H470 V330 H430', 'annual-internal') +
        arrow('M750 264 H838') + arrow('M750 442 H838') + arrow('M280 370 V552 H245 V574') + arrow('M330 370 V552 H413 V574') + (r.flags.soilSupplyDeficit ? '<path class="annual-flow annual-residual" d="M385 370 V527 H636 V574"></path>' : arrow('M385 370 V527 H636 V574', 'annual-residual')) +
        '<rect class="annual-node" x="250" y="270" width="180" height="100" rx="12"></rect><text class="annual-node-title" x="340" y="301" text-anchor="middle">土壤与作物</text><text x="340" y="326" text-anchor="middle">全部收获饲草N</text><text data-annual-diagram="forageHarvestNitrogen" x="340" y="349" text-anchor="middle">' + f(r.forageHarvestNitrogen) + '</text>' +
        '<rect class="annual-node" x="580" y="220" width="170" height="90" rx="12"></rect><text class="annual-node-title" x="665" y="251" text-anchor="middle">动物 · ' + f(inputs.herd) + ' 头</text><text x="665" y="280" text-anchor="middle">采食N ' + f(r.feedNitrogenConsumed + r.feedNitrogenImported) + '</text>' +
        '<rect class="annual-node" x="580" y="400" width="170" height="85" rx="12"></rect><text class="annual-node-title" x="665" y="432" text-anchor="middle">粪肥链</text><text x="665" y="459" text-anchor="middle">比例 ' + f(inputs.lossFraction) + '</text>' +
        label(88, 245, '外购矿质N', r.mineralNitrogen, 'mineralNitrogen') + label(88, 313, '外部沉降N', r.depositionNitrogen, 'depositionNitrogen') + label(665, 40, '外购饲料N', r.feedNitrogenImported, 'feedNitrogenImported') +
        label(470, 205, '自产实际饲用N', r.feedNitrogenConsumed, 'feedNitrogenConsumed') + label(687, 345, '排泄N', r.manureExcretedNitrogen, 'manureExcretedNitrogen', 'start') + label(495, 468, '返回土壤N', r.manureToSoil, 'manureToSoil') +
        label(897, 235, '动物产品出口N', r.animalProductNitrogen, 'animalProductNitrogen') + label(897, 412, '粪肥链损失N', r.chainLoss, 'chainLoss') + label(245, 597, '商品作物出口N', r.cashProductNitrogen, 'cashProductNitrogen') + label(413, 597, '多余饲草出口N', r.feedNitrogenExported, 'feedNitrogenExported') + label(636, 597, r.flags.soilSupplyDeficit ? '土壤N供应赤字' : '土壤N残差', r.soilResidual, 'soilResidual') + '</svg>';
    }
    function render() {
      const r = result, f = fmt, invalid = errors.length > 0;
      panel.classList.toggle('annual-last-valid', invalid);
      q('.annual-error').hidden = !invalid;
      q('.annual-error').textContent = errors.map(error => error.message).join('；');
      q('.annual-status').textContent = (invalid ? '当前输入无效，图、公式和表格保留上次有效结果：' : '当前有效配置：') + f(inputs.herd) + '头，饲草' + f(inputs.forageArea) + ' ha，链条比例' + f(inputs.lossFraction) + '，' + (inputs.replaceRetained ? '明确替代矿质N' : '不替代矿质N');
      for (const control of qa('[data-annual-field]')) {
        const bad = errors.some(error => error.field === control.getAttribute('data-annual-field'));
        control.setAttribute('aria-invalid', String(bad));
      }
      for (const button of qa('[data-annual-stage]')) {
        if (Number(button.getAttribute('data-annual-stage')) === step) button.setAttribute('aria-current', 'step');
        else button.removeAttribute('aria-current');
      }
      q('.annual-stage').innerHTML = stageContent();
      q('.annual-position').textContent = (step + 1) + ' / ' + STEPS.length;
      q('[data-annual-action="previous"]').disabled = step === 0;
      q('[data-annual-action="next"]').disabled = step === STEPS.length - 1;
      for (const button of qa('[data-annual-scenario],[data-annual-download]')) button.disabled = invalid;
      q('.annual-metrics').innerHTML = [['farmSurplus', '全场N盈余'], ['chainLoss', '粪肥链N损失'], ['soilResidual', r.flags.soilSupplyDeficit ? '土壤N残差 · 供应赤字' : '土壤N残差']].map(([key, label]) => '<div><span>' + label + '</span><strong data-annual-value="' + key + '">' + f(r[key]) + '</strong><small>kg N/年</small></div>').join('');
      q('.annual-constraints').innerHTML = '<h3>当前配置的有限检查</h3><ul><li>' + (r.flags.feedImportExceeded ? '未通过：' : '通过：') + '外购饲料 ' + f(r.feedImported) + ' ≤ 10.00 Mg DM/年' + (r.flags.feedImportExceeded ? ' 不成立，超出 ' + f(r.feedImported - 10) : '') + '</li><li>' + (r.flags.soilSupplyDeficit ? '未通过：土壤N供应赤字 ' + f(-r.soilResidual) + ' kg N/年；不能把负数当环境收益' : '通过：土壤N残差非负；仍不是实际养分供应验证') + '</li><li>土地 ' + f(inputs.forageArea) + ' + ' + f(r.cashArea) + ' = 10.00 ha；矿质N投入 ' + f(r.mineralNitrogen) + ' kg N/年非负</li></ul><p class="annual-constraint-summary">' + (r.feasible ? '仅这些教学检查通过，不能推出原模型或真实农场可行。' : '这组配置未通过教学约束；图和账本保留数值以说明问题。') + '</p>';
      q('.annual-chart-scroll').innerHTML = diagram();
      q('.annual-figure-caption').textContent = (invalid ? '上次有效结果。' : '') + '箭头表示去向，线宽不代表数量。虚线框内的自产饲用、排泄和粪肥返回为内部传递；土壤负残差是缺口，不能解释成向环境输出负N。';
      q('.annual-gate-table').innerHTML = table('图的文字替代：跨农场边界的N（kg N/年）', ['边界项', '数值', '解释'], [['外部输入：矿质N', f(r.mineralNitrogen), '外购肥料中的氮元素'], ['外部输入：饲料N', f(r.feedNitrogenImported), '只有购买部分跨农场边界'], ['外部输入：沉降N', f(r.depositionNitrogen), '10 ha × 10 kg N/(ha·年)'], ['输入合计', f(r.farmInputs), '以上三项相加'], ['出口：商品作物N', f(r.cashProductNitrogen), '商品作物产品离场'], ['出口：动物产品N', f(r.animalProductNitrogen), '给定每头产品目标'], ['出口：多余饲草N', f(r.feedNitrogenExported), '未被动物采食的收获部分'], ['产品出口合计', f(r.farmOutputs), '以上三项出口相加'], ['全场N盈余', f(r.farmSurplus), '输入合计 − 产品出口合计'], ['粪肥链损失N', f(r.chainLoss), '排泄N × 自编损失比例'], ['土壤N残差', f(r.soilResidual), r.flags.soilSupplyDeficit ? '供应赤字；不可当环境收益' : '未进一步区分去向；不是校准污染量']]);
      q('.annual-input-table').innerHTML = table('本次有效输入', ['输入', '值', '单位／含义'], [['动物数', f(inputs.herd), '等价头数'], ['饲草面积', f(inputs.forageArea), 'ha'], ['链条损失比例', f(inputs.lossFraction), '0.20=20%'], ['等量替代矿质N', inputs.replaceRetained ? 'true' : 'false', '相对同一配置、比例0.20']]);
      q('.annual-parameter-table').innerHTML = table('全部固定系数均为原创教学输入', ['固定参数', '值', '单位'], PARAMS.map(([key, label, unit]) => [label, f(model.constants[key]), unit]));
      q('.annual-all-table').innerHTML = table('完整结果：所有中间量和计算关系', ['量', '值', '单位', '关系'], FIELDS.map(([key, label, formula]) => [label, f(r[key]), model.units[key], formula]));
      remember();
    }
    function validateControls() {
      const raw = rawControls(), next = {}, found = [];
      for (const key of ['herd', 'forageArea', 'lossFraction']) {
        const value = raw[key];
        if (typeof value !== 'string' || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value)) {
          found.push({field: key, message: ({herd: '动物数', forageArea: '饲草面积', lossFraction: '链条损失比例'})[key] + '不能为空或非数值'});
          continue;
        }
        next[key] = Number(value);
        try { model.calculate({...inputs, [key]: next[key]}); } catch (error) { found.push({field: key, message: error.message}); }
      }
      next.replaceRetained = raw.replaceRetained;
      if (!found.length) {
        try { result = model.calculate(next); inputs = {...next}; } catch (error) { found.push({field: error.field, message: error.message}); }
      }
      errors = found;
    }
    function change(event) {
      if (!event.target.closest('[data-annual-field]')) return;
      if (event.isComposing) return;
      validateControls(); render();
    }
    function chooseStage(number) {
      step = Math.min(STEPS.length - 1, Math.max(0, number)); render();
      const heading = q('.annual-stage').querySelector('h3');
      heading?.focus({preventScroll: true}); heading?.scrollIntoView({block: 'nearest', behavior: 'auto'});
    }
    function reset() {
      const focused = doc.activeElement, hadFocus = focused && panel.contains(focused);
      inputs = {...model.defaults}; result = model.calculate(inputs); step = 0; errors = []; lastDownload = '';
      writeControls(); q('.annual-ledger').open = false; q('.annual-download-status').textContent = ''; render();
      if (hadFocus && !focused.isConnected) q('[data-annual-action="reset"]').focus({preventScroll: true});
    }
    function exportData() {
      if (errors.length) throw new Error('当前输入无效；请修正后下载');
      return {schema: 'paper-annual-balance-v1', kind: 'original-synthetic-teaching-model', caveats: [NOTE, ZERO, LIMIT, '正土壤残差不是校准污染；负残差是供应赤字。'],
        inputs: {...inputs}, constants: {...model.constants}, units: {...model.units}, result: JSON.parse(JSON.stringify(result))};
    }
    function download(kind) {
      if (errors.length) return;
      const data = exportData(), quote = value => '"' + String(value).replace(/"/g, '""') + '"';
      let body, name, type;
      if (kind === 'json') { body = JSON.stringify(data, null, 2); name = 'annual-balance-results.json'; type = 'application/json;charset=utf-8'; }
      else if (kind === 'inputs') { body = 'herd,forageArea,lossFraction,replaceRetained\r\n' + [inputs.herd, inputs.forageArea, inputs.lossFraction, inputs.replaceRetained].join(',') + '\r\n'; name = 'annual-balance-inputs.csv'; type = 'text/csv;charset=utf-8'; }
      else {
        const rows = [['category', 'key', 'label', 'value', 'unit']];
        for (const key of Object.keys(inputs)) rows.push(['input', key, key, inputs[key], model.domain[key].unit || 'boolean']);
        for (const [key, label, unit] of PARAMS) rows.push(['constant', key, label, model.constants[key], unit]);
        rows.push(['constant', 'tolerance', '数值比较容差', model.constants.tolerance, '各检查量原单位']);
        for (const [key, label] of FIELDS) rows.push(['result', key, label, result[key], model.units[key]]);
        rows.push(['constraint', 'feasible', '仅教学检查通过', result.feasible, 'boolean']);
        for (const key of Object.keys(result.flags)) rows.push(['constraint', key, key, result.flags[key], 'boolean']);
        data.caveats.forEach((value, index) => rows.push(['caveat', 'notice' + (index + 1), value, '', '']));
        body = '\ufeff' + rows.map(row => row.map(quote).join(',')).join('\r\n') + '\r\n'; name = 'annual-balance-ledger.csv'; type = 'text/csv;charset=utf-8';
      }
      try {
        const blob = new global.Blob([body], {type}), url = global.URL.createObjectURL(blob), a = doc.createElement('a');
        urls.add(url); a.href = url; a.download = name; panel.append(a); a.click(); a.remove();
        const timer = global.setTimeout(() => { global.URL.revokeObjectURL(url); urls.delete(url); timers.delete(timer); }, 1000); timers.add(timer);
        lastDownload = name; q('.annual-download-status').textContent = '已生成 ' + name + '；请在浏览器下载记录中查看。';
      } catch (error) { q('.annual-download-status').textContent = '浏览器未能生成下载：' + error.message + '。当前账本仍可阅读或打印。'; }
    }
    function click(event) {
      const button = event.target.closest('button');
      if (!button || !panel.contains(button) || button.disabled) return;
      // Explicit attributes: input.step and unrelated host datasets cannot choose a stage.
      const stageAttribute = button.getAttribute('data-annual-stage');
      const action = button.getAttribute('data-annual-action'), scenario = button.getAttribute('data-annual-scenario'), file = button.getAttribute('data-annual-download');
      if (stageAttribute !== null) chooseStage(Number(stageAttribute));
      else if (action === 'previous') chooseStage(step - 1);
      else if (action === 'next') chooseStage(step + 1);
      else if (action === 'reset') reset();
      else if (action === 'print') global.print?.();
      else if (file) download(file);
      else if (scenario && !errors.length) {
        inputs = {...inputs, lossFraction: scenario === 'reference' ? 0.20 : 0.10, replaceRetained: scenario === 'replace'};
        result = model.calculate(inputs); writeControls(); render();
        // Preserve a usable focus target after the stage explanation is replaced.
        q('[data-annual-scenario="' + scenario + '"]')?.focus({preventScroll: true});
      }
    }
    function keydown(event) {
      if (event.target !== panel) return;
      const next = {ArrowLeft: step - 1, ArrowRight: step + 1, Home: 0, End: STEPS.length - 1}[event.key];
      if (next === undefined) return;
      event.preventDefault(); chooseStage(next);
    }
    function beforePrint() { if (printDetails !== null) return; printDetails = q('.annual-ledger').open; q('.annual-ledger').open = true; }
    function afterPrint() { if (printDetails !== null) q('.annual-ledger').open = printDetails; printDetails = null; }
    function onRoute() {
      // A host popstate handler may have just mounted a fresh panel. Its paired
      // hashchange is harmless when its hash and connected container still match.
      if ((global.location?.hash || '') !== mountedHash || !container.isConnected) destroy();
    }
    function busy() {
      if (!mounted || !container.isConnected || !panel.isConnected) return false;
      const focus = doc.activeElement, selection = global.getSelection?.();
      const editing = focus && panel.contains(focus) && ['INPUT', 'SELECT', 'TEXTAREA'].includes(focus.tagName);
      const selected = selection && !selection.isCollapsed && (panel.contains(selection.anchorNode) || panel.contains(selection.focusNode));
      return !!(errors.length || step !== 0 || q('.annual-ledger').open || urls.size || printDetails !== null || editing || selected || Object.keys(model.defaults).some(key => inputs[key] !== model.defaults[key]));
    }
    function destroy() {
      if (!mounted) return;
      mounted = false;
      for (const [name, handler] of [['click', click], ['input', change], ['change', change], ['keydown', keydown]]) panel.removeEventListener(name, handler);
      panel.removeEventListener('toggle', remember, true);
      for (const [name, handler] of [['hashchange', onRoute], ['popstate', onRoute], ['beforeprint', beforePrint], ['afterprint', afterPrint]]) global.removeEventListener(name, handler);
      observer?.disconnect(); timers.forEach(timer => global.clearTimeout(timer)); timers.clear(); urls.forEach(url => global.URL.revokeObjectURL(url)); urls.clear();
      panel.remove(); mounts.delete(container); active.delete(controller);
    }
    const controller = {destroy, reset, isBusy: busy, getExportData: exportData, getState: () => ({inputs: {...inputs}, step, invalid: !!errors.length, errors: errors.map(error => ({...error})), mounted, busy: busy(), pendingTimer: false, pendingDownloads: urls.size, lastDownload, result: JSON.parse(JSON.stringify(result))})};
    mounts.set(container, controller); active.add(controller);
    for (const [name, handler] of [['click', click], ['input', change], ['change', change], ['keydown', keydown]]) panel.addEventListener(name, handler);
    panel.addEventListener('toggle', remember, true);
    for (const [name, handler] of [['hashchange', onRoute], ['popstate', onRoute], ['beforeprint', beforePrint], ['afterprint', afterPrint]]) global.addEventListener(name, handler);
    if (global.MutationObserver) { observer = new global.MutationObserver(() => { if (!container.isConnected || !panel.isConnected) destroy(); }); observer.observe(doc.documentElement, {childList: true, subtree: true}); }
    writeControls(restored?.raw); q('.annual-ledger').open = !!restored?.ledgerOpen; validateControls(); render();
    return controller;
  }
  global.PaperAnnualBalance = {mount, isBusy: () => [...active].some(controller => controller.isBusy())};
}(window));
