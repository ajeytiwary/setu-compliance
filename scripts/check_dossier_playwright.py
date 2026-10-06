import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.pilot_keys import mint_pilot_key

secret=os.environ['EUROSETU_JWT_SECRET']
base=os.environ.get('EUROSETU_TEST_BASE_URL','http://127.0.0.1:8779')
contributor=mint_pilot_key(secret,'tenant-a',['pilot_contributor'],1,'contributor@demo.test')
verifier=mint_pilot_key(secret,'tenant-a',['verifier'],1,'verifier@demo.test')
shots=ROOT/'docs'/'qa'
shots.mkdir(parents=True,exist_ok=True)
errors=[];bad=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1,accept_downloads=True)
    page.on('console',lambda msg: errors.append(msg.text) if msg.type=='error' else None)
    page.on('pageerror',lambda err: errors.append(str(err)))
    page.on('response',lambda r: bad.append((r.status,r.url)) if r.status>=400 else None)
    page.goto(base+'/dossier-demo',wait_until='networkidle')
    page.locator('#token').fill(contributor)
    page.locator('#create').click()
    page.locator('#decision').get_by_text('BLOCKED').wait_for(timeout=15000)
    page.screenshot(path=str(shots/'dossier-blocked.png'),full_page=True)
    print('initial',page.locator('#decision').inner_text(),'blockers',page.locator('#blockers p').all_inner_texts())
    first=page.locator('#documents details').first
    first.locator('summary').click()
    with page.expect_download() as download_info:
        first.locator('button').filter(has_text='Download source PDF').click()
    download=download_info.value
    print('download',download.suggested_filename)
    page.locator('#token').fill(verifier)
    for remaining in range(7,0,-1):
        pending=page.locator('#documents details').filter(has=page.locator('summary')).filter(has_text='PENDING').first
        if not pending.evaluate('(x) => x.open'): pending.locator('summary').click()
        pending.locator('button').filter(has_text='Approve source version').click()
        page.wait_for_function('(n) => [...document.querySelectorAll("#documents summary")].filter(x => x.textContent.includes("PENDING")).length === n',arg=remaining-1)
    print('reviewed',page.locator('#decision').inner_text(),'blockers',page.locator('#blockers p').all_inner_texts())
    page.locator('#token').fill(contributor)
    page.locator('#fix-mtc').click();page.wait_for_function('() => [...document.querySelectorAll("#documents summary")].some(x => x.textContent.includes("MTC · v2"))')
    page.locator('#fix-cbam').click();page.wait_for_function('() => [...document.querySelectorAll("#documents summary")].some(x => x.textContent.includes("CBAM_INSTALLATION · v2"))')
    page.locator('#token').fill(verifier)
    for remaining in range(2,0,-1):
        pending=page.locator('#documents details').filter(has_text='PENDING').first
        if not pending.evaluate('(x) => x.open'): pending.locator('summary').click()
        pending.locator('button').filter(has_text='Approve source version').click()
        page.wait_for_function('(n) => [...document.querySelectorAll("#documents summary")].filter(x => x.textContent.includes("PENDING")).length === n',arg=remaining-1)
    page.locator('#decision').get_by_text('READY').wait_for(timeout=15000)
    page.screenshot(path=str(shots/'dossier-ready.png'),full_page=True)
    print('final',page.locator('#decision').inner_text(),'calc',page.locator('#calc').inner_text())
    print('desktop_overflow',page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(shots/'dossier-mobile.png'),full_page=True)
    print('mobile_overflow',page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
    print('console_errors',errors)
    print('http_errors',bad)
    browser.close()
