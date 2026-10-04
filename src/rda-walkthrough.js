/* Independent, ephemeral RDA teaching panel. No storage, private data or timers. */
(function (global) {
'use strict';
const mounts = new WeakMap(), active = new Set();
let serial = 0;
const stages = ['村庄与字段', '标准化 X / Y', '拟合与残差', '特征值与分母', '变量与村庄图', '回到 Cheng Fig. 7'];
const defaults = {step:0, village:'V1', v4B:3.75, denominator:'total', view:'variables'};
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = (v, precision=6) => v===null || v===undefined || !Number.isFinite(v) ? '未定义' : (Math.abs(v)<0.5*Math.pow(10,-precision)?0:v).toFixed(precision);
const pct = v => v===null || v===undefined ? '未定义' : num(v*100,3)+'%';
const sign = v => v<0?'−':'+';
const textCell = v => typeof v==='number'?num(v):v===null?'未定义（零方差轴）':String(v);
function table(caption, headers, rows) {
 return '<div class="rda-table-scroll" tabindex="0" role="region" aria-label="'+escape(caption)+'，可横向滚动"><table><caption>'+escape(caption)+'</caption><thead><tr>'+headers.map(h=>'<th scope="col">'+escape(h)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map((v,i)=>'<'+(i?'td':'th scope="row"')+'>'+escape(textCell(v))+'</'+(i?'td':'th')+'>').join('')+'</tr>').join('')+'</tbody></table></div>';
}
const matrix = (caption, names, values, columns) => table(caption,['行',...columns],values.map((row,i)=>[names[i],...row]));
const equation = html => '<p class="rda-equation">'+html+'</p>';
const boundary = html => '<div class="rda-boundary">'+html+'</div>';
const localImagePath = value => typeof value==='string' && /^(?:\.\/)?(?:resources|assets|library)\/[\w./%-]+$/.test(value) && !value.split('/').includes('..') ? value : '';
const safeLink = value => typeof value==='string' && (/^https:\/\//.test(value) || /^#\/[\w/?=.%&-]+$/.test(value)) ? value : '';
function links(source) {
 const entries = [[safeLink(source.sourceUrl || source.sourcePageUrl),'查看原文来源'],[safeLink(source.sourcePage || source.localPage),'打开完整原文页'],[safeLink(source.doi && (source.doi.startsWith('https://')?source.doi:'https://doi.org/'+source.doi)),'论文 DOI']];
 return entries.filter(e=>e[0]).map(e=>'<a href="'+escape(e[0])+'"'+(e[0].startsWith('https://')?' target="_blank" rel="noopener noreferrer"':'')+'>'+e[1]+'</a>').join('');
}
function mount(container) {
 if(!container || !container.ownerDocument || typeof container.append!=='function') throw new TypeError('PaperRDA.mount 需要一个 DOM 容器。');
 if(mounts.has(container)) return mounts.get(container);
 const config = global.PAPER_RDA;
 if(!config || !Array.isArray(config.records) || !global.PaperRDAModel) throw new Error('RDA 合成配置或计算模型尚未载入。');
 const doc=container.ownerDocument, uid='paper-rda-'+(++serial), state={...defaults}, source=config.source || {};
 let result=global.PaperRDAModel.calculate(config.records,state.v4B), invalid='', mounted=true, observer;
 const panel=doc.createElement('div');
 panel.className='rda-walkthrough';panel.setAttribute('data-no-terms','');panel.setAttribute('tabindex','0');panel.setAttribute('role','region');panel.setAttribute('aria-labelledby',uid+'-title');
 panel.innerHTML='<header class="rda-header"><p class="rda-eyebrow">RDA · 合成机制演示 · v'+escape(config.version || '5.5.5')+'</p><h2 id="'+uid+'-title">从四个村庄，走到两条约束轴</h2><p>手动查看六个阶段；每一步都保留数值、单位和计算来路。改动 V4 的 B 得分，可以观察拟合、特征值与坐标一起变化。</p></header>'+boundary('<strong>证据边界：</strong>这里的 V1–V4、A/B、所有矩阵与图均为合成教学数据。不是 Cheng 的35村原始数据，不复刻作者图形缩放，也不证明因果。第6步单独查看原图及迁移限制。')+'<nav class="rda-steps" aria-label="RDA 六个手动阶段">'+stages.map((name,i)=>'<button type="button" data-step="'+i+'" aria-controls="'+uid+'-stage"><span aria-hidden="true">'+(i+1)+'</span>'+name+'</button>').join('')+'</nav><div class="rda-inputs"><div class="rda-field"><label for="'+uid+'-b">合成 V4 · 响应 B（0–5 分）</label><input id="'+uid+'-b" data-field="v4B" type="number" min="0" max="5" step="0.25" value="3.75" inputmode="decimal" aria-describedby="'+uid+'-b-help '+uid+'-error"><small id="'+uid+'-b-help">默认 3.75；每次 0.25。试试 4.25，查看轴旋转。仅供敏感性演示。</small><span id="'+uid+'-error" class="rda-error" role="alert"></span></div><div class="rda-field"><label for="'+uid+'-village">跟踪一个合成村庄</label><select id="'+uid+'-village" data-field="village">'+result.row_ids.map(v=>'<option value="'+escape(v)+'">'+escape(v)+'</option>').join('')+'</select><small>用于代入、重建和村庄图的高亮</small></div><div class="rda-field"><label for="'+uid+'-denominator">轴解释率的分母</label><select id="'+uid+'-denominator" data-field="denominator"><option value="total">全部 Y 方差（含残差）</option><option value="constrained">仅拟合 Y 的约束方差</option></select><small>切换标签与比例，不移动任何坐标</small></div><div class="rda-field"><label for="'+uid+'-view">第5步的图形对象</label><select id="'+uid+'-view" data-field="view"><option value="variables">变量：相关坐标</option><option value="observations">村庄：拟合分数与观察投影</option></select><small>两个图的对象与坐标定义不同</small></div></div><div class="rda-toolbar"><button type="button" data-action="previous">上一步</button><button type="button" data-action="next">下一步</button><button type="button" data-action="reset">恢复默认</button></div><p class="rda-status" role="status" aria-live="polite" aria-atomic="true"></p><div class="rda-summary" aria-label="当前合成模型的方差分解"></div><div class="rda-stage" id="'+uid+'-stage" aria-labelledby="'+uid+'-stage-title"></div><p class="rda-footnote">全部演示按需重算，不自动播放；当前改动仅保留在此面板，离开页面即结束。所有数值由同一模型计算，显示值经过四舍五入。</p>';
 container.append(panel);
 const q=s=>panel.querySelector(s), stage=q('.rda-stage'), error=q('.rda-error'), status=q('.rda-status');
 const rows=(values)=>result.row_ids.map((id,i)=>[id,...values[i]]);
 const axisFractions=()=>state.denominator==='total'?result.axis_fraction_of_TOTAL:result.axis_fraction_of_CONSTRAINED;
 const axisLabel=i=>'RDA'+(i+1)+' · '+pct(axisFractions() && axisFractions()[i])+(state.denominator==='total'?' / 全部':' / 约束');
 function stageHead(index,subtitle){return '<header class="rda-stage-head"><span class="rda-eyebrow">阶段 '+(index+1)+' / 6 · '+(index===5?'原文证据与研究迁移':'合成教学')+'</span><h3 id="'+uid+'-stage-title">'+stages[index]+'</h3><p>'+subtitle+'</p></header>';}
 function firstStage(){
 return stageHead(0,'每一行是一个村庄；X 描述村庄条件，Y 是该村庄的两个合成感知汇总分。不是把每个受访者当作独立村庄。')+table('四个村庄的输入；只允许改动 V4 的 B',['村庄','X1 某类作物面积比例（%）','X2 距离（km）','Y_A 感知（分）','Y_B 感知（分）'],rows(result.raw_matrix))+table('字段如何进入矩阵',['字段','角色与单位','整理规则与边界'],[['crop_share_percent','X1；百分数 0–100','分母是合成村庄的总作物生产面积；10表示其中10%属某一类作物，不是0.10'],['distance_km','X2；km','不要将 km 与 m 混在同一列'],['perception_a / perception_b','Y；合成村庄汇总，0–5分','小数表示汇总值；不是单个问卷原始等级'],['village_id','连接键；不进入 X 或 Y','同一村庄的字段按唯一ID连接，不能靠行顺序拼接']])+boundary('<strong>回到实际调查：</strong>先记录问卷原始编码、反向题方向、缺失值与村庄汇总方法，再构建 X/Y。合成 A/B 没有暗示某一个原文 ES/ED 指标，更没有直接复制作者量表。')+'<div class="rda-process" aria-label="从字段到 RDA 的计算流程"><span>统一分析单位</span><b aria-hidden="true">→</b><span>整理 X 与 Y</span><b aria-hidden="true">→</b><span>列标准化</span><b aria-hidden="true">→</b><span>拟合与分解</span></div>';
 }
 function standardizedStage(){
 const i=result.row_ids.indexOf(state.village),raw=result.Y[i][0],mean=result.Y_means[0],sd=result.Y_sample_sd[0];
 return stageHead(1,'本演示对 X、Y 各列使用样本标准差标准化。X 标准化统一系数的单位：在普通满秩最小二乘中，仅改变 X 一列的尺度不会改变拟合 Y。Y 标准化则让各响应列方差同为1，平衡它们在排序中的贡献。')+equation('zᵢⱼ = (原值ᵢⱼ − 列均值ⱼ) / 样本标准差ⱼ；sⱼ = √[Σ(原值 − 均值)² / (n − 1)]')+equation(escape(state.village)+' 的 A：('+num(raw,2)+' − '+num(mean)+') / '+num(sd)+' = <strong>'+num(result.Y_standardized[i][0])+'</strong>')+table('均值与样本标准差（仍带各原始字段的单位）',['列','均值','样本标准差'],[['X1（%）',result.X_means[0],result.X_sample_sd[0]],['X2（km）',result.X_means[1],result.X_sample_sd[1]],['Y_A（分）',result.Y_means[0],result.Y_sample_sd[0]],['Y_B（分）',result.Y_means[1],result.Y_sample_sd[1]]])+'<div class="rda-two">'+matrix('标准化解释矩阵 X_z：无量纲',result.row_ids,result.X_standardized,['X1_z','X2_z'])+matrix('标准化响应矩阵 Y_z：无量纲',result.row_ids,result.Y_standardized,['A_z','B_z'])+'</div>'+boundary('Cheng 原文明确报告将 X 和 Y 标准化至均值0、方差1。本教学明确使用样本标准差；每个响应列样本方差为1，两列总方差为2。尚缺的是作者原始矩阵、各字段重编码细节与绘图 scaling，不能据此声称逐值复现。');
 }
 function fittedStage(){
 const i=result.row_ids.indexOf(state.village);
 return stageHead(2,'用 X_z 线性拟合 Y_z，再把每个观察值拆成拟合值与残差；截距通过列中心化处理。')+equation('B̂ = (X_zᵀ X_z)⁻¹ X_zᵀ Y_z；Ŷ_z = X_z B̂；E = Y_z − Ŷ_z')+matrix('系数 B̂：每列对应一个响应',['X1_z','X2_z'],result.coefficients,['对 A_z','对 B_z'])+'<div class="rda-two">'+matrix('拟合矩阵 Ŷ_z',result.row_ids,result.fitted_Y,['A_z 拟合','B_z 拟合'])+matrix('残差矩阵 E',result.row_ids,result.residual_Y,['A_z 残差','B_z 残差'])+'</div><div class="rda-callout"><h4>'+escape(state.village)+'：把原始分数重建回来</h4>'+['A','B'].map((label,j)=>equation(label+'：'+num(result.Y_standardized[i][j])+' = '+num(result.fitted_Y[i][j])+' '+sign(result.residual_Y[i][j])+' '+num(Math.abs(result.residual_Y[i][j]))+'（标准化）')+equation('原单位：'+num(result.Y[i][j],2)+' = 均值 '+num(result.Y_means[j])+' + s × (拟合 + 残差)<br>= '+num(result.fitted_Y_original_units[i][j])+' '+sign(result.residual_Y_original_units[i][j])+' '+num(Math.abs(result.residual_Y_original_units[i][j]))+' 分')).join('')+'</div>'+matrix('核对 X_zᵀ E：拟合解释变量与残差正交（浮点误差已舍入）',['X1_z','X2_z'],result.XT_residual,['A残差','B残差'])+boundary('残差仍是响应数据的一部分。在线性模型假设之外，它可能包含未观测因素、测量误差和非线性，不能直接命名为某一种原因。');
 }
 function decomposition(){
 const full=result.total_inertia, fit=result.constrained_inertia, res=result.residual_inertia;
 return '<div class="rda-metrics"><div><span>全部 Y 方差</span><strong>'+num(full)+'</strong></div><div><span>约束／拟合部分</span><strong>'+num(fit)+'</strong><small>'+pct(result.overall_unadjusted_R2)+' / 全部</small></div><div><span>残差部分仍在</span><strong>'+num(res)+'</strong><small>'+pct(result.residual_fraction)+' / 全部</small></div></div>';
 }
 function eigenStage(){
 const n=result.row_ids.length, lambda=result.constrained_eigenvalues;
 return stageHead(3,'对拟合矩阵的协方差做特征分解，得到约束轴的方向与方差；轴解释率必须说清楚分母。')+equation('C = Ŷ_zᵀ Ŷ_z / (n − 1) = Ŷ_zᵀ Ŷ_z / '+(n-1)+'；C vₖ = λₖ vₖ')+matrix('拟合协方差 C：不是原始 Y 的协方差',['A_z','B_z'],result.fitted_covariance,['A_z','B_z'])+matrix('单位特征向量 V：每一列是一条轴',['A_z 方向','B_z 方向'],result.eigenvectors_columns,['v₁','v₂'])+equation('总方差 '+num(result.total_inertia)+' = 约束 '+num(result.constrained_inertia)+' + 残差 '+num(result.residual_inertia)+'<br>约束方差 = λ₁ + λ₂ = '+num(lambda[0])+' + '+num(lambda[1]))+table('同一组特征值，两种解释率分母',['成分','特征值 / 方差','占全部 Y 方差','占约束方差'],[['RDA1',lambda[0],pct(result.axis_fraction_of_TOTAL[0]),pct(result.axis_fraction_of_CONSTRAINED && result.axis_fraction_of_CONSTRAINED[0])],['RDA2',lambda[1],pct(result.axis_fraction_of_TOTAL[1]),pct(result.axis_fraction_of_CONSTRAINED && result.axis_fraction_of_CONSTRAINED[1])],['残差',result.residual_inertia,pct(result.residual_fraction),'不属于约束部分']])+varianceBars()+boundary('<strong>当前显示分母：</strong>'+(state.denominator==='total'?'全部 Y 方差。两条约束轴加起来通常不到100%；剩下的是残差。':'约束方差。两条约束轴合计100%，但没有把残差消除。')+' 本例未调整 R² = '+pct(result.overall_unadjusted_R2)+'，不是作者报告的21%，也不是作者结果的重现或显著性证明。默认值的精确分解是2 = 25/18 + 11/18，λ₁ = 5/6、λ₂ = 5/9。')+boundary('约束轴的整体正负号可翻转而不改变解；对角特征值相同时，轴方向也不唯一。本演示只固定一个方便比较的符号约定。切换输入后必须重新求特征向量，不能固定旧坐标。');
 }
 function varianceBars(){
 const fractions=axisFractions(), data=[['RDA1',fractions && fractions[0],'rda-axis-one'],['RDA2',fractions && fractions[1],'rda-axis-two']];
 if(state.denominator==='total')data.push(['残差',result.residual_fraction,'rda-axis-residual']);
 return '<div class="rda-bars" aria-label="'+(state.denominator==='total'?'全部':'约束')+'方差构成">'+data.map(([label,v,cls])=>'<div><span>'+label+'</span><div class="rda-bar"><span class="'+cls+'" style="width:'+Math.max(0,Math.min(100,(v||0)*100))+'%"></span></div><strong>'+pct(v)+'</strong></div>').join('')+'<p>残差始终占全部 Y 的 '+pct(result.residual_fraction)+'；此值不因图表分母切换而改变。</p></div>';
 }
 function plotFrame(body,desc,limit){
 const low=-limit,high=limit,left=72,top=52,size=340,px=x=>left+(x-low)/(high-low)*size,py=y=>top+(high-y)/(high-low)*size;
 const ticks=[-limit,0,limit];
 const axes='<line class="rda-grid" x1="'+left+'" x2="'+(left+size)+'" y1="'+top+'" y2="'+top+'"/><line class="rda-grid" x1="'+left+'" x2="'+(left+size)+'" y1="'+(top+size)+'" y2="'+(top+size)+'"/><line class="rda-axis" x1="'+left+'" x2="'+(left+size)+'" y1="'+py(0)+'" y2="'+py(0)+'"/><line class="rda-axis" x1="'+px(0)+'" x2="'+px(0)+'" y1="'+top+'" y2="'+(top+size)+'"/>'+ticks.map(v=>'<text class="rda-tick" x="'+px(v)+'" y="'+(top+size+22)+'" text-anchor="middle">'+num(v,2)+'</text><text class="rda-tick" x="'+(left-10)+'" y="'+(py(v)+4)+'" text-anchor="end">'+num(v,2)+'</text>').join('');
 return '<figure class="rda-figure"><div class="rda-chart-scroll" tabindex="0" role="region" aria-label="合成 RDA 图，可横向滚动"><svg viewBox="0 0 490 466" role="img" aria-labelledby="'+uid+'-plot-title '+uid+'-plot-desc"><title id="'+uid+'-plot-title">'+(state.view==='variables'?'变量与拟合轴的相关坐标':'合成村庄：拟合分数与观察 Y 投影')+'</title><desc id="'+uid+'-plot-desc">'+escape(desc)+'</desc><defs><marker id="'+uid+'-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path class="rda-arrow-head" d="M0,0 L8,4 L0,8 Z"/></marker></defs>'+axes+body(px,py,size)+'<text x="242" y="450" text-anchor="middle">'+escape(axisLabel(0))+'</text><text x="72" y="25">'+escape(axisLabel(1))+'</text></svg></div><figcaption>'+escape(desc)+' 坐标数值见下表。两轴按相同比例绘制；整体轴符号可翻转。</figcaption></figure>';
 }
 function variablePlot(){
 const variables=[{id:'X1',kind:'解释变量：箭头',coord:result.X_axis_correlations[0]},{id:'X2',kind:'解释变量：箭头',coord:result.X_axis_correlations[1]},{id:'A',kind:'响应变量：圆点',coord:result.Y_axis_correlations[0]},{id:'B',kind:'响应变量：方点',coord:result.Y_axis_correlations[1]}];
 const defined=v=>v.coord.every(c=>c!==null&&Number.isFinite(c));
 const desc='合成变量图：X1/X2 箭头与 A/B 点的位置都是 corr(变量, 拟合轴分数)，仅描述约束子空间；没有将残差画成第三条轴。这不是 Cheng 原图缩放。';
 return plotFrame((px,py,size)=>'<circle class="rda-unit-circle" cx="'+px(0)+'" cy="'+py(0)+'" r="'+(size/2.4)+'"/>'+variables.filter(defined).map((v,i)=>{const x=px(v.coord[0]),y=py(v.coord[1]),shape=i<2?'<line class="rda-predictor" x1="'+px(0)+'" y1="'+py(0)+'" x2="'+x+'" y2="'+y+'" marker-end="url(#'+uid+'-arrow)"/>':i===2?'<circle class="rda-response-a" cx="'+x+'" cy="'+y+'" r="6"/>':'<rect class="rda-response-b" x="'+(x-5)+'" y="'+(y-5)+'" width="10" height="10"/>';return '<g data-variable="'+v.id+'">'+shape+'<text x="'+(x+9)+'" y="'+(y+(i%2?18:-10))+'">'+v.id+'</text></g>';}).join(''),desc,1.2)+table('变量坐标：与拟合轴分数的 Pearson 相关',['变量','图形对象','RDA1 相关','RDA2 相关'],variables.map(v=>[v.id,v.kind,...v.coord]))+(variables.some(v=>!defined(v))?boundary('至少一个轴的方差为零，相关坐标未定义；相应变量不绘图，绝不把未定义坐标当成0。'):'')+table('角度与完整原始相关：二者不等价',['比较','二维坐标夹角余弦','原始变量 Pearson 相关'],[['A 与 B',result.Y_coordinate_cosine,result.Y_raw_correlation],['X1 与 A',result.X1_YA_coordinate_cosine,result.X1_YA_raw_correlation]])+boundary('<strong>为何看起来垂直，却不能说“没有相关”？</strong>默认 A/B 坐标约为(0.912871, 0)与(0, 0.745356)，看起来相隔90°，但原始 Y 的相关为0.272166。X1/A 的默认坐标夹角余弦为0.894427，原始相关为0.816497。角度受坐标定义、缩放和遗漏残差影响，不能无条件读取完整原始相关。上表随输入重算。');
 }
 function villagePlot(){
 const max=Math.max(1,...result.fitted_axis_scores.flat().map(Math.abs),...result.observed_axis_scores.flat().map(Math.abs)),limit=Math.ceil(max*1.2*2)/2;
 const show2D=result.axis_defined.every(Boolean);
 const scoreRow=i=>[...result.fitted_axis_scores[i].map((v,j)=>result.axis_defined[j]?v:null),...result.observed_axis_scores[i].map((v,j)=>result.axis_defined[j]?v:null)];
 const desc='合成村庄图：实心圆是 Ŷ_z V 的拟合村庄分数，空心菱形是 Y_z V 的观察标准化分数投影，虚线是两者差。不是原文响应指标的圆点。';
 return (show2D?plotFrame((px,py)=>result.row_ids.map((id,i)=>{const f=result.fitted_axis_scores[i],o=result.observed_axis_scores[i],fx=px(f[0]),fy=py(f[1]),ox=px(o[0]),oy=py(o[1]),selected=id===state.village;return '<g data-village="'+escape(id)+'" class="'+(selected?'rda-selected':'')+'"><line class="rda-residual-line" x1="'+fx+'" y1="'+fy+'" x2="'+ox+'" y2="'+oy+'"/><circle class="rda-fitted-point" cx="'+fx+'" cy="'+fy+'" r="'+(selected?7:5)+'"/><path class="rda-observed-point" d="M '+ox+' '+(oy-6)+' L '+(ox+6)+' '+oy+' L '+ox+' '+(oy+6)+' L '+(ox-6)+' '+oy+' Z"/><text x="'+(ox+10)+'" y="'+(oy-8)+'">'+escape(id)+(selected?'（已选）':'')+'</text></g>';}).join(''),desc,limit):boundary('约束矩阵不足二维：至少一条轴的特征值为0，二维村庄图不绘制。该轴的拟合坐标和观察投影均标记为未定义；不能把任意补全方向的残差投影解释为第二条 RDA 轴。'))+table('村庄的轴分数：两种点不是同一个量',['村庄','拟合 RDA1','拟合 RDA2','观察投影 RDA1','观察投影 RDA2'],result.row_ids.map((id,i)=>[id,...scoreRow(i)]))+equation('拟合村庄点 = Ŷ_z V；观察投影 = Y_z V；两点差 = E V')+boundary((show2D?'选中的 '+escape(state.village)+' 用较大的实心圆及文字标记。':'当前不显示二维点；表格仅保留有定义的轴分数。')+'这个教学图可以显示四个村庄，但 Cheng Fig. 7 的彩色点表示 ES/ED 指标，不是35个村庄。村庄点不能拿来替换原图指标点。');
 }
 function plotsStage(){return stageHead(4,'先分清“一个点代表谁”，再读坐标。当前图形对象：'+(state.view==='variables'?'变量，与拟合轴的相关':'村庄，拟合分数和观察投影')+'。')+(state.view==='variables'?variablePlot():villagePlot())+boundary('<strong>遗漏残差：</strong>当前约束模型解释全部 Y 方差的 '+pct(result.overall_unadjusted_R2)+'，仍留下 '+pct(result.residual_fraction)+' 的残差。改为“约束方差”分母只会改变轴标签，不会提升模型解释能力。');}
 function sourceStage(){
 const path=localImagePath(source.figurePath),offline=global.location && global.location.protocol==='file:';
 const figure=path&&!offline?'<figure class="rda-source-figure"><div class="rda-source-scroll" tabindex="0" role="region" aria-label="Cheng Fig. 7 原始图像，可横向滚动"><img src="'+escape(path)+'" alt="Cheng Fig. 7 原图：彩色点代表村级服务/负服务指标，黑色箭头代表村庄层面的解释变量。此处不添加教学点或改变图像内容。" loading="lazy" decoding="async"></div><figcaption>'+escape(source.figureCaption || 'Cheng Fig. 7，保持原图图像内容，不重绘、不覆盖教学坐标。')+'</figcaption><p class="rda-image-status" hidden>原图未能加载。请从完整站点缓存或归档打开原文；上面的合成 SVG 与数值表不受影响。</p></figure>':'<div class="rda-image-status">'+(offline?'当前为单文件 file: 模式，原图未嵌入；需要完整站点缓存或归档查看 Cheng Fig. 7。':'未配置可用的本地原图路径，请从完整原文页查看 Cheng Fig. 7。')+' 六个阶段的文字、合成 SVG 与数值表可离线使用。</div>';
 return stageHead(5,'把合成计算与文章证据并排理解，但不要把两者拼成一个“复现结果”。')+figure+'<div class="rda-source-links">'+links(source)+'</div><p class="rda-source-meta">'+escape((source.citation || 'Cheng et al.')+' · '+(source.sourcePageLabel || '原文 Fig. 7')+' · '+(source.license || '版权与使用条件见原文'))+'</p>'+table('Fig. 7 中的图形对象',['对象','原文含义','不能直接推断'],[['彩色点','村级服务 / 负服务指标（按各列定义生成）','不是35个村庄的分布位置'],['黑色箭头','村庄层面的解释变量','箭头本身不是因果效应'],['轴与二维夹角','作者所用排序与缩放下的展示','原始绘图 scaling 和完整特征值表缺失，不能精确重建原图']])+boundary('<strong>21% 的位置：</strong>作者报告值属于原文的模型与分析口径。原图轴标11.7%与9.4%，两者相加不能补出完整特征值、精确残差或作者的完整 R² 定义。本演示的 '+pct(result.overall_unadjusted_R2)+' 是四个合成村庄计算出的未调整 R²；不解释、不替代也不验证作者21%。不要从图片测量坐标来补造完整特征值或未披露的缩放设置。')+(Array.isArray(config.variables)?'<details class="rda-source-variables"><summary>原文14个解释变量：单位、年份与来源</summary>'+table('原文 Table 1 / Fig. 7 字段清单',['变量','单位','含义','年份与来源','解释边界'],config.variables.map(v=>[v.id+' · '+v.label,v.unit,v.meaning,v.year+' · '+v.origin,v.boundary || '见原文定义']))+'</details>':'')+boundary('<strong>原文 Y 并非全是主观量表：</strong>例如 Revenue 是价格 × 产量，未扣成本；Table 2 以10³ CNY/ha报告作物总收入。它属于经济代理指标，不是利润，也不是直接的生物物理 ES 测量。感知指标须按各列定义理解；完整原始 RDA 矩阵及 S1 汇总细节仍未取得。')+'<h4>迁移到自己的研究前，需要补齐</h4><ul><li>确认分析单位、村庄与问卷的连接键、汇总权重，以及每个 ES/ED 指标的方向与缺失处理。</li><li>核对响应类型与量表，说明为何选择线性 RDA；检查共线性、样本独立性和空间结构。</li><li>记录 X/Y 的中心化与标准化、软件版本、绘图 scaling、各轴特征值、解释率分母、调整 R² 和置换检验设计。</li><li>拟合良好不等于因果成立；用研究问题决定可迁移的变量与识别策略，不把这四行合成数值当作实证结论。</li></ul>';
 }
 function render(){
 if(!mounted)return;
 panel.querySelectorAll('[data-step]').forEach(button=>{if(Number(button.getAttribute('data-step'))===state.step)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');});
 q('[data-action="previous"]').disabled=state.step===0;q('[data-action="next"]').disabled=state.step===5;
 q('[data-field="v4B"]').setAttribute('aria-invalid',String(!!invalid));error.textContent=invalid;
 status.textContent=invalid?'输入未采用；以下均为上次有效结果（V4 B = '+num(state.v4B,2)+'）。修正输入或恢复默认。':'第 '+(state.step+1)+' / 6 步 · 当前有效 V4 B = '+num(state.v4B,2)+' · 跟踪 '+state.village+' · 手动查看，无自动播放';
 panel.classList.toggle('rda-last-valid',!!invalid);
 q('.rda-summary').innerHTML=decomposition();
 stage.innerHTML=[firstStage,standardizedStage,fittedStage,eigenStage,plotsStage,sourceStage][state.step]();
 const img=stage.querySelector('img');if(img)img.addEventListener('error',()=>{img.hidden=true;const notice=stage.querySelector('.rda-image-status');if(notice)notice.hidden=false;},{once:true});
 }
 function reset(){
 if(!mounted)return;
 Object.assign(state,defaults);invalid='';result=global.PaperRDAModel.calculate(config.records,state.v4B);
 for(const key of ['v4B','village','denominator','view'])q('[data-field="'+key+'"]').value=String(state[key]);
 render();
 }
 function change(event){
 const target=event.target,field=target.getAttribute && target.getAttribute('data-field');if(!field)return;
 if(field==='v4B'){
 const raw=target.value.trim(), value=Number(raw);
 if(!raw || !Number.isFinite(value) || value<0 || value>5 || Math.abs(value*4-Math.round(value*4))>1e-9){invalid='请输入0至5之间、以0.25为步长的有限数值；空值不会作为0。';render();return;}
 try{const next=global.PaperRDAModel.calculate(config.records,value);state.v4B=value;result=next;invalid='';}catch(e){invalid=e.message;}
 }else if(field==='village' && result.row_ids.includes(target.value))state.village=target.value;
 else if(field==='denominator' && ['total','constrained'].includes(target.value))state.denominator=target.value;
 else if(field==='view' && ['variables','observations'].includes(target.value))state.view=target.value;
 else return;
 render();
 }
 function click(event){
 const button=event.target.closest && event.target.closest('button');if(!button||!panel.contains(button)||button.disabled)return;
 const step=button.getAttribute('data-step'),action=button.getAttribute('data-action');
 if(step!==null){state.step=Number(step);render();}
 else if(action==='next'&&state.step<5){state.step++;render();}
 else if(action==='previous'&&state.step>0){state.step--;render();}
 else if(action==='reset')reset();
 }
 function keydown(event){
 // Only the focused panel itself owns arrow navigation; form controls and scrollers keep native keys.
 if(event.target!==panel || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 const step=event.key==='Home'?0:event.key==='End'?5:Math.max(0,Math.min(5,state.step+(event.key==='ArrowRight'?1:-1)));
 event.preventDefault();state.step=step;render();
 }
 function destroy(){
 if(!mounted)return;
 mounted=false;panel.removeEventListener('click',click);panel.removeEventListener('input',change);panel.removeEventListener('change',change);panel.removeEventListener('keydown',keydown);global.removeEventListener('hashchange',destroy);global.removeEventListener('popstate',destroy);if(observer)observer.disconnect();panel.remove();active.delete(controller);mounts.delete(container);
 }
 function busy(){return mounted && (!!invalid || Object.keys(defaults).some(k=>state[k]!==defaults[k]) || (panel.contains(doc.activeElement) && ['INPUT','SELECT','TEXTAREA'].includes(doc.activeElement.tagName)));}
 const controller={destroy,reset,getState:()=>({...state,invalid:!!invalid,error:invalid,mounted,busy:busy(),pendingTimer:false,lastValidV4B:state.v4B}),isBusy:busy};
 mounts.set(container,controller);active.add(controller);panel.addEventListener('click',click);panel.addEventListener('input',change);panel.addEventListener('change',change);panel.addEventListener('keydown',keydown);global.addEventListener('hashchange',destroy);global.addEventListener('popstate',destroy);
 if(global.MutationObserver){observer=new global.MutationObserver(()=>{if(!container.isConnected||!panel.isConnected)destroy();});observer.observe(doc.documentElement,{childList:true,subtree:true});}
 render();return controller;
}
global.PaperRDA={mount,isBusy:()=>[...active].some(controller=>controller.isBusy())};
})(window);
