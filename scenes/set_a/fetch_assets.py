# Pre-fetch Poly Haven moon rocks (data only). Works around MAX_PATH (>260 chars) in common._get
# by writing with the \?\ prefix, then mirroring to a short cache dir Blender can open.
import sys, os, bpy
ROOT = os.getcwd(); sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'scenes', 'set_a'))
import assets_a as A
for i in range(1, 8):
    slug = f'moon_rock_0{i}'
    try:
        p = A.rock_blend(slug)
        with bpy.data.libraries.load(p, link=False) as (src, dst):
            print('MODEL', slug, p, 'objects:', list(src.objects), 'images:', list(src.images)[:6])
    except Exception as ex:
        import traceback; traceback.print_exc(); print('FAIL', slug, ex)
print('FETCH_DONE')
