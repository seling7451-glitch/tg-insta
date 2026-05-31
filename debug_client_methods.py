from instagrapi import Client
cl = Client()
methods = [m for m in dir(cl) if 'clip' in m or 'reel' in m or 'media' in m]
for m in sorted(methods):
    print(m)
