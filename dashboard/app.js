const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const colors = ['#b9ed92', '#ad9ee8', '#eab670', '#79c3d8'];
const escape = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (n) => '$' + (n / 1e6).toFixed(2) + 'M';
const percent = (n) => (n * 100).toFixed(1) + '%';
let nbaSample, moves = [], f1Loaded = false, nflLoaded = false;
function error(message) { const node = $('#global-error'); node.textContent = message; node.hidden = !message; }
async function api(path, body) {
  const response = await fetch(path, body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Request failed');
  return value;
}
async function busy(button, fn) {
  button.disabled = true; error('');
  try { await fn(); } catch (e) { error(e.message); } finally { button.disabled = false; }
}
$$('.tab').forEach(button => button.addEventListener('click', () => {
  const tab = button.dataset.tab;
  $$('.tab').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-selected', String(b === button)); });
  $$('.project-panel').forEach(p => p.hidden = p.id !== tab);
  $('.intro-aside > span').textContent = ({nba:'01',f1:'02',nfl:'03'}[tab]) + ' / 03';
  error('');
  if (tab === 'f1' && !f1Loaded) $('#f1-form').requestSubmit();
  if (tab === 'nfl' && !nflLoaded) $('#nfl-form').requestSubmit();
}));
function togglePlayer(pid) {
  const current = moves.findIndex(m => m.playerId === pid);
  if (current >= 0) moves.splice(current, 1);
  else {
    const owner = nbaSample.teams.find(t => t.players.some(p => p.id === pid));
    moves.push({playerId:pid,fromTeam:owner.id,toTeam:nbaSample.teams.find(t => t.id !== owner.id).id});
  }
  $('#nba-result').innerHTML = ''; renderTeams();
}
function renderTeams() {
  $('#nba-teams').innerHTML = nbaSample.teams.map(t => `<article class="team"><div class="team-top"><div class="team-name"><div class="team-mark">${escape(t.id)}</div><div><h3>${escape(t.name)}</h3><div class="team-meta">${t.rosterSize} players · demo roster excerpt</div></div></div><div class="team-salary">${money(t.payroll)}<small>TEAM PAYROLL</small></div></div>${t.players.map(p => {
    const selected = moves.some(m => m.playerId === p.id);
    return `<div class="player ${selected?'selected':''}" draggable="true" data-player="${escape(p.id)}"><span class="player-avatar">${escape(p.name.split(' ').map(x => x[0]).join(''))}</span><div><div class="player-name">${escape(p.name)}</div><div class="player-position">${escape(p.position)}${selected?' · outgoing':''}</div></div><span class="player-money">${money(p.salary)}</span><button type="button" aria-pressed="${selected}" aria-label="${selected?'Remove':'Trade'} ${escape(p.name)}">${selected?'Undo':'Trade →'}</button></div>`;
  }).join('')}<div class="dropzone" data-team="${escape(t.id)}">DROP A PLAYER FROM THE OTHER TEAM HERE</div></article>`).join('');
  $$('.player').forEach(p => {
    p.querySelector('button').addEventListener('click', () => togglePlayer(p.dataset.player));
    p.addEventListener('dragstart', e => e.dataTransfer.setData('text/plain', p.dataset.player));
  });
  $$('.dropzone').forEach(z => {
    z.addEventListener('dragover', e => { e.preventDefault(); z.classList.add('over'); });
    z.addEventListener('dragleave', () => z.classList.remove('over'));
    z.addEventListener('drop', e => {
      e.preventDefault(); z.classList.remove('over');
      const pid = e.dataTransfer.getData('text/plain');
      const owner = nbaSample.teams.find(t => t.players.some(p => p.id === pid));
      if (owner && owner.id !== z.dataset.team && !moves.some(m => m.playerId === pid)) togglePlayer(pid);
    });
  });
  $('#trade-count').textContent = `${moves.length} players selected · ${moves.length? 'ready for validation':'select at least one player'}`;
}
$('#nba-reset').addEventListener('click', () => { moves = structuredClone(nbaSample.moves); $('#nba-result').innerHTML = ''; renderTeams(); error(''); });
$('#nba-clear').addEventListener('click', () => { moves = []; $('#nba-result').innerHTML = ''; renderTeams(); error(''); });
$('#nba-validate').addEventListener('click', () => busy($('#nba-validate'), async () => {
  const result = await api('/api/nba/validate', {...nbaSample,moves});
  $('#nba-result').innerHTML = `<div class="result-heading ${result.validUnderImplementedRules?'':'invalid'}">${result.validUnderImplementedRules?'✓ Valid under implemented rules':'Trade fails implemented checks'}<small>${escape(result.season)} SNAPSHOT</small></div><div class="result-table"><table><thead><tr><th>TEAM</th><th>OUTGOING</th><th>INCOMING</th><th>PROJECTED PAYROLL</th><th>MATCHING ROUTE</th><th>HARD CAP</th></tr></thead><tbody>${result.teams.map(t=>`<tr><td>${escape(t.name)}</td><td>${money(t.outgoing)}</td><td>${money(t.incoming)}</td><td>${money(t.projectedPayroll)}</td><td>${escape(t.route)}</td><td>${t.effectiveHardCap?money(t.effectiveHardCap):'None triggered'}</td></tr>`).join('')}</tbody></table></div>${result.violations.map(v=>`<p class="negative">${escape(v)}</p>`).join('')}`;
}));
function lineChart(groups, xKey, yKey, xLabel, yLabel) {
  const w=900,h=240,left=55,right=20,top=18,bottom=35;
  const points=groups.flatMap(g=>g.points);
  const xs=points.map(p=>Number(p[xKey])),ys=points.map(p=>Number(p[yKey]));
  const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.floor(Math.min(...ys)-1),ymax=Math.ceil(Math.max(...ys)+1);
  const X=x=>left+(x-xmin)/Math.max(1,xmax-xmin)*(w-left-right);
  const Y=y=>h-bottom-(y-ymin)/Math.max(1,ymax-ymin)*(h-top-bottom);
  let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${escape(yLabel)} versus ${escape(xLabel)}">`;
  for(let i=0;i<=4;i++) {
    const y=ymin+(ymax-ymin)*i/4;
    svg+=`<line x1="${left}" y1="${Y(y)}" x2="${w-right}" y2="${Y(y)}" stroke="#2a323b"/><text x="${left-9}" y="${Y(y)+3}" text-anchor="end" fill="#97a3ad" font-size="9">${y.toFixed(0)}</text>`;
  }
  for(let i=0;i<=5;i++) {const x=xmin+(xmax-xmin)*i/5;svg+=`<text x="${X(x)}" y="${h-17}" text-anchor="middle" fill="#97a3ad" font-size="9">${Math.round(x)}</text>`;}
  groups.forEach((g,i)=>svg+=`<polyline points="${g.points.map(p=>`${X(Number(p[xKey]))},${Y(Number(p[yKey]))}`).join(' ')}" fill="none" stroke="${colors[i%colors.length]}" stroke-width="1.7"/>`);
  return svg+`<text x="${w/2}" y="${h-1}" fill="#97a3ad" font-size="9" text-anchor="middle">${escape(xLabel)}</text><text x="6" y="12" fill="#97a3ad" font-size="9">${escape(yLabel)}</text></svg>`;
}
$('#f1-form').addEventListener('submit', e => {
  e.preventDefault(); busy(e.target.querySelector('button'), async () => {
    const input=Object.fromEntries([...new FormData(e.target)].map(([k,v])=>[k,Number(v)])); input.rainProbability/=100;
    const result=await api('/api/f1/simulate',input); f1Loaded=true;
    const groups=result.results.map(r=>({name:r.strategy,points:result.lapTrace.filter(p=>p.strategy===r.strategy)}));
    $('#f1-results').innerHTML=`<div class="stats"><div class="stat"><span>LOWEST MEAN RACE TIME</span><strong>${(result.results[0].meanSeconds/60).toFixed(2)} <small>min</small></strong><small>${escape(result.results[0].strategy)}</small></div><div class="stat"><span>TOTAL SIMULATED RACES</span><strong>${(result.runsPerStrategy*result.results.length).toLocaleString()}</strong><small>${result.runsPerStrategy.toLocaleString()} per strategy · seed ${result.seed}</small></div><div class="stat"><span>RAIN SCENARIO PROBABILITY</span><strong>${percent(result.rainProbability)}</strong><small>All strategies adapt to intermediates</small></div></div><div class="result-table"><table><thead><tr><th>STRATEGY</th><th>MEAN (S)</th><th>10TH–90TH PERCENTILE (S)</th><th>LOWEST-TIME SHARE</th></tr></thead><tbody>${result.results.map(r=>`<tr><td>${escape(r.strategy)}</td><td>${r.meanSeconds.toFixed(1)}</td><td>${r.p10Seconds.toFixed(1)} – ${r.p90Seconds.toFixed(1)}</td><td>${percent(r.winProbability)}</td></tr>`).join('')}</tbody></table></div><div class="chart-card"><h3>Dry-race lap trace</h3>${lineChart(groups,'lap','lapSeconds','Lap number','Lap time (s)')}<div class="chart-legend">${groups.map((g,i)=>`<span><i style="background:${colors[i]}"></i>${escape(g.name)}</span>`).join('')}</div><p class="footnote">Deterministic reference traces. Spikes include the configured pit-lane loss.</p></div>`;
  });
});
function nflContext(form) {
  return Object.fromEntries([...new FormData(form)].map(([k,v])=>[k,k==='previous_play'?v:Number(v)]));
}
$('#nfl-form').addEventListener('submit',e=>{
  e.preventDefault(); busy(e.target.querySelector('button'),async()=>{
    const input=nflContext(e.target);
    const prediction=await api('/api/nfl/predict',input);
    const recommend=input.down===4&&input.seconds_remaining<=900?await api('/api/nfl/recommend',{...input,seed:42}):null;
    nflLoaded=true;
    $('#nfl-results').innerHTML=`<div class="card prediction-card"><div class="prediction-top"><div><p class="eyebrow">PREDICTED PLAY CALL</p><strong>${escape(prediction.prediction[0].toUpperCase()+prediction.prediction.slice(1))}</strong></div><span class="model-label">LOGISTIC BASELINE</span></div><div class="probability-row"><span>Pass</span><span>${percent(prediction.pass_probability)}</span></div><div class="track"><i style="width:${prediction.pass_probability*100}%"></i></div><div class="probability-row"><span>Run</span><span>${percent(prediction.run_probability)}</span></div><div class="track run"><i style="width:${prediction.run_probability*100}%"></i></div><p class="footnote">Trained on synthetic plays. This is a probability estimate, not a guaranteed call.</p></div>${recommend?`<div class="card action-card"><div class="action-heading"><h3>Fourth-down comparison</h3><span>${escape(({go:'GO FOR IT',field_goal:'FIELD GOAL',punt:'PUNT'})[recommend.recommendation])}</span></div><div class="actions">${recommend.actions.map(a=>`<div class="action-row"><div><span>${escape(({go:'Go for it',field_goal:'Field goal',punt:'Punt'})[a.action])}</span><span>${percent(a.win_probability)}</span></div><div class="track"><i style="width:${a.win_probability*100}%"></i></div><small>95% sampling interval: ${percent(a.interval95[0])}–${percent(a.interval95[1])}</small></div>`).join('')}</div><p class="footnote">${recommend.runs.toLocaleString()} continuations per action. Simplified clock and drive model; uncalibrated win estimates.</p></div>`:'<p class="footnote">Select fourth down with 900 seconds or less remaining for strategy comparisons.</p>'}`;
    const report=await api('/api/nfl/metrics');
    $('#nfl-metrics').innerHTML=`<div class="stats"><div class="stat"><span>SYNTHETIC TEST ACCURACY</span><strong>${percent(report.test.accuracy)}</strong><small>${report.test.rows} held-out demo plays</small></div><div class="stat"><span>MAJORITY BASELINE ACCURACY</span><strong>${percent(report.majority_baseline_accuracy)}</strong><small>Same held-out demo season</small></div><div class="stat"><span>TRAINING / VALIDATION / TEST</span><strong>${report.splits.train.games} / ${report.splits.validation.games} / ${report.splits.test.games}</strong><small>Separate games and seasons</small></div></div>`;
  });
});
function parseCSV(text) {
  const rows=[];let row=[],field='',quote=false;
  for(let i=0;i<text.length;i++) {
    const c=text[i];
    if(c==='"') {if(quote&&text[i+1]==='"'){field+='"';i++;}else quote=!quote;}
    else if(c===','&&!quote){row.push(field);field='';}
    else if((c==='\n'||c==='\r')&&!quote){if(c==='\r'&&text[i+1]==='\n')i++;row.push(field);if(row.some(Boolean))rows.push(row);row=[];field='';}
    else field+=c;
  }
  if(quote)throw new Error('Unterminated quoted CSV field');
  row.push(field);if(row.some(Boolean))rows.push(row);
  const header=rows.shift()||[];
  return rows.map(r=>Object.fromEntries(header.map((h,i)=>[h,r[i]??''])));
}
$('#telemetry-file').addEventListener('change',async e=>{
  error('');
  try {
    const file=e.target.files[0];if(!file)return;
    if(file.size>8e6)throw new Error('Use a CSV smaller than 8 MB');
    const rows=parseCSV(await file.text()).filter(r=>Number(r.lap_duration)>0&&Number(r.lap_number)>0&&r.driver_number);
    if(!rows.length||rows.length>20000)throw new Error('Use a normalized CSV with 1–20,000 valid laps');
    const drivers=[...new Set(rows.map(r=>r.driver_number))].slice(0,4);
    const groups=drivers.map(d=>({name:'Driver '+d,points:rows.filter(r=>r.driver_number===d).sort((a,b)=>Number(a.lap_number)-Number(b.lap_number))}));
    $('#telemetry-result').innerHTML=`<div class="chart-card"><h3>${rows.length.toLocaleString()} imported lap records</h3>${lineChart(groups,'lap_number','lap_duration','Lap number','Observed lap time (s)')}<div class="chart-legend">${groups.map((g,i)=>`<span><i style="background:${colors[i]}"></i>${escape(g.name)}</span>`).join('')}</div></div>`;
  } catch(e) {error(e.message);}
});
try {nbaSample=await api('/api/nba/sample');moves=structuredClone(nbaSample.moves);renderTeams();}catch(e){error(e.message);}
