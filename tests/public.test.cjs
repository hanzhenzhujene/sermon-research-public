const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const catalogue=JSON.parse(fs.readFileSync(path.join(root,'data/catalogue.json'),'utf8'));
const feasibility=JSON.parse(fs.readFileSync(path.join(root,'data/feasibility.json'),'utf8'));
const extensions=JSON.parse(fs.readFileSync(path.join(root,'data/extensions.json'),'utf8'));
const main={innerHTML:''};
const context={URL,URLSearchParams,console,setTimeout,clearTimeout,document:{getElementById:id=>id==='main'?main:{textContent:JSON.stringify(id==='public-data'?catalogue:id==='feasibility-data'?feasibility:extensions)}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'src/app.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/feasibility.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/extensions.js'),'utf8'),context);
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
test('historical roster filters retain separate counting units',()=>{
  assert.equal(run('state={};historicalRows().length'),150);
  assert.equal(run("state={tradition:'Catholic'};historicalRows().length"),50);
  assert.equal(run("state={region:'Alaska'};historicalRows().length"),3);
  assert.equal(run("state={region:'Alaska',tradition:'Mainline Protestant'};historicalRows().length"),1);
  assert.equal(run("state={denomination:'United Methodist'};historicalRows().length"),20);
  assert.equal(run("state={q:'Abundant Life Outreach'};historicalRows().length"),1);
  assert.equal(run('D.churches.length'),86);assert.equal(run('F.screens.length'),12);
});
test('historical details preserve original date labels and rejected identity match',()=>{
  run("state={};historicalDetail(E.roster.records.find(r=>r.id==='YALE2022-133'))");
  assert.ok(main.innerHTML.includes('Morris County')&&main.innerHTML.includes('Passaic'));
  assert.ok(main.innerHTML.includes('Not independently verified'));
  assert.equal(run('E.overlap.accepted_matches'),0);assert.equal(run('E.overlap.actual_overlap'),null);
});
test('Holy Trinity yearly, speaker and youth filters expose compositional differences',()=>{
  assert.equal(run('orthodoxRows().length'),97);
  assert.equal(run("orthodoxRows({year:'2022'}).length"),47);
  assert.equal(run("orthodoxRows({year:'2025'}).length"),50);
  assert.equal(run("orthodoxRows({year:'2022',speaker:'Aris Metrakos'}).length"),22);
  assert.equal(run("orthodoxRows({year:'2022',speaker:'Aris Metrakos',kind:'youth sermon'}).length"),7);
  assert.equal(run("orthodoxRows({year:'2025',speaker:'Aris Metrakos',kind:'youth sermon'}).length"),0);
  assert.equal(run("E.orthodox.records.filter(r=>r.filename_date&&r.filename_date!==r.date).length"),7);
});
test('extension exports preserve unknowns, original dates and safe links',()=>{
  assert.equal(run('historicalExportRows(E.roster.records).length'),150);
  assert.equal(run("orthodoxExportRows(E.orthodox.records).filter(r=>r[12]===null).length"),97);
  const rendered=run("orthodoxRowMarkup({...E.orthodox.records[0],title:'<img onerror=1>',media_url:'javascript:alert(1)'})").join('');
  assert.ok(rendered.includes('&lt;img'));
  assert.ok(!rendered.includes('href="javascript:'));
  assert.ok(!rendered.includes('<audio'));
});
test('unnamed speakers are filterable and additional attribution retains its role',()=>{
  assert.equal(run("orthodoxRows({speaker:'Name not stated'}).length"),13);
  const html=run("orthodoxRowMarkup(E.orthodox.records.find(r=>r.id==='holy_trinity_sf_2022-09-11_063'))").join('');
  assert.ok(html.includes('Father Nicholas — reminders'));
  assert.ok(!html.includes('[object Object]'));
  assert.equal(run("orthodoxExportRows([E.orthodox.records.find(r=>r.id==='holy_trinity_sf_2022-09-11_063')])[0][10]"),'Father Nicholas — reminders');
});
console.log('13 public interaction and safety test groups passed.');
