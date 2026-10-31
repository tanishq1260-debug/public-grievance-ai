from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import sqlite3, uuid, shutil, re

BASE = Path(__file__).resolve().parent
# Vercel functions have ephemeral writable storage. Use /tmp there;
# local development keeps files beside the project. Data on Vercel is not durable.
IS_VERCEL = bool(__import__('os').environ.get('VERCEL'))
DATA_DIR = Path('/tmp/public_grievance_ai') if IS_VERCEL else BASE
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / 'grievances.db'
UPLOADS = DATA_DIR / 'uploads'
UPLOADS.mkdir(exist_ok=True)
app = FastAPI(title='Public Grievance AI Assistant', version='1.0.0')
app.mount('/static', StaticFiles(directory=BASE/'static'), name='static')
app.mount('/uploads', StaticFiles(directory=UPLOADS), name='uploads')
templates = Jinja2Templates(directory=BASE/'templates')


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticket TEXT UNIQUE, citizen TEXT, email TEXT,
            category TEXT, subject TEXT, description TEXT, location TEXT, department TEXT,
            priority TEXT, status TEXT DEFAULT 'Submitted', attachment TEXT, created_at TEXT,
            updated_at TEXT, admin_note TEXT DEFAULT '')''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE,
            password TEXT, role TEXT DEFAULT 'citizen')''')
        # Demo accounts, intended for local hackathon demo only.
        c.execute('INSERT OR IGNORE INTO users(name,email,password,role) VALUES(?,?,?,?)',
                  ('Demo Citizen','citizen@demo.local','citizen123','citizen'))
        c.execute('INSERT OR IGNORE INTO users(name,email,password,role) VALUES(?,?,?,?)',
                  ('Demo Admin','admin@demo.local','admin123','admin'))

init_db()

KEYWORDS = {
 'Sanitation': ['garbage','waste','dump','clean','drain','sewage','dustbin','sanitation'],
 'Water Supply': ['water','pipe','leak','tap','drinking water','supply'],
 'Roads & Transport': ['road','pothole','traffic','street','signal','footpath'],
 'Electricity': ['electric','power','streetlight','light','transformer','wire'],
 'Public Safety': ['unsafe','accident','danger','crime','fire','hazard'],
 'Public Health': ['hospital','health','mosquito','disease','medical','clinic'],
 'Other': []
}
DEPARTMENTS = {
 'Sanitation':'Municipal Sanitation Department', 'Water Supply':'Water Works Department',
 'Roads & Transport':'Roads and Transport Department', 'Electricity':'Electricity Department',
 'Public Safety':'Public Safety Department', 'Public Health':'Public Health Department',
 'Other':'General Grievance Cell'
}

def classify(text):
    t = text.lower()
    scores = {cat: sum(1 for k in words if k in t) for cat, words in KEYWORDS.items()}
    category = max(scores, key=scores.get)
    if scores[category] == 0: category = 'Other'
    urgent_words = ['urgent','emergency','danger','fire','injury','life threatening','exposed wire']
    priority = 'High' if any(w in t for w in urgent_words) else ('Medium' if category != 'Other' else 'Low')
    summary = re.sub(r'\s+', ' ', text).strip()
    if len(summary) > 180: summary = summary[:177].rstrip() + '...'
    return category, DEPARTMENTS[category], priority, summary


def page(request, name, **kwargs):
    return templates.TemplateResponse(name, {'request': request, **kwargs})

@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    with conn() as c:
        total = c.execute('SELECT COUNT(*) n FROM complaints').fetchone()['n']
        resolved = c.execute("SELECT COUNT(*) n FROM complaints WHERE status='Resolved'").fetchone()['n']
        pending = total - resolved
        recent = c.execute('SELECT * FROM complaints ORDER BY id DESC LIMIT 5').fetchall()
    return page(request, 'index.html', total=total, resolved=resolved, pending=pending, recent=recent)

@app.get('/submit', response_class=HTMLResponse)
def submit_page(request: Request): return page(request, 'submit.html')

@app.post('/submit')
async def submit_complaint(citizen: str = Form(...), email: str = Form(...), subject: str = Form(...),
                          description: str = Form(...), location: str = Form(...),
                          attachment: UploadFile = File(None)):
    full = f'{subject}. {description}'
    category, department, priority, summary = classify(full)
    ticket = 'GRV-' + uuid.uuid4().hex[:8].upper()
    filename = None
    if attachment and attachment.filename:
        ext = Path(attachment.filename).suffix.lower()
        if ext not in {'.png','.jpg','.jpeg','.pdf','.txt','.doc','.docx'}:
            raise HTTPException(400, 'Allowed attachment types: image, PDF, or document')
        filename = ticket + ext
        with (UPLOADS/filename).open('wb') as out: shutil.copyfileobj(attachment.file, out)
    now = datetime.now().isoformat(timespec='seconds')
    with conn() as c:
        c.execute('''INSERT INTO complaints(ticket,citizen,email,category,subject,description,location,department,priority,status,attachment,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,'Submitted',?,?,?)''',
          (ticket,citizen,email,category,subject,description,location,department,priority,filename,now,now))
    return RedirectResponse(f'/track/{ticket}?new=1', status_code=303)

@app.get('/track', response_class=HTMLResponse)
def track_page(request: Request): return page(request, 'track.html', complaint=None, ticket='')

@app.get('/track/{ticket}', response_class=HTMLResponse)
def track_ticket(request: Request, ticket: str):
    with conn() as c: item = c.execute('SELECT * FROM complaints WHERE ticket=?',(ticket.upper(),)).fetchone()
    return page(request, 'track.html', complaint=item, ticket=ticket.upper())

@app.get('/admin', response_class=HTMLResponse)
def admin(request: Request, q: str = '', status: str = 'All'):
    sql = 'SELECT * FROM complaints WHERE 1=1'; args=[]
    if q:
        sql += ' AND (ticket LIKE ? OR subject LIKE ? OR citizen LIKE ? OR location LIKE ?)'; args += [f'%{q}%']*4
    if status != 'All': sql += ' AND status=?'; args.append(status)
    sql += ' ORDER BY CASE priority WHEN "High" THEN 1 WHEN "Medium" THEN 2 ELSE 3 END, id DESC'
    with conn() as c:
        rows=c.execute(sql,args).fetchall()
        stats={s:c.execute('SELECT COUNT(*) n FROM complaints WHERE status=?',(s,)).fetchone()['n'] for s in ['Submitted','In Progress','Resolved']}
        total=c.execute('SELECT COUNT(*) n FROM complaints').fetchone()['n']
    return page(request,'admin.html',rows=rows,stats=stats,total=total,q=q,status=status)

@app.post('/admin/{ticket}/update')
def update(ticket: str, status: str = Form(...), admin_note: str = Form('')):
    if status not in {'Submitted','In Progress','Resolved','Rejected'}: raise HTTPException(400,'Invalid status')
    with conn() as c:
        c.execute('UPDATE complaints SET status=?,admin_note=?,updated_at=? WHERE ticket=?',
                  (status,admin_note,datetime.now().isoformat(timespec='seconds'),ticket.upper()))
    return RedirectResponse('/admin',status_code=303)

@app.get('/api/complaints')
def api_complaints():
    with conn() as c: rows=c.execute('SELECT ticket,category,subject,location,department,priority,status,created_at FROM complaints ORDER BY id DESC').fetchall()
    return {'complaints':[dict(r) for r in rows]}

@app.get('/api/analytics')
def analytics():
    with conn() as c:
        total=c.execute('SELECT COUNT(*) n FROM complaints').fetchone()['n']
        by_category=[dict(r) for r in c.execute('SELECT category label,COUNT(*) value FROM complaints GROUP BY category ORDER BY value DESC')]
        by_status=[dict(r) for r in c.execute('SELECT status label,COUNT(*) value FROM complaints GROUP BY status')]
    return {'total':total,'by_category':by_category,'by_status':by_status}

@app.get('/health')
def health(): return {'status':'ok','app':'Public Grievance AI Assistant'}
