/**
 * IEPP Workspace pre-registration billing SANDBOX.
 * In-memory demonstration only; no PG/API calls, no persistence, no atomic DB guarantees.
 * DO NOT USE as production billing system.
 */
function positiveInt(v, name) {
  if (!Number.isSafeInteger(v) || v <= 0) throw new TypeError(`${name} must be a positive safe integer`);
  return v;
}
function nonnegativeInt(v, name) {
  if (!Number.isSafeInteger(v) || v < 0) throw new TypeError(`${name} must be a nonnegative safe integer`);
  return v;
}
function name(v,field) {
  if (typeof v !== 'string' || !v.trim() || v.length > 160) throw new TypeError(`${field} invalid`);
  return v.trim();
}

export function quoteMaximumCost({inputTokensMax, outputTokensMax, inputPriceMicroUsdPerMillion, outputPriceMicroUsdPerMillion, toolBudgetMicrousd = 0, safetyMarginBps = 1500}) {
  const inp=BigInt(positiveInt(inputTokensMax,'inputTokensMax'));
  const out=BigInt(positiveInt(outputTokensMax,'outputTokensMax'));
  const ip=BigInt(nonnegativeInt(inputPriceMicroUsdPerMillion,'inputPriceMicroUsdPerMillion'));
  const op=BigInt(nonnegativeInt(outputPriceMicroUsdPerMillion,'outputPriceMicroUsdPerMillion'));
  const tools=BigInt(nonnegativeInt(toolBudgetMicrousd,'toolBudgetMicrousd'));
  const margin=BigInt(nonnegativeInt(safetyMarginBps,'safetyMarginBps'));
  if (margin > 10000n) throw new RangeError('safetyMarginBps must be <= 10000');
  // ceil((tokens * quoted microUSD per 1M) / 1M)
  const base=((inp*ip+out*op+999999n)/1000000n)+tools;
  const total=(base*(10000n+margin)+9999n)/10000n;
  if(total>BigInt(Number.MAX_SAFE_INTEGER))throw new RangeError('quote overflow');
  return Number(total);
}

export class BillingSandbox {
  constructor({plans={TRIAL7:{amountKrw:1900, days:7, budgetMicrousd:250000}}} = {}) {
    this.plans=plans; this.orders=new Map(); this.entitlements=new Map(); this.actions=new Map();
  }
  registerOrder({orderId,tenantId,planId}) {
    orderId=name(orderId,'orderId'); tenantId=name(tenantId,'tenantId'); planId=name(planId,'planId');
    const plan=this.plans[planId]; if(!plan)throw new Error('plan not configured');
    if(this.orders.has(orderId))throw new Error('duplicate orderId');
    this.orders.set(orderId,{orderId,tenantId,planId,amountKrw:positiveInt(plan.amountKrw,'amountKrw'),state:'payment_pending'});
    return {orderId,state:'payment_pending'};
  }
  /** `providerVerified=true` can only come from a trusted backend payment verification adapter.
   * This sandbox cannot authenticate real PG receipts. */
  confirmFromTrustedAdapter({orderId,providerOrderId,providerAmountKrw,providerStatus,providerVerified=false}) {
    const order=this.orders.get(name(orderId,'orderId'));
    if(!order)throw new Error('order not found');
    if(providerVerified!==true)throw new Error('trusted PG verification required');
    if(providerOrderId!==orderId || providerAmountKrw!==order.amountKrw || providerStatus!=='DONE')throw new Error('PG order/amount/status mismatch');
    if(order.state==='paid')return {orderId,entitlementId:orderId,state:'already_confirmed'};
    if(order.state!=='payment_pending')throw new Error('order not payable');
    order.state='paid';
    const plan=this.plans[order.planId];
    this.entitlements.set(orderId,{id:orderId,tenantId:order.tenantId,days:plan.days,budgetMicrousd:positiveInt(plan.budgetMicrousd,'budgetMicrousd'),usedMicrousd:0,reservedMicrousd:0,state:'active'});
    return {orderId,entitlementId:orderId,state:'entitlement_active'};
  }
  reserveAction({tenantId,actionId,entitlementId,maxCostMicrousd,providerHealth='unknown',providerAvailableMicrousd=null}) {
    tenantId=name(tenantId,'tenantId');actionId=name(actionId,'actionId');entitlementId=name(entitlementId,'entitlementId');
    const key=`${tenantId}::${actionId}`;
    const existing=this.actions.get(key);
    if(existing) {
      if(existing.entitlementId!==entitlementId || existing.maxCostMicrousd!==maxCostMicrousd)throw new Error('same action ID different request');
      return {...existing, duplicate:true};
    }
    const entitlement=this.entitlements.get(entitlementId);
    if(!entitlement || entitlement.tenantId!==tenantId || entitlement.state!=='active')throw new Error('no valid owned entitlement');
    const max=positiveInt(maxCostMicrousd,'maxCostMicrousd');
    if(providerHealth!=='ready' || !Number.isSafeInteger(providerAvailableMicrousd) || providerAvailableMicrousd<max)throw new Error('operator API unavailable/insufficient');
    if(entitlement.budgetMicrousd-entitlement.usedMicrousd-entitlement.reservedMicrousd<max)throw new Error('customer service budget exceeded');
    entitlement.reservedMicrousd+=max;
    const act={tenantId,actionId,entitlementId,maxCostMicrousd:max,state:'reserved',actualCostMicrousd:null};
    this.actions.set(key,act);return {...act};
  }
  getAction(tenantId,actionId){return this.actions.get(`${tenantId}::${actionId}`)||null;}
  markProviderUncertain({tenantId,actionId}) {
    const a=this.getAction(tenantId,actionId);if(!a)throw new Error('unknown action');
    if(a.state!=='reserved')throw new Error('invalid transition');
    a.state='unknown'; // hold reservation; DO NOT automatically retry
    return {...a};
  }
  settleAction({tenantId,actionId,observedActualCostMicrousd,receiptVerified=false}) {
    const a=this.getAction(tenantId,actionId);if(!a)throw new Error('unknown action');
    if(a.state==='completed' || a.state==='over_cap')return {...a,duplicate:true};
    if(!['reserved','unknown'].includes(a.state))throw new Error('invalid transition');
    if(receiptVerified!==true)throw new Error('verified provider usage required');
    const actual=nonnegativeInt(observedActualCostMicrousd,'observedActualCostMicrousd');
    const e=this.entitlements.get(a.entitlementId);
    e.reservedMicrousd-=a.maxCostMicrousd;
    const charged=Math.min(actual,a.maxCostMicrousd);
    e.usedMicrousd+=charged;
    a.actualCostMicrousd=actual;
    a.customerChargedMicrousd=charged;
    a.operatorOverageMicrousd=Math.max(0,actual-charged);
    a.state=actual>a.maxCostMicrousd?'over_cap':'completed';
    return {...a};
  }
  failConfirmed({tenantId,actionId,providerGuaranteedZeroCost=false}) {
    const a=this.getAction(tenantId,actionId);if(!a)throw new Error('unknown action');
    if(a.state==='failed_confirmed')return {...a,duplicate:true};
    if(!['reserved','unknown'].includes(a.state)||providerGuaranteedZeroCost!==true)throw new Error('provider confirmation required');
    this.entitlements.get(a.entitlementId).reservedMicrousd-=a.maxCostMicrousd;
    a.state='failed_confirmed';return {...a};
  }
  snapshot(entitlementId) {
    const e=this.entitlements.get(entitlementId);if(!e)throw new Error('unknown entitlement');
    return {...e,remainingMicrousd:e.budgetMicrousd-e.reservedMicrousd-e.usedMicrousd};
  }
}