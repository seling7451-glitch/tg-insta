from pathlib import Path
from instagrapi import Client
from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, INSTAGRAM_SESSION_FILE

cl = Client()

session_path = Path(INSTAGRAM_SESSION_FILE)
if session_path.exists():
    cl.load_settings(str(session_path))
else:
    print('SESSION FILE NOT FOUND')

try:
    cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
except Exception as exc:
    print('LOGIN ERROR:', exc)
    raise

threads = cl.direct_threads(amount=10)
print('THREADS:', len(threads))
for t in threads:
    users = [(u.pk, getattr(u, 'username', None)) for u in t.users]
    print('--- THREAD', t.id, 'users', users)
    print('  msg count:', len(t.messages))
    for m in t.messages:
        print('  MSG', m.id, 'item_type=', m.item_type, 'text=', getattr(m, 'text', None))
        print('    has_media=', hasattr(m, 'media') and m.media is not None,
              'has_clip=', hasattr(m, 'clip') and m.clip is not None,
              'has_reel=', hasattr(m, 'reel_share') and m.reel_share is not None,
              'has_visual=', hasattr(m, 'visual_media') and m.visual_media is not None,
              'has_attachments=', hasattr(m, 'attachments') and m.attachments is not None)
        if hasattr(m, 'media') and m.media:
            print('    media video_url=', getattr(m.media, 'video_url', None), 'video_versions=', getattr(m.media, 'video_versions', None), 'carousel_media=', getattr(m.media, 'carousel_media', None))
        if hasattr(m, 'clip') and m.clip:
            print('    clip video_url=', getattr(m.clip, 'video_url', None), 'video_versions=', getattr(m.clip, 'video_versions', None))
        if hasattr(m, 'reel_share') and m.reel_share:
            print('    reel_share media=', getattr(m.reel_share, 'media', None))
