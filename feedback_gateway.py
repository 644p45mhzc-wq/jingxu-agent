import os
from urllib.parse import urlsplit
import httpx
from fastapi import APIRouter, Header, Query, HTTPException
from backend import support
router = APIRouter(prefix="/api/feedback")

def forward(path, method, authorization, body=None):
    url=os.getenv("FEEDBACK_SERVICE_URL", "").strip().rstrip('/')
    if not url: return None
    parsed=urlsplit(url)
    if parsed.scheme != 'https' and not (parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost')):
        raise HTTPException(503,"反馈服务地址需要 HTTPS")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(503,"反馈服务地址配置无效")
    try:
        with httpx.Client(timeout=15,follow_redirects=False) as client:
            r=client.request(method,url+'/api/feedback'+path,headers={'Authorization':authorization},json=body)
        if r.status_code>=500: raise HTTPException(503,"反馈服务暂时不可用，请稍后重试")
        data=r.json()
        if not r.is_success: raise HTTPException(r.status_code,"反馈请求未成功，请稍后重试")
        return data
    except (httpx.HTTPError,ValueError): raise HTTPException(503,"暂时连接不上反馈服务，请稍后重试")

@router.post('/mine',status_code=201)
def create(body:support.Question,authorization:str=Header(default='')):
    support.owner_identity(authorization)
    result=forward('/mine','POST',authorization,body.model_dump())
    return result if result is not None else support.create_owned(body,authorization)

@router.get('/mine')
def listing(authorization:str=Header(default=''),before:int=Query(default=9223372036854775807,ge=1)):
    support.owner_identity(authorization)
    result=forward('/mine?before='+str(before),'GET',authorization)
    return result if result is not None else support.list_owned(authorization,before)

@router.post('/claim')
def claim(body:support.Claim,authorization:str=Header(default='')):
    support.owner_identity(authorization)
    result=forward('/claim','POST',authorization,body.model_dump())
    return result if result is not None else support.claim_old(body,authorization)
