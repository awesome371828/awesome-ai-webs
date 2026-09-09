#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWESOME AI — ChatGPT Clone: Supabase DB, вход по имени+логину+паролю, cookie, поддержка"""
import os, re, io, time, json, base64, urllib.parse, hashlib, random, html, uuid as _uuid
from datetime import datetime, timedelta, timezone
import requests, urllib3
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
app.secret_key = os.getenv("SECRET_KEY", "awesome-ai-chatgpt-secret-2026")
app.permanent_session_lifetime = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True

# ===== КЛЮЧИ =====
YANDEX_API_KEY    = os.getenv("YANDEX_API_KEY", "AQVNyfn82epL9dy8C_kftzeypq6eF9lFd6SZnFzV")
FOLDER_ID         = os.getenv("FOLDER_ID", "b1g4aq87c7j61c6g3i5l")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "MDFhMDBkNmEtMmExNC03M2JkLWFlZmMtOTQ0OWVlOTc5M2U1OmE1ZWJhM2NlLTQwYjAtNDZlYi1iMmY2LTE3OTFmYzhhYTQ2MA==")
SUPABASE_URL  = os.getenv("SUPABASE_URL", "https://lprxbmshmuucymkgaqwk.supabase.co")
SUPABASE_KEY  = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxwcnhibXNobXV1Y3lta2dhcXdrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY3NDk0MjgsImV4cCI6MjEwMjMyNTQyOH0.Ie9jSH5RMxeOq8aU-Dv6MXlojWMUTOLE723Hdg6heZU")
SUPPORT_USERNAME = "@flidges"

OWNER_LOGIN    = os.getenv("OWNER_LOGIN", "admin")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "qawsedrf2346")
FREE_LIMIT   = 40
MAX_HISTORY  = 24
GIGA_TIMEOUT = 30
YGPT_TIMEOUT = 25
SEARCH_TIMEOUT = 4

MOSCOW_TZ = timezone(timedelta(hours=3))
def gm(): return datetime.now(MOSCOW_TZ)
def gdate(): return gm().strftime('%d.%m.%Y')
def now_iso(): return gm().strftime('%Y-%m-%d %H:%M:%S')
def fmt_date(s):
    if not s: return "—"
    try:
        v = str(s).replace('T',' ')[:19]
        return datetime.strptime(v, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
    except Exception: return s
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

# ===== SUPABASE =====
from supabase import create_client
_sb = None
try:
    _sb = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    _sb = None

def sb_table(name): return _sb.table(name) if _sb else None

# ----- Пользователи -----
def get_user(uid):
    if not _sb: return None
    try:
        r = _sb.table('users').select('*').eq('user_id', str(uid)).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None

def get_user_by_login(login):
    if not _sb: return None
    try:
        r = _sb.table('users').select('*').eq('login', str(login)).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None

def reg_user(login, name, pw):
    login = (login or '').strip(); name = (name or '').strip()
    if not login or len(login) < 3: return False, "Логин мин. 3 символа"
    if not name: return False, "Имя обязательно"
    if not pw or len(pw) < 3: return False, "Пароль мин. 3 символа"
    if not _sb: return False, "База недоступна"
    if get_user_by_login(login): return False, "Этот логин уже занят"
    try:
        owner = 1 if login.lower() == OWNER_LOGIN.lower() else 0
        data = {
            "user_id": login,
            "login": login,
            "name": name,
            "password": hash_pw(pw),
            "messages_today": 0,
            "premium": 0,
            "is_admin": owner,
            "is_owner": owner,
            "theme": "light",
            "joined_at": now_iso(),
            "xp": 0,
            "level": 1,
            "ref_code": hashlib.md5((login+str(random.random())).encode()).hexdigest()[:8],
            "ref_count": 0,
            "last_reset": gm().strftime('%Y-%m-%d'),
        }
        _sb.table('users').insert(data).execute()
        return True, "OK"
    except Exception as e:
        return False, "Ошибка БД: " + str(e)

def login_user(login, pw):
    login = (login or '').strip()
    if not login: return False, "Введи логин"
    u = get_user_by_login(login)
    if not u: return False, "Аккаунт не найден. Зарегистрируйся"
    if u.get('password') != hash_pw(pw): return False, "Неверный пароль"
    return True, "OK"

def eff_status(uid):
    u = get_user(uid) or {}
    owner = 1 if str(u.get('login','')).lower() == OWNER_LOGIN.lower() else int(u.get('is_owner',0) or 0)
    is_admin = 1 if owner else int(u.get('is_admin',0) or 0)
    premium = int(u.get('premium',0) or 0)
    expires = u.get('premium_expires')
    if premium and expires:
        try:
            if gm() > datetime.strptime(str(expires).replace('T',' ')[:19],'%Y-%m-%d %H:%M:%S').replace(tzinfo=MOSCOW_TZ):
                premium = 0; expires = None
        except Exception: pass
    return {'premium': 1 if owner or premium else 0, 'premium_expires': expires,
            'is_admin': is_admin, 'is_owner': owner,
            'level': int(u.get('level',1) or 1), 'xp': int(u.get('xp',0) or 0), 'ref_count': u.get('ref_count',0)}

def can_send(uid):
    s = eff_status(uid)
    if s['is_owner'] or s['is_admin'] or s['premium']: return True
    u = get_user(uid) or {}
    return int(u.get('messages_today',0) or 0) < FREE_LIMIT

def incr(uid):
    s = eff_status(uid)
    u = get_user(uid) or {}
    cnt = int(u.get('messages_today',0) or 0)
    if s['is_owner'] or s['is_admin']:
        add_xp(uid, 5); return
    try:
        _sb.table('users').update({'messages_today': cnt+1}).eq('user_id', str(uid)).execute()
    except Exception: pass
    add_xp(uid, 10)

def add_xp(uid, amt):
    try:
        u = get_user(uid) or {}
        xp = int(u.get('xp',0) or 0) + int(amt)
        lvl = 1 + xp // 100
        _sb.table('users').update({'xp': xp, 'level': lvl}).eq('user_id', str(uid)).execute()
    except Exception: pass

def upd_settings(uid, **kw):
    try:
        _sb.table('users').update({k:v for k,v in kw.items() if v is not None}).eq('user_id', str(uid)).execute()
    except Exception: pass

# ----- Память -----
def get_memory(uid, limit=30):
    if not _sb: return []
    try:
        r = _sb.table('user_memory').select('fact').eq('user_id', str(uid)).order('id', desc=True).limit(limit).execute()
        return [x['fact'] for x in r.data]
    except Exception: return []
def remember(uid, fact):
    fact = (fact or '').strip()[:500]
    if not fact or len(fact) < 4: return
    if not _sb: return
    try:
        dup = _sb.table('user_memory').select('id').eq('user_id', str(uid)).eq('fact', fact).execute()
        if not dup.data:
            _sb.table('user_memory').insert({'user_id': str(uid), 'fact': fact, 'created_at': now_iso()}).execute()
    except Exception: pass

def extract_facts(uid, text):
    tl = text.lower(); facts = []
    if "меня зовут" in tl or "мое имя" in tl:
        m = re.search(r'(?:меня зовут|мое имя)[:\s]+([А-Яа-яЁёA-Za-z\-]+)', tl)
        if m: facts.append("Имя пользователя: "+m.group(1))
    for kw,label in [("мне ", "Возраст: "),("я живу в ", "Город: "),("я работаю ", "Работа: "),("учусь в ", "Учёба: "),("я из ", "Город: ")]:
        if kw in tl:
            m = re.search(re.escape(kw)+r'([^,.!?\n]{2,60})', tl)
            if m: facts.append(label+m.group(1).strip())
    if any(x in tl for x in ["мне нравится","я люблю","обожаю"]):
        m = re.search(r'(?:мне нравится|я люблю|обожаю)\s+([^,.!?\n]{2,60})', tl)
        if m: facts.append("Интерес/хобби: "+m.group(1).strip())
    for f in facts: remember(uid, f)

# ----- Чат (Supabase) -----
def create_chat(uid, title="Новый чат"):
    try:
        r = _sb.table('chats_web').insert({'user_id': str(uid), 'title': title, 'created_at': now_iso(), 'pinned': 0}).execute()
        return r.data[0]['id']
    except Exception: return None
def get_chats(uid):
    try:
        r = _sb.table('chats_web').select('*').eq('user_id', str(uid)).order('created_at', desc=True).execute()
        return r.data or []
    except Exception: return []
def add_msg(cid, role, content, image=None):
    try:
        _sb.table('messages_web').insert({'chat_id': int(cid), 'role': role, 'content': content or '', 'image': image, 'created_at': now_iso()}).execute()
    except Exception: pass
def get_msgs(cid):
    try:
        r = _sb.table('messages_web').select('*').eq('chat_id', int(cid)).order('id').execute()
        return r.data or []
    except Exception: return []
def hist(cid):
    m = get_msgs(cid)
    if len(m) <= MAX_HISTORY: return m or []
    return (m[:6] + m[-MAX_HISTORY+6:]) if len(m) > 6 else m
def set_title(cid, t):
    try: _sb.table('chats_web').update({'title': t[:50]}).eq('id', int(cid)).execute()
    except Exception: pass
def del_chat(uid, cid):
    try:
        _sb.table('messages_web').delete().eq('chat_id', int(cid)).execute()
        _sb.table('chats_web').delete().eq('id', int(cid)).eq('user_id', str(uid)).execute()
    except Exception: pass
def pin_chat(cid):
    try:
        r = _sb.table('chats_web').select('pinned').eq('id', int(cid)).execute()
        v = 0 if (r.data and r.data[0].get('pinned')) else 1
        _sb.table('chats_web').update({'pinned': v}).eq('id', int(cid)).execute()
    except Exception: pass

# ===== НЕЙРОСЕТЬ =====
tok = None; tok_t = 0
def get_tok():
    global tok, tok_t
    if tok and time.time()-tok_t < 180: return tok
    for _ in range(3):
        try:
            r = requests.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={"Content-Type":"application/x-www-form-urlencoded","Accept":"application/json",
                         "RqUID": str(_uuid.uuid4()), "Authorization":"Basic "+GIGACHAT_AUTH_KEY},
                data="scope=GIGACHAT_API_PERS", timeout=10, verify=False)
            if r.status_code == 200:
                j = r.json()
                if j.get("access_token"): tok = j["access_token"]; tok_t = time.time(); return tok
        except Exception: pass
        time.sleep(0.7)
    tok = None
    return None

def giga(hlist, sysp, max_tok=2000):
    try:
        t = get_tok()
        if not t: return None
        msgs = [{"role":"system","content":sysp[:3000]}] + \
               [{"role":h.get("role","user"),"content":(h.get("content") or "")[:800]} for h in hlist[-12:] if h.get("role") in ("user","assistant")]
        r = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization":"Bearer "+t,"Content-Type":"application/json","Accept":"application/json"},
            json={"model":"GigaChat-Pro","messages":msgs,"temperature":0.85,"max_tokens":max_tok},
            timeout=GIGA_TIMEOUT, verify=False)
        if r.status_code == 200:
            try: return r.json()["choices"][0]["message"]["content"]
            except Exception: return None
    except Exception: pass
    return None

def ygpt(text, sysp):
    try:
        r = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={"Authorization":"Api-Key "+YANDEX_API_KEY,"Content-Type":"application/json"},
            json={"modelUri":"gpt://"+FOLDER_ID+"/yandexgpt/latest",
                  "completionOptions":{"temperature":0.7,"maxTokens":700,"stream":False},
                  "messages":[{"role":"system","text":sysp[:1500]},{"role":"user","text":text}]},
            timeout=YGPT_TIMEOUT)
        if r.status_code == 200:
            try: return r.json()["result"]["alternatives"][0]["message"]["text"]
            except Exception: return None
    except Exception: pass
    return None

SUPER = """ТЫ — AWESOME AI, самый мощный живой ИИ-помощник нового поколения. Уровень ChatGPT.
📍 Ты в РОССИИ, город МОСКВА. Сегодня: {d}, время: {t} (московское).
{memory}
СТИЛЬ: отвечай как живой эксперт — живо, тепло, с юмором. Давай конкретику, цифры, примеры.
ФОРМАТ: разделяй на разделы **1. Название**. Важное выделяй **жирным**. Используй эмодзи.
ПРАВИЛА: если есть свежие данные из поиска ниже — опирайся на них. Никогда не выдумывай актуальные события.
Ты полноценный собеседник — поддерживай разговор, задавай встречные вопросы, запоминай детали."""

def smart_answer(uid, text, history, img=None, doc=None):
    mem = get_memory(uid)
    sp = SUPER.format(d=gdate(), t=gm().strftime('%H:%M'),
        memory=("Помнишь о пользователе:\n"+("\n".join("• "+f for f in mem))) if mem else "")
    if eff_status(uid)['premium']: sp += "\n💎 Пользователь Premium — максимум глубины."
    if img: sp += f"\n📸 Изображение: {img}"
    if doc: sp += f"\n📄 Документ: {doc[:3000]}"
    tl = (text or "").lower().strip()
    try: extract_facts(uid, text)
    except Exception: pass
    full = history + [{"role":"user","content":text or "Опиши"}]
    a = giga(full, sp)
    if a and len(a) > 4: return a
    b = ygpt(text, sp)
    if b and len(b) > 4: return b
    # фолбэки
    if img: return f"📸 {img}"
    if any(w in tl for w in ["привет","здравств","хай","ку"]): return "👋 Привет! Рад тебя видеть. Чем займёмся сегодня?"
    if "время" in tl and ("сейчас" in tl or "сколько" in tl or "час" in tl):
        return f"🕒 Сейчас **{gm().strftime('%H:%M:%S')}** (Москва), дата: **{gdate()}**."
    if "дата" in tl or "какое сегодня число" in tl:
        return f"📅 Сегодня **{gdate()}**, {['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье'][gm().weekday()]}."
    if "переведи" in tl or "перевод" in tl:
        target = 'ru'
        if "англ" in tl: target = 'en'
        elif "немец" in tl: target = 'de'
        elif "франц" in tl: target = 'fr'
        txt = re.sub(r'(переведи|на английский|на русский|на немецкий|на французский|пожалуйста|на .*?)','',tl,flags=re.I).strip()
        return "🌍 "+translate(txt[:500],target) if txt else "Напиши что перевести."
    if "анекдот" in tl or "шутк" in tl or "рассмеши" in tl:
        jokes=["— Почему программист перепутал Хэллоуин и Рождество? — Oct 31 == Dec 25 😄","— Админ заходит в бар, а там все буферы переполнены 😅","— Что сказал один сервер другому? — Ты сегодня в сети? 📶"]
        return "😂 "+random.choice(jokes)
    if "комплимент" in tl or "похвали" in tl:
        return "✨ Ты потрясающий! У тебя отличный вкус, ты любопытный и явно умный собеседник. Таких людей приятно встречать!"
    if "крипт" in tl or "биткоин" in tl or "эфир" in tl:
        c = crypto(); return c if c else "🪙 Не удалось получить цену."
    if "курс" in tl or "доллар" in tl or "евро" in tl or "валют" in tl:
        c = currency(); return c if c else "💵 Не удалось получить курс."
    if "погода" in tl:
        m = re.search(r'(в|в городе)\s+([а-яА-Яa-zA-Z\- ]+)', tl)
        if m:
            w = weather(m.group(2).strip()); return w if w else "🌤 Напиши: погода в [город]"
        return "🌤 Напиши: погода в [город]"
    if "запомни" in tl or "выучи" in tl:
        fact = re.sub(r'(запомни|выучи|что)\s*','',tl).strip()[:500]
        if len(fact) > 3:
            remember(uid, fact); return "🧠 Запомнил: «"+fact+"». Расскажу при случае!"
        return "🧠 Что именно запомнить?"
    if "что ты помнишь" in tl or "память" in tl:
        return "🧠 **Что я помню о тебе:**\n"+("\n".join("• "+f for f in mem) if mem else "Пока ничего. Скажи «запомни...», и я сохраню!")
    if "кто ты" in tl or "что ты умеешь" in tl:
        return "Я **AWESOME AI** — живой помощник ✨\n\n**1.** Общаюсь 🗣\n**2.** Ищу в интернете 🌐\n**3.** Помню о тебе 🧠\n**4.** Считаю 🧮\n**5.** Рисую 🎨\n**6.** Погода/валюты/крипта 🌤💵🪙\n**7.** Перевожу 🌍\n**8.** Шучу 😂\n\nЧто попробуем?"
    if re.search(r'\d+\s*[\+\-\*\/]\s*\d+', tl):
        try:
            res = eval(re.sub(r'[^0-9+\-*/(). ]','',tl)); return f"🧮 Результат: **{res}**"
        except: return "🧮 Не понял выражение."
    if "режим" in tl or "стань" in tl:
        return "⚡ **Режимы** — просто скажи:\n• «Будь моим юристом» ⚖️\n• «Будь моим психологом» 🧠\n• «Будь моим учителем» 📚\n• «Будь моим кодером» 💻\n• «Будь моим маркетологом» 📈"
    return "🤖 Обрабатываю... Напиши чуть подробнее, и я дам полный ответ!"

def describe_img(b64):
    try:
        t = get_tok()
        if not t: return "📸 Изображение"
        r = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization":"Bearer "+t,"Content-Type":"application/json","Accept":"application/json"},
            json={"model":"GigaChat-Pro","messages":[{"role":"system","content":"Опиши изображение подробно на русском, живо."},
                {"role":"user","content":[{"type":"text","text":"Что на изображении?"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+b64}}]}],"temperature":0.5,"max_tokens":400},timeout=GIGA_TIMEOUT,verify=False)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
    except Exception: pass
    return "📸 Изображение"
def gen_img(prompt):
    try:
        c = prompt
        for w in ['нарисуй','сгенерируй','покажи','картинку','изображение','нарисуй мне']: c = c.replace(w,'').strip()
        if not c: c = prompt
        r = requests.get(f"https://image.pollinations.ai/prompt/{urllib.parse.quote(c)}?width=1024&height=1024&nologo=true", headers={"User-Agent":"Mozilla/5.0"}, timeout=25)
        if r.status_code == 200 and len(r.content) > 1000: return base64.b64encode(r.content).decode()
    except Exception: pass
    return None
def translate(text, target='ru'):
    try:
        r = requests.post("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl="+target+"&dt=t&q="+urllib.parse.quote(text[:5000]), timeout=8)
        if r.status_code == 200: return "".join(x[0] for x in r.json()[0] if x[0])
    except Exception: pass
    return text
def weather(city):
    try:
        r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(city)}&appid=4c8f5c0b8a9f2c5d6e7f8g9h0i1j2k3l&units=metric&lang=ru", timeout=SEARCH_TIMEOUT)
        if r.status_code == 200:
            d = r.json(); return f"🌤 **{city}**: {round(d['main']['temp'])}°C, {d['weather'][0]['description']}\n💨 Ветер: {d['wind']['speed']} м/с\n💧 Влажность: {d['main']['humidity']}%"
    except Exception: pass
    return None
def currency():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=SEARCH_TIMEOUT)
        rates = r.json().get('rates',{}); usd = rates.get('RUB','?'); eur = usd/rates.get('EUR',1) if rates.get('EUR') else '?'
        return f"💵 **Курс валют:**\nUSD: **{round(usd,2)}₽**\nEUR: **{round(eur,2)}₽**"
    except Exception: return None
def crypto():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd", timeout=SEARCH_TIMEOUT)
        d = r.json(); return f"🪙 **Криптовалюта:**\nBTC: **${d.get('bitcoin',{}).get('usd','?')}**\nETH: **${d.get('ethereum',{}).get('usd','?')}**"
    except Exception: return None
def read_pdf(b64):
    try:
        import fitz
        raw = base64.b64decode(b64.split(',')[-1]); doc = fitz.open(stream=raw, filetype="pdf")
        return "".join(page.get_text() for page in doc)[:5000] or "PDF без текста"
    except Exception: return "PDF загружен"

# ===== API =====
@app.route('/')
def index(): return render_template_string(INDEX_HTML)

@app.route('/favicon.ico')
def favicon():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="24" fill="#10a37f"/><text x="50" y="68" font-size="52" text-anchor="middle" fill="#fff" font-family="sans-serif" font-weight="bold">A</text></svg>'
    return app.response_class(svg, mimetype='image/svg+xml')

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        d = request.json
        login = str(d.get('login','')).strip(); name = str(d.get('name','')).strip(); pw = str(d.get('password',''))
        ok, msg = reg_user(login, name, pw)
        if not ok: return jsonify({'ok':False,'error':msg})
        session.permanent=True; session['user_id']=login; session['name']=name
        return jsonify({'ok':True,'user_id':login,'name':name})
    except Exception as e:
        return jsonify({'ok':False,'error':'Ошибка регистрации: '+str(e)}), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        d = request.json
        login = str(d.get('login','')).strip(); pw = str(d.get('password',''))
        ok, msg = login_user(login, pw)
        if not ok: return jsonify({'ok':False,'error':msg})
        u = get_user_by_login(login)
        session.permanent=True; session['user_id']=login; session['name']=u.get('name') if u else login
        return jsonify({'ok':True,'user_id':login,'name':session['name']})
    except Exception as e:
        return jsonify({'ok':False,'error':'Ошибка входа: '+str(e)}), 400

@app.route('/api/logout', methods=['POST'])
def api_logout(): session.clear(); return jsonify({'ok':True})

@app.route('/api/me')
def api_me():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    u = get_user(uid)
    if not u: session.clear(); return jsonify({'ok':False})
    return jsonify({'ok':True,'user_id':uid,'name':session.get('name') or u.get('name'),'theme':u.get('theme','light'),'avatar':u.get('avatar','')})

@app.route('/api/status')
def api_status():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    s = eff_status(uid); u = get_user(uid) or {}
    if s['is_owner']: st="Владелец"; lim="∞"
    elif s['is_admin']: st="Админ"; lim="∞"
    elif s['premium']: st="Premium"; lim="∞"
    else: st="Free"; lim=f"{max(0,FREE_LIMIT-int(u.get('messages_today',0) or 0))}/{FREE_LIMIT}"
    return jsonify({'ok':True,'premium':bool(s['premium']),'is_admin':bool(s['is_admin']),'is_owner':bool(s['is_owner']),
                    'premium_expires':fmt_date(s['premium_expires']) if s['premium'] else None,
                    'status_text':st,'limit_text':lim,'messages_today':int(u.get('messages_today',0) or 0),'free_limit':FREE_LIMIT,
                    'level':s['level'],'xp':s['xp']})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False,'error':'Авторизуйся'})
    if not can_send(uid): return jsonify({'ok':False,'error':'Дневной лимит исчерпан'})
    d = request.json; msg = d.get('message','').strip(); cid = d.get('chat_id'); img = d.get('image'); doc = d.get('document')
    if not msg and not img and not doc: return jsonify({'ok':False,'error':'Пустое'})
    if not cid: cid = create_chat(uid)
    h = hist(cid)
    idesc=None; dtext=None
    if img:
        try:
            raw = base64.b64decode(img.split(',')[-1])
            if HAS_PIL:
                im = Image.open(io.BytesIO(raw)).convert('RGB'); im.thumbnail((700,700))
                b = io.BytesIO(); im.save(b,'JPEG',quality=80); idesc=describe_img(base64.b64encode(b.getvalue()).decode())
            else: idesc=describe_img(img.split(',')[-1])
        except Exception: idesc="📸"
    if doc:
        dtext = read_pdf(doc.get('data','')) if doc.get('type')=='pdf' else "Документ: "+doc.get('name','')
    add_msg(cid,'user',msg,img)
    response = smart_answer(uid, msg, h, idesc, dtext)
    try: incr(uid)
    except Exception: pass
    add_msg(cid,'assistant',response)
    try:
        ms = get_msgs(cid)
        fu = next((m for m in ms if m['role']=='user' and m.get('content')), None)
        if fu: set_title(cid, fu['content'][:40])
    except Exception: pass
    return jsonify({'ok':True,'response':response,'chat_id':cid})

@app.route('/api/chats')
def api_chats():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    chats = get_chats(uid)
    for c in chats: c['messages'] = get_msgs(c['id'])
    return jsonify({'ok':True,'chats':chats})

@app.route('/api/chat/new', methods=['POST'])
def api_chat_new():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    return jsonify({'ok':True,'chat_id':create_chat(uid)})

@app.route('/api/chat/delete', methods=['POST'])
def api_chat_delete():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    del_chat(uid, request.json.get('chat_id')); return jsonify({'ok':True})

@app.route('/api/chat/pin', methods=['POST'])
def api_chat_pin():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    pin_chat(request.json.get('chat_id')); return jsonify({'ok':True})

@app.route('/api/chat/rename', methods=['POST'])
def api_chat_rename():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    set_title(request.json.get('chat_id'), request.json.get('title','Чат')); return jsonify({'ok':True})

@app.route('/api/search', methods=['POST'])
def api_search():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    q = request.json.get('q','').lower(); res=[]
    for c in get_chats(uid):
        for m in c['messages']:
            if q in str(m.get('content','')).lower():
                res.append({'chat_id':c['id'],'title':c['title'],'snippet':str(m.get('content',''))[:80]}); break
    return jsonify({'ok':True,'results':res})

@app.route('/api/share', methods=['POST'])
def api_share():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    cid = request.json.get('chat_id'); sid = hashlib.md5((str(cid)+now_iso()).encode()).hexdigest()[:10]
    try: _sb.table('shared_chats').insert({'id':sid,'chat_id':int(cid),'created_at':now_iso()}).execute()
    except Exception: pass
    return jsonify({'ok':True,'share_id':sid})

@app.route('/shared/<sid>')
def shared(sid):
    try:
        r = _sb.table('shared_chats').select('chat_id').eq('id', sid).execute()
        if not r.data: return "Чат не найден",404
        msgs = get_msgs(r.data[0]['chat_id'])
    except Exception:
        return "Чат не найден",404
    return render_template_string("""<html><head><title>Общий чат</title></head><body style="background:#fff;color:#111;font-family:Segoe UI;padding:20px;max-width:760px;margin:auto"><h2>💬 Общий чат</h2>{{h|safe}}</body></html>""",
        h="".join(f'<div style="background:#f7f7f8;border-radius:12px;padding:12px;margin:10px 0;white-space:pre-wrap">{"Вы" if m["role"]=="user" else "🤖 AWESOME AI"}:<br>'+html.escape(m.get("content") or "")+"</div>" for m in msgs))

@app.route('/api/export', methods=['POST'])
def api_export():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    msgs = get_msgs(request.json.get('chat_id'))
    txt = "".join(("Вы: " if m['role']=='user' else "AWESOME AI: ")+str(m.get('content') or "")+"\n\n" for m in msgs)
    f = io.BytesIO(txt.encode('utf-8'))
    return send_file(f, as_attachment=True, download_name="chat.txt", mimetype="text/plain")

@app.route('/api/translate', methods=['POST'])
def api_translate():
    d = request.json; return jsonify({'ok':True,'translated':translate(d.get('text',''),d.get('target','ru'))})

@app.route('/api/draw', methods=['POST'])
def api_draw():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False,'error':'Авторизуйся'})
    if not can_send(uid): return jsonify({'ok':False,'error':'Лимит!'})
    img = gen_img(request.json.get('prompt',''))
    if img:
        try: incr(uid)
        except Exception: pass
        return jsonify({'ok':True,'image':img})
    return jsonify({'ok':False,'error':'Не удалось'})

@app.route('/api/profile')
def api_profile():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    u = get_user(uid); s = eff_status(uid)
    return jsonify({'ok':True,'user_id':uid,'name':u.get('name'),'login':u.get('login'),'theme':u.get('theme','light'),
                    'avatar':u.get('avatar',''),'ref_code':u.get('ref_code'),'premium':bool(s['premium']),
                    'is_admin':bool(s['is_admin']),'is_owner':bool(s['is_owner']),'level':s['level'],'xp':s['xp'],
                    'premium_expires':fmt_date(s['premium_expires']) if s['premium'] else None,
                    'messages_today':int(u.get('messages_today',0) or 0),'joined_at':u.get('joined_at')})

@app.route('/api/settings', methods=['POST'])
def api_settings():
    uid = session.get('user_id')
    if not uid: return jsonify({'ok':False})
    d = request.json
    upd_settings(uid, name=d.get('name'), theme=d.get('theme'), avatar=d.get('avatar'))
    if d.get('name'): session['name']=d['name']
    return jsonify({'ok':True})

# ===== АДМИНКА =====
def admin_check():
    uid = session.get('user_id')
    if not uid: return None, False, "Нет авторизации"
    if not eff_status(uid)['is_owner']: return None, False, "Нет доступа"
    return uid, True, ""

UNITS={'s':'секунд','sec':'секунд','min':'минут','m':'минут','h':'часов','hour':'часов','d':'дней','day':'дней','w':'недель','week':'недель','mo':'месяцев','month':'месяцев','y':'лет','year':'лет'}
def parse_duration(num, unit):
    try: n=int(num)
    except: return None
    now=gm()
    if unit in ('s','sec'): return (now+timedelta(seconds=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit in ('min','m'): return (now+timedelta(minutes=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit in ('h','hour'): return (now+timedelta(hours=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit in ('d','day'): return (now+timedelta(days=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit in ('w','week'): return (now+timedelta(weeks=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit in ('mo','month'): return (now+relativedelta(months=n)).strftime('%Y-%m-%d %H:%M:%S')
    if unit in ('y','year'): return (now+relativedelta(years=n)).strftime('%Y-%m-%d %H:%M:%S')
    return None

@app.route('/api/admin/stats')
def admin_stats():
    uid,ok,err = admin_check()
    if not ok: return jsonify({'ok':False,'error':err})
    try:
        users = _sb.table('users').select('*').execute().data or []
        total=len(users)
        prem=sum(1 for u in users if u.get('premium')==1)
        admins=sum(1 for u in users if u.get('is_admin')==1)
    except Exception:
        users=[]; total=0; prem=0; admins=0
    return jsonify({'ok':True,'total':total,'premium':prem,'admins':admins,
                    'users':[{'id':u.get('user_id'),'name':u.get('name'),'premium':u.get('premium'),'is_admin':u.get('is_admin'),'expires':u.get('premium_expires'),'level':u.get('level'),'xp':u.get('xp')} for u in users]})

@app.route('/api/admin/give', methods=['POST'])
def admin_give():
    uid,ok,err = admin_check()
    if not ok: return jsonify({'ok':False,'error':err})
    d = request.json; target = str(d.get('user_id','')).strip(); action = d.get('action')
    if not target: return jsonify({'ok':False,'error':'Укажи ID'})
    if not get_user(target): return jsonify({'ok':False,'error':'Пользователь не найден'})
    try:
        if action=='give_prem':
            exp = parse_duration(d.get('num',30), d.get('unit','d'))
            if not exp: return jsonify({'ok':False,'error':'Неверный срок'})
            _sb.table('users').update({'premium':1,'premium_expires':exp}).eq('user_id',target).execute()
        elif action=='take_prem':
            _sb.table('users').update({'premium':0,'premium_expires':None}).eq('user_id',target).execute()
        elif action=='give_admin':
            _sb.table('users').update({'is_admin':1}).eq('user_id',target).execute()
        elif action=='take_admin':
            _sb.table('users').update({'is_admin':0}).eq('user_id',target).execute()
        elif action=='delete_user':
            _sb.table('users').delete().eq('user_id',target).execute()
        elif action=='reset_pass':
            newpw = d.get('password','')
            if len(newpw)<3: return jsonify({'ok':False,'error':'Пароль мин.3'})
            _sb.table('users').update({'password':hash_pw(newpw)}).eq('user_id',target).execute()
        elif action=='set_xp':
            _sb.table('users').update({'xp':int(d.get('value',0)),'level':1+int(d.get('value',0))//100}).eq('user_id',target).execute()
        elif action=='set_theme':
            _sb.table('users').update({'theme':d.get('value','light')}).eq('user_id',target).execute()
    except Exception as e:
        return jsonify({'ok':False,'error':'Ошибка: '+str(e)})
    return jsonify({'ok':True})

# ===== HTML: точная копия ChatGPT =====
INDEX_HTML = r"""<!DOCTYPE html><html lang="ru"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Awesome AI</title>
<link rel="icon" href="/favicon.ico">
<style>
:root{--bg:#ffffff;--side:#f9f9f9;--border:#d9d9e3;--text:#0d0d0d;--muted:#6b6b74;--green:#10a37f;--green2:#0e8a6d;--hover:#ececf1;--shadow:rgba(0,0,0,.15)}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Söhne','Segoe UI',-apple-system,system-ui,sans-serif}
html,body{height:100%}
body{background:var(--bg);color:var(--text);overflow:hidden;-webkit-font-smoothing:antialiased}
.app{display:flex;height:100vh}
/* ---- Сайдбар как у ChatGPT ---- */
.sidebar{width:260px;background:var(--side);display:flex;flex-direction:column;border-right:1px solid var(--border);transition:transform .28s cubic-bezier(.4,0,.2,1);z-index:60}
.sidebar.closed{transform:translateX(-100%);width:0;min-width:0;border:none}
.new-chat{margin:10px;padding:11px 13px;background:#fff;border:1px solid var(--border);border-radius:8px;color:var(--text);cursor:pointer;font-size:13.5px;display:flex;align-items:center;gap:8px;transition:background .15s,box-shadow .15s}
.new-chat:hover{background:var(--hover);box-shadow:0 1px 3px var(--shadow)}
.chat-list{flex:1;overflow-y:auto;padding:4px 8px}
.chat-item{padding:10px 12px;border-radius:8px;cursor:pointer;margin-bottom:2px;font-size:13.5px;display:flex;align-items:center;gap:9px;transition:background .12s}
.chat-item:hover{background:#fff}
.chat-item.active{background:#fff;border:1px solid var(--border)}
.chat-item .t{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chat-item .del{opacity:0;background:none;border:none;color:var(--muted);cursor:pointer;font-size:13px}
.chat-item:hover .del{opacity:1}
.side-foot{padding:8px;border-top:1px solid var(--border)}
.side-btn{display:flex;align-items:center;gap:9px;width:100%;padding:9px 10px;border:none;background:none;color:var(--text);cursor:pointer;font-size:13.5px;border-radius:8px;transition:background .12s;text-align:left}
.side-btn:hover{background:#fff}
.side-btn .ic{width:28px;height:28px;border-radius:6px;background:var(--green);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:14px;flex-shrink:0;overflow:hidden}
.side-btn .ic img{width:100%;height:100%;object-fit:cover}
/* ---- Главная ---- */
.main{flex:1;display:flex;flex-direction:column;min-width:0;background:var(--bg)}
.topbar{height:48px;display:flex;align-items:center;gap:8px;padding:0 16px;border-bottom:1px solid var(--border);flex-shrink:0}
.burger{background:none;border:none;color:var(--text);font-size:19px;cursor:pointer;padding:6px;border-radius:6px;transition:background .12s}
.burger:hover{background:var(--hover)}
.topbar .ct{flex:1;text-align:center;font-size:14px;font-weight:500}
.topbar .rt{color:var(--muted);font-size:13px}
.messages{flex:1;overflow-y:auto}
.welcome{max-width:760px;margin:0 auto;padding:9vh 24px 24px;text-align:center;animation:fadeUp .5s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.welcome h1{font-size:clamp(26px,5vw,38px);font-weight:600;margin-bottom:10px;color:#111}
.welcome p{color:var(--muted);font-size:16px;margin-bottom:28px}
.sugg-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;max-width:680px;margin:0 auto}
.sugg{border:1px solid var(--border);border-radius:12px;padding:15px;cursor:pointer;font-size:13px;color:var(--muted);text-align:left;background:#fff;transition:background .15s,box-shadow .15s}
.sugg:hover{background:var(--hover);box-shadow:0 1px 4px var(--shadow)}
.sugg:active{transform:scale(.98)}
.msgrow{display:flex;gap:14px;padding:18px 22px;border-bottom:1px solid var(--border);animation:fadeUp .25s ease}
.msgrow.user{background:var(--bg)}
.msgrow.ai{background:#f7f7f8}
.msgrow .mb{max-width:780px;width:100%;margin:0 auto;font-size:15.5px;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.msgrow .mb b{font-weight:600}
.msgrow .mb .h{display:block;font-weight:600;font-size:17px;margin:16px 0 5px}
.msgrow .mb .h:first-child{margin-top:0}
.msgrow .ma{width:30px;height:30px;border-radius:6px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:600}
.msgrow.user .ma{background:var(--green);color:#fff}
.typing span{display:inline-block;width:7px;height:7px;border-radius:50%;background:#999;margin-right:4px;animation:blink 1.2s infinite}
.typing span:nth-child(2){animation-delay:.2s}.typing span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}
.inputarea{padding:12px 22px;background:var(--bg);flex-shrink:0}
.inputwrap{max-width:780px;margin:0 auto;display:flex;align-items:flex-end;gap:6px;background:#fff;border:1px solid var(--border);border-radius:24px;padding:9px 10px;transition:box-shadow .2s}
.inputwrap:focus-within{box-shadow:0 0 0 1px var(--green)}
textarea{flex:1;background:none;border:none;outline:none;color:var(--text);font-size:15px;resize:none;max-height:150px;line-height:1.5}
.tbtn{background:none;border:none;color:var(--muted);width:32px;height:32px;border-radius:8px;cursor:pointer;font-size:16px;transition:background .12s;flex-shrink:0}
.tbtn:hover{background:var(--hover)}
.sendbtn{width:32px;height:32px;border-radius:50%;background:var(--green);border:none;color:#fff;cursor:pointer;font-size:14px;flex-shrink:0;transition:background .15s,transform .1s;opacity:.5}
.sendbtn.on{opacity:1}
.sendbtn:hover{background:var(--green2)}
.sendbtn:active{transform:scale(.9)}
.foot{max-width:780px;margin:6px auto 0;text-align:center;font-size:11.5px;color:var(--muted)}
.foot a{color:var(--green);text-decoration:none}
/* ---- Модалки ---- */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:100;display:flex;align-items:center;justify-content:center;padding:16px;opacity:0;visibility:hidden;transition:opacity .22s,visibility .22s}
.overlay.show{opacity:1;visibility:visible}
.modal{background:#fff;border-radius:16px;padding:26px;width:100%;max-width:410px;text-align:center;transform:scale(.95);opacity:0;transition:transform .24s,opacity .22s;box-shadow:0 10px 40px rgba(0,0,0,.2)}
.overlay.show .modal{transform:scale(1);opacity:1}
.modal h2{margin-bottom:6px;font-size:20px}.modal p{color:var(--muted);font-size:14px;margin-bottom:16px}
.tabs{display:flex;background:var(--side);border-radius:8px;padding:4px;margin-bottom:16px}
.tab{flex:1;padding:8px;border-radius:6px;border:none;background:transparent;color:var(--muted);cursor:pointer;font-weight:500;font-size:14px}
.tab.active{background:#fff;color:var(--text);box-shadow:0 1px 3px var(--shadow)}
.inp{width:100%;padding:12px;background:var(--side);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:15px;margin-bottom:10px;outline:none}
.inp:focus{border-color:var(--green)}
.btn{width:100%;padding:12px;border:none;border-radius:8px;background:var(--green);color:#fff;font-weight:600;font-size:15px;cursor:pointer;margin-bottom:8px;transition:background .15s}
.btn:hover{background:var(--green2)}
.btn.ghost{background:var(--side);color:var(--text);border:1px solid var(--border)}
.logo-xl{width:54px;height:54px;border-radius:14px;background:var(--green);color:#fff;font-size:28px;font-weight:700;display:flex;align-items:center;justify-content:center;margin:0 auto 14px}
/* ---- Cookie ---- */
.cookie{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid var(--border);padding:14px 20px;z-index:200;display:flex;align-items:center;gap:14px;justify-content:space-between;transform:translateY(120%);transition:transform .35s cubic-bezier(.34,1.56,.64,1)}
.cookie.show{transform:translateY(0)}
.cookie p{font-size:13px;color:var(--muted)}
.cookie .cb{background:var(--green);color:#fff;border:none;border-radius:8px;padding:9px 18px;cursor:pointer;font-weight:600;white-space:nowrap;transition:background .15s}
.cookie .cb:hover{background:var(--green2)}
.toast{position:fixed;top:18px;right:18px;background:#fff;border:1px solid var(--border);border-radius:10px;padding:12px 16px;z-index:400;font-size:14px;box-shadow:0 4px 20px rgba(0,0,0,.15);transform:translateX(130%);transition:transform .3s}
.toast.show{transform:translateX(0)}
.toast.err{border-color:#e5484d}.toast.ok{border-color:var(--green)}
::-webkit-scrollbar{width:8px}::-webkit-scrollbar-thumb{background:#d9d9e3;border-radius:4px}
@media(max-width:768px){.sidebar{position:fixed;left:0;top:0;bottom:0;transform:translateX(-100%)}.sidebar.open{transform:translateX(0);box-shadow:0 0 40px rgba(0,0,0,.3)}.msgrow{padding:14px}.cookie{flex-direction:column;align-items:flex-start}}
</style></head><body>
<div class="app">
<aside class="sidebar" id="sidebar">
<button class="new-chat" onclick="newChat()">✏️ Новый чат</button>
<div class="chat-list" id="chatList"></div>
<div class="side-foot">
<button class="side-btn" onclick="openSupport()"><span class="ic">💬</span>Поддержка</button>
<button class="side-btn" onclick="openSettings()"><span class="ic" id="avBox">?</span><span id="uName">Пользователь</span></button>
</div>
</aside>
<div class="main">
<div class="topbar">
<button class="burger" onclick="toggleSidebar()">☰</button>
<div class="ct" id="ctTitle">Новый чат</div>
<div class="rt" id="uStatus"></div>
</div>
<div class="messages" id="messages">
<div class="welcome" id="welcome">
<h1>Чем я могу помочь?</h1><p>Твой умный собеседник нового поколения</p>
<div class="sugg-grid">
<button class="sugg" onclick="send('Объясни простыми словами квантовые вычисления')">🔬 Объясни простыми словами</button>
<button class="sugg" onclick="send('Напиши код на Python для бота')">💻 Напиши код</button>
<button class="sugg" onclick="send('Составь план на день')">📋 Составь план</button>
<button class="sugg" onclick="send('погода в Москве')">🌤 Погода</button>
<button class="sugg" onclick="send('курс доллара')">💵 Курс валют</button>
<button class="sugg" onclick="send('придумай название для кофейни')">☕ Идеи названий</button>
</div></div></div>
<div class="inputarea">
<div class="inputwrap">
<button class="tbtn" onclick="draw()" title="Рисовать">🎨</button>
<textarea id="input" rows="1" placeholder="Отправь сообщение" oninput="autoGrow(this)" onkeydown="onKey(event)"></textarea>
<button class="sendbtn" id="sendBtn" onclick="send()">➤</button>
</div>
<div class="foot">Awesome AI может ошибаться. Поддержка: <a href="https://t.me/flidges" target="_blank">@flidges</a></div>
</div>
</div></div>

<div class="cookie" id="cookie">
<p>🍪 Мы используем файлы cookie, чтобы улучшить ваш опыт работы с сервисом.</p>
<button class="cb" onclick="acceptCookie()">Принять</button>
</div>

<div class="overlay" id="authOverlay">
<div class="modal">
<div class="logo-xl">A</div>
<div class="tabs"><button class="tab active" id="tabLogin" onclick="switchTab('login')">Вход</button><button class="tab" id="tabReg" onclick="switchTab('reg')">Регистрация</button></div>
<h2 id="authTitle">Вход</h2><p id="authSub">Войди, чтобы продолжить</p>
<div id="regWrap" style="display:none"><input class="inp" id="regName" placeholder="Имя"></div>
<input class="inp" id="authLogin" placeholder="Логин">
<input class="inp" type="password" id="authPass" placeholder="Пароль">
<button class="btn" id="authBtn" onclick="submitAuth()">Войти</button>
</div></div>

<div class="overlay" id="supportOverlay">
<div class="modal">
<div class="logo-xl">💬</div>
<h2>Поддержка</h2><p>Напишите нам — поможем быстро</p>
<a class="btn" style="display:block;text-decoration:none;text-align:center" href="https://t.me/flidges" target="_blank">📨 Telegram: @flidges</a>
<button class="btn ghost" onclick="closeOv('supportOverlay')">Закрыть</button>
</div></div>

<div class="overlay" id="settingsOverlay">
<div class="modal"><h2>Профиль</h2><p>Настройки</p>
<input class="inp" id="setName" placeholder="Имя">
<div id="profInfo" style="font-size:13px;color:var(--muted);margin-bottom:12px;text-align:left"></div>
<button class="btn" onclick="saveSettings()">Сохранить</button>
<button class="btn ghost" onclick="logout()">Выйти</button>
<button class="btn ghost" onclick="closeOv('settingsOverlay')">Закрыть</button></div></div>

<script>
let uid=null,cid=null,sending=false,mode='login';
const $=id=>document.getElementById(id);
function toast(t,ty){const e=document.createElement('div');e.className='toast '+(ty||'');e.textContent=t;document.body.appendChild(e);requestAnimationFrame(()=>e.classList.add('show'));setTimeout(()=>{e.classList.remove('show');setTimeout(()=>e.remove(),300)},3000)}
async function api(u,m,b){try{const o={method:m||'GET',headers:{'Content-Type':'application/json'}};if(b)o.body=JSON.stringify(b);const r=await fetch(u,o);const t=await r.text();try{return JSON.parse(t)}catch(e){return{ok:false,error:'Сервер ['+r.status+']: '+t.slice(0,200)}}}catch(e){return{ok:false,error:'Нет соединения'}}}
function toggleSidebar(){const s=$('sidebar');if(innerWidth<=768)s.classList.toggle('open');else s.classList.toggle('closed')}
function openOv(id){$(id).classList.add('show')}
function closeOv(id){$(id).classList.remove('show')}
function switchTab(m){mode=m;$('tabLogin').className='tab'+(m==='login'?' active':'');$('tabReg').className='tab'+(m==='reg'?' active':'');$('regWrap').style.display=m==='reg'?'block':'none';$('authTitle').textContent=m==='reg'?'Регистрация':'Вход';$('authBtn').textContent=m==='reg'?'Создать':'Войти'}
async function submitAuth(){const login=$('authLogin').value.trim(),pw=$('authPass').value;if(!login||!pw){toast('Заполни логин и пароль','err');return}const body=mode==='reg'?{login,password:pw,name:$('regName').value.trim()}:{login,password:pw};const r=await api(mode==='reg'?'/api/register':'/api/login','POST',body);if(r.ok){uid=r.user_id;closeOv('authOverlay');toast('Добро пожаловать!','ok');init()}else toast(r.error||'Ошибка','err')}
async function logout(){await api('/api/logout','POST');location.reload()}
async function init(){const me=await api('/api/me');if(me.ok){uid=me.user_id;$('authOverlay').classList.remove('show');if(me.avatar)$('avBox').innerHTML='<img src="'+me.avatar+'">';else $('avBox').textContent=String(me.name||'?').slice(0,1).toUpperCase();$('uName').textContent=me.name||'Пользователь';await loadChats();await checkStatus()}else openOv('authOverlay')}
async function checkStatus(){const r=await api('/api/status');if(r.ok)$('uStatus').textContent=r.status_text+' · Ур.'+r.level}
async function loadChats(){const r=await api('/api/chats');if(!r.ok)return;const l=$('chatList');l.innerHTML='';r.chats.forEach(c=>{const d=document.createElement('div');d.className='chat-item'+(c.id===cid?' active':'');d.innerHTML=(c.pinned?'⭐ ':'💬')+'<span class="t">'+esc(c.title||'Чат')+'</span><button class="del" onclick="delChat('+c.id+',event)">✕</button>';d.onclick=()=>openChat(c);l.appendChild(d)})}
function openChat(c){cid=c.id;$('messages').innerHTML='';$('welcome').style.display='none';$('ctTitle').textContent=c.title||'Чат';(c.messages||[]).forEach(m=>addMsg(m.role,m.content,m.image));if(innerWidth<=768)toggleSidebar()}
async function newChat(){const r=await api('/api/chat/new','POST');if(r.ok){cid=r.chat_id;$('messages').innerHTML='';$('welcome').style.display='';$('ctTitle').textContent='Новый чат';loadChats()}}
async function delChat(id,e){e.stopPropagation();await api('/api/chat/delete','POST',{chat_id:id});if(id===cid){cid=null;boxReset()}loadChats()}
function boxReset(){$('messages').innerHTML='';$('welcome').style.display='';$('ctTitle').textContent='Новый чат'}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmtAI(t){if(!t)return'';let out='';for(const line of t.split('\n')){const h=line.match(/^\*\*(.+?)\*\*$/);if(h){out+='<div class="h">'+esc(h[1])+'</div>';continue}const parts=line.split(/(\*\*.*?\*\*)/g);let p='';for(const part of parts){if(part.startsWith('**')&&part.endsWith('**')&&part.length>4)p+='<b>'+esc(part.slice(2,-2))+'</b>';else p+=esc(part)}out+='<div style="margin:2px 0">'+p+'</div>'}return out}
function addMsg(role,text,img){const box=$('messages');if($('welcome'))$('welcome').style.display='none';const m=document.createElement('div');m.className='msgrow '+role;let av=role==='user'?'<div class="ma">'+String(uid||'?').slice(0,1).toUpperCase()+'</div>':'<div class="ma">🤖</div>';let content=role==='ai'?fmtAI(text):esc(text);if(img)content+='<img style="max-width:100%;border-radius:10px;margin-top:8px" src="'+img+'">';m.innerHTML=av+'<div class="mb">'+content+'</div>';box.appendChild(m);box.scrollTop=box.scrollHeight}
function addTyping(){const box=$('messages');const m=document.createElement('div');m.className='msgrow ai';m.id='typing';m.innerHTML='<div class="ma">🤖</div><div class="mb typing"><span></span><span></span><span></span></div>';box.appendChild(m);box.scrollTop=box.scrollHeight}
function rmTyping(){const t=$('typing');if(t)t.remove()}
async function send(preset){if(sending)return;const input=$('input');const msg=(preset!==undefined)?preset:input.value.trim();if(!msg)return;input.value='';autoGrow(input);addMsg('user',msg);sending=true;addTyping();const r=await api('/api/chat','POST',{message:msg,chat_id:cid});rmTyping();sending=false;if(r.ok){cid=r.chat_id;addMsg('ai',r.response);$('ctTitle').textContent='Чат';loadChats()}else addMsg('ai','⚠️ '+(r.error||'Ошибка'));checkStatus()}
function onKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}
function autoGrow(t){t.style.height='auto';t.style.height=Math.min(t.scrollHeight,150)+'px'}
async function draw(){const p=prompt('🎨 Что нарисовать?');if(!p)return;addMsg('user','🎨 '+p);sending=true;addTyping();const r=await api('/api/draw','POST',{prompt:p});rmTyping();sending=false;if(r.ok&&r.image)addMsg('ai','Готово!',r.image);else addMsg('ai','⚠️ '+(r.error||'Не удалось'))}
function openSupport(){openOv('supportOverlay')}
async function openSettings(){const r=await api('/api/profile');if(r.ok){$('setName').value=r.name||'';$('profInfo').innerHTML='ID: <b>'+esc(r.user_id)+'</b><br>'+(r.premium?'💎 Premium до '+esc(r.premium_expires):'🔓 Free')+'<br>⭐ Уровень '+r.level+' · XP '+r.xp}openOv('settingsOverlay')}
async function saveSettings(){const r=await api('/api/settings','POST',{name:$('setName').value.trim()||undefined});if(r.ok){closeOv('settingsOverlay');toast('Сохранено','ok');init()}}
function acceptCookie(){$('cookie').classList.remove('show');try{localStorage.setItem('sc_cookie','1')}catch(e){}}
document.addEventListener('DOMContentLoaded',()=>{init();try{if(!localStorage.getItem('sc_cookie'))setTimeout(()=>$('cookie').classList.add('show'),800)}catch(e){}});
</script></body></html>"""

if __name__ == '__main__':
    print("🧠 AWESOME AI — ChatGPT Clone (Supabase)")
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
