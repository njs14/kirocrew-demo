async page => {
  await page.getByRole('heading',{name:'Direct MCP/AWS probe',exact:true}).waitFor();
  if((await page.locator('#run-status').innerText())!=='Ready')throw new Error('Fresh operator screen required');
  const startedAt=new Date().toISOString(),marks=[];
  await page.screencast.start({path:'recordings/20260913/raw/05-direct-mcp-aws.webm',size:{width:1600,height:1000}});
  const start=Date.now(),mark=label=>marks.push({time:(Date.now()-start)/1000,label});
  try{
    mark('Direct probe scope and fixed outcomes');
    await page.waitForTimeout(3000);
    await page.getByRole('button',{name:'Start bounded probe',exact:true}).click();
    mark('Start the real bounded command');
    await page.locator('#run-status').filter({hasText:/Checks passed|Run failed/}).waitFor({timeout:90000});
    const outcome=await page.locator('#run-status').innerText();
    mark('Read the completed command outcomes');
    await page.waitForTimeout(9000);
    if(outcome==='Checks passed'){
      await page.getByRole('button',{name:'Inspect receipt fields',exact:true}).click();
      await page.locator('#receipt-json').scrollIntoViewIfNeeded();
      mark('Inspect the fresh receipt fields');
      await page.waitForTimeout(6000);
      await page.getByRole('button',{name:'Inspect receipt fields',exact:true}).click();
      await page.getByRole('heading',{name:'Direct MCP/AWS probe',exact:true}).scrollIntoViewIfNeeded();
      mark('Return to the three outcomes');
      await page.waitForTimeout(3500);
    }
    return {scene:'direct-mcp-aws',startedAt,endedAt:new Date().toISOString(),marks,outcome,artifactUrl:await page.locator('#receipt-download').getAttribute('href'),nativeBackendProof:false};
  }finally{await page.screencast.stop();}
}
