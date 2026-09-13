async page => {
  await page.goto('http://127.0.0.1:5605/#slide-3');
  await page.setViewportSize({ width: 1600, height: 1000 });
  const expand = page.getByRole('button', { name: 'Expand image: Accepted September 11 endpoint-control reference. One enclosure preserved. Broader capabilities require their own verification.', exact: true });
  await expand.waitFor({ state: 'visible' });
  const marks = [];
  const startedAt = new Date().toISOString();
  const startedMs = Date.now();
  const mark = (label) => marks.push({ label, at: new Date().toISOString(), seconds: (Date.now() - startedMs) / 1000 });
  await page.screencast.start({ path: '/Users/noahsutter/git-projects/kirocrew-demo/recordings/20260913/raw/01-endpoint-reference.webm', size: { width: 1600, height: 1000 } });
  mark('capture-start');
  await page.screencast.showChapter('Architecture reference', {
    description: 'The accepted endpoint-control enclosure. Reference and recorded evidence; broader enforcement remains unverified.',
    duration: 2200,
  });
  mark('reference-slide');
  await page.waitForTimeout(3000);
  await expand.hover();
  await page.waitForTimeout(650);
  await expand.click();
  mark('expand-reference');
  await page.getByRole('heading', { name: 'Original evidence image', exact: true }).waitFor({ state: 'visible' });
  await page.waitForTimeout(8500);
  await page.getByRole('button', { name: 'Close', exact: true }).hover();
  await page.waitForTimeout(650);
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  mark('close-reference');
  await page.waitForTimeout(2200);
  await page.getByRole('button', { name: 'Next slide', exact: true }).hover();
  await page.waitForTimeout(650);
  await page.getByRole('button', { name: 'Next slide', exact: true }).click();
  mark('recorded-arm-placement');
  await page.getByRole('heading', { name: 'ARM execution in us-east-1', exact: true }).waitFor({ state: 'visible' });
  await page.waitForTimeout(6500);
  mark('capture-end');
  await page.screencast.stop();
  return {
    scene: '01-endpoint-reference',
    startedAt,
    endedAt: new Date().toISOString(),
    marks,
    rawPath: 'recordings/20260913/raw/01-endpoint-reference.webm',
    viewport: { width: 1600, height: 1000 },
    sourceUrl: 'http://127.0.0.1:5605/#slide-3',
    endUrl: page.url(),
    title: await page.title(),
    browser: await page.evaluate(() => navigator.userAgent),
    scope: 'Actual browser navigation of the accepted presentation, September 11 architecture reference and September 13 recorded ARM evidence. Does not verify current infrastructure, live controls, or native Kiro CLI enforcement.',
    mutations: 'None: source document and image bytes unchanged; navigated existing slide and image-dialog controls only.',
  };
}
