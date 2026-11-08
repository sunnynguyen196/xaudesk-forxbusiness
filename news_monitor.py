"""Read-only public VNWallstreet Telegram monitor. Standard library only."""
import re, time, threading, urllib.request, html
from html.parser import HTMLParser
from datetime import datetime, timezone
from urllib.parse import urljoin

SOURCE='https://t.me/s/vnwallstreet'
SITE='https://vnwallstreet.com/#/home'
INTERVAL=120
RULES=[
 ('Vàng',r'\b(?:xauusd|xau/usd|gold|spot gold|comex)\b|giá vàng|vàng giao ngay|kim loại quý', 'Giá vàng hoặc dòng tiền vào vàng có thể phản ứng trực tiếp; kiểm tra giá MT5 và thời điểm tin.'),
 ('Fed / lãi suất Mỹ',r'\b(?:fomc|fedwatch|federal reserve|powell)\b|\bfed\b|lãi suất (?:mỹ|hoa kỳ)|cục dự trữ liên bang', 'Kỳ vọng lãi suất Mỹ ảnh hưởng lợi suất thực và chi phí cơ hội nắm giữ vàng; chiều tác động phụ thuộc mức bất ngờ.'),
 ('Lạm phát / việc làm Mỹ',r'\b(?:nfp|nonfarm|pce|cpi|ppi)\b|bảng lương phi nông nghiệp|lạm phát mỹ|việc làm mỹ|thất nghiệp mỹ', 'Dữ liệu Mỹ có thể thay đổi kỳ vọng Fed và USD, từ đó tác động đến XAU/USD.'),
 ('USD / lợi suất Mỹ',r'\b(?:dxy|us dollar index|treasury yields|us10y)\b|chỉ số đô la|đồng usd|đồng đô la mỹ|lợi suất trái phiếu (?:mỹ|kho bạc mỹ)', 'USD và lợi suất Mỹ thường tác động đến vàng; cần đối chiếu hướng biến động thực tế.'),
 ('Rủi ro địa chính trị',r'\b(?:hormuz|iran|israel|houthi|ukraine|russia|saudi aramco)\b|eo biển hormuz|vịnh oman|tàu dầu|tàu chở dầu|tên lửa|không kích|xung đột|chiến sự|phong tỏa hàng hải|tấn công quân sự', 'Rủi ro leo thang có thể tăng nhu cầu trú ẩn, nhưng tác động đến vàng không chắc chắn và có thể đảo chiều.'),
 ('Ngân hàng trung ương / ETF vàng',r'\b(?:spdr|gold etf|central bank gold)\b|dự trữ vàng|mua vàng của ngân hàng trung ương', 'Dòng vốn ETF hoặc nhu cầu dự trữ có thể ảnh hưởng cung cầu vàng; cần xác minh số liệu.'),
]
class Posts(HTMLParser):
 def __init__(self):super().__init__();self.posts=[];self.cur=None;self.capture=False;self.depth=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);cls=a.get('class','')
  if tag=='div' and 'tgme_widget_message_wrap' in cls.split():
   self.cur={'text':'','url':'','datetime':''};self.depth=1;return
  if self.cur is None:return
  if tag=='div':self.depth+=1
  if tag=='div' and 'tgme_widget_message_text' in cls.split():self.capture=True
  if tag=='a' and 'tgme_widget_message_date' in cls.split():self.cur['url']=a.get('href','')
  if tag=='time' and a.get('datetime'):self.cur['datetime']=a['datetime']
  if tag=='br' and self.capture:self.cur['text']+='\n'
 def handle_endtag(self,tag):
  if self.cur is None:return
  if tag=='div':
   self.depth-=1
   if self.depth==0:
    self.posts.append(self.cur);self.cur=None;self.capture=False
  if tag=='div' and self.capture and self.depth<=2:self.capture=False
 def handle_data(self,data):
  if self.cur is not None and self.capture:self.cur['text']+=data

def classify(t):
 text=t.casefold();matches=[(n,why) for n,rx,why in RULES if re.search(rx,text,re.I)]
 if not matches:return None
 # Strict filter: geopolitics needs material market transmission, not generic political remarks.
 if all(n=='Rủi ro địa chính trị' for n,_ in matches) and not re.search(r'tên lửa|không kích|tấn công|tàu dầu|tàu chở dầu|hormuz|phong tỏa|vịnh oman|chiến sự|xung đột|leo thang|saudi aramco|dầu thô|mìn|bốc cháy',text,re.I):return None
 return matches

class Monitor:
 def __init__(self):
  self.lock=threading.Lock();self.data={'items':[],'last_checked':None,'last_success':None,'telegram_status':'Chưa kiểm tra','website_status':'Website động: chưa có luồng bài viết được xác minh','interval_seconds':INTERVAL};self.next=0;self.running=False
 def get(self,force=False):
  with self.lock:
   if not self.running and (force or time.time()>=self.next):
    self.running=True;self.next=time.time()+INTERVAL;threading.Thread(target=self.update,daemon=True).start()
   return dict(self.data)
 def update(self):
  checked=int(time.time());items=[];status='Không đọc được Telegram'
  try:
   req=urllib.request.Request(SOURCE,headers={'User-Agent':'Mozilla/5.0 (compatible; XAUDeskReadOnly/1.0)'})
   with urllib.request.urlopen(req,timeout=12) as resp:
    raw=resp.read(1500000).decode('utf-8','replace')
   parser=Posts();parser.feed(raw)
   for post in parser.posts:
    txt=' '.join(html.unescape(post['text']).split())[:1200]
    if not txt:continue
    matched=classify(txt)
    if not matched:continue
    url=post['url']
    if not url.startswith('https://t.me/vnwallstreet/'):continue
    items.append({'id':url.rsplit('/',1)[-1],'text':txt,'url':url,'published':post['datetime'],'categories':[x[0] for x in matched],'analysis':' '.join(dict.fromkeys(x[1] for x in matched)),'impact':'Cần xác nhận trên MT5 / USD / lợi suất','verified':False,'source':'telegram','relevance':'Cao' if any(x[0] in ('Vàng','Fed / lãi suất Mỹ','Lạm phát / việc làm Mỹ','USD / lợi suất Mỹ') for x in matched) else 'Trung bình','needs_confirmation':True})
   items=list({item['id']:item for item in items}.values())[-40:][::-1]
   status=f'Đã đọc {len(parser.posts)} bài công khai; lọc được {len(items)} tin liên quan đến vàng (chưa xác minh độc lập)'
   with self.lock:self.data.update(items=items,last_success=checked,telegram_status=status)
  except Exception as e:
   status='Không thể đọc Telegram: '+str(e)[:110]
   with self.lock:self.data['telegram_status']=status
  finally:
   with self.lock:self.data['last_checked']=checked;self.running=False
MONITOR=Monitor()
