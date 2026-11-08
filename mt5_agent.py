"""Runs on Windows next to MT5; sends read-only snapshots over HTTPS."""
import os, time, json, urllib.request, urllib.error
from market import snapshot
URL=os.environ.get('XAU_CLOUD_URL','').rstrip('/')
TOKEN=os.environ.get('XAU_INGEST_TOKEN','')
INTERVAL=max(5,int(os.environ.get('XAU_PUSH_SECONDS','10')))
if not URL.startswith('https://') or not TOKEN:
    raise SystemExit('Set XAU_CLOUD_URL=https://... and XAU_INGEST_TOKEN')
print('MT5 -> cloud agent started; market data only, no account data',flush=True)
while True:
    try:
        data=snapshot()
        body=json.dumps(data,allow_nan=False).encode()
        req=urllib.request.Request(URL+'/api/ingest',data=body,headers={'Content-Type':'application/json','X-XAU-Token':TOKEN},method='POST')
        with urllib.request.urlopen(req,timeout=12) as r:
            result=json.load(r)
        print('Uploaded',data['symbol'],'quote_utc',data['quote_utc'],'ok',result.get('ok'),flush=True)
    except Exception as e:
        print('Upload failed:',type(e).__name__,str(e)[:180],flush=True)
    time.sleep(INTERVAL)
