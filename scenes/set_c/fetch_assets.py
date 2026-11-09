"""Pre-download Set C Poly Haven data (CC0) into the same paths tools/common.py uses.
Run with Blender's bundled python: python.exe -I scenes/set_c/fetch_assets.py <ROOT>
Data only: nothing downloaded is executed."""
import sys, os, json, urllib.request
ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, 'assets')
UA = {'User-Agent': 'Mozilla/5.0 (blender-film-build)'}

def get(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r, open(dest + '.part', 'wb') as f:
        f.write(r.read())
    os.replace(dest + '.part', dest)
    print('got', dest, flush=True)
    return dest

def files(slug):
    req = urllib.request.Request(f'https://api.polyhaven.com/files/{slug}', headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def model(slug, res='1k'):
    f = files(slug); e = f['blend'][res]['blend']
    d = os.path.join(ASSETS, 'polyhaven', 'models', slug)
    get(e['url'], os.path.join(d, os.path.basename(e['url'])))
    for rel, inc in e.get('include', {}).items():
        get(inc['url'], os.path.join(d, rel))

def tex(slug, res='2k', maps=('nor_gl', 'Rough', 'AO')):
    f = files(slug)
    for m in maps:
        if m not in f: continue
        entry = f[m][res]
        fmt = 'jpg' if 'jpg' in entry else ('png' if 'png' in entry else list(entry)[0])
        url = entry[fmt]['url']
        get(url, os.path.join(ASSETS, 'polyhaven', 'tex', slug, os.path.basename(url)))

for s in ['quiver_tree_01', 'quiver_tree_02', 'dead_quiver_trunk', 'namaqualand_boulder_02', 'namaqualand_boulder_03', 'namaqualand_boulder_04']:
    try: model(s)
    except Exception as ex: print('FAIL', s, ex)
for s in ['sand_02', 'aerial_sand', 'rock_face_03', 'sandstone_cracks']:
    try: tex(s)
    except Exception as ex: print('FAIL', s, ex)
print('FETCH_DONE')
