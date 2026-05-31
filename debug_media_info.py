from pathlib import Path
from instagrapi import Client
from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, INSTAGRAM_SESSION_FILE

cl = Client()
path = Path(INSTAGRAM_SESSION_FILE)
cl.load_settings(str(path))
cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
url = 'https://www.instagram.com/reel/DY-T_ofsVNG/?id=3908649462296302406_70287205765&is_sponsored=false&is_ineligible_for_clips_chaining=false'
print('URL:', url)
pk = cl.media_pk_from_url(url)
print('PK:', pk)
media = cl.media_info(pk)
print('Media type:', type(media))
for attr in ['video_url','video_versions','image_versions2','carousel_media','media_type','pk','code']:
    if hasattr(media, attr):
        print(attr, getattr(media, attr))
