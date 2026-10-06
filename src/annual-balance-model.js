/* Original synthetic conservation lesson. Not FarmDESIGN/FarmM3 or author data.
 * No environment, DOM, storage or network dependency. All N flows are kg N/year.
 */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.PaperAnnualBalanceModel = factory();
}(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const defaults = Object.freeze({herd: 8, forageArea: 6, lossFraction: 0.20, replaceRetained: false});
  const domain = Object.freeze({
    herd: Object.freeze({min: 0, max: 20, step: 1, unit: '头'}),
    forageArea: Object.freeze({min: 0, max: 10, step: 0.5, unit: 'ha'}),
    lossFraction: Object.freeze({min: 0, max: 0.20, step: 0.05, unit: '比例'}),
    replaceRetained: Object.freeze({type: 'boolean'}),
    configurations: 4410
  });
  const constants = Object.freeze({totalArea: 10, forageYield: 6, feedPerAnimal: 5,
    feedNitrogenConcentration: 25, forageMineralRate: 100, cashMineralRate: 80,
    depositionRate: 10, cashProductRate: 60, animalProductRate: 20,
    feedImportCap: 10, referenceLossFraction: 0.20, tolerance: 1e-9});
  const units = Object.freeze({cashArea: 'ha', forageHarvest: 'Mg DM/year', feedDemand: 'Mg DM/year',
    feedConsumed: 'Mg DM/year', feedImported: 'Mg DM/year', feedExported: 'Mg DM/year',
    forageHarvestNitrogen: 'kg N/year', feedNitrogenConsumed: 'kg N/year',
    feedNitrogenImported: 'kg N/year', feedNitrogenExported: 'kg N/year',
    cashProductNitrogen: 'kg N/year', animalProductNitrogen: 'kg N/year',
    manureExcretedNitrogen: 'kg N/year', chainLoss: 'kg N/year', manureToSoil: 'kg N/year',
    baseMineralNitrogen: 'kg N/year', retainedNitrogen: 'kg N/year', mineralNitrogen: 'kg N/year',
    depositionNitrogen: 'kg N/year', soilResidual: 'kg N/year', farmInputs: 'kg N/year',
    farmOutputs: 'kg N/year', farmSurplus: 'kg N/year', checkError: 'kg N/year'});
  const labels = {herd: '动物数', forageArea: '饲草面积', lossFraction: '粪肥链损失比例'};
  function fail(field, message) {
    const error = new RangeError(message);
    error.field = field;
    throw error;
  }
  function calculate(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('需要完整的四项合成输入');
    const keys = Object.keys(input);
    if (keys.length !== 4 || keys.some(key => !Object.prototype.hasOwnProperty.call(defaults, key))) throw new TypeError('只接受 herd、forageArea、lossFraction、replaceRetained 四项输入');
    for (const key of ['herd', 'forageArea', 'lossFraction']) {
      const value = input[key], rule = domain[key];
      if (typeof value !== 'number' || !Number.isFinite(value)) fail(key, labels[key] + '必须是有限数值，不能空白或用字符串替代');
      if (value < rule.min || value > rule.max) fail(key, labels[key] + '须在 ' + rule.min + ' 至 ' + rule.max + ' 之间');
      const steps = (value - rule.min) / rule.step;
      if (Math.abs(steps - Math.round(steps)) > constants.tolerance) fail(key, labels[key] + '须按 ' + rule.step + ' 的步长输入');
    }
    if (typeof input.replaceRetained !== 'boolean') fail('replaceRetained', '是否替代矿质N必须明确为 true 或 false');
    const inputs = {herd: input.herd, forageArea: input.forageArea, lossFraction: input.lossFraction, replaceRetained: input.replaceRetained};
    const {herd, forageArea, lossFraction, replaceRetained} = inputs, c = constants;
    const cashArea = c.totalArea - forageArea;
    const forageHarvest = c.forageYield * forageArea, feedDemand = c.feedPerAnimal * herd;
    // Harvest leaves soil in full. Only the consumed part enters the animal.
    // Surplus crosses the farm gate as an export; there is no invisible stock.
    const feedConsumed = Math.min(forageHarvest, feedDemand);
    const feedImported = Math.max(feedDemand - forageHarvest, 0);
    const feedExported = Math.max(forageHarvest - feedDemand, 0);
    const forageHarvestNitrogen = forageHarvest * c.feedNitrogenConcentration;
    const feedNitrogenConsumed = feedConsumed * c.feedNitrogenConcentration;
    const feedNitrogenImported = feedImported * c.feedNitrogenConcentration;
    const feedNitrogenExported = feedExported * c.feedNitrogenConcentration;
    const animalProductNitrogen = herd * c.animalProductRate;
    const manureExcretedNitrogen = feedNitrogenConsumed + feedNitrogenImported - animalProductNitrogen;
    const chainLoss = manureExcretedNitrogen * lossFraction;
    const manureToSoil = manureExcretedNitrogen - chainLoss;
    const baseMineralNitrogen = forageArea * c.forageMineralRate + cashArea * c.cashMineralRate;
    const retainedNitrogen = (c.referenceLossFraction - lossFraction) * manureExcretedNitrogen;
    const mineralNitrogen = baseMineralNitrogen - (replaceRetained ? retainedNitrogen : 0);
    // Defensive boundary: reject rather than clamp if a future fixture is extended.
    if (mineralNitrogen < 0) fail('replaceRetained', '替代后矿质N小于0；这组输入被拒绝，不能把负投入当作出口');
    const depositionNitrogen = c.depositionRate * c.totalArea;
    const cashProductNitrogen = c.cashProductRate * cashArea;
    const soilResidual = mineralNitrogen + depositionNitrogen + manureToSoil - forageHarvestNitrogen - cashProductNitrogen;
    const farmInputs = mineralNitrogen + feedNitrogenImported + depositionNitrogen;
    const farmOutputs = cashProductNitrogen + animalProductNitrogen + feedNitrogenExported;
    const farmSurplus = farmInputs - farmOutputs;
    const checkError = farmInputs - farmOutputs - chainLoss - soilResidual;
    const flags = {feedImportExceeded: feedImported > c.feedImportCap + c.tolerance, soilSupplyDeficit: soilResidual < -c.tolerance};
    return {inputs, cashArea, forageHarvest, feedDemand, feedConsumed, feedImported, feedExported,
      forageHarvestNitrogen, feedNitrogenConsumed, feedNitrogenImported, feedNitrogenExported,
      cashProductNitrogen, animalProductNitrogen, manureExcretedNitrogen, chainLoss, manureToSoil,
      baseMineralNitrogen, retainedNitrogen, mineralNitrogen, depositionNitrogen, soilResidual,
      farmInputs, farmOutputs, farmSurplus, checkError,
      feasible: !flags.feedImportExceeded && !flags.soilSupplyDeficit, flags};
  }
  return Object.freeze({calculate, defaults, domain, constants, units});
}));
