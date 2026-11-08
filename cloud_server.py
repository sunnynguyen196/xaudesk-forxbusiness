"""XAUDesk cloud server: read-only market snapshots, no trading/account endpoints."""
import os, json, time, hmac, threading, math, base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent
TOKEN=os.environ.get('XAU_INGEST_TOKEN','')
USER=os.environ.get('XAU_DASH_USER','')
PASSWORD=os.environ.get('XAU_DASH_PASSWORD','')
PORT=int(os.environ.get('PORT','8765'))
STORE=Path(os.environ.get('XAU_STORE','/tmp/xaudesk_snapshot.json'))
LOCK=threading.Lock()
MAX_BODY=50000

def valid(d):
    def num(x):return isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x)
    if not isinstance(d,dict) or d.get('symbol')!='XAUUSD.c':return False
    if not all(num(d.get(k)) for k in ('bid','ask','quote_utc','sent_utc')):return False
    if d['bid']<=0 or d['ask']<d['bid'] or abs(d['sent_utc']-time.time())>120:return False
    bars=d.get('candles')
    if not isinstance(bars,list) or not 5<=len(bars)<=80:return False
    prev=0
    for b in bars:
        if not isinstance(b,dict) or not all(num(b.get(k)) for k in ('t','o','h','l','c')):return False
        if b['t']<=prev or b['l']<=0 or b['h']<max(b['o'],b['c']) or b['l']>min(b['o'],b['c']):return False
        prev=b['t']
    return True

def secure_equal(a,b):return hmac.compare_digest(a.encode(),b.encode())
class Handler(BaseHTTPRequestHandler):
    def reply(self,code,obj,mime='application/json; charset=utf-8',extra=None):
        body=json.dumps(obj,allow_nan=False).encode() if isinstance(obj,dict) else obj
        self.send_response(code)
        self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if extra:
            for k,v in extra.items():self.send_header(k,v)
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def authorized(self):
        if not USER or not PASSWORD:return False
        h=self.headers.get('Authorization','')
        if not h.startswith('Basic '):return False
        try:
            u,p=base64.b64decode(h[6:],validate=True).decode().split(':',1)
            return secure_equal(u,USER) and secure_equal(p,PASSWORD)
        except (ValueError,UnicodeError):return False
    def guard(self):
        if not self.authorized():
            self.reply(401,{'error':'Authentication required'},extra={'WWW-Authenticate':'Basic realm="XAUDesk Private"'})
            return False
        return True
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/health':return self.reply(200,{'ok':True,'service':'xaudesk-cloud'})
        if not self.guard():return
        if path in ('/','/index.html'):
            return self.reply(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
        if path=='/api/state':
            try:
                with LOCK:d=json.loads(STORE.read_text(encoding='utf-8'))
                if not valid(d):raise ValueError('Invalid stored snapshot')
                now=int(time.time());age=now-int(d['quote_utc']);upload_age=now-int(d['sent_utc'])
                return self.reply(200,{'ok':True,'data':d,'stale':age>30 or age< -60 or upload_age>30,'age_seconds':age,'server_utc':now})
            except (OSError,ValueError,TypeError):
                return self.reply(200,{'ok':False,'error':'Chưa nhận dữ liệu hợp lệ từ MT5 hoặc dữ liệu chưa được lưu.','server_utc':int(time.time())})
        return self.reply(404,{'error':'Not found'})
    def do_POST(self):
        if urlsplit(self.path).path!='/api/ingest':return self.reply(404,{'error':'Not found'})
        if not TOKEN or not secure_equal(self.headers.get('X-XAU-Token',''),TOKEN):return self.reply(401,{'error':'Invalid ingestion token'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=MAX_BODY:return self.reply(413,{'error':'Invalid payload size'})
            d=json.loads(self.rfile.read(n))
            if not valid(d):return self.reply(422,{'error':'Invalid market snapshot'})
            with LOCK:
                STORE.parent.mkdir(parents=True,exist_ok=True)
                tmp=STORE.with_suffix('.tmp');tmp.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');tmp.replace(STORE)
            return self.reply(200,{'ok':True,'received_utc':int(time.time())})
        except (ValueError,TypeError,UnicodeDecodeError):return self.reply(400,{'error':'Invalid JSON'})
    def log_message(self,fmt,*args):pass
if __name__=='__main__':
    if not all((TOKEN,USER,PASSWORD)) or min(map(len,(TOKEN,PASSWORD)))<20:
        raise SystemExit('Set XAU_INGEST_TOKEN and XAU_DASH_PASSWORD (at least 20 chars) and XAU_DASH_USER')
    print(f'XAUDesk Cloud listening on {PORT}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
