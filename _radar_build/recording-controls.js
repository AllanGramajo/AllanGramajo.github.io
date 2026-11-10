// Replay measured samples; the full-window signal processing stays offline/noncausal.
const playback={time:0,playing:false,showAll:true,last:0,speed:1,raf:0};
const recordingLibrary=JSON.parse($('recordingLibraryData').textContent);
const publicSelect=$('publicRecordingSelect');
publicSelect.replaceChildren();
for(let i=0;i<recordingLibrary.records.length;i++){
  const entry=recordingLibrary.records[i],option=document.createElement('option');
  option.value=String(i);option.textContent=entry.source.name;publicSelect.append(option);
}
function updateRecordingUI(){
  if(!record)return;
  const idx=recordingLibrary.records.findIndex(e=>e.sha256===record.sha256);
  publicSelect.value=idx>=0?String(idx):'';
  const src=record.source,license=src.license||{};
  $('embeddedCredit').textContent=src.kind==='github-build'
    ?`${src.name}. ${src.attribution||'MobiVital authors'}. ${license.name||license.id||'See provenance'}. Unmodified recorded samples; separate teaching-baseline analysis.`
    :`${src.name} · Local import. Format checked; human origin is not independently verified.`;
  updatePlaybackUI();
}
function updatePlaybackUI(){
  $('replayTime').textContent=`${playback.time.toFixed(1)} / 30.0 s`;
  $('replaySeek').value=String(playback.time);
  $('replayToggle').textContent=playback.playing?'Pause':'Play recording';
  $('replayToggle').setAttribute('aria-pressed',String(playback.playing));
  $('replayFull').setAttribute('aria-pressed',String(playback.showAll));
  $('replayState').textContent=playback.showAll?'Full recording overview':playback.playing?'Playing recorded samples':playback.time>=30?'End of recording':'Playback paused';
}
function pausePlayback(){playback.playing=false;cancelAnimationFrame(playback.raf);playback.raf=0;updatePlaybackUI();}
function resetPlayback(showAll=false){pausePlayback();playback.time=0;playback.showAll=showAll;updatePlaybackUI();}
function redrawPlayback(){if(record&&analysis)wavePlot(analysis);updatePlaybackUI();}
function playbackFrame(now){
  if(!playback.playing)return;
  playback.time=Math.min(30,playback.time+(now-playback.last)/1000*playback.speed);
  playback.last=now;redrawPlayback();
  if(playback.time>=30){pausePlayback();return;}
  playback.raf=requestAnimationFrame(playbackFrame);
}
function playRecording(){
  if(!record||busy)return;
  if(playback.showAll||playback.time>=30)playback.time=0;
  playback.showAll=false;playback.playing=true;playback.last=performance.now();
  updatePlaybackUI();cancelAnimationFrame(playback.raf);playback.raf=requestAnimationFrame(playbackFrame);
}
$('replayToggle').onclick=()=>playback.playing?pausePlayback():playRecording();
$('replayRestart').onclick=()=>{resetPlayback(false);redrawPlayback();};
$('replayFull').onclick=()=>{pausePlayback();playback.showAll=true;redrawPlayback();};
$('replaySeek').oninput=e=>{const t=Number(e.target.value);pausePlayback();playback.showAll=false;playback.time=t;redrawPlayback();};
$('replaySpeed').onchange=e=>{playback.speed=Number(e.target.value);playback.last=performance.now();};
document.addEventListener('visibilitychange',()=>{if(document.hidden&&playback.playing)pausePlayback();});
new IntersectionObserver(entries=>{if(!entries[0].isIntersecting&&playback.playing)pausePlayback();},{threshold:0}).observe($('recordings'));
async function unpackRecording(entry){
  if(!entry||entry.encoding!=='gzip-base64')throw Error('Unknown recording-library encoding.');
  if(typeof DecompressionStream==='undefined')throw Error('Open this website in a current Chrome, Edge, Firefox or Safari browser to unpack the recordings.');
  const binary=atob(entry.data),bytes=new Uint8Array(binary.length);
  for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
  const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  const raw=await new Response(stream).arrayBuffer();
  if(raw.byteLength!==entry.source.bytes||raw.byteLength>32*1024*1024)throw Error('Embedded file size does not match its source manifest.');
  const text=decodeCSV(raw),hash=await sha256(text);
  if(hash!==entry.sha256||hash!==entry.source.sha256)throw Error('Embedded recording checksum does not match.');
  return text;
}
async function selectPublicRecording(index){
  const entry=recordingLibrary.records[index];if(!entry||busy)return;
  const previous=record?recordingLibrary.records.findIndex(e=>e.sha256===record.sha256):-1;
  pausePlayback();busy=true;buttons();
  status(`Opening bundled public recording ${index+1}/${recordingLibrary.records.length}: ${entry.source.name}. No network request.`);
  try{const text=await unpackRecording(entry);await loadRecord(text,entry.source);}
  catch(e){publicSelect.value=previous>=0?String(previous):'';status(`Recording rejected: ${e.message} The previous valid recording is retained.`,true);}
  finally{busy=false;buttons();}
}
publicSelect.onchange=e=>selectPublicRecording(Number(e.target.value));
window.RadarLab.selectPublicRecording=selectPublicRecording;
window.RadarLab.getPlayback=()=>({time:playback.time,playing:playback.playing,showAll:playback.showAll,speed:playback.speed});
window.RadarLab.libraryManifest=()=>recordingLibrary.records.map(e=>e.source);
