"""Bounded public repository lookup. Hosting is provenance, not an authority guarantee."""
import base64
import hashlib
import json
import os
import re
import time
from urllib.parse import quote,urlencode,urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
from .storage import digest,load_json,save_json,utcnow

PROTOCOL='public_repository_lookup_v2_entities'
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Redirect refused')

def public_get(url):
    u=urlparse(url)
    if u.scheme!='https' or u.hostname not in {'huggingface.co','api.github.com'} or u.port not in (None,443) or u.username or u.password:
        raise ValueError('Disallowed source URL')
    headers={'User-Agent':'ResearchReview/1.0','Accept':'application/json'}
    token=os.getenv('HF_TOKEN') if u.hostname=='huggingface.co' else os.getenv('GITHUB_TOKEN')
    if token:headers['Authorization']='Bearer '+token
    for attempt in range(2):
        try:
            with build_opener(NoRedirect()).open(Request(url,headers=headers),timeout=12) as response:
                data=response.read(250001)
                if len(data)>250000:raise ValueError('Source exceeds 250 KB limit')
                return data.decode('utf-8')
        except HTTPError as exc:
            if attempt==0 and exc.code in (429,502,503):
                try:delay=float(exc.headers.get('Retry-After','1'))
                except ValueError:delay=1
                if 0<=delay<=3:time.sleep(delay);continue
            raise ValueError('Source HTTP '+str(exc.code)) from None
    raise ValueError('Source unavailable')

def normalized(value):return re.sub('[^a-z0-9]','',value.casefold())

class OnlineSources:
    def __init__(self,cache_dir,fetch=public_get,max_requests=24):
        self.cache_dir=cache_dir;self.fetch=fetch;self.max_requests=max_requests;self.requests=0

    def _get(self,url):
        if self.requests>=self.max_requests:raise ValueError('Online source request budget exhausted')
        self.requests+=1
        return self.fetch(url)

    def lookup(self,entity,kind):
        key=digest({'protocol':PROTOCOL,'entity':entity,'kind':kind})
        path=self.cache_dir/(key+'.json')
        if path.exists():
            record=load_json(path)
            for source in record['sources']:
                if hashlib.sha256(source['text'].encode()).hexdigest()!=source['sha256']:
                    raise ValueError('Online snapshot integrity mismatch')
            return {**record,'cache_hit':True}
        result={'entity':entity,'kind':kind,'status':'unavailable','sources':[],
                'candidates':[],'errors':[],'retrieved_at':utcnow(),'cache_hit':False,'protocol':PROTOCOL}
        from .proposal_checks import searchable_entity
        if not searchable_entity(entity):
            result.update(status='needs_specific_entity',errors=['Supply a specific model or dataset identity.'])
            save_json(path,result);return result
        try:
            collection='datasets' if kind=='dataset' else 'models'
            # Explicit qualified repository IDs require no ambiguous name search.
            if re.fullmatch(r'[\w.-]+/[\w.-]+',entity):ids=[entity]
            else:
                hits=json.loads(self._get('https://huggingface.co/api/'+collection+'?'+urlencode({'search':entity,'limit':5})))
                ids=[h.get('id',h.get('modelId','')) for h in hits]
                ids=[i for i in ids if re.fullmatch(r'[\w.-]+/[\w.-]+',i)]
                result['candidates']=ids
                exact=[i for i in ids if normalized(i.split('/')[-1])==normalized(entity)]
                if len(exact)!=1:
                    result['status']='ambiguous' if ids else 'not_found'
                    save_json(path,result);return result
                ids=exact
            repo=ids[0]
            info=json.loads(self._get('https://huggingface.co/api/'+collection+'/'+quote(repo,safe='/')))
            revision=info.get('sha')
            if not isinstance(revision,str) or not re.fullmatch(r'[a-fA-F0-9]{40,64}',revision):raise ValueError('Missing immutable repository revision')
            base='https://huggingface.co/'+('datasets/' if kind=='dataset' else '')+repo
            metadata={k:info.get(k) for k in ['id','author','sha','private','gated','cardData','tags','pipeline_tag']}
            self._source(result,entity,base,json.dumps(metadata,ensure_ascii=False,indent=2),'hub_metadata',repo,revision)
            try:
                card=self._get(base+'/resolve/'+revision+'/README.md')
                self._source(result,entity,base+'/blob/'+revision+'/README.md',card,'repository_card',repo,revision)
                # Follow only a bounded, explicit project link in the retrieved card.
                links=list(dict.fromkeys(re.findall(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',card)))
                for link in links[:1]:
                    try:
                        readme=json.loads(self._get('https://api.github.com/repos/'+link.rstrip('.')+'/readme'))
                        if readme.get('encoding')!='base64':raise ValueError('Unsupported README encoding')
                        text=base64.b64decode(readme['content'],validate=False).decode('utf-8')
                        self._source(result,entity,readme.get('html_url','https://github.com/'+link),text,'linked_github_readme',link,readme.get('sha'))
                    except (ValueError,OSError,KeyError) as exc:result['errors'].append('Linked GitHub documentation unavailable: '+type(exc).__name__)
            except (ValueError,OSError) as exc:result['errors'].append('Repository card unavailable: '+type(exc).__name__)
            result['status']='retrieved'
        except (ValueError,OSError,KeyError,TypeError) as exc:
            # No raw exception/headers: credentials must never enter a trace.
            result['errors'].append('Lookup failed: '+type(exc).__name__)
        save_json(path,result)
        return result

    @staticmethod
    def _source(result,entity,url,text,kind,repo,revision):
        if len(text)>100000:raise ValueError('Document exceeds context limit')
        result['sources'].append({'source_id':'online_'+digest({'url':url,'text':text})[:20],
            'entity':entity,'url':url,'retrieved_at':result['retrieved_at'],'text':text,
            'sha256':hashlib.sha256(text.encode()).hexdigest(),'facts':{},'kind':kind,
            'repository':repo,'revision':revision,
            'authority':'Publisher-hosted or repository-linked documentation; original-author ownership not independently established.',
            'resolution':'Unique normalized name match or explicit repository ID; name matching is not identity proof.'})
