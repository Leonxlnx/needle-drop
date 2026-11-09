"""Set A asset fetch: Poly Haven models via common.ph_files (data only).
common._get fails here because the project root is so deep that asset paths exceed Windows MAX_PATH (260).
We download with the long-path prefix into assets/polyhaven/models/<slug>/ (project convention)
and mirror into a short cache dir under TEMP that Blender can open. Images get packed into set_a.blend."""
import os, shutil, urllib.request
import common as C

BS = chr(92)
PREFIX = BS + BS + '?' + BS
SHORT = os.path.join(os.environ.get('TEMP', 'C:' + BS + 'Temp'), 'ndA')


def _long(p):
    p = os.path.abspath(p)
    return p if p.startswith(PREFIX) else PREFIX + p


def _get(url, dest):
    L = _long(dest)
    if os.path.exists(L) and os.path.getsize(L) > 0:
        return dest
    os.makedirs(_long(os.path.dirname(dest)), exist_ok=True)
    req = urllib.request.Request(url, headers=C.UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(L + '.part', 'wb') as f:
        f.write(r.read())
    os.replace(L + '.part', L)
    return dest


def rock_blend(slug, res='1k'):
    """Return a SHORT path to the model .blend (textures mirrored next to it)."""
    sd = os.path.join(SHORT, slug)
    files = os.path.join(sd, 'files.txt')
    if os.path.exists(files):
        p = open(files).read().strip()
        if os.path.exists(p):
            return p
    f = C.ph_files(slug)
    entry = f['blend'][res]['blend']
    d = os.path.join(C.ASSETS, 'polyhaven', 'models', slug)
    rels = [os.path.basename(entry['url'])]
    _get(entry['url'], os.path.join(d, rels[0]))
    for rel, inc in entry.get('include', {}).items():
        _get(inc['url'], os.path.join(d, rel)); rels.append(rel)
    for rel in rels:
        dst = os.path.join(sd, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(_long(os.path.join(d, rel)), dst)
    out = os.path.join(sd, rels[0])
    with open(files, 'w') as fh:
        fh.write(out)
    return out
