async page => {
  await page.getByRole('heading', { name: 'Client and server, in one view' }).waitFor();
  const startedAt = new Date().toISOString();
  const marks = [];
  await page.screencast.start({path:'recordings/20260913/raw/03-client-server-telemetry.webm',size:{width:1600,height:1000}});
  const start = Date.now();
  const mark = label => marks.push({time:(Date.now()-start)/1000,label});
  try {
    mark('Both sources are current');
    await page.waitForTimeout(2500);
    await page.getByRole('button',{name:'Refresh',exact:true}).click();
    mark('Refresh the stored collector samples');
    await page.waitForTimeout(2200);
    await page.getByRole('region',{name:'Client telemetry',exact:true}).getByText('More measurements',{exact:true}).click();
    mark('Inspect Mac process measurements');
    await page.waitForTimeout(3500);
    await page.getByRole('region',{name:'Client telemetry',exact:true}).getByText('More measurements',{exact:true}).click();
    await page.getByRole('region',{name:'Server telemetry',exact:true}).getByText('More measurements',{exact:true}).click();
    mark('Inspect EC2 service measurements');
    await page.waitForTimeout(3500);
    await page.getByRole('region',{name:'Server telemetry',exact:true}).getByText('More measurements',{exact:true}).click();
    await page.getByRole('button',{name:'Client',exact:true}).click();
    mark('Filter collection logs to the client');
    await page.waitForTimeout(3500);
    await page.getByRole('button',{name:'Server',exact:true}).click();
    mark('Filter collection logs to the server');
    await page.waitForTimeout(3500);
    await page.getByRole('button',{name:'All',exact:true}).click();
    mark('Restore all collection events');
    await page.waitForTimeout(2500);
    return {scene:'client-server-telemetry',startedAt,endedAt:new Date().toISOString(),marks,recordedPage:page.url(),nativeBackendProof:false};
  } finally { await page.screencast.stop(); }
}
