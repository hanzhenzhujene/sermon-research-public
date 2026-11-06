const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const catalogue=JSON.parse(fs.readFileSync(path.join(root,'data/catalogue.json'),'utf8'));
const feasibility=JSON.parse(fs.readFileSync(path.join(root,'data/feasibility.json'),'utf8'));
const main={innerHTML:''};
const context={URL,URLSearchParams,console,setTimeout,clearTimeout,document:{getElementById:id=>id==='main'?main:{textContent:JSON.stringify(id==='public-data'?catalogue:feasibility)}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'src/app.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/feasibility.js'),'utf8'),context);
const run=source=>vm.runInContext(source,context);
const test=(name,fn)=>{fn();console.log('PASS '+name)};
test('selected and supplemental populations stay separate',()=>{
  assert.equal(run('state={};feasibilityRows().length'),12);
  assert.equal(run("state={group:'supplemental'};feasibilityRows().length"),3);
});
test('route, state, tradition and search filters combine',()=>{
  assert.equal(run("state={route:'audio_archive_links'};feasibilityRows().length"),2);
  assert.equal(run("state={route:'audio_archive_links',region:'CA'};feasibilityRows().length"),1);
  assert.equal(run("state={tradition:'Episcopal Church'};feasibilityRows().length"),1);
  assert.equal(run("state={q:'Adam Thomas'};feasibilityRows()[0].id"),'stmark-mystic-ct');
  assert.equal(run("state={category:'priority_text'};feasibilityRows().length"),2);
  assert.equal(run("state={category:'priority_text',region:'KS'};feasibilityRows().length"),0);
});
test('HTML and source-link injection rejected',()=>{
  assert.equal(run("esc('<img src=x onerror=alert(1)>')"),'&lt;img src=x onerror=alert(1)&gt;');
  assert.equal(run("safeUrl('javascript:alert(1)')"),null);
  assert.equal(run("safeUrl('https://user:secret@example.com')"),null);
  assert.ok(!run("ext('javascript:alert(1)','unsafe')").includes('href='));
});
test('CSV formulas are escaped, including leading whitespace',()=>{
  for(const cell of ['=1+1','+SUM(A1:A2)','-1+2','@SUM(A1)','  =1+1','\t=1+1']){
    const result=run('safeCsvCell('+JSON.stringify(cell)+')');assert.ok(result.startsWith('"\''),result);
  }
  assert.equal(run("safeCsvCell('A \"quoted\" title')"),'"A ""quoted"" title"');
  assert.equal(run('safeCsvCell(null)'),'""');
});
test('speaker table renders separate yearly counts without object noise',()=>{
  const target={innerHTML:''},annual={insertAdjacentHTML:()=>{}};
  context.document.getElementById=id=>id==='study-speakers'?target:annual;
  run("renderStudySupplement('fourth')");
  assert.ok(target.innerHTML.includes('Joseph L. Morrow'));
  assert.ok(target.innerHTML.includes('3 target checks: 1 without inspected conflict, 2 discrepancies'));
  assert.ok(!target.innerHTML.includes('[object Object]'));
});
test('supplemental item observations expose date and access limits',()=>{
  const value=run("observationTable(F.supplemental.find(r=>r.id==='supplemental-grace-cathedral-sf'))");
  assert.ok(value.includes('2025-05-23')&&value.includes('Not established'));
  assert.ok(value.includes('Publication date known; event date unknown'));
});
test('legacy routes and existing deep-link keys remain supported',()=>{
  assert.equal(run('oldViews.map'),'churches');assert.equal(run('oldViews.licensed'),'items');
  assert.equal(run("path('churches',{id:'overture:test'})"),'#view=churches&id=overture%3Atest');
});
test('rights clarification applies only to the identified work',()=>{
  const matched=run("itemRights(D.items.find(r=>r.id==='manuscript:vandermeulen-2022-05-29'))");
  assert.ok(matched.includes('CC BY-NC 4.0')&&matched.includes('operation'));
  const unrelated=run("itemRights(D.items.find(r=>r.id==='manuscript:vandermeulen-2025-07-13'))");
  assert.ok(unrelated.includes('bounded private use')&&!unrelated.includes('<table>'));
});
console.log('8 public interaction and safety test groups passed.');
