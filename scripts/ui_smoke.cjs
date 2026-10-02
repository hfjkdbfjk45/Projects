const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const path=require('node:path');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function healthy(url){for(let i=0;i<80;i++){try{const r=await fetch(url);if(r.ok)return;}catch{}await sleep(250);}throw Error('Server did not become healthy: '+url);}
(async()=>{
  const py=process.env.PYTHON||'python3';
  const demo=spawn(py,['launch.py'],{cwd:root,stdio:'inherit'});
  const flask=spawn(py,['api.py'],{cwd:path.join(root,'projects/nfl-play-predictor'),stdio:'inherit'});
  let browser;
  try{
    await healthy('http://127.0.0.1:8000/health');await healthy('http://127.0.0.1:5000/health');
    browser=await chromium.launch({headless:true});
    const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8000');
    await page.getByRole('button',{name:'Validate trade'}).click();
    await page.getByText('Valid under implemented rules',{exact:false}).waitFor();
    fs.mkdirSync(path.join(root,'docs/screenshots'),{recursive:true});
    await page.screenshot({path:path.join(root,'docs/screenshots/nba.png'),fullPage:true});
    await page.getByRole('button',{name:'Clear',exact:true}).click();
    await page.getByRole('button',{name:'Trade Marcus Cole',exact:true}).click();
    await page.getByRole('button',{name:'Trade Noah Price',exact:true}).click();
    await page.getByRole('button',{name:'Validate trade'}).click();
    await page.getByText('Trade fails implemented checks',{exact:false}).waitFor();
    await page.locator('[data-tab=f1]').click();
    await page.getByText('Dry-race lap trace',{exact:true}).waitFor();
    await page.screenshot({path:path.join(root,'docs/screenshots/f1.png'),fullPage:true});
    await page.locator('[data-tab=nfl]').click();
    await page.getByText('Fourth-down comparison',{exact:true}).waitFor();
    await page.screenshot({path:path.join(root,'docs/screenshots/nfl.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,'Mobile horizontal overflow');
    await page.screenshot({path:path.join(root,'docs/screenshots/mobile.png'),fullPage:true});
    await page.goto('http://127.0.0.1:5000');
    await page.getByRole('button',{name:'Analyze situation'}).click();
    await page.getByText('Fourth-down comparison',{exact:true}).waitFor();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,'React mobile horizontal overflow');
    assert.deepEqual(errors,[],'Browser errors');
    console.log('Browser flows passed: valid trade, invalid trade, F1, NFL, mobile, React/Flask');
  }finally{
    if(browser)await browser.close();demo.kill();flask.kill();
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
