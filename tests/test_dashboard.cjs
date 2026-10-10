// Optional: node tests/test_dashboard.cjs. Exercises real dashboard code without a browser.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'dashboard/template.html'), 'utf8');
const script = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const data = {results: {
  country_month: [
    {country:'UK',month:'2011-01',gross_pence:10000,cancel_pence:2000,net_pence:8000,sale_orders:2},
    {country:'France',month:'2011-12',gross_pence:5000,cancel_pence:1000,net_pence:4000,sale_orders:1}],
  products: [], customers:[{buyers:2,repeat_buyers:1,repeat_gross_pence:10000,identified_gross_pence:15000,top_decile_gross_pence:10000}],
  cohort_retention:[{cohort:'2011-01',month_index:0,cohort_size:2,active_buyers:2,retention_pct:100}]
},quality:{source_rows:3,duplicate_rows_removed:0,checks:{reconciles:true}}};
const nodes = new Map();
function node(id) {
  if (!nodes.has(id)) nodes.set(id, {
    value:id==='avoid'?'10':id==='margin'?'35':'',textContent:id==='dataset'?JSON.stringify(data):'',listeners:{},
    set innerHTML(v) {this.html=v;const first=v.match(/<option(?: value="([^"]*)")?>([^<]*)/);if(first)this.value=first[1]||first[2];},
    get innerHTML(){return this.html;},
    addEventListener(event,fn){this.listeners[event]=fn;}
  });
  return nodes.get(id);
}
vm.runInNewContext(script,{document:{getElementById:node},Intl,console});
assert.equal(node('gross').textContent,'£150');
assert.equal(node('net').textContent,'£120');
assert.equal(node('retained').textContent,'£3');
assert.ok(node('notice').textContent.includes('Partial month'));
node('country').value='UK';node('country').listeners.change();
assert.equal(node('gross').textContent,'£100');
assert.equal(node('rate').textContent,'20.00%');
node('avoid').value='0';node('avoid').listeners.input();
assert.equal(node('contribution').textContent,'£0');
node('country').value='France';node('end').value='2011-01';node('country').listeners.change();
assert.equal(node('gross').textContent,'£0');
assert.equal(node('rate').textContent,'N/A');
node('reset').listeners.click();assert.equal(node('gross').textContent,'£150');
console.log('Dashboard totals, filters, empty state, reset and scenario tests passed.');
