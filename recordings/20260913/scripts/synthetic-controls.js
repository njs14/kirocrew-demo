async page => {
  await page.getByRole('heading',{name:'Local synthetic control rehearsal',exact:true}).waitFor();
  if((await page.locator('#run-status').innerText())!=='Ready')throw new Error('Fresh rehearsal state required');
  const startedAt=new Date().toISOString(),marks=[];
  await page.screencast.start({path:'recordings/20260913/raw/06-synthetic-controls.webm',size:{width:1600,height:1000}});
  const start=Date.now(),mark=label=>marks.push({time:(Date.now()-start)/1000,label});
  try{
    mark('Read the isolated synthetic scope');
    await page.waitForTimeout(3500);
    await page.getByRole('button',{name:'Start synthetic rehearsal',exact:true}).click();
    mark('Run the frozen control rehearsal');
    await page.locator('#run-status').filter({hasText:/Checks passed|Run failed/}).waitFor({timeout:90000});
    const outcome=await page.locator('#run-status').innerText();
    mark('Read the recorded control outcomes');
    await page.waitForTimeout(8500);
    if(outcome==='Checks passed'){
      await page.getByRole('button',{name:'Inspect receipt fields',exact:true}).click();
      await page.locator('#receipt-json').scrollIntoViewIfNeeded();
      mark('Inspect synthetic approval and SEL receipt fields');
      await page.waitForTimeout(6500);
      await page.getByRole('button',{name:'Inspect receipt fields',exact:true}).click();
      await page.getByRole('heading',{name:'Local synthetic control rehearsal',exact:true}).scrollIntoViewIfNeeded();
      mark('Return to the rehearsal results');
      await page.waitForTimeout(3000);
    }
    return {scene:'synthetic-controls',startedAt,endedAt:new Date().toISOString(),marks,outcome,artifactUrl:await page.locator('#receipt-download').getAttribute('href'),nativeBackendProof:false};
  }finally{await page.screencast.stop();}
}
