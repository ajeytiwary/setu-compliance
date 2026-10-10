"""Browser smoke check for the real-document reviewer screen."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from app.pilot_keys import mint_pilot_key

base=os.environ.get('EUROSETU_TEST_BASE_URL','http://127.0.0.1:8779')
corpus=Path(os.environ['EUROSETU_PUBLIC_CORPUS_DIR'])
secret=os.environ['EUROSETU_JWT_SECRET']
contributor=mint_pilot_key(secret,'tenant-a',['pilot_contributor'],1,'real-contributor@demo.test')
verifier=mint_pilot_key(secret,'tenant-a',['verifier'],1,'real-verifier@demo.test')
errors=[];bad=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900},accept_downloads=True)
    page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.on('response',lambda r:bad.append((r.status,r.url)) if r.status>=400 else None)
    page.goto(base+'/real-dossier',wait_until='networkidle')
    page.locator('#token').fill(contributor)
    page.locator('#create').click()
    page.locator('#decision').get_by_text('BLOCKED').wait_for()
    for id in ('975352350','975352352'):
        page.locator('#file').set_input_files(str(corpus/f'scribd-{id}.pdf'))
        page.locator('#upload').click()
        page.wait_for_function('(n)=>document.querySelectorAll("#documents > details").length===n',arg=1 if id=='975352350' else 2)
    assert '1 candidate links' in page.locator('#graph').inner_text()
    assert 'SOURCE_VALUE_CONFLICT' in page.locator('#blockers').inner_text()
    page.locator('#token').fill(verifier)
    for remaining in (2,1):
        doc=page.locator('#documents > details').filter(has_text='PENDING').first
        doc.locator(':scope > summary').click()
        doc.get_by_label('Document review reason').fill('Compared the source PDF with extracted fields')
        doc.get_by_text('Approve after source check').click()
        page.wait_for_function('(n)=>[...document.querySelectorAll("#documents summary")].filter(x=>x.textContent.includes("PENDING")).length===n',arg=remaining-1)
    assert page.locator('#decision').inner_text()=='BLOCKED'
    assert 'COMPLETE_EU_SHIPMENT_AND_VERIFIED_CBAM_NOT_ESTABLISHED' in page.locator('#blockers').inner_text()
    edge=page.locator('#graph details').first
    edge.locator('summary').click()
    edge.get_by_label('Link review reason').fill('Net weight differs by 0.01 kg')
    edge.get_by_text('Reject link').click()
    page.locator('#graph summary').get_by_text('REJECTED').wait_for()
    shots=Path('docs/qa');shots.mkdir(exist_ok=True)
    page.screenshot(path=str(shots/'real-dossier-desktop.png'),full_page=True)
    desktop=page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(shots/'real-dossier-mobile.png'),full_page=True)
    mobile=page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
    print({'decision':'BLOCKED','documents':2,'edges':1,'desktop_overflow':desktop,'mobile_overflow':mobile,'console_errors':errors,'http_errors':bad})
    assert not (desktop or mobile or errors or bad)
    browser.close()
