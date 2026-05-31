from pathlib import Path
from instagrapi import Client
from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, INSTAGRAM_SESSION_FILE

cl = Client()
path = Path(INSTAGRAM_SESSION_FILE)
if path.exists():
    cl.load_settings(str(path))
else:
    raise SystemExit('No session file')
cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
threads = cl.direct_threads(amount=5)
for t in threads:
    for m in t.messages:
        if m.item_type == 'xma_clip':
            print('MSG', m.id, 'item_type', m.item_type)
            print('ATTRS', [a for a in dir(m) if not a.startswith('_')])
            try:
                print('DICT', m.__dict__)
            except Exception as e:
                print('DICT ERROR', e)
            raise SystemExit
print('no xma_clip found')
