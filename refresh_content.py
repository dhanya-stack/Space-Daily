"""Fetch shared NASA news and gallery data once. Run daily or from GitHub Actions.
No API key required. Failures retain the previous good cache.
"""
import datetime as dt
import html
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

BASE=pathlib.Path(__file__).resolve().parent
OUT=BASE/'data'/'latest.json'
UA={'User-Agent':'SpaceDailyPrototype/0.1 educational demo (contact: configure-before-production)'}
# Kept server-side only. The current RSS, Image Library, and new APOD endpoint
# do not require it; do not print, cache, or expose this value.
NASA_API_KEY=os.environ.get('NASA_API_KEY')

def get(url, timeout=20):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return response.read()

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=[]

    def handle_starttag(self, tag, attrs):
        if tag != 'meta': return
        values={key.lower():value for key,value in attrs if value}
        if values.get('property','').lower() in ('og:image','og:image:secure_url') or values.get('name','').lower() == 'twitter:image':
            self.images.append(values.get('content',''))

def article_image(link):
    """Use the official preview image declared by a NASA article, if available."""
    host=urllib.parse.urlparse(link).hostname or ''
    if not (host == 'nasa.gov' or host.endswith('.nasa.gov')): return None
    try:
        parser=MetadataParser()
        parser.feed(get(link,timeout=10).decode('utf-8',errors='replace'))
        return next((image for image in parser.images if image.startswith('https://')),None)
    except Exception:
        return None

def articles():
    root=ET.fromstring(get('https://www.nasa.gov/news-release/feed/'))
    results=[]
    for item in root.findall('.//channel/item')[:8]:
        def field(t): return (item.findtext(t) or '').strip()
        title,link,date=field('title'),field('link'),field('pubDate')
        desc=field('description')
        desc=html.unescape(re.sub('<[^>]+>',' ',desc))
        if title and link:
            result={'title':html.unescape(title),'link':link,'date':date,'description':desc[:300]}
            image=article_image(link)
            if image: result['image']=image
            results.append(result)
    return results

def apod():
    """Fetch APOD from NASA's current WordPress endpoint, not the retiring legacy API."""
    payload=json.loads(get('https://science.nasa.gov/wp-json/wp/v2/apod-basic'))
    item=payload[0] if isinstance(payload,list) and payload else payload if isinstance(payload,dict) else {}
    if item.get('media_type')!='image': return None
    image=item.get('hdurl') or item.get('url')
    if not isinstance(image,str) or not image.startswith('https://'): return None
    return {
        'date':item.get('date',''),
        'title':html.unescape(item.get('title','NASA Astronomy Picture of the Day')),
        'explanation':html.unescape(re.sub('<[^>]+>',' ',item.get('explanation',''))),
        'image':image,
        'link':item.get('permalink') or item.get('url') or 'https://science.nasa.gov/apod/',
        'credit':html.unescape(re.sub('<[^>]+>',' ',item.get('credit') or item.get('copyright') or 'NASA — see original source')),
        'alt':html.unescape(item.get('alt','')),
        'media_type':'image',
    }

def images(topic):
    params=urllib.parse.urlencode({'q':topic,'media_type':'image','page_size':12})
    payload=json.loads(get('https://images-api.nasa.gov/search?'+params))
    results=[]
    for item in payload.get('collection',{}).get('items',[]):
        info=(item.get('data') or [{}])[0]; links=item.get('links') or []
        thumb=next((l.get('href') for l in links if l.get('rel')=='preview'),None)
        if not thumb: continue
        nasa_id=info.get('nasa_id')
        # The search API's item URL points to raw collection JSON.  Send visitors
        # to the accessible NASA image page instead.
        page='https://images.nasa.gov/' + ('details/'+urllib.parse.quote(str(nasa_id),safe='')+'/' if nasa_id else '')
        results.append({'title':info.get('title','NASA photograph'),'image':thumb,'link':page,'credit':info.get('secondary_creator') or info.get('center') or 'NASA'})
        if len(results)>=6: break
    return results

def main():
    previous={}
    if OUT.exists():
        try: previous=json.loads(OUT.read_text(encoding='utf-8'))
        except json.JSONDecodeError: pass
    data={'news':previous.get('news',[]),'gallery':previous.get('gallery',{}),'apod':previous.get('apod'),'updated':previous.get('updated')}
    success=False
    try:
        data['news']=articles();success=True;print('News refreshed')
    except Exception as err:print('News unavailable:',err)
    try:
        result=apod()
        if result:
            data['apod']=result;success=True;print('APOD refreshed')
    except Exception as err:print('APOD unavailable:',err)
    for topic in ('galaxy','moon','saturn','nebula','spacecraft'):
        try:
            result=images(topic)
            if result:data['gallery'][topic]=result;success=True
            print(topic,'images:',len(result))
        except Exception as err:print(topic,'unavailable:',err)
    if success:data['updated']=dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Wrote',OUT)

if __name__=='__main__':main()
