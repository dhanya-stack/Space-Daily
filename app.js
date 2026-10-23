const $=id=>document.getElementById(id);
const date=new Date();
$('dateHero').textContent=date.toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'});

$('menuBtn').onclick=()=>{const nav=$('nav');nav.classList.toggle('open');$('menuBtn').setAttribute('aria-expanded',nav.classList.contains('open'))};
document.querySelectorAll('nav a').forEach(link=>link.onclick=()=>$('nav').classList.remove('open'));
document.querySelectorAll('[data-answer]').forEach(button=>button.onclick=()=>{$('quizFeedback').textContent=button.dataset.answer==='right'?'Correct. The Moon rotates once for each orbit around Earth.':'Not quite. The Moon rotates once for each orbit around Earth.'});

const storageKey='spacedaily-interests';let interests=[];
try{interests=JSON.parse(localStorage.getItem(storageKey)||'[]')}catch{}
function renderPrefs(){document.querySelectorAll('[data-interest]').forEach(button=>{const chosen=interests.includes(button.dataset.interest);button.classList.toggle('selected',chosen);button.setAttribute('aria-pressed',String(chosen))});$('interestMessage').textContent=interests.length?`Selected: ${interests.join(', ')}.`:'Select any topics.'}
renderPrefs();
document.querySelectorAll('[data-interest]').forEach(button=>button.onclick=()=>{const value=button.dataset.interest;interests=interests.includes(value)?interests.filter(item=>item!==value):[...interests,value];localStorage.setItem(storageKey,JSON.stringify(interests));renderPrefs()});
$('resetPrefs').onclick=()=>{interests=[];localStorage.removeItem(storageKey);renderPrefs()};
document.querySelectorAll('[data-open-newsletter]').forEach(button=>button.onclick=()=>$('newsletter').scrollIntoView({behavior:'smooth'}));

const safeUrl=value=>{try{const url=new URL(value);return ['https:','http:'].includes(url.protocol)?url.href:''}catch{return ''}};
const clean=value=>String(value||'').replace(/<[^>]*>/g,'').replace(/\s+/g,' ').trim().slice(0,450);
let galleryData={};

function renderGallery(topic){
  document.querySelectorAll('[data-filter]').forEach(button=>button.classList.toggle('selected',button.dataset.filter===topic));
  const items=galleryData[topic]||[],area=$('galleryGrid');area.replaceChildren();
  if(!items.length){area.innerHTML='<div class="placeholder">Images for this category are not cached yet. <a href="https://images.nasa.gov/" target="_blank" rel="noopener">Explore the NASA Image Library ↗</a></div>';return}
  items.forEach(item=>{const card=document.createElement('article'),image=document.createElement('img'),content=document.createElement('div'),title=document.createElement('strong'),credit=document.createElement('p'),link=document.createElement('a');card.className='gallery-card';image.loading='lazy';image.alt=item.title||'NASA archive image';image.src=safeUrl(item.image);title.textContent=clean(item.title);credit.textContent=`Credit: ${clean(item.credit||'NASA — check source rights')}`;link.textContent='View image and rights ↗';link.href=safeUrl(item.link)||'https://images.nasa.gov/';link.target='_blank';link.rel='noopener';content.append(title,credit,link);card.append(image,content);area.append(card)});
}
document.querySelectorAll('[data-filter]').forEach(button=>button.onclick=()=>renderGallery(button.dataset.filter));

function populateEditorialImages(){
  const photo=$('lessonPhoto');
  photo.src='https://images-assets.nasa.gov/image/AS11-40-5875/AS11-40-5875~thumb.jpg';
  photo.alt='Apollo 11 astronaut on the lunar surface';
  $('lessonPhotoLink').href='https://images.nasa.gov/details/AS11-40-5875/';
  $('lessonPhotoCredit').textContent='NASA · Apollo 11 · view source and rights ↗';
}

function renderApod(apod){
  if(!apod||apod.media_type!=='image'||!safeUrl(apod.image))return;
  $('apodImage').src=safeUrl(apod.image);$('apodImage').alt=clean(apod.alt)||clean(apod.title)||'NASA Astronomy Picture of the Day';
  $('apodDate').textContent=apod.date?`NASA APOD · ${apod.date}`:'NASA APOD';
  $('apodTitle').textContent=clean(apod.title);
  $('apodDescription').textContent=clean(apod.explanation).slice(0,430);
  $('apodCredit').textContent=`Image credit: ${clean(apod.credit||'NASA — see original source')}`;
  $('apodLink').href=safeUrl(apod.link)||'https://science.nasa.gov/apod/';
  $('apodSource').href=safeUrl(apod.link)||'https://science.nasa.gov/apod/';
  $('apodFeature').hidden=false;$('apodStatus').textContent='';
}

async function loadData(){
  try{
    const response=await fetch('data/latest.json',{cache:'no-cache'});if(!response.ok)throw Error('Missing data');
    const data=await response.json();galleryData=data.gallery||{};populateEditorialImages();renderApod(data.apod);renderGallery('galaxy');
    const grid=$('newsGrid');grid.replaceChildren();
    (data.news||[]).slice(0,6).forEach((article,index)=>{const card=document.createElement('article'),body=document.createElement('div'),meta=document.createElement('span'),title=document.createElement('h3'),description=document.createElement('p'),link=document.createElement('a');card.className=`news-card ${index===0?'news-featured':''}`;const imageUrl=safeUrl(article.image);if(imageUrl){const image=document.createElement('img');image.className='news-pic';image.src=imageUrl;image.alt='';image.loading=index===0?'eager':'lazy';card.append(image)}body.className='news-card-body';meta.className='news-meta';meta.textContent=`NASA · ${article.date||'Latest'}`;title.textContent=clean(article.title);description.textContent=clean(article.description).slice(0,index===0?245:145);link.href=safeUrl(article.link)||'https://www.nasa.gov/news/';link.target='_blank';link.rel='noopener';link.textContent='Read original story ↗';body.append(meta,title,description,link);card.append(body);grid.append(card)});
    if(!grid.children.length)grid.innerHTML='<div class="placeholder">No headlines are available in the current cache. Visit <a href="https://www.nasa.gov/news/" target="_blank" rel="noopener">NASA News ↗</a>.</div>';
    $('newsStatus').textContent=data.updated?`NASA content refreshed ${new Date(data.updated).toLocaleString('en-GB')}.`:'';
  }catch{renderGallery('galaxy');$('newsStatus').textContent='NASA content has not loaded.'}
}
loadData();
