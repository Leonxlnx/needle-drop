// Mix music + SFX from a cue sheet into a mastered stereo WAV with ffmpeg.
// Usage: node tools/mix.js audio/cues.json audio/mix.wav
// cues.json:
// { "duration": 30,
//   "music": [{ "file": "audio/music/x.mp3", "at": 0, "offset": 12.5, "dur": 30, "gain_db": -3, "fade_in": 0.3, "fade_out": 2.5 }],
//   "sfx":   [{ "file": "audio/sfx/y.wav", "at": 3.2, "offset": 0, "dur": null, "gain_db": -8, "fade_in": 0, "fade_out": 0.1, "pan": 0, "rate": 1 }],
//   "duck":  { "enabled": true, "threshold": 0.08, "ratio": 4 },          // optional: SFX bus ducks music
//   "master": { "lufs": -14, "tp": -1.0 } }
const fs = require('fs');
const { execFileSync } = require('child_process');
const [cuesPath, outPath] = process.argv.slice(2);
const cues = JSON.parse(fs.readFileSync(cuesPath, 'utf8'));
const D = cues.duration;
const inputs = [], chains = [];
let idx = 0;
function clip(c, label) {
  inputs.push('-i', c.file);
  const i = idx++;
  const f = [];
  f.push(`aresample=48000`, `aformat=sample_fmts=fltp:channel_layouts=stereo`);
  if (c.rate && c.rate !== 1) f.push(`asetrate=${Math.round(48000 * c.rate)}`, `aresample=48000`);
  const off = c.offset || 0;
  if (c.dur != null) f.push(`atrim=start=${off}:duration=${c.dur}`); else if (off) f.push(`atrim=start=${off}`);
  f.push('asetpts=PTS-STARTPTS');
  if (c.fade_in) f.push(`afade=t=in:st=0:d=${c.fade_in}`);
  if (c.fade_out && c.dur != null) f.push(`afade=t=out:st=${Math.max(0, c.dur - c.fade_out)}:d=${c.fade_out}`);
  if (c.gain_db) f.push(`volume=${c.gain_db}dB`);
  if (c.pan) { const l = Math.min(1, 1 - c.pan), r = Math.min(1, 1 + c.pan); f.push(`pan=stereo|c0=${l.toFixed(3)}*c0|c1=${r.toFixed(3)}*c1`); }
  const ms = Math.round((c.at || 0) * 1000);
  if (ms > 0) f.push(`adelay=${ms}|${ms}`);
  f.push(`apad=whole_dur=${D}`, `atrim=duration=${D}`);
  chains.push(`[${i}:a]${f.join(',')}[${label}]`);
  return `[${label}]`;
}
const mus = (cues.music || []).map((c, k) => clip(c, `m${k}`));
const sfx = (cues.sfx || []).map((c, k) => clip(c, `s${k}`));
let graph = chains.join(';');
const musBus = mus.length > 1 ? (graph += `;${mus.join('')}amix=inputs=${mus.length}:normalize=0[mb]`, '[mb]') : mus[0];
const sfxBus = sfx.length > 1 ? (graph += `;${sfx.join('')}amix=inputs=${sfx.length}:normalize=0[sb]`, '[sb]') : sfx[0];
let pre;
if (musBus && sfxBus) {
  if (cues.duck && cues.duck.enabled) {
    graph += `;${sfxBus}asplit=2[sk][sx];${musBus}[sk]sidechaincompress=threshold=${cues.duck.threshold || 0.08}:ratio=${cues.duck.ratio || 4}:attack=5:release=250[md];[md][sx]amix=inputs=2:normalize=0[pre]`;
  } else graph += `;${musBus}${sfxBus}amix=inputs=2:normalize=0[pre]`;
  pre = '[pre]';
} else pre = musBus || sfxBus;
const m = cues.master || {};
graph += `;${pre}alimiter=limit=0.95:level=false,loudnorm=I=${m.lufs ?? -14}:TP=${m.tp ?? -1}:LRA=11,aresample=48000[out]`;
const args = ['-y', '-hide_banner', '-loglevel', 'error', ...inputs, '-filter_complex', graph, '-map', '[out]', '-t', String(D), '-c:a', 'pcm_s24le', outPath];
fs.writeFileSync(outPath + '.ffargs.txt', args.join('\n'));
execFileSync('ffmpeg', args, { stdio: 'inherit' });
console.log('MIX_OK', outPath);
