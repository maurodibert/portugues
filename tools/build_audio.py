"""Record pt-BR audio (macOS voice Luciana) for every fixed phrase of a lesson and embed the manifest.

usage: python3 tools/build_audio.py a0/l01.html
Phrases come from data-s attributes plus the lesson's ABC/VOCAB/EX arrays. " / " in a phrase becomes a pause.
"""
import hashlib, html, json, os, re, subprocess, sys, tempfile

page = sys.argv[1]
lesson = os.path.splitext(os.path.basename(page))[0]
audio_dir = os.path.join(os.path.dirname(page), 'audio', lesson)
os.makedirs(audio_dir, exist_ok=True)
s = open(page).read()
body, js = s.split('<script>', 1)
strings = [html.unescape(x) for x in re.findall(r'data-s="([^"]+)"', body)]

tmp = tempfile.mkdtemp()
parts = [m.group(0) for p in [r'const ABC=.*?\]\];', r'const VOCAB=\[.*?\n\];', r'const EX=\[.*?\n\];'] if (m := re.search(p, js, re.S))]
exsay = re.search(r'const exSay=.*?;\n', js)
collect = '\n'.join(parts) + '\n' + (exsay.group(0) if exsay else '') + '''
const out=new Set(%s);
if (typeof ABC!=='undefined') ABC.forEach(([l,n])=>out.add(n));
if (typeof VOCAB!=='undefined') VOCAB.forEach(v=>out.add(v[0]));
if (typeof EX!=='undefined') EX.forEach(sec=>sec.items.forEach(([q,ok,opts])=>{ if(sec.mc) opts.forEach(o=>out.add(o)); else out.add(exSay(q,ok,sec.wide)); }));
console.log(JSON.stringify([...out]));''' % json.dumps(strings)
open(tmp + '/collect.js', 'w').write(collect)
strings = json.loads(subprocess.run(['node', tmp + '/collect.js'], capture_output=True, text=True, check=True).stdout)

manifest = {}
for t in strings:
    spoken = t.replace(' / ', ' [[slnc 900]] ')
    name = hashlib.md5(spoken.encode()).hexdigest()[:10] + '.m4a'
    manifest[t] = name
    out = os.path.join(audio_dir, name)
    if not os.path.exists(out):
        subprocess.run(['say', '-v', 'Luciana', '-r', '150', '-o', tmp + '/x.aiff', spoken], check=True)
        subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', tmp + '/x.aiff', out], check=True)
for f in os.listdir(audio_dir):
    if f not in manifest.values():
        os.remove(os.path.join(audio_dir, f))
s = re.sub(r'/\*AUDIO_MANIFEST\*/.*?/\*END\*/', lambda m: '/*AUDIO_MANIFEST*/' + json.dumps(manifest, ensure_ascii=False) + '/*END*/', s, flags=re.S)
open(page, 'w').write(s)
print(len(manifest), 'audios in', audio_dir)
