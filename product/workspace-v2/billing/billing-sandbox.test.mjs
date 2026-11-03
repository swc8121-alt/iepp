import test from 'node:test';
import assert from 'node:assert/strict';
import {BillingSandbox, quoteMaximumCost} from './billing-sandbox.mjs';
const env=()=>{const s=new BillingSandbox();s.registerOrder({orderId:'order-123',tenantId:'account-a',planId:'TRIAL7'});return s;};
const pg={orderId:'order-123',providerOrderId:'order-123',providerAmountKrw:1900,providerStatus:'DONE',providerVerified:true};
function ready(){const s=env();s.confirmFromTrustedAdapter(pg);return s;}
const request={tenantId:'account-a',actionId:'task-1',entitlementId:'order-123',maxCostMicrousd:75000,providerHealth:'ready',providerAvailableMicrousd:1000000};
test('price quote uses integer microUSD arithmetic including tool overhead',()=>{
  const x=quoteMaximumCost({inputTokensMax:10000,outputTokensMax:4000,inputPriceMicroUsdPerMillion:100000,outputPriceMicroUsdPerMillion:500000,toolBudgetMicrousd:10000,safetyMarginBps:1000});
  assert.equal(x,14300);
});
test('cannot issue entitlement from success URL alone',()=>{
  const s=env();assert.throws(()=>s.confirmFromTrustedAdapter({...pg,providerVerified:false}));assert.equal(s.entitlements.size,0);
});
test('PG amount mismatch and status mismatch cannot issue access',()=>{
  for(const bad of [{providerAmountKrw:1901},{providerStatus:'CANCELED'},{providerOrderId:'other'}]){
   const s=env();assert.throws(()=>s.confirmFromTrustedAdapter({...pg,...bad}));assert.equal(s.entitlements.size,0);
  }
});
test('duplicate payment confirmation makes only one entitlement',()=>{
  const s=env();s.confirmFromTrustedAdapter(pg);const r=s.confirmFromTrustedAdapter(pg);
  assert.equal(r.state,'already_confirmed');assert.equal(s.entitlements.size,1);
});
test('duplicate action id cannot charge reservation twice',()=>{
 const s=ready();s.reserveAction(request);const dupe=s.reserveAction(request);
 assert.equal(dupe.duplicate,true);assert.equal(s.snapshot('order-123').reservedMicrousd,75000);
});
test('same actionId and different input is rejected',()=>{
 const s=ready();s.reserveAction(request);assert.throws(()=>s.reserveAction({...request,maxCostMicrousd:80000}));
});
test('cross-tenant use is rejected even when order ID is known',()=>{
 const s=ready();assert.throws(()=>s.reserveAction({...request,tenantId:'account-b'}));
});
test('provider balance unknown, exhausted, and customer budget exhausted fail closed',()=>{
 const s=ready();for(const o of [{providerHealth:'unknown'},{providerAvailableMicrousd:null},{providerAvailableMicrousd:5000},{maxCostMicrousd:260000}]) assert.throws(()=>s.reserveAction({...request,...o}));
 assert.equal(s.snapshot('order-123').usedMicrousd,0);assert.equal(s.snapshot('order-123').reservedMicrousd,0);
});
test('timeout unknown holds reserve and does not authorize automatic retry',()=>{
 const s=ready();s.reserveAction(request);s.markProviderUncertain({tenantId:'account-a',actionId:'task-1'});
 assert.equal(s.snapshot('order-123').reservedMicrousd,75000);
 assert.equal(s.reserveAction(request).duplicate,true);
 assert.throws(()=>s.failConfirmed({tenantId:'account-a',actionId:'task-1'}));
});
test('verified receipt reconciles cost and releases unspent reservation',()=>{
 const s=ready();s.reserveAction(request);s.settleAction({tenantId:'account-a',actionId:'task-1',receiptVerified:true,observedActualCostMicrousd:50000});
 assert.equal(s.snapshot('order-123').remainingMicrousd,200000);assert.equal(s.snapshot('order-123').reservedMicrousd,0);
});
test('unverified provider usage cannot settle',()=>{
 const s=ready();s.reserveAction(request);assert.throws(()=>s.settleAction({tenantId:'account-a',actionId:'task-1',observedActualCostMicrousd:1000}));
 assert.equal(s.snapshot('order-123').reservedMicrousd,75000);
});
test('over-cap receipt is recorded as operator loss not customer overspend',()=>{
 const s=ready();s.reserveAction(request);const a=s.settleAction({tenantId:'account-a',actionId:'task-1',receiptVerified:true,observedActualCostMicrousd:90000});
 assert.equal(a.operatorOverageMicrousd,15000);assert.equal(a.customerChargedMicrousd,75000);assert.equal(a.state,'over_cap');
});
test('provider zero-cost confirmation releases reservation once',()=>{
 const s=ready();s.reserveAction(request);s.failConfirmed({tenantId:'account-a',actionId:'task-1',providerGuaranteedZeroCost:true});s.failConfirmed({tenantId:'account-a',actionId:'task-1',providerGuaranteedZeroCost:true});
 assert.equal(s.snapshot('order-123').reservedMicrousd,0);
});
test('negative monetary inputs never accepted',()=>{
 assert.throws(()=>quoteMaximumCost({inputTokensMax:1,outputTokensMax:1,inputPriceMicroUsdPerMillion:1,outputPriceMicroUsdPerMillion:1,toolBudgetMicrousd:-1}));
});