#!/usr/bin/env python3
"""Extend the pinned radar source without altering the portfolio homepage.
Usage: python _radar_build/restore.py UPSTREAM_DIR OUTPUT_HTML [VERIFIED_LIBRARY_DIR]
Public CSV bytes stay unchanged; compression is lossless. Playback is not live acquisition.
"""
from pathlib import Path
import base64, gzip, hashlib, json, re, sys

ROOT=Path(__file__).resolve().parent
UPSTREAM=Path(sys.argv[1]).resolve()
OUTPUT=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(UPSTREAM))
import build_site as b
COMMIT='42572b4231be0d43a9be0690c30c48ca4427a65c'
NAMES=['231026_userI_tripod_01_5.csv','231026_userI_tripod_01_2.csv','231012_userK_tripod_01_4.csv','231026_userG_tripod_01_7.csv','231026_userJ_tripod_03_5.csv','231116_userJ_tripod_01_5.csv','231130_userJ_tripod_02_3.csv','240205_userI_tripod_01_1.csv']

def safe_json(value):
    return json.dumps(value,separators=(',',':'),ensure_ascii=True).replace('<','\\u003c')
def replace_once(text,old,new):
    if text.count(old)!=1: raise ValueError('Missing or ambiguous patch anchor: '+old[:100])
    return text.replace(old,new,1)
def script(page,name):
    matches=re.findall(r'<script\b[^>]*\bid="'+name+r'"[^>]*>(.*?)</script>',page,re.S)
    if len(matches)!=1: raise ValueError('Expected unique JSON script: '+name)
    return json.loads(matches[0])
def set_script(page,name,value):
    pattern=r'(<script\b[^>]*\bid="'+name+r'"[^>]*>)(.*?)(</script>)'
    page,n=re.subn(pattern,lambda m:m[1]+safe_json(value)+m[3],page,count=1,flags=re.S)
    if n!=1: raise ValueError('Missing JSON script '+name)
    return page

if len(sys.argv)>3:
    folder=Path(sys.argv[3]);sources=json.loads((folder/'manifest.json').read_text())['records']
    evidence=json.loads((folder/'license-evidence.json').read_text())
    raw_files={name:(folder/name).read_bytes() for name in NAMES}
else:
    from datetime import datetime,timezone
    license_info,evidence=b.verify_reuse('15022885')
    tree=b.get_json(f'https://api.github.com/repos/{b.REPOSITORY}/git/trees/{COMMIT}')
    entries={e['path']:e for e in tree['tree']}
    sources=[];raw_files={}
    for name in NAMES:
        url=f'https://raw.githubusercontent.com/{b.REPOSITORY}/{COMMIT}/{name}'
        raw=b.get_bytes(url);b.validate_csv(raw)
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if blob!=entries[name]['sha'] or len(raw)!=entries[name]['size']: raise ValueError('Upstream integrity mismatch: '+name)
        src={'name':name,'kind':'github-build','url':url,'repository':'https://github.com/'+b.REPOSITORY,'commit':COMMIT,'git_blob_sha1':blob,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'license':license_info,'attribution':'; '.join(license_info['creators']),'dataset_doi':'https://doi.org/10.5281/zenodo.15022885','retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'rows':1500,'columns':254,'sample_rate_hz':50,'raw_samples_modified':False,'limitations':'Selected public segments. Recorded-data replay, not live acquisition or clinical validation.'}
        raw_files[name]=raw;sources.append(src)
records=[]
for name in NAMES:
    src=next(s for s in sources if s['name']==name);raw=raw_files[name];b.validate_csv(raw)
    assert len(raw)==src['bytes'] and hashlib.sha256(raw).hexdigest()==src['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==src['git_blob_sha1']
    assert src['commit']==COMMIT and src['license']['id']=='cc-by-4.0'
    records.append({'encoding':'gzip-base64','data':base64.b64encode(gzip.compress(raw,compresslevel=6,mtime=0)).decode(),'sha256':src['sha256'],'source':src})
library={'schema':'chest-radar-public-library/1','records':records}
page=(UPSTREAM/'_site/index.html').read_text()
if 'id="recordingLibraryData"' in page: raise ValueError('Source already contains a recording library')
page=replace_once(page,'<script id="recordingData"','<script type="application/json" id="recordingLibraryData">'+safe_json(library)+'</script>\n<script id="recordingData"')
page=page.replace('Computed only after import','Measured recordings · offline replay')
page=page.replace('One public sample is embedded at build time with source revision, checksum and reuse attribution.','Eight public recordings are embedded with individual source revisions, checksums and reuse attribution.')
page=page.replace('The deployed website includes one public MobiVital recording, published numerical results and separately labeled synthetic experiments. The workbench computes from the embedded recording; it is not a rerun of either paper’s method. One segment is not a population-level validation.','This website includes eight selectable public MobiVital recordings, published numerical results and separately labeled synthetic experiments. The workbench computes from the selected recording; it is not a rerun of either paper’s method. These selected segments are not population-level validation.')
page=page.replace('Computed from the public recording embedded in this page. No CSV download or import is required.','Computed from your selected public recording. Eight CSVs are embedded; no separate download or import is required.')
page=replace_once(page,'<span class="tag">RECORDING INCLUDED</span><h3 style="margin-top:20px">Ready when the page opens.</h3><p class="small">The public recording is part of this HTML file. Its waveform loads automatically—no CSV download, account or external data connection.</p>','''<span class="tag">8 PUBLIC CSV RECORDINGS INCLUDED</span><h3 style="margin-top:20px">Choose a recording. Inspect its actual signal.</h3><label class="small" for="publicRecordingSelect">Public recording</label><select id="publicRecordingSelect" aria-label="Choose bundled public CSV recording" style="width:100%;margin:10px 0 16px" disabled></select><p class="small">Switch between eight original 30-second MobiVital recordings. All CSVs are embedded in this page; no separate downloads, account or data connection are needed.</p>''')
page=page.replace('The offline copy contains the recording, graphs and all four physics experiments. External source links are optional.','The offline copy keeps all eight selectable recordings, the current selection, graphs and all four physics experiments.')
page=page.replace('These plots use the same imported recording.','These plots use the selected recording. Diagnostics and rate estimates use the full 26-second retained window.')
page=page.replace('No imported human waveform','Choose a public recording to inspect its waveform')
controls='''<div class="controls no-print" style="margin-top:14px;gap:10px"><button id="replayToggle" class="primary" disabled>Play recording</button><button id="replayRestart" disabled>Restart</button><button id="replayFull" aria-pressed="true" disabled>Show full trace</button><label class="small" for="replaySpeed">Speed</label><select id="replaySpeed" style="width:auto;min-width:8rem" disabled><option value="0.5">0.5×</option><option value="1" selected>1× actual timing</option><option value="2">2×</option><option value="4">4×</option></select><span id="replayTime" class="mono small">0.0 / 30.0 s</span></div><div class="controls no-print"><label class="small" for="replaySeek">Seek</label><input type="range" id="replaySeek" aria-label="Seek through recorded samples" min="0" max="30" step="0.02" value="0" style="flex:1;min-width:140px" disabled></div><p class="tiny"><strong id="replayState">Full recording overview</strong> · Playback of measured data, not a live sensor. Traces are processed offline. Rate and correlation values below use the full retained window, not only the revealed samples.</p>'''
page,n=re.subn(r'(<canvas\b[^>]*\bid="wavePlot"[^>]*>.*?</canvas>)',lambda m:m[1]+controls,page,count=1,flags=re.S)
assert n==1
page=replace_once(page,"function buttons(){['binSlider','autoBin','saveOffline','saveAnalysis','clearRecording'].forEach(id=>$(id).disabled=!record||busy);$('fileIn').disabled=busy;}","function buttons(){['binSlider','autoBin','saveOffline','saveAnalysis','clearRecording','replayToggle','replayRestart','replayFull','replaySeek','replaySpeed'].forEach(id=>$(id).disabled=!record||busy);$('fileIn').disabled=busy;$('publicRecordingSelect').disabled=busy;}")
page=replace_once(page,"renderAnalysis();buttons();$('signalDetails').open=true;return analysis;}","resetPlayback(true);renderAnalysis();buttons();updateRecordingUI();$('signalDetails').open=true;return analysis;}")
page=replace_once(page,"$('fileIn').onchange=async e=>{const f=e.target.files[0];if(!f)return;busy=true;","$('fileIn').onchange=async e=>{const f=e.target.files[0];if(!f)return;pausePlayback();busy=true;")
marker="(async()=>{bars('bpm');busy=true;buttons();renderAnalysis();try{await restoreBundled();}"
page=replace_once(page,marker,(ROOT/'recording-controls.js').read_text()+'\n'+marker)
start=page.index('function wavePlot(a){');end=page.index('\nfunction iqPlot(a)',start)
page=page[:start]+'''function wavePlot(a){
const {ctx,w,h}=initCanvas('wavePlot'),m=axes(ctx,w,h,'recording time (s)','normalized amplitude');
const pw=w-m.l-m.r,ph=h-m.t-m.b;let lim=3;
for(const sig of [a.radarNorm,a.beltNorm])if(sig)for(const v of sig)lim=Math.max(lim,Math.abs(v));
lim=Math.min(8,Math.ceil(lim));const x=t=>m.l+t/30*pw,y=v=>h-m.b-(v+lim)/(2*lim)*ph;
ctx.fillStyle='#171717';ctx.fillRect(x(0),m.t,x(2)-x(0),ph);ctx.fillRect(x(28),m.t,x(30)-x(28),ph);
ctx.strokeStyle='#333';ctx.beginPath();ctx.moveTo(m.l,y(0));ctx.lineTo(w-m.r,y(0));ctx.stroke();
ctx.fillStyle='#aaa';ctx.font='14px system-ui';for(const t of [0,5,10,15,20,25,30])ctx.fillText(String(t),x(t)-7,h-m.b+22);
ctx.fillText('+'+lim,13,m.t+10);ctx.fillText('−'+lim,13,h-m.b);
ctx.save();ctx.beginPath();ctx.rect(m.l,m.t,pw,ph);ctx.clip();
const count=playback.showAll?a.radar.length:Math.max(0,Math.min(a.radar.length,Math.floor((playback.time-2)*50)+1));
pathLine(ctx,a.radarNorm?a.radarNorm.subarray(0,count):null,i=>x(2+i/50),y,colors.fg);
pathLine(ctx,a.beltNorm?a.beltNorm.subarray(0,count):null,i=>x(2+i/50),y,colors.red,[7,5]);
if(!playback.showAll){ctx.strokeStyle='#aaa';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x(playback.time),m.t);ctx.lineTo(x(playback.time),h-m.b);ctx.stroke();
const sample=Math.floor((playback.time-2)*50);if(sample>=0&&sample<a.radar.length){for(const [sig,col]of[[a.radarNorm,colors.fg],[a.beltNorm,colors.red]])if(sig){ctx.fillStyle=col;ctx.beginPath();ctx.arc(x(2+sample/50),y(sig[sample]),3,0,2*Math.PI);ctx.fill();}}
}
ctx.restore();ctx.fillStyle='#aaa';ctx.font='12px system-ui';ctx.fillText('2 s trimmed at each edge · full-segment offline filtering',m.l+8,m.t+14);
if(!a.radarNorm||!a.beltNorm){ctx.fillStyle='#bbb';ctx.fillText('Constant channel: corresponding metric is unavailable.',m.l+8,m.t+31);}
}'''+page[end:]
# Store each original recording once, and save only the selected public checksum.
initial=script(page,'recordingData')
assert initial['sha256'] in [r['sha256'] for r in records]
page=set_script(page,'recordingData',{'schema':'chest-radar-selection/1','librarySha256':initial['sha256'],'sha256':initial['sha256'],'selectedBin':initial.get('selectedBin')})
start=page.index('async function restoreBundled(){');end=page.index('\n// Replay measured samples;',start)
page=page[:start]+'''async function restoreBundled(){
const stored=JSON.parse($('recordingData').textContent);if(!stored)throw Error('Embedded recording selection is missing.');
if(stored.rawText){if(!stored.sha256||await sha256(stored.rawText)!==stored.sha256)throw Error('Saved checksum mismatch.');return loadRecord(stored.rawText,stored.source,stored.selectedBin);}
const entry=recordingLibrary.records.find(e=>e.sha256===(stored.librarySha256||stored.sha256));
if(!entry)throw Error('Selected recording is missing from the library.');
status('Opening the embedded public recording. No internet connection is needed.');
return loadRecord(await unpackRecording(entry),entry.source,stored.selectedBin);
}
'''+page[end:]
start=page.index("$('saveOffline').onclick=");end=page.index('// ----- Plots:',start)
page=page[:start]+'''$('saveOffline').onclick=()=>{if(!record)return;const root=document.documentElement.cloneNode(true);const bundled=recordingLibrary.records.find(e=>e.sha256===record.sha256);const payload=bundled?{schema:'chest-radar-selection/1',librarySha256:record.sha256,sha256:record.sha256,selectedBin:analysis.bin}:{rawText:record.rawText,source:record.source,selectedBin:analysis.bin,sha256:record.sha256};root.querySelector('#recordingData').textContent=JSON.stringify(payload).replace(/</g,'\\\\u003c');const manifest=JSON.parse(root.querySelector('#sourceData').textContent);manifest.raw_human_recordings_bundled=record.source.kind==='github-build';manifest.bundled_recording=record.source;root.querySelector('#sourceData').textContent=JSON.stringify(manifest).replace(/</g,'\\\\u003c');root.querySelectorAll('canvas').forEach(c=>{c.width=c.width;});download('chest-radar-recording-library.html','<!doctype html>\\n'+root.outerHTML,'text/html');};
'''+page[end:]
meta=script(page,'sourceData');meta['bundled_recording_count']=8;meta['bundled_recordings']=[r['source'] for r in records];meta['playback']='Recorded samples replayed at adjustable speed; full-window offline signal processing.'
page=set_script(page,'sourceData',meta)
assert 'fetch(' not in page and "connect-src 'none'" in page
OUTPUT.parent.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(page)
data=OUTPUT.parent/'data';data.mkdir(exist_ok=True)
(data/'manifest.json').write_text(json.dumps({'schema':'chest-radar-public-library/1','records':[r['source'] for r in records]},indent=2))
(data/'license-evidence.json').write_text(json.dumps(evidence,indent=2))
(OUTPUT.parent/'ATTRIBUTION.md').write_text('# Recording attribution\n\nOriginal public MobiVital CSV recordings, UCLA NESL.\n\n'+records[0]['source']['attribution']+'\n\nDataset: https://doi.org/10.5281/zenodo.15022885\n\nSource: https://github.com/nesl/MobiVital-dataset/tree/'+COMMIT+'\n\nLicense: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/ .\n\nOriginal sample bytes are unchanged and losslessly compressed. Signal-processing displays and playback controls are separate teaching implementations. Project: Allan Gramajo and Alan Acosta, equal contributors.\n')
print('BUILT',OUTPUT,OUTPUT.stat().st_size,'bytes; all eight verified original recordings embedded')
