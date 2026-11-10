#!/usr/bin/env python3
"""Test the generated file offline, or the anonymous live page with --live URL."""
from pathlib import Path
import base64,gzip,hashlib,json,math,os,re,subprocess,sys,tempfile,urllib.request
from playwright.sync_api import sync_playwright

LIVE=sys.argv[1]=='--live'
TARGET=sys.argv[2] if LIVE else Path(sys.argv[1]).resolve().as_uri()
OUT=Path(os.environ.get('RADAR_REPORT_DIR','_radar_test_results'));OUT.mkdir(exist_ok=True)
if LIVE:
    with urllib.request.urlopen(TARGET,timeout=60) as r:
        assert r.status==200
        page=r.read(60*1024*1024).decode()
else: page=Path(sys.argv[1]).read_text()
def script(name):
    found=re.findall(r'<script\b[^>]*\bid="'+name+r'"[^>]*>(.*?)</script>',page,re.S)
    assert len(found)==1,name
    return json.loads(found[0])
lib=script('recordingLibraryData')['records'];assert len(lib)==8
results={'target':TARGET,'recordings':[],'checks':[],'limitations':'Software and sample-identity tests, not clinical validation.'}
for entry in lib:
    raw=gzip.decompress(base64.b64decode(entry['data'],validate=True));src=entry['source']
    assert len(raw)==src['bytes']
    assert hashlib.sha256(raw).hexdigest()==entry['sha256']==src['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==src['git_blob_sha1']
    assert src['kind']=='github-build' and src['license']['id']=='cc-by-4.0'
    assert src['commit']=='42572b4231be0d43a9be0690c30c48ca4427a65c'
    rows=raw.decode('utf-8-sig').splitlines();assert len(rows)==1500
    for row in rows:
        parts=row.split(',');assert len(parts)==254
        assert all(math.isfinite(float(v)) for v in parts)
    results['recordings'].append({'name':src['name'],'sha256':entry['sha256'],'rows':1500,'columns':254})
results['checks'].append('Eight source-verified CSVs; exact hashes, dimensions, finite samples and reuse attribution')
assert "connect-src 'none'" in page and 'fetch(' not in page
with tempfile.TemporaryDirectory() as tmp:
    count=0
    for attrs,code in re.findall(r'<script\b([^>]*)>(.*?)</script>',page,re.S):
        assert not re.search(r'\bsrc\s*=',attrs)
        if 'application/json' in attrs:json.loads(code);continue
        p=Path(tmp)/f'{count}.js';p.write_text(code);subprocess.run(['node','--check',str(p)],check=True);count+=1
    assert count==3,count
results['checks'].append('Three executable scripts pass Node syntax checks; no external code or runtime data fetch')
with sync_playwright() as p:
    options={'headless':True,'args':['--no-sandbox']}
    if os.environ.get('CHROMIUM_PATH'):options['executable_path']=os.environ['CHROMIUM_PATH']
    browser=p.chromium.launch(**options)
    context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    tab=context.new_page();errors=[];requests=[]
    tab.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
        if LIVE and r.request.is_navigation_request() and r.request.url.split('#')[0]==TARGET.split('#')[0]:r.continue_()
        elif r.request.url.startswith(('http:','https:')):requests.append(r.request.url);r.abort()
        else:r.continue_()
    context.route('**/*',route)
    tab.goto(TARGET+'#recordings',wait_until='load',timeout=90000)
    tab.wait_for_function("window.RadarLab && RadarLab.getState().record && !document.getElementById('publicRecordingSelect').disabled",timeout=90000)
    assert tab.locator('#publicRecordingSelect option').count()==8
    for i,entry in enumerate(lib):
        tab.select_option('#publicRecordingSelect',str(i))
        tab.wait_for_function("h=>RadarLab.getState().record.sha256===h && !document.getElementById('publicRecordingSelect').disabled",arg=entry['sha256'],timeout=60000)
        metrics=tab.evaluate("()=>{let s=RadarLab.getState();return {name:s.record.source.name,n:s.record.n,fs:s.record.fs,bin:s.analysis.bin,radarRR:s.analysis.radarRR,beltRR:s.analysis.beltRR,corr:s.analysis.corr,points:s.analysis.radar.length}}")
        assert metrics['name']==entry['source']['name'] and metrics['n']==1500 and metrics['points']==1300
        assert all(math.isfinite(metrics[k]) for k in ('radarRR','beltRR','corr'))
        results['recordings'][i]['browser_metrics']=metrics
    results['checks'].append('All eight selector choices load and produce finite radar/belt metrics from 1,500 samples')
    tab.locator('#binSlider').evaluate("e=>{e.value=31;e.dispatchEvent(new Event('input',{bubbles:true}));}")
    assert tab.evaluate('RadarLab.getState().analysis.bin')==30
    tab.click('#autoBin');assert tab.evaluate('RadarLab.getState().selectionMode')=='radar-only auto'
    tab.locator('#replayToggle').scroll_into_view_if_needed();tab.click('#replayToggle')
    tab.wait_for_function('RadarLab.getPlayback().time>0.3',timeout=10000)
    tab.click('#replayToggle');assert not tab.evaluate('RadarLab.getPlayback().playing')
    tab.locator('#replaySeek').evaluate("e=>{e.value=12;e.dispatchEvent(new Event('input',{bubbles:true}));}")
    assert abs(tab.evaluate('RadarLab.getPlayback().time')-12)<0.001
    tab.select_option('#replaySpeed','4');assert tab.evaluate('RadarLab.getPlayback().speed')==4
    tab.click('#replayRestart');assert tab.evaluate('RadarLab.getPlayback().time')==0
    tab.click('#replayFull');assert tab.evaluate('RadarLab.getPlayback().showAll')
    results['checks'].append('Manual/automatic bins, playback/pause, seek, 4x speed, restart and full trace work')
    tab.select_option('#publicRecordingSelect','0')
    tab.wait_for_function("h=>RadarLab.getState().record.sha256===h && !document.getElementById('publicRecordingSelect').disabled",arg=lib[0]['sha256'])
    tab.locator('#recordings').scroll_into_view_if_needed();tab.screenshot(path=str(OUT/'recordings.png'))
    with tab.expect_download() as download:tab.click('#saveOffline')
    saved=OUT/'offline-copy.html';download.value.save_as(saved)
    offline=context.new_page();offline.on('pageerror',lambda e:errors.append(str(e)))
    offline.goto(saved.resolve().as_uri()+'#recordings',timeout=90000)
    offline.wait_for_function("window.RadarLab && RadarLab.getState().record && !document.getElementById('publicRecordingSelect').disabled",timeout=90000)
    assert offline.locator('#publicRecordingSelect option').count()==8
    offline.select_option('#publicRecordingSelect','7')
    offline.wait_for_function('h=>RadarLab.getState().record.sha256===h',arg=lib[7]['sha256'])
    results['checks'].append('Saved offline copy retains all eight choices and restores/switches data without network')
    tab.set_viewport_size({'width':390,'height':844})
    assert tab.evaluate('document.documentElement.scrollWidth <= innerWidth+2')
    results['checks'].append('Mobile-width page has no horizontal document overflow')
    assert not errors,errors
    # Ignore an optional favicon lookup, not any application dependency.
    assert all(u.endswith('/favicon.ico') for u in requests),requests
    results['checks'].append('No JavaScript errors or external application requests')
    browser.close()
results['status']='PASS'
(OUT/'results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
