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
HISTORY=BASE/'data'/'newsletter-history.json'
UA={'User-Agent':'SpaceDailyPrototype/0.1 educational demo (contact: configure-before-production)'}
# Kept server-side only. The current RSS, Image Library, and new APOD endpoint
# do not require it; do not print, cache, or expose this value.
NASA_API_KEY=os.environ.get('NASA_API_KEY')
IMAGE_HOSTS=('nasa.gov','images-assets.nasa.gov')
_IMAGE_VALIDATION_CACHE={}

def get(url, timeout=20):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return response.read()

def normalise_image_url(url):
    """Return a safe, encoded first-party NASA image URL or None."""
    if not isinstance(url,str): return None
    try:
        parsed=urllib.parse.urlsplit(url.strip())
    except ValueError:
        return None
    host=(parsed.hostname or '').lower()
    if parsed.scheme!='https' or not host or not any(host==allowed or host.endswith('.'+allowed) for allowed in IMAGE_HOSTS):
        return None
    path=urllib.parse.quote(urllib.parse.unquote(parsed.path),safe='/%:@+~._-')
    query=urllib.parse.quote(urllib.parse.unquote(parsed.query),safe='=&%:+,~._-')
    return urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,path,query,''))

def valid_image_url(url, timeout=12):
    """Confirm that a NASA URL responds as an image; never cache failed media."""
    url=normalise_image_url(url)
    if not url: return None
    if url in _IMAGE_VALIDATION_CACHE: return _IMAGE_VALIDATION_CACHE[url]
    for method in ('HEAD','GET'):
        try:
            headers=dict(UA,Accept='image/avif,image/webp,image/*,*/*;q=0.8')
            if method=='GET': headers['Range']='bytes=0-1023'
            request=urllib.request.Request(url,headers=headers,method=method)
            with urllib.request.urlopen(request,timeout=timeout) as response:
                if response.headers.get_content_type().startswith('image/'):
                    _IMAGE_VALIDATION_CACHE[url]=url
                    return url
        except Exception:
            continue
    _IMAGE_VALIDATION_CACHE[url]=None
    return None

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=[]
        self.description=''

    def handle_starttag(self, tag, attrs):
        if tag != 'meta': return
        values={key.lower():value for key,value in attrs if value}
        if values.get('property','').lower() in ('og:image','og:image:secure_url') or values.get('name','').lower() == 'twitter:image':
            self.images.append(values.get('content',''))
        if not self.description and (values.get('property','').lower() == 'og:description' or values.get('name','').lower() == 'description'):
            self.description=values.get('content','')

def article_metadata(link):
    """Use only official NASA article metadata for previews and summaries."""
    host=urllib.parse.urlparse(link).hostname or ''
    if not (host == 'nasa.gov' or host.endswith('.nasa.gov')): return None, ''
    try:
        parser=MetadataParser()
        parser.feed(get(link,timeout=10).decode('utf-8',errors='replace'))
        return next((checked for image in parser.images if (checked:=valid_image_url(image))),None), parser.description
    except Exception:
        return None, ''

def summary(text):
    text=html.unescape(re.sub('<[^>]+>',' ',text or ''))
    text=re.sub(r'\s+',' ',text).strip()
    return text[:360]

def category(title, description):
    text=(title+' '+description).lower()
    discovery=('discovery','science','galaxy','star','planet','asteroid','hubble','webb','cosmic','exoplanet')
    return 'Discovery' if any(word in text for word in discovery) else 'NASA update'

def articles():
    root=ET.fromstring(get('https://www.nasa.gov/news-release/feed/'))
    results=[];seen=set()
    for item in root.findall('.//channel/item')[:8]:
        def field(t): return (item.findtext(t) or '').strip()
        title,link,date=field('title'),field('link'),field('pubDate')
        desc=field('description')
        if title and link:
            identity=(link.rstrip('/'),html.unescape(title).lower())
            if identity in seen: continue
            seen.add(identity)
            image,source_description=article_metadata(link)
            description=summary(source_description or desc)
            result={'title':html.unescape(title),'link':link,'date':date,'description':description,'category':category(title,description)}
            if image: result['image']=image
            results.append(result)
    return results

def apod():
    """Fetch APOD from NASA's current WordPress endpoint, not the retiring legacy API."""
    payload=json.loads(get('https://science.nasa.gov/wp-json/wp/v2/apod-basic'))
    item=payload[0] if isinstance(payload,list) and payload else payload if isinstance(payload,dict) else {}
    if item.get('media_type')!='image': return None
    image=next((checked for candidate in (item.get('hdurl'),item.get('url')) if (checked:=valid_image_url(candidate))),None)
    if not image: return None
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
        thumb=next((checked for link in links if link.get('rel')=='preview' and (checked:=valid_image_url(link.get('href')))),None)
        if not thumb: continue
        nasa_id=info.get('nasa_id')
        # The search API's item URL points to raw collection JSON.  Send visitors
        # to the accessible NASA image page instead.
        page='https://images.nasa.gov/' + ('details/'+urllib.parse.quote(str(nasa_id),safe='')+'/' if nasa_id else '')
        results.append({'title':info.get('title','NASA photograph'),'image':thumb,'link':page,'credit':info.get('secondary_creator') or info.get('center') or 'NASA'})
        if len(results)>=6: break
    return results

def retain_last_valid_images(fresh, previous):
    """Keep a previously validated image when current NASA metadata has none."""
    old={(item.get('link') or '').rstrip('/'):item for item in previous if item.get('link')}
    for item in fresh:
        prior=old.get((item.get('link') or '').rstrip('/'),{})
        if not item.get('image') and prior.get('image'):
            item['image']=prior['image']
    return fresh

def update_news_history(news, captured_at):
    """Retain a small, public editorial archive for weekly newsletter selection.

    This archive contains only already-public NASA article metadata. It never
    contains subscribers, credentials, or delivery data.
    """
    previous=[]
    if HISTORY.exists():
        try:
            previous=json.loads(HISTORY.read_text(encoding='utf-8')).get('news',[])
        except json.JSONDecodeError:
            previous=[]
    merged={}
    for item in previous+news:
        link=(item.get('link') or '').rstrip('/')
        if not link: continue
        record=dict(item)
        record['captured_at']=item.get('captured_at') or captured_at
        merged[link]=record
    cutoff=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=35)
    kept=[]
    for item in merged.values():
        try:
            seen=dt.datetime.fromisoformat(item['captured_at'].replace('Z','+00:00'))
        except (KeyError, ValueError):
            continue
        if seen>=cutoff: kept.append(item)
    kept.sort(key=lambda item:item.get('captured_at',''),reverse=True)
    HISTORY.write_text(json.dumps({'updated':captured_at,'news':kept},ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    previous={}
    if OUT.exists():
        try: previous=json.loads(OUT.read_text(encoding='utf-8'))
        except json.JSONDecodeError: pass
    updated=previous.get('updated','')
    if updated.startswith(dt.datetime.now(dt.timezone.utc).date().isoformat()) and os.environ.get('SPACE_DAILY_FORCE_REFRESH')!='1':
        if previous.get('news') and not HISTORY.exists():
            update_news_history(previous['news'],updated)
        print('Cache already refreshed today; set SPACE_DAILY_FORCE_REFRESH=1 to refresh again')
        return
    data={'news':previous.get('news',[]),'gallery':previous.get('gallery',{}),'apod':previous.get('apod'),'updated':previous.get('updated')}
    success=False
    try:
        refreshed=articles()
        if refreshed:
            data['news']=retain_last_valid_images(refreshed,previous.get('news',[]));success=True;print('News refreshed')
        else: print('News refresh returned no valid articles; retained last cache')
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
    if data['news']:
        update_news_history(data['news'],data.get('updated') or dt.datetime.now(dt.timezone.utc).isoformat())
    print('Wrote',OUT)

if __name__=='__main__':main()
