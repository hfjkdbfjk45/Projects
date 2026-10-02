import React,{useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import '../../../../dashboard/styles.css';

const initial={down:4,ydstogo:3,yardline_100:38,seconds_remaining:420,score_differential:-3,quarter:4,previous_play:'pass',runs:2000};
const pct=n=>(n*100).toFixed(1)+'%';
const labels={go:'Go for it',field_goal:'Field goal',punt:'Punt'};
async function api(path,body){
  const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
  const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');return data;
}
function App(){
  const [context,setContext]=useState(initial),[prediction,setPrediction]=useState(null),[recommendation,setRecommendation]=useState(null);
  const [report,setReport]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  useEffect(()=>{api('/api/metrics').then(setReport).catch(e=>setError(e.message));},[]);
  function update(e){setContext({...context,[e.target.name]:e.target.name==='previous_play'?e.target.value:Number(e.target.value)});setPrediction(null);setRecommendation(null);}
  async function analyze(e){
    e.preventDefault();setBusy(true);setError('');setPrediction(null);setRecommendation(null);
    try{
      setPrediction(await api('/api/predict',context));
      if(context.down===4&&context.seconds_remaining<=900)setRecommendation(await api('/api/recommend',{...context,seed:42}));
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function live(){
    setBusy(true);setError('');
    try{const data=await api('/api/live');setContext({...initial,...data.context});setPrediction(data.prediction);setRecommendation(null);}
    catch(e){setError(e.message);}finally{setBusy(false);}
  }
  const fields=[['ydstogo','Yards to go',1,99],['yardline_100',"Yards from opponent's goal",1,99],['seconds_remaining','Game clock (seconds)',1,3600],['score_differential','Offense score difference',-80,80],['runs','Simulation runs',100,5000]];
  return <><header><a className="brand" href="/"><span className="brand-icon">S</span>ScoreLab<span className="brand-label">NFL ANALYTICS</span></a><a href="https://github.com/hfjkdbfjk45/Projects">View source ↗</a></header><main>
    <section className="intro"><div><p className="eyebrow">SALMAN NUR / NFL PLAY PREDICTOR</p><h1>Read the situation.<br/><span>Compare the next call.</span></h1><p className="intro-copy">React + Flask · causal Transformer training · PostgreSQL ETL</p></div></section>
    {error&&<div className="error" role="alert">{error}</div>}
    <div className="nfl-layout"><form className="nfl-inputs card" onSubmit={analyze}><h3>Pre-snap situation</h3><div className="input-grid">
      <label>Down<select name="down" value={context.down} onChange={update}>{[1,2,3,4].map(n=><option key={n}>{n}</option>)}</select></label>
      {fields.map(([name,label,min,max])=><label key={name}>{label}<input type="number" name={name} min={min} max={max} value={context[name]} onChange={update} required/></label>)}
      <label>Quarter<select name="quarter" value={context.quarter} onChange={update}>{[1,2,3,4].map(n=><option key={n}>{n}</option>)}</select></label>
      <label>Previous offensive call<select name="previous_play" value={context.previous_play} onChange={update}>{['none','run','pass'].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
    </div><button className="primary" disabled={busy}>Analyze situation →</button><button type="button" className="secondary" onClick={live} disabled={busy} style={{width:'100%',marginTop:10}}>Load configured live context</button><p className="footnote">Live mode requires a configured data provider. Fourth-down comparisons support the final 900 seconds.</p></form>
    <div className="nfl-output" aria-live="polite">{prediction?<><div className="card prediction-card"><div className="prediction-top"><div><p className="eyebrow">PREDICTED PLAY CALL</p><strong>{prediction.prediction.toUpperCase()}</strong></div><span className="model-label">{prediction.model}</span></div>{['pass','run'].map(call=><React.Fragment key={call}><div className="probability-row"><span>{call}</span><span>{pct(prediction[call+'_probability'])}</span></div><div className={'track '+call}><i style={{width:pct(prediction[call+'_probability'])}}/></div></React.Fragment>)}<p className="footnote">{prediction.data_source}</p></div>
      {recommendation&&<div className="card action-card"><div className="action-heading"><h3>Fourth-down comparison</h3><span>{labels[recommendation.recommendation]}</span></div><div className="actions">{recommendation.actions.map(a=><div className="action-row" key={a.action}><div><span>{labels[a.action]}</span><span>{pct(a.win_probability)}</span></div><div className="track"><i style={{width:pct(a.win_probability)}}/></div><small>95% sampling interval: {pct(a.interval95[0])}–{pct(a.interval95[1])}</small></div>)}</div><p className="footnote">Uncalibrated estimates; intervals cover simulation sampling error only.</p></div>}</>:<div className="empty">Analyze a situation to see probabilities.</div>}</div></div>
    {report&&<div className="stats"><div className="stat"><span>BASELINE HELD-OUT ACCURACY</span><strong>{pct(report.test.accuracy)}</strong><small>{report.data_source}</small></div><div className="stat"><span>TEST DATASET</span><strong>{report.test.rows.toLocaleString()} plays</strong><small>{report.splits.test.games} separate games</small></div><div className="stat"><span>MAJORITY BASELINE</span><strong>{pct(report.majority_baseline_accuracy)}</strong><small>Same test split</small></div></div>}
    <footer><p>Reproducible training, explicit data provenance.</p><a href="https://github.com/hfjkdbfjk45/Projects">Source and verification ↗</a></footer></main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
