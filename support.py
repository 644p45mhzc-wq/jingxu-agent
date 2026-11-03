import hashlib
import os
import secrets
import sqlite3
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException, Depends, Query
from pydantic import BaseModel, Field
router = APIRouter(prefix="/api/support")
def database():
    path = Path(os.getenv("FEEDBACK_DB", str(Path(__file__).resolve().parents[1] / "data" / "feedback.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("BEGIN IMMEDIATE")
    con.execute("CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY, token TEXT UNIQUE, question TEXT NOT NULL, reply TEXT NOT NULL DEFAULT '', created TEXT DEFAULT CURRENT_TIMESTAMP, updated TEXT DEFAULT CURRENT_TIMESTAMP)")
    if 'owner' not in {r[1] for r in con.execute('PRAGMA table_info(tickets)')}:
        con.execute('ALTER TABLE tickets ADD COLUMN owner TEXT')
    con.execute('CREATE INDEX IF NOT EXISTS tickets_owner_id ON tickets(owner,id)')
    con.commit()
    return con
class Question(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
class Reply(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
def admin(authorization: str = Header(default="")):
    key = os.getenv("FEEDBACK_ADMIN_KEY", "")
    if len(key) < 32:
        raise HTTPException(503, "开发者后台尚未配置")
    if not secrets.compare_digest(authorization, "Bearer " + key):
        raise HTTPException(401, "后台密钥无效")
def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()
@router.post("/tickets", status_code=201)
def create(body: Question):
    if not body.text.strip(): raise HTTPException(422, "请填写问题")
    token = secrets.token_urlsafe(32)
    con = database()
    try:
        with con:
            con.execute("INSERT INTO tickets(token,question) VALUES (?,?)", (digest(token), body.text.strip()))
    finally: con.close()
    return {"code": token}
@router.get("/ticket")
def read(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ")
    con = database()
    try:
        row = con.execute("SELECT question,reply,created,updated FROM tickets WHERE token=?", (digest(token),)).fetchone()
    finally: con.close()
    if not row: raise HTTPException(404, "查询码无效")
    return dict(row)
@router.get("/admin/tickets", dependencies=[Depends(admin)])
def listing(before: int = Query(default=9223372036854775807, ge=1)):
    con = database()
    try: return [dict(r) for r in con.execute("SELECT id,question,reply,created,updated FROM tickets WHERE id < ? ORDER BY id DESC LIMIT 200", (before,))]
    finally: con.close()
@router.put("/admin/tickets/{ticket_id}", dependencies=[Depends(admin)])
def respond(ticket_id: int, body: Reply):
    if not body.text.strip(): raise HTTPException(422, "回复不能为空")
    con = database()
    try:
        with con:
            result = con.execute("UPDATE tickets SET reply=?,updated=CURRENT_TIMESTAMP WHERE id=?", (body.text.strip(),ticket_id))
            if not result.rowcount: raise HTTPException(404, "反馈不存在")
    finally: con.close()
    return {"ok": True}

import re

def owner_identity(authorization):
    if not re.fullmatch(r"Bearer [a-f0-9]{64}", authorization):
        raise HTTPException(401, "用户身份无效，请重新打开反馈窗口")
    return digest("owner:" + authorization[7:])

def create_owned(body, authorization):
    owner = owner_identity(authorization)
    if not body.text.strip(): raise HTTPException(422, "请填写问题")
    con = database()
    try:
        with con:
            row = con.execute("INSERT INTO tickets(token,owner,question) VALUES (?,?,?)", (digest(secrets.token_urlsafe(32)),owner,body.text.strip()))
            return {"id": row.lastrowid}
    finally: con.close()

def list_owned(authorization, before):
    owner = owner_identity(authorization)
    con = database()
    try:
        return [dict(r) for r in con.execute("SELECT id,question,reply,created,updated FROM tickets WHERE owner=? AND id<? ORDER BY id DESC LIMIT 50", (owner,before))]
    finally: con.close()

class Claim(BaseModel):
    codes: list[str] = Field(max_length=200)

def claim_old(body, authorization):
    owner = owner_identity(authorization)
    if any(len(c)>128 for c in body.codes): raise HTTPException(422,"旧凭据无效")
    con = database()
    try:
        with con:
            for code in body.codes:
                con.execute("UPDATE tickets SET owner=? WHERE token=? AND owner IS NULL", (owner,digest(code)))
    finally: con.close()
    return {"ok": True}
