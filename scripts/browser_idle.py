"""Browser acceptance helper; never changes application release guards.

Playwright fast_forward simulates a clock jump and fires due timers at most once.
Idle-reading checks instead drain queued rendering, then run the normal callbacks.
https://playwright.dev/python/docs/api/class-clock#clock-run-for
"""
import json

def observe_activity(page):
    page.add_init_script("""(()=>{
      window.__paperTestActivity=[];
      for(const type of ['pointerdown','keydown','input','scroll'])
        document.addEventListener(type,event=>{
          const rows=window.__paperTestActivity;
          rows.push({type,at:Date.now(),tag:event.target?.tagName||'',id:event.target?.id||'',scrollY});
          if(rows.length>12)rows.shift();
        },{capture:true,passive:true});
    })();""")

def release_snapshot(page):
    return page.evaluate("""()=>({
      safe:PaperRelease.safeToReload(),
      walkthroughBusy:!!window.PaperWalkthrough?.isBusy?.(),
      rdaBusy:!!window.PaperRDA?.isBusy?.(),
      activeElement:{tag:document.activeElement?.tagName,id:document.activeElement?.id},
      scrollY,now:Date.now(),recentActivity:window.__paperTestActivity||[]
    })""")

def after_reading_idle(page):
    page.evaluate("""()=>{
      window.__paperTestFramesReady=false;
      requestAnimationFrame(()=>requestAnimationFrame(()=>{window.__paperTestFramesReady=true;}));
    }""")
    page.clock.run_for(250)
    assert page.evaluate('window.__paperTestFramesReady===true'), 'Queued animation frames did not settle'
    page.clock.run_for(13000)
    state=release_snapshot(page)
    print('IDLE_GUARD '+json.dumps(state,ensure_ascii=False),flush=True)
    return state['safe']
