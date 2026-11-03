"""Standalone feedback server. Never configure FEEDBACK_SERVICE_URL here."""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import FileResponse
from backend import support
app=FastAPI(title='竞序 · 开发者反馈中心',docs_url=None,redoc_url=None)
app.include_router(support.router)
ROOT=Path(__file__).resolve().parents[1]/'frontend'
@app.middleware('http')
async def private_responses(request,call_next):
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    return response
@app.get('/')
def home(): return FileResponse(ROOT/'support-admin.html')
@app.get('/static/support-admin.js')
def script(): return FileResponse(ROOT/'support-admin.js')
@app.get('/health')
def health(): return {'ok':True}
@app.post('/api/feedback/mine',status_code=201)
def create(body:support.Question,authorization:str=Header(default='')):
    return support.create_owned(body,authorization)
@app.get('/api/feedback/mine')
def mine(authorization:str=Header(default=''),before:int=Query(default=9223372036854775807,ge=1)):
    return support.list_owned(authorization,before)
@app.post('/api/feedback/claim')
def claim(body:support.Claim,authorization:str=Header(default='')):
    return support.claim_old(body,authorization)
