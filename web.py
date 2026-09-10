#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWESOME AI — ULTIMATE PRO: PostgreSQL (relaxdev), Premium, фото, 5 провайдеров, долгая память, 30+ механических функций"""
import os, re, io, time, json, base64, urllib.parse, hashlib, random, html, uuid as _uuid
from datetime import datetime, timedelta, timezone
import requests, urllib3
import psycopg2, psycopg2.extras
from flask import Flask, request, jsonify, render_template_string, session, send_file

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    def relativedelta(**kw):
        kw.pop("years", None); kw.pop("months", None)
        return timedelta(**kw)
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "awesome-pro-secret-2026")
app.permanent_session_lifetime = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "AQVNyfn82epL9dy8C_kftzeypq6eF9lFd6SZnFzV")
FOLDER_ID = os.getenv("FOLDER_ID", "b1g4aq87c7j61c6g3i5l")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "MDFhMDBkNmEtMmExNC03M2JkLWFlZmMtOTQ0OWVlOTc5M2U1OmE1ZWJhM2NlLTQwYjAtNDZlYi1iMmY2LTE3OTFmYzhhYTQ2MA==")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

OWNER_LOGIN, OWNER_PASSWORD = "admin", "qawsedrf2346"
FREE_LIMIT = 50
MAX_HISTORY = 60
MEM_LIMIT = 100
GIGA_TIMEOUT, YGPT_TIMEOUT, SEARCH_TIMEOUT = 40, 35, 6

MOSCOW_TZ = timezone(timedelta(hours=3))
def gm(): return datetime.now(MOSCOW_TZ)
def gdate(): return gm().strftime('%d.%m.%Y')
def now_iso(): return gm().strftime('%Y-%m-%d %H:%M:%S')
def fmt_date(s):
    if not s: return "—"
    try: return datetime.strptime(str(s).replace('T',' ')[:19], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
    except Exception: return s
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()
def get_db(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db(); cur = conn.cursor()
    def ex(sql):
        try: cur.execute(sql); conn.commit()
        except Exception: conn.rollback()
    ex("""CREATE TABLE IF NOT EXISTS users(
        user_id TEXT PRIMARY KEY, login TEXT UNIQUE, name TEXT, password TEXT,
        premium INTEGER DEFAULT 0, messages_today INTEGER DEFAULT 0, last_reset TEXT,
        premium_expires TEXT, is_admin INTEGER DEFAULT 0, is_owner INTEGER DEFAULT 0,
        theme TEXT DEFAULT 'dark', joined_at TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
        avatar TEXT DEFAULT '', ref_code TEXT, ref_count INTEGER DEFAULT 0)""")
    ex("""CREATE TABLE IF NOT EXISTS chats_web(id BIGSERIAL PRIMARY KEY, user_id TEXT,
        title TEXT DEFAULT 'Новый чат', created_at TEXT, pinned INTEGER DEFAULT 0)""")
    ex("""CREATE TABLE IF NOT EXISTS messages_web(id BIGSERIAL PRIMARY KEY, chat_id BIGINT,
        role TEXT, content TEXT, image TEXT, created_at TEXT)""")
    ex("""CREATE TABLE IF NOT EXISTS total_stats_web(user_id TEXT PRIMARY KEY, total_messages INTEGER DEFAULT 0)""")
    ex("""CREATE TABLE IF NOT EXISTS admin_log(id BIGSERIAL PRIMARY KEY, admin_id TEXT, action TEXT, created_at TEXT)""")
    ex("""CREATE TABLE IF NOT EXISTS notifications(id BIGSERIAL PRIMARY KEY, user_id TEXT, text TEXT, read INTEGER DEFAULT 0, created_at TEXT)""")
    ex("""CREATE TABLE IF NOT EXISTS user_memory(id BIGSERIAL PRIMARY KEY, user_id TEXT, fact TEXT, created_at TEXT)""")
    ex("""CREATE TABLE IF NOT EXISTS web_cache(query TEXT PRIMARY KEY, result TEXT, ts TEXT)""")
    try:
        cur.execute("ALTER TABLE users ALTER COLUMN user_id TYPE TEXT USING user_id::text")
        cur.execute("ALTER TABLE users ALTER COLUMN premium TYPE INTEGER USING COALESCE(premium::int,0)")
        cur.execute("ALTER TABLE users ALTER COLUMN messages_today TYPE INTEGER USING COALESCE(messages_today::int,0)")
        cur.execute("ALTER TABLE users ALTER COLUMN is_admin TYPE INTEGER USING COALESCE(is_admin::int,0)")
        cur.execute("ALTER TABLE users ALTER COLUMN is_owner TYPE INTEGER USING COALESCE(is_owner::int,0)")
        cur.execute("ALTER TABLE users ALTER COLUMN xp TYPE INTEGER USING COALESCE(xp::int,0)")
        cur.execute("ALTER TABLE users ALTER COLUMN level TYPE INTEGER USING COALESCE(level::int,1)")
        cur.execute("ALTER TABLE users ALTER COLUMN ref_count TYPE INTEGER USING COALESCE(ref_count::int,0)")
        conn.commit()
    except Exception: conn.rollback()
    try:
        cur.execute("SELECT user_id FROM users WHERE login=%s", (OWNER_LOGIN,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users(user_id,login,name,password,messages_today,last_reset,is_admin,is_owner,theme,joined_at,xp,level) VALUES(%s,%s,%s,%s,0,%s,1,1,'dark',%s,0,1)",
                        (OWNER_LOGIN, OWNER_LOGIN, "AWESOME", hash_pw(OWNER_PASSWORD), gm().strftime('%Y-%m-%d'), now_iso()))
            cur.execute("INSERT INTO total_stats_web(user_id,total_messages) VALUES(%s,0) ON CONFLICT DO NOTHING", (OWNER_LOGIN,))
        conn.commit()
    except Exception: conn.rollback()
    cur.close(); conn.close()
init_db()

def get_user(uid):
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE user_id=%s", (str(uid),)); row=cur.fetchone()
    cur.close(); conn.close(); return dict(row) if row else None
def get_user_by_login(login):
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE login=%s", (str(login),)); row=cur.fetchone()
    cur.close(); conn.close(); return dict(row) if row else None
def reg_user(login, name, pw):
    login=(login or '').strip(); name=(name or '').strip()
    if not login or len(login)<3: return False,"Логин мин. 3 символа"
    if not name: return False,"Имя обязательно"
    if not pw or len(pw)<3: return False,"Пароль мин. 3 символа"
    if get_user_by_login(login): return False,"Этот логин уже занят"
    owner=1 if login.lower()==OWNER_LOGIN.lower() else 0
    try:
        conn=get_db(); cur=conn.cursor()
        ref=hashlib.md5((login+str(random.random())).encode()).hexdigest()[:8]
        cur.execute("INSERT INTO users(user_id,login,name,password,messages_today,last_reset,is_admin,is_owner,theme,joined_at,xp,level,ref_code) VALUES(%s,%s,%s,%s,0,%s,%s,%s,'dark',%s,0,1,%s)",
                    (login,login,name,hash_pw(pw),gm().strftime('%Y-%m-%d'),owner,owner,now_iso(),ref))
        cur.execute("INSERT INTO total_stats_web(user_id,total_messages) VALUES(%s,0) ON CONFLICT DO NOTHING", (login,))
        conn.commit(); cur.close(); conn.close(); return True,"OK"
    except Exception as e: return False,"Ошибка БД: "+str(e)
def login_user(login, pw):
    u=get_user_by_login((login or '').strip())
    if not u: return False,"Аккаунт не найден. Зарегистрируйся"
    if u.get('password')!=hash_pw(pw): return False,"Неверный пароль"
    return True,"OK"
def eff_status(uid):
    u=get_user(uid) or {}
    owner=1 if str(u.get('login','')).lower()==OWNER_LOGIN.lower() else int(u.get('is_owner',0) or 0)
    is_admin=1 if owner else int(u.get('is_admin',0) or 0)
    premium=int(u.get('premium',0) or 0); exp=u.get('premium_expires')
    if premium and exp:
        try:
            if gm()>datetime.strptime(str(exp).replace('T',' ')[:19],'%Y-%m-%d %H:%M:%S').replace(tzinfo=MOSCOW_TZ):
                premium=0; exp=None
        except Exception: pass
    return {'premium':1 if owner or premium else 0,'premium_expires':exp,'is_admin':is_admin,'is_owner':owner,
            'level':int(u.get('level',1) or 1),'xp':int(u.get('xp',0) or 0)}
def can_send(uid):
    s=eff_status(uid)
    if s['is_owner'] or s['is_admin'] or s['premium']: return True
    u=get_user(uid) or {}; return int(u.get('messages_today',0) or 0) < FREE_LIMIT
def upd(uid, **kw):
    try:
        conn=get_db(); cur=conn.cursor()
        cols=",".join(k+"=%s" for k in kw); vals=[kw[k] for k in kw]+[str(uid)]
        cur.execute("UPDATE users SET "+cols+" WHERE user_id=%s", vals); conn.commit(); cur.close(); conn.close()
    except Exception: pass
def incr(uid):
    u=get_user(uid) or {}; s=eff_status(uid)
    if s['is_owner'] or s['is_admin']: add_xp(uid,5); return
    upd(uid, messages_today=int(u.get('messages_today',0) or 0)+1); add_xp(uid,10)
def add_xp(uid, amt):
    u=get_user(uid) or {}; xp=int(u.get('xp',0) or 0)+int(amt)
    upd(uid, xp=xp, level=1+xp//100)

def get_memory(uid, limit=MEM_LIMIT):
    try:
        conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT fact FROM user_memory WHERE user_id=%s ORDER BY id DESC LIMIT %s",(str(uid),limit))
        rows=cur.fetchall(); cur.close(); conn.close(); return [r['fact'] for r in rows]
    except Exception: return []
def remember(uid, fact):
    fact=(fact or '').strip()[:500]
    if not fact or len(fact)<4: return
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("SELECT COUNT(*) FROM user_memory WHERE user_id=%s AND fact=%s",(str(uid),fact))
        if cur.fetchone()[0]==0: cur.execute("INSERT INTO user_memory(user_id,fact,created_at) VALUES(%s,%s,%s)",(str(uid),fact,now_iso()))
        conn.commit(); cur.close(); conn.close()
    except Exception: pass
def extract_facts(uid, text):
    tl=text.lower(); facts=[]
    if "меня зовут" in tl or "мое имя" in tl:
        m=re.search(r'(?:меня зовут|мое имя)[:\s]+([A-Za-zА-Яа-яЁё\-]+)',tl)
        if m: facts.append("Имя: "+m.group(1))
    for kw,label in [("мне ","Возраст: "),("я живу в ","Город: "),("я работаю ","Работа: ")]:
        if kw in tl:
            m=re.search(re.escape(kw)+r'([^,.!?\n]{2,60})',tl)
            if m: facts.append(label+m.group(1).strip())
    if any(x in tl for x in ["мне нравится","я люблю","обожаю"]):
        m=re.search(r'(?:мне нравится|я люблю|обожаю)\s+([^,.!?\n]{2,60})',tl)
        if m: facts.append("Хобби: "+m.group(1).strip())
    for f in facts: remember(uid,f)

def create_chat(uid, title="Новый чат"):
    conn=get_db(); cur=conn.cursor()
    cur.execute("INSERT INTO chats_web(user_id,title,created_at,pinned) VALUES(%s,%s,%s,0) RETURNING id",(str(uid),title,now_iso()))
    cid=cur.fetchone()[0]; conn.commit(); cur.close(); conn.close(); return cid
def get_chats(uid):
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM chats_web WHERE user_id=%s ORDER BY pinned DESC, created_at DESC",(str(uid),))
    rows=cur.fetchall(); cur.close(); conn.close(); return [dict(r) for r in rows]
def add_msg(cid, role, content, image=None):
    conn=get_db(); cur=conn.cursor()
    cur.execute("INSERT INTO messages_web(chat_id,role,content,image,created_at) VALUES(%s,%s,%s,%s,%s)",(int(cid),role,content or '',image,now_iso()))
    conn.commit(); cur.close(); conn.close()
def get_msgs(cid):
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM messages_web WHERE chat_id=%s ORDER BY id",(int(cid),))
    rows=cur.fetchall(); cur.close(); conn.close(); return [dict(r) for r in rows]
def hist(cid):
    m=get_msgs(cid)
    if len(m)<=MAX_HISTORY: return m or []
    return (m[:10]+m[-MAX_HISTORY+10:]) if len(m)>10 else m
def set_title(cid,t):
    conn=get_db(); cur=conn.cursor(); cur.execute("UPDATE chats_web SET title=%s WHERE id=%s",(t[:50],int(cid))); conn.commit(); cur.close(); conn.close()
def del_chat(uid,cid):
    conn=get_db(); cur=conn.cursor()
    cur.execute("DELETE FROM messages_web WHERE chat_id=%s",(int(cid),))
    cur.execute("DELETE FROM chats_web WHERE id=%s AND user_id=%s",(int(cid),str(uid)))
    conn.commit(); cur.close(); conn.close()

tok=None; tok_t=0
def get_tok():
    global tok, tok_t
    if tok and time.time()-tok_t<180: return tok
    for _ in range(3):
        try:
            r=requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={"Content-Type":"application/x-www-form-urlencoded","Accept":"application/json",
                         "RqUID":str(_uuid.uuid4()),"Authorization":"Basic "+GIGACHAT_AUTH_KEY},
                data="scope=GIGACHAT_API_PERS",timeout=14,verify=False)
            if r.status_code==200:
                j=r.json()
                if j.get("access_token"): tok=j["access_token"]; tok_t=time.time(); return tok
        except Exception: pass
        time.sleep(0.7)
    tok=None; return None
def giga(hlist, sysp, max_tok=2200):
    try:
        t=get_tok()
        if not t: return None
        msgs=[{"role":"system","content":sysp[:3000]}]+[{"role":h.get("role","user"),"content":(h.get("content") or "")[:1200]} for h in hlist[-16:] if h.get("role") in ("user","assistant")]
        r=requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization":"Bearer "+t,"Content-Type":"application/json","Accept":"application/json"},
            json={"model":"GigaChat-Pro","messages":msgs,"temperature":0.85,"max_tokens":max_tok},timeout=GIGA_TIMEOUT,verify=False)
        if r.status_code==200:
            try: return r.json()["choices"][0]["message"]["content"]
            except Exception: return None
    except Exception: pass
    return None
def ygpt(text, sysp):
    try:
        r=requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={"Authorization":"Api-Key "+YANDEX_API_KEY,"Content-Type":"application/json"},
            json={"modelUri":"gpt://"+FOLDER_ID+"/yandexgpt/latest","completionOptions":{"temperature":0.7,"maxTokens":900,"stream":False},
                  "messages":[{"role":"system","text":sysp[:1500]},{"role":"user","text":text}]},timeout=YGPT_TIMEOUT)
        if r.status_code==200:
            try: return r.json()["result"]["alternatives"][0]["message"]["text"]
            except Exception: return None
    except Exception: pass
    return None
def openai_call(hlist, sysp, max_tok=1400):
    if not OPENAI_API_KEY: return None
    try:
        msgs=[{"role":"system","content":sysp[:3000]}]+[{"role":h.get("role","user"),"content":(h.get("content") or "")[:1200]} for h in hlist[-16:] if h.get("role") in ("user","assistant")]
        r=requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":"Bearer "+OPENAI_API_KEY,"Content-Type":"application/json"},
            json={"model":"gpt-4o-mini","messages":msgs,"temperature":0.85,"max_tokens":max_tok},timeout=GIGA_TIMEOUT)
        if r.status_code==200:
            try: return r.json()["choices"][0]["message"]["content"]
            except Exception: return None
    except Exception: pass
    return None
def deepseek_call(hlist, sysp, max_tok=1800):
    if not DEEPSEEK_API_KEY: return None
    try:
        msgs=[{"role":"system","content":sysp[:3000]}]+[{"role":h.get("role","user"),"content":(h.get("content") or "")[:1200]} for h in hlist[-16:] if h.get("role") in ("user","assistant")]
        r=requests.post("https://api.deepseek.com/chat/completions",
            headers={"Authorization":"Bearer "+DEEPSEEK_API_KEY,"Content-Type":"application/json"},
            json={"model":"deepseek-chat","messages":msgs,"temperature":0.85,"max_tokens":max_tok},timeout=GIGA_TIMEOUT)
        if r.status_code==200:
            try: return r.json()["choices"][0]["message"]["content"]
            except Exception: return None
    except Exception: pass
    return None
def gemini_call(text, sysp):
    if not GEMINI_API_KEY: return None
    try:
        body={"contents":[{"role":"user","parts":[{"text":sysp[:3000]+"\n\nЗадача:\n"+text}]}],
              "generationConfig":{"temperature":0.8,"maxOutputTokens":1600}}
        r=requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key="+GEMINI_API_KEY,
            headers={"Content-Type":"application/json"},json=body,timeout=GIGA_TIMEOUT)
        if r.status_code==200:
            try:
                parts=r.json()["candidates"][0]["content"]["parts"]
                return "".join(p.get("text","") for p in parts) or None
            except Exception: return None
    except Exception: pass
    return None
def describe_img(b64):
    for attempt in range(3):
        try:
            t=get_tok()
            if not t: return None
            payload={"model":"GigaChat-Pro","messages":[
                {"role":"system","content":"Ты — эксперт по анализу изображений. Подробно, живо опиши на русском: объекты, людей, эмоции, окружение, детали, цвета, текст на картинке."},
                {"role":"user","content":[
                    {"type":"text","text":"Подробно опиши, что изображено на этой фотографии."},
                    {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+b64}}
                ]}],"temperature":0.6,"max_tokens":900}
            r=requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={"Authorization":"Bearer "+t,"Content-Type":"application/json","Accept":"application/json"},
                json=payload,timeout=GIGA_TIMEOUT,verify=False)
            if r.status_code==200:
                try:
                    c=r.json()["choices"][0]["message"]["content"]
                    if c and len(c.strip())>3: return c.strip()
                except Exception: return None
        except Exception: pass
        time.sleep(1.0)
    return None

SUPER="""ТЫ — AWESOME AI ULTIMATE, самая мощная нейросеть уровня ChatGPT.
РОССИЯ, МОСКВА. Сегодня: {d}, время: {t} (МСК).
{memory}
СТИЛЬ: живой, тёплый, глубокий интеллект. Конкретика, цифры, структура.
ФОРМАТ: разделы **1. Название**, важное **жирным**, эмодзи.
Если дано описание изображения — отвечай по нему."""

def smart_answer(uid, text, history, img_desc=None, doc=None, has_img=False):
    mem=get_memory(uid)
    sp=SUPER.format(d=gdate(), t=gm().strftime('%H:%M'),
        memory=("Помнишь о пользователе:\n"+"\n".join("• "+f for f in mem)) if mem else "")
    if img_desc: sp += "\n\nАНАЛИЗ ИЗОБРАЖЕНИЯ:\n"+img_desc
    if doc: sp += "\nДокумент: "+doc[:3000]
    tl=(text or "").lower().strip()
    try: extract_facts(uid, text)
    except Exception: pass
    if has_img and not text.strip() and not img_desc:
        return "📷 Вижу фото, но сервис анализа изображений сейчас недоступен (хостинг блокирует внешний трафик к vision-модели). Опиши словами, что на нём — и я помогу!"
    hfull=history+[{"role":"user","content":text or "Опиши изображение" if has_img else (text or "Опиши")}]
    res=None
    a=giga(hfull, sp)
    if a and len(a)>4: res=a
    else:
        b=ygpt(text, sp)
        if b and len(b)>4: res=b
        else:
            e=gemini_call(text, sp)
            if e and len(e)>4: res=e
            else:
                c=openai_call(hfull, sp)
                if c and len(c)>4: res=c
                else:
                    d=deepseek_call(hfull, sp)
                    if d and len(d)>4: res=d
    if res: return res
    if img_desc: return "Я вижу это так:\n\n"+img_desc
    # ==== 30+ МЕХАНИЧЕСКИХ ФУНКЦИЙ ====
    if re.search(r'\d+\s*[\+\-\*\/\(\)]\s*\d+', tl) and ("посчитай" in tl or "сколько будет" in tl or "вычисли" in tl or re.search(r'[0-9]+\s*[\/\*\+\-]\s*[0-9]',tl)):
        try:
            expr=re.sub(r'[^0-9+\-*/(). ]','',text)
            if re.search(r'\d+\s*[\/]\s*0',expr): return "На ноль делить нельзя! 😅"
            resx=eval(expr)
            if isinstance(resx,float) and resx.is_integer(): resx=int(resx)
            return "🧮 Результат: **"+str(resx)+"**"
        except Exception: return "Не понял пример. Напиши как: «сколько будет 12*4+8»"
    unit_conv=[(('км в мили','мили в км'),0.621371),(('кг в фунты','фунты в кг'),2.20462),
               (('метры в футы','футы в метры'),3.28084),(('литры в галлоны','галлоны в литры'),0.264172),
               (('градусы в радианы','радианы в градусы'),0.0174533)]
    for words,factor in unit_conv:
        if any(w in tl for w in words):
            m=re.search(r'([\d.]+)',tl)
            if m:
                try:
                    val=float(m.group(1))*factor
                    out=words[0].split(' в ')[1] if ' в ' in words[0] else words[0]
                    return "📏 **"+m.group(1)+"** → **"+str(round(val,2))+"** "+out
                except Exception: return "Не понял число."
    if "парол" in tl or "password" in tl:
        ln=re.search(r'(\d+)',tl); length=int(ln.group(1)) if ln else 12; length=max(6,min(length,32))
        chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return "🔐 Пароль: `"+"".join(random.choice(chars) for _ in range(length))+"` (длина "+str(length)+")"
    if "кубик" in tl: return "🎲 Кубик: **"+str(random.randint(1,6))+"**"
    if "монет" in tl or "орел" in tl or "решка" in tl: return "🪙 Выпало: **"+random.choice(["Орёл","Решка"])+"**"
    if ("случайное число" in tl or "рандом" in tl):
        m=re.findall(r'(\d+)\s*(?:до|из)\s*(\d+)',tl)
        if m: return "🎯 Случайное: **"+str(random.randint(int(m[0][0]),int(m[0][1])))+"**"
        return "🎲 Случайное: **"+str(random.randint(1,100))+"**"
    if "таймер" in tl or "сколько секунд" in tl:
        m=re.search(r'(\d+)\s*(минут|секунд|часов)',tl)
        if m:
            n=int(m.group(1)); unit=m.group(2)
            sec=n*(60 if unit.startswith('мин') else 3600 if unit.startswith('час') else 1)
            return "⏱️ "+str(n)+" "+unit+" = **"+str(sec)+"** секунд."
    if "задач" in tl or "to-do" in tl or "список дел" in tl:
        if "добавь" in tl or "запиши" in tl:
            task=re.sub(r'(добавь|запиши|в список|задач|задачу|to-do|дел)','',tl).strip()[:200]
            if len(task)>2: remember(uid,"Задача: "+task); return "✅ Добавил задачу: "+task
        tasks=[f for f in get_memory(uid,50) if f.startswith("Задача:")]
        return "📋 Задачи:\n"+"\n".join("• "+f.replace("Задача: ","") for f in tasks) if tasks else "Задач нет. Напиши «добавь задачу купить молоко»."
    if "дней до" in tl or "дней осталось" in tl:
        m=re.search(r'(\d{1,2})[.\/-](\d{1,2})(?:[.\/-](\d{2,4}))?',tl)
        if m:
            try:
                dd=datetime(int(m.group(3) or gm().year),int(m.group(2)),int(m.group(1)))
                days=(dd.replace(tzinfo=MOSCOW_TZ)-gm()).days
                return "📆 Осталось **"+str(days)+"** дн." if days>=0 else "Дата прошла "+str(-days)+" дн. назад."
            except: return "Формат: «сколько дней до 25.12»"
    if "процент" in tl or "%" in tl:
        m=re.search(r'(\d+(?:[.,]\d+)?)\s*%?\s*(?:от|из)\s*(\d+(?:[.,]\d+)?)',tl.replace(',','.'))
        if m:
            try:
                p=float(m.group(1)); total=float(m.group(2))
                return "🧮 "+m.group(1)+"% от "+m.group(2)+" = **"+str(round(total*p/100,2))+"**"
            except: pass
    if "квадрат" in tl or "в квадрате" in tl:
        m=re.search(r'(\d+)',tl)
        if m: return "🧮 "+m.group(1)+"² = **"+str(int(m.group(1))**2)+"**"
    if "корень" in tl:
        m=re.search(r'(\d+)',tl)
        if m: return "√"+m.group(1)+" ≈ **"+str(round(float(m.group(1))**0.5,3))+"**"
    if "степень" in tl or "в степени" in tl:
        m=re.search(r'(\d+)\s*(?:\^|в степени)\s*(\d+)',tl)
        if m: return "🧮 "+m.group(1)+"^"+m.group(2)+" = **"+str(int(m.group(1))**int(m.group(2)))+"**"
    if "бинар" in tl or "в двоичн" in tl:
        m=re.search(r'(\d+)',tl)
        if m: return "💾 "+m.group(1)+" в двоичной = **"+bin(int(m.group(1)))[2:]+"**"
    if "в шестнадцат" in tl or "hex" in tl:
        m=re.search(r'(\d+)',tl)
        if m: return "🔢 "+m.group(1)+" в hex = **"+hex(int(m.group(1)))[2:].upper()+"**"
    if "факториал" in tl:
        m=re.search(r'(\d+)',tl)
        if m:
            n=int(m.group(1)); f=1
            for i in range(2,n+1): f*=i
            return "➗ "+m.group(1)+"! = **"+str(f)+"**"
    if "среднее" in tl or "avg" in tl:
        nums=re.findall(r'(\d+(?:[.,]\d+)?)',tl.replace(',','.'))
        if len(nums)>=2:
            vals=[float(x) for x in nums]
            return "📊 Среднее = **"+str(round(sum(vals)/len(vals),2))+"**"
    if "сумму" in tl or "сложи" in tl:
        nums=re.findall(r'(\d+(?:[.,]\d+)?)',tl.replace(',','.'))
        if len(nums)>=2:
            vals=[float(x) for x in nums]
            return "➕ Сумма = **"+str(round(sum(vals),2))+"**"
    if "привет" in tl or "здравств" in tl or tl in ["ку","хай","прив"]:
        return "Привет! ✨ Умею считать, конвертировать, генерить пароли, бросать кубик, считать дни, вести задачи, проценты, квадраты, корни, степени, бинар/hex, факториалы, среднее и суммы. Что делаем?"
    if "время" in tl and ("сейчас" in tl or "сколько" in tl):
        return "Сейчас "+gm().strftime('%H:%M:%S')+" (Москва), дата: "+gdate()+"."
    if "дата" in tl or "какое сегодня число" in tl:
        return "Сегодня "+gdate()+", "+['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье'][gm().weekday()]+"."
    if "переведи" in tl or "перевод" in tl:
        target='en' if "на англ" in tl else ('de' if "на немец" in tl else 'ru')
        txt=re.sub(r'(переведи|на английский|на русский|на немецкий|пожалуйста|на .*?)','',tl,flags=re.I).strip()
        return "Перевод: "+translate(txt[:500],target) if txt else "Что перевести?"
    if "шутк" in tl or "анекдот" in tl or "рассмеши" in tl:
        return "😂 "+random.choice(["Почему программист перепутал Хэллоуин и Рождество? Oct 31 == Dec 25","Админ заходит в бар, а там все буферы переполнены"])
    if "комплимент" in tl or "похвали" in tl: return "Ты потрясающий! Умный, любопытный и с отличным вкусом! 🌟"
    if "крипт" in tl or "биткоин" in tl:
        c=crypto(); return c if c else "Не удалось получить цену."
    if "курс" in tl or "доллар" in tl or "валют" in tl:
        c=currency(); return c if c else "Не удалось получить курс."
    if "погода" in tl:
        m=re.search(r'(в|в городе)\s+([a-zA-Zа-яА-Я\- ]+)',tl)
        if m:
            w=weather(m.group(2).strip()); return w if w else "Напиши: погода в [город]"
        return "Напиши: погода в [город]"
    if "запомни" in tl or "выучи" in tl:
        fact=re.sub(r'(запомни|выучи|что)\s*','',tl).strip()[:500]
        if len(fact)>3: remember(uid,fact); return "Запомнил: ✅ "+fact
        return "Что запомнить?"
    if "что ты помнишь" in tl or "память" in tl:
        return "Что я помню о тебе:\n"+"\n".join("• "+f for f in mem) if mem else "Пока ничего. Скажи «запомни...»."
    if "кто ты" in tl or "что ты умеешь" in tl:
        return "Я AWESOME AI ULTIMATE ✨\n**Механические функции**:\n1. Калькулятор\n2. Конвертер единиц\n3. Пароли\n4. Кубик/монета/рандом\n5. Таймер/секунды\n6. Задачи (todo)\n7. Дни до даты\n8. Проценты\n9. Квадраты/корни/степени\n10. Бинар/hex\n11. Факториал\n12. Среднее/сумма\n13. Память\n14. Погода/валюты/крипта\n15. Перевод\n\nЧто пробуем?"
    return "Обрабатываю... Напиши конкретно. Примеры: «посчитай 15% от 200», «переведи 5 км в мили», «сгенерируй пароль 16», «брось кубик», «сколько дней до 25.12», «5 в степени 3»."

def gen_img(prompt):
    try:
        c=prompt
        for w in ['нарисуй','сгенерируй','покажи','картинку','изображение']: c=c.replace(w,'').strip()
        if not c: c=prompt
        r=requests.get("https://image.pollinations.ai/prompt/"+urllib.parse.quote(c)+"?width=1024&height=1024&nologo=true",headers={"User-Agent":"Mozilla/5.0"},timeout=25)
        if r.status_code==200 and len(r.content)>1000: return base64.b64encode(r.content).decode()
    except Exception: pass
    return None
def translate(text,target='ru'):
    try:
        r=requests.post("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl="+target+"&dt=t&q="+urllib.parse.quote(text[:5000]),timeout=8)
        if r.status_code==200: return "".join(x[0] for x in r.json()[0] if x[0])
    except Exception: pass
    return text
def weather(city):
    try:
        r=requests.get("https://api.openweathermap.org/data/2.5/weather?q="+urllib.parse.quote(city)+"&appid=4c8f5c0b8a9f2c5d6e7f8g9h0i1j2k3l&units=metric&lang=ru",timeout=SEARCH_TIMEOUT)
        if r.status_code==200:
            d=r.json(); return "Погода в "+city+": "+str(round(d['main']['temp']))+"°C, "+d['weather'][0]['description']
    except Exception: pass
    return None
def currency():
    try:
        r=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=SEARCH_TIMEOUT)
        rates=r.json().get('rates',{}); usd=rates.get('RUB','?'); eur=usd/rates.get('EUR',1) if rates.get('EUR') else '?'
        return "Курс: USD "+str(round(usd,2))+"₽, EUR "+str(round(eur,2))+"₽"
    except Exception: return None
def crypto():
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd",timeout=SEARCH_TIMEOUT)
        d=r.json(); return "BTC $"+str(d.get('bitcoin',{}).get('usd','?'))+", ETH $"+str(d.get('ethereum',{}).get('usd','?'))
    except Exception: return None
def read_pdf(b64):
    try:
        import fitz
        raw=base64.b64decode(b64.split(',')[-1]); doc=fitz.open(stream=raw,filetype="pdf")
        return "".join(page.get_text() for page in doc)[:5000] or "PDF без текста"
    except Exception: return "PDF загружен"

@app.route('/favicon.ico')
def favicon():
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22e0a8"/><stop offset=".5" stop-color="#5b8cff"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs><rect width="100" height="100" rx="28" fill="url(#g)"/><path d="M50 16 L82 84 H69 L61 63 H39 L31 84 H18 Z M45 52 H55 L50 38 Z" fill="#fff"/></svg>'
    return app.response_class(svg, mimetype='image/svg+xml')

@app.route('/')
def index(): return render_template_string(INDEX_HTML)

@app.route('/api/diag')
def diag():
    try:
        c=get_db(); c.close()
        prov={'gigachat':bool(GIGACHAT_AUTH_KEY),'yandex':bool(YANDEX_API_KEY and FOLDER_ID),
              'openai':bool(OPENAI_API_KEY),'deepseek':bool(DEEPSEEK_API_KEY),'gemini':bool(GEMINI_API_KEY)}
        return jsonify({'ok':True,'db':'postgres-ok','providers':prov})
    except Exception as e: return jsonify({'ok':False,'error':str(e)})

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        d=request.json
        ok,msg=reg_user(str(d.get('login','')).strip(),str(d.get('name','')).strip(),str(d.get('password','')))
        if not ok: return jsonify({'ok':False,'error':msg})
        session.permanent=True; session['user_id']=str(d.get('login')).strip(); session['name']=str(d.get('name')).strip()
        return jsonify({'ok':True})
    except Exception as e: return jsonify({'ok':False,'error':'Ошибка: '+str(e)}),400
@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        d=request.json; login=str(d.get('login','')).strip()
        ok,msg=login_user(login,str(d.get('password','')))
        if not ok: return jsonify({'ok':False,'error':msg})
        u=get_user_by_login(login)
        session.permanent=True; session['user_id']=login; session['name']=u.get('name') if u else login
        return jsonify({'ok':True})
    except Exception as e: return jsonify({'ok':False,'error':'Ошибка: '+str(e)}),400
@app.route('/api/logout',methods=['POST'])
def api_logout(): session.clear(); return jsonify({'ok':True})
@app.route('/api/me')
def api_me():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False})
    u=get_user(uid)
    if not u: session.clear(); return jsonify({'ok':False})
    return jsonify({'ok':True,'user_id':uid,'name':session.get('name') or u.get('name'),'theme':u.get('theme','dark'),'avatar':u.get('avatar','')})
@app.route('/api/status')
def api_status():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False})
    s=eff_status(uid); u=get_user(uid) or {}
    if s['is_owner']: st="Владелец"; lim="∞"
    elif s['is_admin']: st="Админ"; lim="∞"
    elif s['premium']: st="Premium"; lim="∞"
    else: st="Free"; lim=str(max(0,FREE_LIMIT-int(u.get('messages_today',0) or 0)))+"/"+str(FREE_LIMIT)
    return jsonify({'ok':True,'premium':bool(s['premium']),'is_admin':bool(s['is_admin']),'is_owner':bool(s['is_owner']),
                    'premium_expires':fmt_date(s['premium_expires']) if s['premium'] else None,'status_text':st,'limit_text':lim,
                    'messages_today':int(u.get('messages_today',0) or 0),'free_limit':FREE_LIMIT,'level':s['level'],'xp':s['xp']})
@app.route('/api/chat', methods=['POST'])
def api_chat():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False,'error':'Авторизуйся'})
    if not can_send(uid): return jsonify({'ok':False,'error':'Дневной лимит 50 исчерпан. Купи Premium для безлимита!'})
    d=request.json; msg=d.get('message','').strip(); cid=d.get('chat_id'); img=d.get('image'); doc=d.get('document')
    if not msg and not img and not doc: return jsonify({'ok':False,'error':'Пустое'})
    if not cid: cid=create_chat(uid)
    h=hist(cid); idesc=None; dtext=None; has_img=bool(img)
    if img:
        try:
            raw=base64.b64decode(img.split(',')[-1])
            if HAS_PIL:
                im=Image.open(io.BytesIO(raw)).convert('RGB'); im.thumbnail((1200,1200))
                b=io.BytesIO(); im.save(b,'JPEG',quality=88); idesc=describe_img(base64.b64encode(b.getvalue()).decode())
            else: idesc=describe_img(img.split(',')[-1])
        except Exception: idesc=None
    if doc: dtext=read_pdf(doc.get('data','')) if doc.get('type')=='pdf' else "Документ: "+doc.get('name','')
    add_msg(cid,'user',msg,img)
    response=smart_answer(uid,msg,h,idesc,dtext,has_img)
    try: incr(uid)
    except Exception: pass
    add_msg(cid,'assistant',response)
    try:
        ms=get_msgs(cid); fu=next((m for m in ms if m['role']=='user' and m.get('content')),None)
        if fu: set_title(cid,fu['content'][:40])
    except Exception: pass
    return jsonify({'ok':True,'response':response,'chat_id':cid})
@app.route('/api/chats')
def api_chats():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False})
    chats=get_chats(uid)
    for c in chats:
        c['messages']=get_msgs(c['id']) or []
    return jsonify({'ok':True,'chats':chats})
@app.route('/api/chat/new',methods=['POST'])
def api_chat_new():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False})
    return jsonify({'ok':True,'chat_id':create_chat(uid)})
@app.route('/api/chat/delete',methods=['POST'])
def api_chat_delete():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False})
    del_chat(uid,request.json.get('chat_id')); return jsonify({'ok':True})
@app.route('/api/search',methods=['POST'])
def api_search():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False})
    q=request.json.get('q','').lower(); res=[]
    for c in get_chats(uid):
        for m in get_msgs(c['id']):
            if q in str(m.get('content','')).lower():
                res.append({'chat_id':c['id'],'title':c['title'],'snippet':str(m.get('content',''))[:80]}); break
    return jsonify({'ok':True,'results':res})
@app.route('/api/translate',methods=['POST'])
def api_translate():
    d=request.json; return jsonify({'ok':True,'translated':translate(d.get('text',''),d.get('target','ru'))})
@app.route('/api/draw',methods=['POST'])
def api_draw():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False,'error':'Авторизуйся'})
    if not can_send(uid): return jsonify({'ok':False,'error':'Лимит! Купи Premium'})
    img=gen_img(request.json.get('prompt',''))
    if img:
        try: incr(uid)
        except Exception: pass
        return jsonify({'ok':True,'image':img})
    return jsonify({'ok':False,'error':'Не удалось'})
@app.route('/api/profile')
def api_profile():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False})
    u=get_user(uid); s=eff_status(uid)
    return jsonify({'ok':True,'user_id':uid,'name':u.get('name'),'login':u.get('login'),'theme':u.get('theme','dark'),
                    'avatar':u.get('avatar',''),'premium':bool(s['premium']),'is_admin':bool(s['is_admin']),'is_owner':bool(s['is_owner']),
                    'level':s['level'],'xp':s['xp'],'premium_expires':fmt_date(s['premium_expires']) if s['premium'] else None,
                    'messages_today':int(u.get('messages_today',0) or 0),'joined_at':u.get('joined_at')})
@app.route('/api/settings',methods=['POST'])
def api_settings():
    uid=session.get('user_id')
    if not uid: return jsonify({'ok':False})
    d=request.json
    upd(uid,name=d.get('name'),theme=d.get('theme'),avatar=d.get('avatar'))
    if d.get('name'): session['name']=d['name']
    return jsonify({'ok':True})

def admin_check():
    uid=session.get('user_id')
    if not uid: return None,False,"Нет авторизации"
    if not eff_status(uid)['is_owner']: return None,False,"Нет доступа"
    return uid,True,""
def parse_duration(num,unit):
    try: n=int(num)
    except: return None
    now=gm()
    if unit=='s': return (now+timedelta(seconds=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit=='min': return (now+timedelta(minutes=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit=='h': return (now+timedelta(hours=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit=='d': return (now+timedelta(days=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit=='w': return (now+timedelta(weeks=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit=='mo': return (now+relativedelta(months=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit=='y': return (now+relativedelta(years=n)).strftime('%Y-%m-%d %H:%M:%S')
    return None
@app.route('/api/admin/stats')
def admin_stats():
    uid,ok,err=admin_check()
    if not ok: return jsonify({'ok':False,'error':err})
    conn=get_db(); cur=conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users"); total=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE premium=1"); prem=cur.fetchone()[0]
    cur.execute("SELECT user_id,name,premium,is_admin,premium_expires,level,xp FROM users ORDER BY joined_at DESC LIMIT 300")
    users=cur.fetchall(); cur.close(); conn.close()
    return jsonify({'ok':True,'total':total,'premium':prem,
                    'users':[{'id':r[0],'name':r[1],'premium':r[2],'is_admin':r[3],'expires':r[4],'level':r[5],'xp':r[6]} for r in users]})
@app.route('/api/resetadmin')
def resetadmin():
    try:
        good = hashlib.sha256("qawsedrf2346".encode()).hexdigest()
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE login='admin'")
        exists = cur.fetchone()
        if exists:
            cur.execute("UPDATE users SET password=%s, is_admin=1, is_owner=1 WHERE user_id='admin'", (good,))
        else:
            cur.execute("INSERT INTO users(user_id,login,name,password,messages_today,last_reset,is_admin,is_owner,theme,joined_at,xp,level) VALUES('admin','admin','AWESOME',%s,0,%s,1,1,'dark',%s,0,1)",
                        (good, gm().strftime('%Y-%m-%d'), now_iso()))
            cur.execute("INSERT INTO total_stats_web(user_id,total_messages) VALUES('admin',0) ON CONFLICT DO NOTHING")
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True, 'msg': 'Пароль admin сброшен на qawsedrf2346', 'hash': good})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
@app.route('/api/admin/give',methods=['POST'])
def admin_give():
    uid,ok,err=admin_check()
    if not ok: return jsonify({'ok':False,'error':err})
    d=request.json; target=str(d.get('user_id','')).strip(); action=d.get('action')
    if not get_user(target): return jsonify({'ok':False,'error':'Пользователь не найден'})
    try:
        if action=='give_prem':
            exp=parse_duration(d.get('num',30),d.get('unit','d'))
            if not exp: return jsonify({'ok':False,'error':'Неверный срок'})
            upd(target,premium=1,premium_expires=exp)
        elif action=='take_prem': upd(target,premium=0,premium_expires=None)
        elif action=='give_admin': upd(target,is_admin=1)
        elif action=='take_admin': upd(target,is_admin=0)
        elif action=='delete_user':
            conn=get_db(); cur=conn.cursor(); cur.execute("DELETE FROM users WHERE user_id=%s",(target,)); conn.commit(); cur.close(); conn.close()
        elif action=='reset_pass':
            npw=d.get('password','')
            if len(npw)<3: return jsonify({'ok':False,'error':'Пароль мин.3'})
            upd(target,password=hash_pw(npw))
    except Exception as e: return jsonify({'ok':False,'error':'Ошибка: '+str(e)})
    return jsonify({'ok':True})

# ================= HTML (клиентское переключение чатов) =================
INDEX_HTML = r"""<!DOCTYPE html><html lang="ru"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>✨ Awesome AI — самая умная нейросеть</title>
<link rel="icon" href="/favicon.ico"><meta name="theme-color" content="#07090d">
<style>
:root{--bg:#07090d;--panel:rgba(18,23,32,.62);--panel2:rgba(24,30,42,.74);--line:rgba(255,255,255,.09);--text:#f0f4f8;--muted:#98a6b6;--accent:#22e0a8;--accent2:#5b8cff;--accent3:#a855f7;--gold:#ffd76a;--danger:#ff5c7a}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Söhne','Segoe UI',system-ui,sans-serif}
html,body{height:100%}
body{background:var(--bg);color:var(--text);overflow:hidden;-webkit-font-smoothing:antialiased}
.scene{position:fixed;inset:0;z-index:0;overflow:hidden;background:
radial-gradient(120% 120% at 15% 10%,#0d2b24 0%,transparent 50%),
radial-gradient(120% 120% at 85% 20%,#141a3d 0%,transparent 50%),
radial-gradient(120% 120% at 50% 100%,#1b1030 0%,transparent 55%),#07090d}
.glow{position:absolute;border-radius:50%;filter:blur(70px);mix-blend-mode:screen;will-change:transform;animation:drift var(--d,20s) ease-in-out infinite alternate}
.g1{--d:16s;width:520px;height:520px;background:radial-gradient(circle,#16d6a4,transparent 65%);top:-140px;left:-100px;opacity:.5}
.g2{--d:22s;width:460px;height:460px;background:radial-gradient(circle,#4f7dff,transparent 65%);bottom:-120px;right:-80px;opacity:.45}
.g3{--d:28s;width:400px;height:400px;background:radial-gradient(circle,#b26bff,transparent 65%);top:45%;left:52%;opacity:.4}
.g4{--d:34s;width:360px;height:360px;background:radial-gradient(circle,#ffd76a,transparent 68%);top:8%;right:22%;opacity:.22}
@keyframes drift{0%{transform:translate(0,0) scale(1)}100%{transform:translate(var(--tx,60px),var(--ty,40px)) scale(1.18)}}
.star{position:absolute;border-radius:50%;background:#fff;opacity:.7;animation:tw 3s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.12}50%{opacity:.85}}
.app{position:relative;z-index:1;display:flex;height:100vh}
.sidebar{width:280px;background:var(--panel);backdrop-filter:blur(22px) saturate(1.4);-webkit-backdrop-filter:blur(22px) saturate(1.4);border-right:1px solid var(--line);display:flex;flex-direction:column;transition:margin-left .3s cubic-bezier(.4,0,.2,1);z-index:60}
.app.collapsed .sidebar{margin-left:-280px}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.brand{display:flex;align-items:center;gap:11px;padding:16px 14px 12px}
.brand .logo{width:38px;height:38px;border-radius:11px;background:conic-gradient(from 180deg,#22e0a8,#5b8cff,#a855f7,#22e0a8);display:flex;align-items:center;justify-content:center;box-shadow:0 6px 22px rgba(34,224,168,.45);animation:spin 8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.brand .nm{font-weight:800;font-size:17px;background:linear-gradient(90deg,#22e0a8,#5b8cff);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.new-chat{margin:4px 12px 10px;padding:12px 14px;background:linear-gradient(135deg,rgba(34,224,168,.16),rgba(91,140,255,.14));border:1px solid var(--line);border-radius:13px;color:#fff;cursor:pointer;font-size:14px;display:flex;align-items:center;gap:9px;font-weight:600;transition:.2s}.new-chat:hover{border-color:rgba(34,224,168,.6);transform:translateY(-1px)}
.chat-list{flex:1;overflow-y:auto;padding:4px 8px}
.chat-item{padding:11px 13px;border-radius:11px;cursor:pointer;margin-bottom:3px;font-size:13.5px;display:flex;align-items:center;gap:9px;transition:.15s;border:1px solid transparent}.chat-item:hover,.chat-item.active{background:rgba(255,255,255,.05);border-color:var(--line)}
.chat-item .t{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.chat-item .del{opacity:0;background:none;border:none;color:var(--muted);cursor:pointer;font-size:14px;padding:2px 4px}.chat-item:hover .del{opacity:1}
.side-foot{padding:8px;border-top:1px solid var(--line)}
.side-btn{display:flex;align-items:center;gap:10px;width:100%;padding:9px 11px;border:none;background:none;color:var(--text);cursor:pointer;font-size:13.5px;border-radius:11px;text-align:left}.side-btn:hover{background:rgba(255,255,255,.05)}
.side-btn .ic{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:15px;flex-shrink:0}
.prem-btn{margin:8px 10px;padding:12px;border-radius:13px;border:none;cursor:pointer;font-weight:800;font-size:14px;color:#241503;background:linear-gradient(120deg,#ffe08a,#ffb347,#ff7a59);background-size:220% 220%;animation:grad 4s ease infinite;display:flex;align-items:center;justify-content:center;gap:8px;box-shadow:0 8px 26px rgba(255,170,70,.4);transition:.2s}.prem-btn:hover{transform:translateY(-2px) scale(1.02)}
.prem-btn.act{background:linear-gradient(120deg,#22e0a8,#34d399);color:#04241a}
@keyframes grad{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.topbar{height:54px;display:flex;align-items:center;gap:10px;padding:0 18px;border-bottom:1px solid var(--line);flex-shrink:0;background:rgba(7,9,13,.45);backdrop-filter:blur(14px)}
.burger{background:none;border:none;color:var(--text);font-size:20px;cursor:pointer;padding:6px;border-radius:9px}.burger:hover{background:rgba(255,255,255,.07)}
.topbar .ct{flex:1;text-align:center;font-size:14px;color:var(--muted);font-weight:500}
.pill{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid var(--line);background:rgba(255,255,255,.04)}
.messages{flex:1;overflow-y:auto}
.welcome{max-width:820px;margin:0 auto;padding:7vh 24px 24px;text-align:center;animation:fadeUp .6s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
.welcome h1{font-size:clamp(30px,6vw,48px);font-weight:800;margin-bottom:12px;background:linear-gradient(90deg,#22e0a8,#5b8cff,#a855f7,#ffb347,#22e0a8);background-size:300% auto;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;animation:gr 6s linear infinite;filter:drop-shadow(0 4px 30px rgba(34,224,168,.25))}
@keyframes gr{to{background-position:300% center}}
.welcome p{color:var(--muted);font-size:17px;margin-bottom:30px}
.sugg-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;max-width:720px;margin:0 auto}
.sugg{border:1px solid var(--line);border-radius:16px;padding:16px;cursor:pointer;font-size:13px;color:var(--muted);text-align:left;background:var(--panel);backdrop-filter:blur(10px);transition:.2s}.sugg:hover{background:var(--panel2);transform:translateY(-3px);border-color:rgba(34,224,168,.5)}
.msgrow{display:flex;gap:15px;padding:22px 26px;border-bottom:1px solid var(--line);animation:fadeUp .25s ease}
.msgrow.user{background:rgba(255,255,255,.015)}.msgrow.ai{background:rgba(18,23,32,.4)}
.msgrow .mb{max-width:820px;width:100%;margin:0 auto;font-size:15.5px;line-height:1.75;white-space:pre-wrap;word-break:break-word}
.msgrow .mb b{font-weight:700}.msgrow .mb .h{display:block;font-weight:800;font-size:17px;margin:18px 0 6px}.msgrow .mb .h:first-child{margin-top:0}
.msgrow .ma{width:34px;height:34px;border-radius:10px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-weight:700;box-shadow:0 6px 18px rgba(0,0,0,.35)}
.msgrow.user .ma{background:conic-gradient(from 180deg,#22e0a8,#5b8cff);color:#04121c}.msgrow .mb img{max-width:100%;max-height:420px;border-radius:14px;margin-top:10px;box-shadow:0 10px 34px rgba(0,0,0,.5);border:1px solid var(--line)}
.typing span{display:inline-block;width:7px;height:7px;border-radius:50%;background:#22e0a8;margin-right:5px;animation:blink 1.2s infinite}.typing span:nth-child(2){animation-delay:.2s}.typing span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.2;transform:scale(1)}40%{opacity:1;transform:scale(1.3)}}
.inputarea{padding:14px 24px;flex-shrink:0}
.attach-preview{max-width:820px;margin:0 auto 8px;display:none;gap:9px;align-items:center;background:var(--panel2);border:1px solid var(--line);border-radius:15px;padding:8px}
.attach-preview img{width:52px;height:52px;object-fit:cover;border-radius:9px}.attach-preview .an{flex:1;font-size:13px;color:var(--muted);overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.attach-preview .rm{background:none;border:none;color:var(--muted);cursor:pointer;font-size:18px}
.inputwrap{max-width:820px;margin:0 auto;display:flex;align-items:flex-end;gap:6px;background:var(--panel2);backdrop-filter:blur(16px);border:1px solid var(--line);border-radius:28px;padding:10px 12px;transition:.2s}.inputwrap:focus-within{border-color:rgba(34,224,168,.6);box-shadow:0 0 0 4px rgba(34,224,168,.12)}
textarea{flex:1;background:none;border:none;outline:none;color:var(--text);font-size:15px;resize:none;max-height:150px;line-height:1.5}
.tbtn{background:none;border:none;color:var(--muted);width:36px;height:36px;border-radius:10px;cursor:pointer;font-size:17px}.tbtn:hover{background:rgba(255,255,255,.08)}
.sendbtn{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#22e0a8,#0d9d7a);border:none;color:#03140d;cursor:pointer;font-size:16px;flex-shrink:0;opacity:.45;transition:.2s}.sendbtn.on{opacity:1}.sendbtn:hover{transform:scale(1.1)}
.foot{max-width:820px;margin:7px auto 0;text-align:center;font-size:11.5px;color:var(--muted)}.foot a{color:var(--accent);text-decoration:none}
.overlay{position:fixed;inset:0;background:rgba(4,6,10,.78);backdrop-filter:blur(8px);z-index:100;display:flex;align-items:center;justify-content:center;padding:16px;opacity:0;visibility:hidden;transition:opacity .25s,visibility .25s}
.overlay.show{opacity:1;visibility:visible}
.modal{background:var(--panel2);backdrop-filter:blur(26px) saturate(1.4);border:1px solid var(--line);border-radius:20px;padding:30px;width:100%;max-width:430px;text-align:center;transform:scale(.94) translateY(10px);opacity:0;transition:transform .28s,opacity .25s;box-shadow:0 30px 80px rgba(0,0,0,.6)}.overlay.show .modal{transform:scale(1) translateY(0);opacity:1}
.modal.wide{max-width:600px}
.modal h2{margin-bottom:7px;font-size:22px;font-weight:800}.modal p{color:var(--muted);font-size:14px;margin-bottom:18px}
.tabs{display:flex;background:rgba(255,255,255,.05);border-radius:12px;padding:4px;margin-bottom:18px}
.tab{flex:1;padding:10px;border-radius:9px;border:none;background:transparent;color:var(--muted);cursor:pointer;font-weight:600;font-size:14px}.tab.active{background:linear-gradient(135deg,rgba(34,224,168,.2),rgba(91,140,255,.2));color:#fff;border:1px solid var(--line)}
.inp{width:100%;padding:13px;background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:11px;color:var(--text);font-size:15px;margin-bottom:11px;outline:none}.inp:focus{border-color:rgba(34,224,168,.6)}
.btn{width:100%;padding:13px;border:none;border-radius:11px;background:linear-gradient(135deg,#22e0a8,#0d9d7a);color:#03140d;font-weight:800;font-size:15px;cursor:pointer;margin-bottom:9px;transition:.2s}.btn:hover{transform:translateY(-1px)}
.btn.ghost{background:rgba(255,255,255,.06);color:var(--text);border:1px solid var(--line)}
.btn.gold{background:linear-gradient(120deg,#ffe08a,#ffb347,#ff7a59);color:#241503;font-weight:800}
.logo-xl{width:60px;height:60px;border-radius:16px;background:conic-gradient(from 180deg,#22e0a8,#5b8cff,#a855f7);color:#fff;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;box-shadow:0 10px 34px rgba(34,224,168,.4)}
.row{display:flex;gap:9px;align-items:center;margin-bottom:11px}.row label{flex:1;text-align:left;font-size:14px;color:var(--muted)}
.cookie{position:fixed;bottom:0;left:0;right:0;background:rgba(12,16,22,.92);backdrop-filter:blur(14px);border-top:1px solid var(--line);padding:15px 22px;z-index:200;display:flex;align-items:center;gap:14px;justify-content:space-between;transform:translateY(120%);transition:transform .4s}
.cookie.show{transform:translateY(0)}.cookie p{font-size:13px;color:var(--muted)}.cookie .cb{background:linear-gradient(135deg,#22e0a8,#0d9d7a);color:#03140d;border:none;border-radius:11px;padding:10px 20px;cursor:pointer;font-weight:800;white-space:nowrap}
.toast{position:fixed;top:18px;right:18px;background:rgba(16,21,30,.95);border:1px solid var(--line);border-radius:13px;padding:13px 18px;z-index:400;font-size:14px;transform:translateX(130%);transition:transform .35s;backdrop-filter:blur(12px)}.toast.show{transform:translateX(0)}.toast.err{border-color:var(--danger)}.toast.ok{border-color:var(--accent)}
::-webkit-scrollbar{width:9px}::-webkit-scrollbar-thumb{background:#26303d;border-radius:5px}
@media(max-width:768px){.sidebar{position:fixed;left:0;top:0;bottom:0;margin-left:0!important;transform:translateX(-100%);transition:transform .3s}.sidebar.open{transform:translateX(0)}.msgrow{padding:16px}.cookie{flex-direction:column;align-items:flex-start}}
</style></head><body>
<div class="scene" id="scene"><div class="glow g1" style="--tx:70px;--ty:50px"></div><div class="glow g2" style="--tx:-80px;--ty:-40px"></div><div class="glow g3" style="--tx:40px;--ty:-70px"></div><div class="glow g4" style="--tx:-50px;--ty:60px"></div></div>
<div class="app" id="app">
<aside class="sidebar" id="sidebar">
<div class="brand"><div class="logo"><svg width="22" height="22" viewBox="0 0 100 100"><path d="M50 18 L82 84 H69 L61 63 H39 L31 84 H18 Z M45 53 H55 L50 40 Z" fill="#fff"/></svg></div><span class="nm">Awesome AI</span></div>
<button class="new-chat" onclick="newChat()">✏️ Новый чат</button>
<div class="chat-list" id="chatList"></div>
<div class="side-foot">
<button class="prem-btn" id="premBtn" onclick="buyPremium()">💎 Купить Premium</button>
<button class="side-btn" onclick="openSupport()"><span class="ic">💬</span>Поддержка</button>
<button class="side-btn" onclick="openSettings()"><span class="ic" id="avBox">?</span><span id="uName">Пользователь</span></button>
</div></aside>
<div class="main">
<div class="topbar"><button class="burger" onclick="toggleSidebar()">☰</button><div class="ct" id="ctTitle">Новый чат · <span class="pill" id="uStatus"></span></div></div>
<div class="messages" id="messages">
<div class="welcome" id="welcome">
<h1>Чем я могу помочь?</h1><p>Твой самый умный и современный ИИ-собеседник</p>
<div class="sugg-grid">
<button class="sugg" onclick="send('сколько будет 15% от 200')">🧮 Проценты</button>
<button class="sugg" onclick="send('переведи 5 км в мили')">📏 Единицы</button>
<button class="sugg" onclick="send('сгенерируй пароль 16')">🔐 Пароль</button>
<button class="sugg" onclick="send('брось кубик')">🎲 Кубик</button>
<button class="sugg" onclick="send('добавь задачу купить молоко')">📋 Задача</button>
<button class="sugg" onclick="send('сколько дней до 25.12')">📆 Дни</button>
</div></div></div>
<div class="inputarea">
<div class="attach-preview" id="attachPreview"><img id="attachImg"><span class="an" id="attachName"></span><button class="rm" onclick="removeAttach()">✕</button></div>
<div class="inputwrap">
<input type="file" id="fileInput" accept="image/*,.pdf" style="display:none" onchange="handleFile(this)">
<button class="tbtn" onclick="document.getElementById('fileInput').click()" title="Прикрепить фото">📎</button>
<button class="tbtn" onclick="draw()" title="Рисовать">🎨</button>
<textarea id="input" rows="1" placeholder="Отправь сообщение Awesome AI" oninput="autoGrow(this)" onkeydown="onKey(event)"></textarea>
<button class="sendbtn" id="sendBtn" onclick="send()">➤</button>
</div>
<div class="foot">Awesome AI может ошибаться. Поддержка: <a href="https://t.me/flidges" target="_blank">@flidges</a></div>
</div></div></div>

<div class="cookie" id="cookie"><p>🍪 Мы используем cookies для улучшения сервиса.</p><button class="cb" onclick="acceptCookie()">Принять</button></div>

<div class="overlay" id="authOverlay">
<div class="modal">
<div class="logo-xl"><svg width="36" height="36" viewBox="0 0 100 100"><path d="M50 20 L80 80 H68 L61 64 H39 L32 80 H20 Z M45 54 H55 L50 42 Z" fill="#fff"/></svg></div>
<div class="tabs"><button class="tab active" id="tabLogin" onclick="switchTab('login')">Вход</button><button class="tab" id="tabReg" onclick="switchTab('reg')">Регистрация</button></div>
<h2 id="authTitle">Вход</h2><p id="authSub">Войди, чтобы продолжить</p>
<div id="regWrap" style="display:none"><input class="inp" id="regName" placeholder="Имя"></div>
<input class="inp" id="authLogin" placeholder="Логин">
<input class="inp" type="password" id="authPass" placeholder="Пароль">
<button class="btn" id="authBtn" onclick="submitAuth()">Войти</button>
</div></div>

<div class="overlay" id="premOverlay">
<div class="modal">
<div class="logo-xl">💎</div><h2>Awesome AI Premium</h2>
<p>Безлимит запросов, приоритетный доступ, все модели и эксклюзивные функции!</p>
<a class="btn gold" style="display:block;text-decoration:none;text-align:center" href="https://t.me/flidges" target="_blank">💬 Написать @flidges и купить</a>
<button class="btn ghost" onclick="closeOv('premOverlay')">Закрыть</button></div></div>

<div class="overlay" id="supportOverlay">
<div class="modal"><div class="logo-xl">💬</div><h2>Поддержка</h2><p>Напишите нам — поможем быстро</p>
<a class="btn" style="display:block;text-decoration:none;text-align:center" href="https://t.me/flidges" target="_blank">📨 Telegram: @flidges</a>
<button class="btn ghost" onclick="closeOv('supportOverlay')">Закрыть</button></div></div>

<div class="overlay" id="settingsOverlay">
<div class="modal wide"><h2>⚙️ Настройки аккаунта</h2><p>Персонализация</p>
<div class="row"><label>Имя</label><input class="inp" id="setName" style="margin:0;flex:1.4" placeholder="Имя"></div>
<div class="row"><label>Тема</label><select class="inp" id="setTheme" style="margin:0;flex:1.4"><option value="dark">🌙 Тёмная</option><option value="light">☀️ Светлая</option></select></div>
<div id="profInfo" style="font-size:13px;color:var(--muted);margin:12px 0;text-align:left"></div>
<button class="btn" onclick="saveSettings()">Сохранить</button>
<button class="btn ghost" onclick="logout()">Выйти</button>
<button class="btn ghost" onclick="closeOv('settingsOverlay')">Закрыть</button></div></div>

<script>
let uid=null,cid=null,sending=false,mode='login',attachedImage=null,chatsCache=[];
const $=id=>document.getElementById(id);
function toast(t,ty){const e=document.createElement('div');e.className='toast '+(ty||'');e.textContent=t;document.body.appendChild(e);requestAnimationFrame(()=>e.classList.add('show'));setTimeout(()=>{e.classList.remove('show');setTimeout(()=>e.remove(),320)},3200)}
async function api(u,m,b){try{const o={method:m||'GET',headers:{'Content-Type':'application/json'}};if(b)o.body=JSON.stringify(b);const r=await fetch(u,o);const t=await r.text();try{return JSON.parse(t)}catch(e){return{ok:false,error:'Сервер ['+r.status+']'}}}catch(e){return{ok:false,error:'Нет соединения'}}}
function toggleSidebar(){const s=$('sidebar'),app=$('app');if(innerWidth<=768)s.classList.toggle('open');else app.classList.toggle('collapsed')}
function openOv(id){$(id).classList.add('show')}function closeOv(id){$(id).classList.remove('show')}
function buyPremium(){openOv('premOverlay')}
function switchTab(m){mode=m;$('tabLogin').className='tab'+(m==='login'?' active':'');$('tabReg').className='tab'+(m==='reg'?' active':'');$('regWrap').style.display=m==='reg'?'block':'none';$('authTitle').textContent=m==='reg'?'Регистрация':'Вход';$('authBtn').textContent=m==='reg'?'Создать':'Войти'}
async function submitAuth(){const login=$('authLogin').value.trim(),pw=$('authPass').value;if(!login||!pw){toast('Заполни логин и пароль','err');return}const body=mode==='reg'?{login,password:pw,name:$('regName').value.trim()}:{login,password:pw};const r=await api(mode==='reg'?'/api/register':'/api/login','POST',body);if(r.ok){uid=login;closeOv('authOverlay');toast('Добро пожаловать!','ok');init()}else toast(r.error||'Ошибка','err')}
async function logout(){await api('/api/logout','POST');location.reload()}
async function init(){const me=await api('/api/me');if(me.ok){uid=me.user_id;$('authOverlay').classList.remove('show');if(me.avatar)$('avBox').innerHTML='<img style="width:100%;height:100%;object-fit:cover" src="'+me.avatar+'">';else $('avBox').textContent=String(me.name||'?').slice(0,1).toUpperCase();$('uName').textContent=me.name||'Пользователь';await loadChats();await checkStatus()}else openOv('authOverlay')}
async function checkStatus(){const r=await api('/api/status');if(r.ok){$('uStatus').textContent=r.status_text+' · Ур.'+r.level;const b=$('premBtn');if(r.premium){b.textContent='💎 Premium активен';b.classList.add('act')}else{b.textContent='💎 Купить Premium';b.classList.remove('act')}}}
async function loadChats(){const r=await api('/api/chats');if(!r.ok){toast('Не удалось загрузить чаты','err');return}chatsCache=r.chats||[];renderChats()}
function renderChats(){const l=$('chatList');l.innerHTML='';chatsCache.forEach(c=>{const d=document.createElement('div');d.className='chat-item'+(Number(c.id)===Number(cid)?' active':'');d.setAttribute('data-cid',c.id);d.innerHTML='💬<span class="t">'+esc(c.title||'Чат')+'</span><button class="del" onclick="event.stopPropagation();delChat('+c.id+')">✕</button>';d.onclick=()=>openChat(c.id);l.appendChild(d)})}
function openChat(id){if(!id)return;const ch=chatsCache.find(x=>Number(x.id)===Number(id));if(!ch){toast('Чат не найден','err');return}cid=Number(id);$('messages').innerHTML='';$('welcome').style.display='none';$('ctTitle').textContent=ch.title||'Чат';(ch.messages||[]).forEach(m=>addMsg(m.role,m.content,m.image));renderChats();if(innerWidth<=768)$('sidebar').classList.remove('open')}
async function newChat(){const r=await api('/api/chat/new','POST');if(r.ok){cid=r.chat_id;$('messages').innerHTML='';$('welcome').style.display='';$('ctTitle').textContent='Новый чат';loadChats()}}
async function delChat(id){await api('/api/chat/delete','POST',{chat_id:id});if(Number(id)===Number(cid)){cid=null;boxReset()}loadChats()}
function boxReset(){$('messages').innerHTML='';$('welcome').style.display='';$('ctTitle').textContent='Новый чат'}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmtAI(t){if(!t)return'';let out='';for(const line of String(t).split('\n')){const h=line.match(/^\*\*(.+?)\*\*$/);if(h){out+='<div class="h">'+esc(h[1])+'</div>';continue}const parts=line.split(/(\*\*.*?\*\*)/g);let p='';for(const part of parts){if(part.startsWith('**')&&part.endsWith('**')&&part.length>4)p+='<b>'+esc(part.slice(2,-2))+'</b>';else p+=esc(part)}out+='<div style="margin:2px 0">'+p+'</div>'}return out}
function addMsg(role,text,img){const box=$('messages');if($('welcome'))$('welcome').style.display='none';const m=document.createElement('div');m.className='msgrow '+role;let av=role==='user'?'<div class="ma">'+String(uid||'?').slice(0,1).toUpperCase()+'</div>':'<div class="ma">🤖</div>';let content=role==='ai'?fmtAI(text):esc(text);if(img)content+='<img src="'+img+'">';m.innerHTML=av+'<div class="mb">'+content+'</div>';box.appendChild(m);box.scrollTop=box.scrollHeight}
function addTyping(){const box=$('messages');const m=document.createElement('div');m.className='msgrow ai';m.id='typing';m.innerHTML='<div class="ma">🤖</div><div class="mb typing"><span></span><span></span><span></span></div>';box.appendChild(m);box.scrollTop=box.scrollHeight}
function rmTyping(){const t=$('typing');if(t)t.remove()}
async function send(preset){if(sending)return;const input=$('input');const msg=(preset!==undefined)?preset:input.value.trim();if(!msg&&!attachedImage)return;input.value='';autoGrow(input);addMsg('user',msg,attachedImage);sending=true;addTyping();const body={message:msg,chat_id:cid};if(attachedImage)body.image=attachedImage;const r=await api('/api/chat','POST',body);rmTyping();sending=false;if(r.ok){cid=r.chat_id;addMsg('ai',r.response);$('ctTitle').textContent='Чат';loadChats()}else{addMsg('ai','⚠️ '+(r.error||'Ошибка'));toast(r.error,'err')}attachedImage=null;$('attachPreview').style.display='none';checkStatus()}
function onKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}
function autoGrow(t){t.style.height='auto';t.style.height=Math.min(t.scrollHeight,150)+'px'}
function handleFile(inp){const f=inp.files[0];if(!f)return;const reader=new FileReader();reader.onload=e=>{attachedImage=e.target.result;$('attachImg').src=attachedImage;$('attachName').textContent=f.name;$('attachPreview').style.display='flex'};reader.readAsDataURL(f);inp.value=''}
function removeAttach(){attachedImage=null;$('attachPreview').style.display='none'}
async function draw(){const p=prompt('🎨 Что нарисовать?');if(!p)return;addMsg('user','🎨 '+p);sending=true;addTyping();const r=await api('/api/draw','POST',{prompt:p});rmTyping();sending=false;if(r.ok&&r.image)addMsg('ai','Готово!',r.image);else addMsg('ai','⚠️ '+(r.error||'Не удалось'))}
function openSupport(){openOv('supportOverlay')}
async function openSettings(){const r=await api('/api/profile');if(r.ok){$('setName').value=r.name||'';$('setTheme').value=r.theme||'dark';$('profInfo').innerHTML='ID: <b>'+esc(r.user_id)+'</b><br>'+(r.premium?'💎 Premium до '+esc(r.premium_expires):'🔓 Free · 50 запросов/день')+'<br>⭐ Уровень '+r.level+' · XP '+r.xp}openOv('settingsOverlay')}
async function saveSettings(){const r=await api('/api/settings','POST',{name:$('setName').value.trim()||undefined,theme:$('setTheme').value});if(r.ok){closeOv('settingsOverlay');toast('Сохранено','ok');init()}}
function acceptCookie(){$('cookie').classList.remove('show');try{localStorage.setItem('sc_cookie','1')}catch(e){}}
function buildScene(){const s=$('scene');for(let i=0;i<60;i++){const st=document.createElement('div');st.className='star';const sz=(Math.random()*2+1);st.style.width=sz+'px';st.style.height=sz+'px';st.style.left=Math.random()*100+'%';st.style.top=Math.random()*100+'%';st.style.animationDelay=(Math.random()*3)+'s';st.style.animationDuration=(Math.random()*3+2)+'s';s.appendChild(st)}}
document.addEventListener('DOMContentLoaded',()=>{buildScene();init();try{if(!localStorage.getItem('sc_cookie'))setTimeout(()=>$('cookie').classList.add('show'),900)}catch(e){}});
</script></body></html>"""

if __name__ == '__main__':
    print("AWESOME AI — ULTIMATE PRO (PostgreSQL relaxdev)")
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
