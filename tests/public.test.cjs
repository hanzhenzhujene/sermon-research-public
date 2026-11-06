const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const catalogue=JSON.parse(fs.readFileSync(path.join(root,'data/catalogue.json'),'utf8'));
const feasibility=JSON.parse(fs.readFileSync(path.join(root,'data/feasibility.json'),'utf8'));
const extensions=JSON.parse(fs.readFileSync(path.join(root,'data/extensions.json'),'utf8'));
const comparison=JSON.parse(fs.readFileSync(path.join(root,'data/comparison.json'),'utf8'));
const catholic=JSON.parse(fs.readFileSync(path.join(root,'data/catholic.json'),'utf8'));
const evidence=JSON.parse(fs.readFileSync(path.join(root,'data/evidence.json'),'utf8'));
const main={innerHTML:''};
const context={URL,URLSearchParams,console,setTimeout,clearTimeout,document:{getElementById:id=>id==='main'?main:{textContent:JSON.stringify(id==='public-data'?catalogue:id==='feasibility-data'?feasibility:id==='extensions-data'?extensions:id==='catholic-data'?catholic:id==='evidence-data'?evidence:comparison)}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'src/app.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/feasibility.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/extensions.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/catholic.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/comparison.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/evidence.js'),'utf8')+'\n'+fs.readFileSync(path.join(root,'src/thomas-evidence.js'),'utf8'),context);
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
test('Catholic current-match and route filters preserve the eight-record subset',()=>{
  assert.equal(run('catholicScreenRows().length'),8);
  assert.equal(run("catholicScreenRows({identity:'strong_current_name_locality'}).length"),6);
  assert.equal(run("catholicScreenRows({identity:'probable_unconfirmed'}).length"),2);
  assert.equal(run("catholicScreenRows({route:'homily_specific_route'}).length"),2);
  assert.equal(run("catholicScreenRows({route:'mass_stream_route'}).length"),4);
  assert.equal(run("catholicScreenRows({route:'unresolved'}).length"),2);
  assert.equal(run('D.churches.length'),86);assert.equal(run('E.roster.records.length'),150);
});
test('Catholic date cutoffs retain post-cutoff 2022 material',()=>{
  assert.equal(run("catholicItemRows('catholic-irvine-tony',{year:'2022'}).length"),7);
  assert.equal(run("catholicItemRows('catholic-irvine-tony',{year:'2022',cutoff:'on_or_after'}).length"),1);
  assert.equal(run("catholicItemRows('catholic-irvine-tony',{year:'2022',cutoff:'on_or_after'})[0].date"),'2022-12-11');
  assert.equal(run("catholicItemRows('catholic-ave-maria-florida-vidal',{year:'2022'}).length"),38);
  assert.equal(run("catholicItemRows('catholic-ave-maria-florida-vidal',{year:'2025',inspected:'yes'}).length"),2);
});
test('Catholic source and clergy conflicts remain separate',()=>{
  run("state={};catholicReviewDetail(C.roster_reviews.find(r=>r.id==='YALE2022-131'))");
  assert.ok(main.innerHTML.includes('Kyle Ingels')&&main.innerHTML.includes('Robert E. Jaeger'));
  assert.ok(main.innerHTML.includes('conflict')&&main.innerHTML.includes('2022: unknown'));
  run("catholicReviewDetail(C.roster_reviews.find(r=>r.id==='YALE2022-137'))");
  assert.ok(main.innerHTML.includes('St. Pioux')&&main.innerHTML.includes('St. Pius'));
});
test('Catholic downloads retain rite and occasion without a delivery claim',()=>{
  const values=run("catholicItemExportRows(catholicItemRows('catholic-ave-maria-florida-vidal',{inspected:'yes'}))");
  assert.equal(values.length,4);
  assert.ok(values.some(r=>r[6].includes('Extraordinary Form')));
  assert.ok(values.some(r=>r[6].includes('Baccalaureate')));
  assert.equal(run('C.items.filter(r=>r.delivery_date===null).length'),49);
});
test('historical roster deep links expose new checks without changing source names',()=>{
  run("state={};historicalDetail(E.roster.records.find(r=>r.id==='YALE2022-101'))");
  assert.ok(main.innerHTML.includes('Santa Maria Navidad'));
  assert.ok(main.innerHTML.includes('view=catholic')&&main.innerHTML.includes('YALE2022-101'));
  assert.ok(main.innerHTML.includes('historical events not linked'));
});
test('Catholic non-sermon context retains its original links',()=>{
  run("state={};catholicReviewDetail(C.roster_reviews.find(r=>r.id==='YALE2022-109'))");
  assert.ok(main.innerHTML.includes('href="https://seas-aloha.org/fathers-notes-2022"'));
  assert.ok(main.innerHTML.includes('Clergy introduction, not sermon'));
});
test('source decisions have exclusive action groups and separate recording evidence',()=>{
  assert.equal(run('decisionRows().length'),7);
  assert.equal(run("decisionRows({group:'primary_written_comparison'}).length"),2);
  assert.equal(run("decisionRows({group:'priority_gap_resolution'}).length"),2);
  assert.equal(run("decisionRows({group:'supplementary_written_source'}).length"),3);
  assert.equal(run("decisionRows({q:'Seattle'})[0].detail_view"),'seattle');
  assert.equal(run("decisionRows({q:'Adam Thomas'})[0].detail_view"),'thomas');
  assert.ok(run("decisionCard(X.decisions.items.find(r=>r.id==='catholic-irvine-tony'))").includes('2025-02-17') || run("decisionCard(X.decisions.items.find(r=>r.id==='catholic-irvine-tony'))").includes('February 17'));
});
test('Seattle raw and quarantined candidate units remain distinct',()=>{
  assert.equal(run('seattleWrittenRows().length'),48);
  assert.equal(run("seattleWrittenRows({kind:'homily_candidate'}).length"),46);
  assert.equal(run("seattleWrittenRows({kind:'other_writing'}).length"),2);
  assert.equal(run("seattleWrittenRows({status:'quarantined'}).length"),1);
  assert.equal(run("seattleWrittenRows({kind:'homily_candidate'}).filter(r=>r.sunday).length"),40);
  assert.equal(run("new Set(seattleWrittenRows({kind:'homily_candidate'}).filter(r=>r.sunday).map(r=>r.index_date)).size"),39);
  assert.equal(run("new Set(seattleWrittenRows({kind:'homily_candidate'}).filter(r=>r.sunday&&!r.quarantined_index_date).map(r=>r.index_date)).size"),38);
});
test('Seattle year and month filters preserve 2022 unknown written coverage',()=>{
  assert.equal(run("seattleEventRows({year:'2022'}).length"),70);
  assert.equal(run("seattleEventRows({year:'2025'}).length"),60);
  assert.equal(run("seattleSundayRows({year:'2022'}).length"),52);
  assert.equal(run("seattleSundayRows({year:'2025',month:'06'}).length"),5);
  assert.equal(run("seattleSundayRows({year:'2022'}).every(r=>r.written_status==='not_enumerated')"),true);
  assert.equal(run("seattleWrittenRows({month:'2025-06',status:'quarantined'}).length"),1);
});
test('Seattle omitted video field and mixed voices are explicit',()=>{
  assert.equal(run("observationFor('https://www.stjames-cathedral.org/Pubs/Pastor/2025/25aug10.aspx').video_link_observed"),null);
  assert.ok(run("seattleObservationMarkup(observationFor('https://www.stjames-cathedral.org/Pubs/Pastor/2025/25aug10.aspx'))").includes('Unspecified'));
  assert.ok(run("seattleObservationMarkup(observationFor('https://www.stjames-cathedral.org/Pubs/Pastor/2022/22may1.aspx'))").includes('testimony'));
});
test('Fourth evidence filters do not add targets or remove original conflicts',()=>{
  assert.equal(run('fourthEvidenceRows().length'),17);
  assert.equal(run("fourthEvidenceRows({year:'2025',status:'enriched'}).length"),11);
  assert.equal(run("fourthEvidenceRows({year:'2025',status:'unknown'}).length"),2);
  assert.equal(run("fourthEvidenceRows({status:'conflict'}).length"),4);
  assert.equal(run('F.fourth.target_checks.length'),33);
  assert.equal(run("F.fourth.target_checks.filter(r=>r.status==='discrepancy').length"),4);
});
test('Fourth later corroboration and service-specific limits survive rendering',()=>{
  run("state={};fourthEvidenceDetail(X.fourth.conflicts_2022.find(r=>r.text_link_url.endsWith('092522-400.html')))");
  assert.ok(main.innerHTML.includes('Earlier bulletin observation')&&main.innerHTML.includes('Separate later bulletin corroboration'));
  assert.ok(main.innerHTML.includes('January 1, 2017')&&main.innerHTML.includes('Listen to the Prophets'));
  run("fourthEvidenceDetail(X.fourth.targets_2025.find(r=>r.event_date_as_indexed==='2025-05-11'))");
  assert.ok(main.innerHTML.includes('11:00 only')&&main.innerHTML.includes('9:30'));
  run("fourthEvidenceDetail(X.fourth.targets_2025.find(r=>r.event_date_as_indexed==='2025-01-05'))");
  assert.ok(main.innerHTML.includes('Epiphanies and Ongoing Revelations')&&main.innerHTML.includes('Epiphanies and Revelations'));
});
test('Sunday author and evidence filters preserve unknowns and exclusions',()=>{
  assert.equal(run("seattleSundayRows({year:'2022',status:'not_enumerated'}).length"),52);
  assert.equal(run("seattleSundayRows({year:'2022',author:'Michael G. Ryan'}).length"),0);
  assert.equal(run("seattleSundayRows({year:'2025',status:'quarantined'}).length"),1);
  assert.equal(run("seattleSundayRows({year:'2025',status:'candidate'}).length"),38);
  assert.equal(run("seattleSundayRows({year:'2025',status:'not_observed'}).length"),13);
});
test('Fourth earlier time uncertainty is scoped beside later bulletin evidence',()=>{
  const text=run("expandedScreen(F.screens.find(r=>r.id==='fourth-chicago-il')).limits.join(' ')");
  assert.ok(text.includes('earlier manuscript-header checks')&&text.includes('11 of 13'));
  assert.ok(!text.includes('All 2025 target service times remain unconfirmed.'));
  assert.ok(run("F.fourth.limits.join(' ')").includes('All 2025 target service times remain unconfirmed.'));
});


test('new routes retain inherited counts and source association limits',()=>{
 assert.equal(run('Y.decisions.items.length'),7); assert.equal(run('D.churches.length'),86);
 assert.equal(run('E.roster.records.length'),150); assert.equal(run('F.screens.length'),12);
 assert.equal(run('D.items.length'),47); assert.equal(run('X.seattle.events.length'),130);
 assert.equal(run('Y.covenant.records.length'),14);
 assert.equal(run('Y.ai.cases.length'),4);
});
test('Covenant filtering respects the date conflict and ending evidence',()=>{
 assert.equal(run('covenantRows().length'),14);
 assert.equal(run("covenantRows({year:'2022'}).length"),7);
 assert.equal(run("covenantRows({cutoff:'eligible'}).length"),3);
 assert.equal(run("covenantRows({cutoff:'unknown'})[0].title"),'Facts Still Matter');
 assert.equal(run("covenantRows({cutoff:'unknown'})[0].sermon_header_date"),'2025-04-28');
 assert.equal(run("covenantRows({ending:'checked'}).length"),7);
 assert.equal(run("covenantRows({ending:'prior'}).length"),2);
 assert.equal(run("covenantRows({ending:'unknown'}).length"),5);
});
test('Fourth matching retains optional 53 to 3 to 2 relationship',()=>{
 assert.equal(run('fourthMatchRows().length'),53);
 assert.equal(run("fourthMatchRows({month:'same'}).length"),3);
 assert.equal(run("new Set(fourthMatchRows({month:'same'}).map(r=>r.post_url)).size"),2);
 assert.equal(run("Y.fourth.diagnostic.other_indexed_same_name_author_without_observed_text_links.every(r=>r.text_link_observed===false)"),true);
});
test('Covenant detail exposes unknown version and does not correct Monday',()=>{
 run("state={};covenantDetail(Y.covenant.records.find(r=>r.title==='Facts Still Matter'))");
 assert.ok(main.innerHTML.includes('2025-04-28')&&main.innerHTML.includes('Sunday Morning'));
 assert.ok(main.innerHTML.includes('Monday'));
 assert.ok(main.innerHTML.includes('First public availability')&&main.innerHTML.includes('unknown'));
});
test('AI cases remain component-specific with delivery uncertainty',()=>{
 run("state={};aiCaseDetail(Y.ai.cases.find(r=>r.id==='ai-bossen-houston-2024'))");
 assert.ok(main.innerHTML.includes('not labeled AI-written'));
 run("aiCaseDetail(Y.ai.cases.find(r=>r.id==='ai-mockingbird-2022'))");
 assert.ok(main.innerHTML.includes('Exclude from delivered-sermon exposure counts'));
});
test('Thomas scopes separate fourteen checked cutoff candidates and the index-only fifteenth',()=>{
 assert.equal(run('thomasPairs().length'),14);assert.equal(run("thomasPairs({scope:'all'}).length"),15);
 assert.equal(run("thomasPairs({scope:'after'}).length"),1);assert.equal(run("thomasPairs({evidence:'detail'}).length"),14);
 assert.equal(run("thomasPairs({evidence:'index'}).length"),0);assert.equal(run("thomasAnnualRows({year:'2022'}).length"),43);
 assert.equal(run("thomasAnnualRows({year:'2025'}).length"),45);
});
test('Thomas detail preserves rank-five label difference and author association limits',()=>{
 run("state={};thomasPairDetail(thomasPairRecords().find(r=>r.candidate_rank===5))");
 assert.ok(main.innerHTML.includes('Palm/Passion Sunday C')&&main.innerHTML.includes('Palm/Passion C'));
 assert.ok(main.innerHTML.includes('not independent confirmation of either event'));
 assert.ok(main.innerHTML.includes('metadata only, not prose similarity'));
 assert.ok(!main.innerHTML.includes('[object Object]'));
});
test('All fifteen pair details render without object noise or untranslated text',()=>{
 for(const r of evidence.thomas.candidates){run('state={};thomasPairDetail(thomasPairRecords().find(r=>r.pair_id==='+JSON.stringify(r.pair_id)+'))');assert.ok(!/\[object Object\]|[\u3400-\u9fff]/.test(main.innerHTML));}
});
test('Thomas partial-reference group preserves genre, license history and no reuse claim',()=>{
 assert.equal(run("thomasPairs({references:'equal',evidence:'detail'}).length"),10);
 assert.equal(run("thomasPairs({references:'partial',evidence:'detail'}).length"),4);
 assert.equal(run("thomasPairs({scope:'all',evidence:'index'}).length"),1);
 assert.equal(run("thomasPairs({scope:'after',evidence:'detail'}).length"),0);
 for(const rank of [11,12,13,14]){
  run(`state={};thomasPairDetail(thomasPairRecords().find(r=>r.candidate_rank===${rank}))`);
  assert.ok(main.innerHTML.includes('Partial-reference comparison')&&main.innerHTML.includes('0.5 — metadata only, not prose similarity'));
  assert.ok(!main.innerHTML.includes('This candidate remains index-level'));
 }
 run("thomasPairDetail(thomasPairRecords().find(r=>r.candidate_rank===12))");
 assert.ok(main.innerHTML.includes('later extraction did not reproduce')&&main.innerHTML.includes('not an established predecessor'));
 run("thomasPairDetail(thomasPairRecords().find(r=>r.candidate_rank===13))");
 assert.ok(main.innerHTML.includes('Prose followed by a song'));
 run("thomasPairDetail(thomasPairRecords().find(r=>r.candidate_rank===15))");
 assert.ok(main.innerHTML.includes('outside the November 30, 2022')&&main.innerHTML.includes('This candidate remains index-level'));
});
console.log('36 public interaction and safety test groups passed.');
