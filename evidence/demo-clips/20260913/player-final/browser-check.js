async (page) => {
  const checks = [];
  const scenes = [];
  const expect = (condition, label) => { if (!condition) throw new Error(label); checks.push(label); };
  const errors = [];
  page.on("pageerror", error => errors.push(String(error)));
  await page.setViewportSize({ width: 1440, height: 1000 });
  expect(await page.evaluate(() => window.presentationApi.count) === 20, "Twenty-slide edition");
  for (let index = 14; index < 20; index++) {
    await page.evaluate(i => window.presentationApi.goTo(i), index);
    const slide = page.locator(`#slide-${index + 1}`);
    const video = slide.locator("video");
    await video.evaluate(el => new Promise((resolve, reject) => {
      if (el.readyState >= 2) return resolve();
      el.addEventListener("loadeddata", resolve, { once: true });
      el.addEventListener("error", () => reject(new Error("Video failed to load")), { once: true });
    }));
    const scene = await slide.evaluate(el => ({id: el.dataset.sceneId, title: el.dataset.title}));
    scene.metadata = await video.evaluate(el => ({duration: el.duration, width: el.videoWidth, height: el.videoHeight, muted: el.muted, controls: el.controls, playsInline: el.playsInline}));
    expect(scene.metadata.duration > 0 && scene.metadata.width === 1600 && scene.metadata.height === 1000 && scene.metadata.muted && scene.metadata.controls && scene.metadata.playsInline, `${scene.id}: decoded metadata and muted native controls`);
    await slide.getByRole("button", { name: "Replay", exact: true }).click();
    await page.waitForFunction(id => {const v = document.querySelector(`#${id} video`); return !v.paused && v.currentTime > 0.15;}, `slide-${index + 1}`);
    expect(await video.evaluate(el => !el.paused), `${scene.id}: playback advances`);
    const cueButtons = slide.locator("[data-cue-time]");
    const cueCount = await cueButtons.count();
    scene.cues = [];
    for (let cueIndex = 0; cueIndex < cueCount; cueIndex++) {
      const cue = cueButtons.nth(cueIndex);
      const expectedTime = Number(await cue.getAttribute("data-cue-time"));
      const label = await cue.getAttribute("data-cue-label");
      await cue.click();
      await page.waitForFunction(({id,time}) => {const v=document.querySelector(`#${id} video`);return !v.seeking && v.paused && Math.abs(v.currentTime-time)<0.05;}, {id: `slide-${index+1}`,time:expectedTime});
      expect(await slide.locator(".demo-cue-detail strong").textContent() === label, `${scene.id}: cue ${cueIndex + 1} seeks, pauses and updates details`);
      scene.cues.push({label,time:expectedTime,evidence:await slide.locator(".demo-cue-detail a").getAttribute("href")});
      if (scene.id === "client-server-telemetry" && cueIndex === 3) await page.screenshot({path:"evidence/demo-clips/20260913/player-final/desktop-telemetry.png"});
      if (scene.id === "direct-mcp-aws" && cueIndex === 2) await page.screenshot({path:"evidence/demo-clips/20260913/player-final/desktop-direct-result.png"});
    }
    scene.desktop = await slide.evaluate(el => {
      const bounds = el.getBoundingClientRect();
      const screen = el.querySelector("video").getBoundingClientRect();
      const footer = el.querySelector(".slide-footer").getBoundingClientRect();
      const controls = el.querySelector(".demo-controls").getBoundingClientRect();
      return {width:bounds.width,height:bounds.height,scrollWidth:el.scrollWidth,scrollHeight:el.scrollHeight,videoWidth:screen.width,videoHeight:screen.height,controlsBottom:controls.bottom,footerTop:footer.top,overflow:el.scrollHeight>el.clientHeight || el.scrollWidth>el.clientWidth,controlsOverlapFooter:controls.bottom>footer.top};
    });
    expect(!scene.desktop.overflow && !scene.desktop.controlsOverlapFooter && scene.desktop.videoWidth > 800 && scene.desktop.videoHeight > 400, `${scene.id}: desktop fit and clear video area`);
    await slide.getByRole("button", { name:"Replay",exact:true }).click();
    await page.waitForFunction(id=>!document.querySelector(`#${id} video`).paused,`slide-${index+1}`);
    await page.getByRole("button", {name:"Notes",exact:true}).click();
    expect(await video.evaluate(el=>el.paused),`${scene.id}: notes dialog pauses playback`);
    await page.locator("#notes-dialog [data-close]").click();
    await slide.getByRole("button", {name:"Replay",exact:true}).click();
    await page.waitForFunction(id=>!document.querySelector(`#${id} video`).paused,`slide-${index+1}`);
    await page.getByRole("button", {name:"Previous slide",exact:true}).click();
    expect(await video.evaluate(el=>el.paused),`${scene.id}: leaving the slide pauses playback`);
    scenes.push(scene);
  }
  await page.evaluate(() => window.presentationApi.goTo(14));
  let slide = page.locator("#slide-15");
  let video = slide.locator("video");
  await slide.getByRole("checkbox",{name:"Pause at chapters"}).check();
  await slide.getByRole("button",{name:"Replay",exact:true}).click();
  await page.waitForFunction(()=>{const v=document.querySelector("#slide-15 video");return v.paused && Math.abs(v.currentTime-2.7)<0.05;},null,{timeout:10000});
  expect((await slide.locator(".demo-status").textContent()).includes("Guided pause"),"Guided playback pauses at 2.7 seconds");
  await slide.getByRole("checkbox",{name:"Pause at chapters"}).uncheck();
  await slide.getByRole("button",{name:"Replay",exact:true}).click();
  await page.getByRole("button",{name:"Slides",exact:true}).click();
  expect(await video.evaluate(el=>el.paused),"Overview dialog pauses playback");
  await page.locator("#overview-dialog [data-close]").click();
  await video.focus();
  await page.keyboard.press("ArrowRight");
  expect(await page.evaluate(()=>window.presentationApi.current())===14,"Video keyboard focus does not navigate the deck");
  await slide.locator("h2").click();
  await page.keyboard.press("ArrowRight");
  expect(await page.evaluate(()=>window.presentationApi.current())===15,"ArrowRight outside media controls advances slides");
  for (let index=14;index<20;index++) {
    await page.setViewportSize({width:390,height:844});
    await page.evaluate(i=>window.presentationApi.goTo(i),index);
    slide = page.locator(`#slide-${index+1}`);
    await slide.locator("[data-cue-time]").first().click();
    const mobile = await slide.evaluate(el=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,targets:Array.from(el.querySelectorAll(".demo-cues button")).map(button=>button.getBoundingClientRect().height)}));
    expect(mobile.documentWidth<=mobile.width && mobile.targets.every(height=>height>=44),`${scenes[index-14].id}: mobile fit and target sizes`);
    scenes[index-14].mobile=mobile;
    if(index===16) await page.screenshot({path:"evidence/demo-clips/20260913/player-final/mobile-telemetry.png",fullPage:true});
  }
  expect(errors.length===0,"No uncaught page errors");
  return {scope:"Browser playback and controls of the recorded-demo edition; no live portal or probe execution",passed:true,checks,scenes,uncaughtPageErrors:errors};
}
