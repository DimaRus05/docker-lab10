"""Проверка запущенного стенда без остановки и удаления контейнеров."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
from urllib.request import build_opener, ProxyHandler, HTTPSHandler, Request

ROOT = Path(__file__).resolve().parent
COMPOSE = ['docker', 'compose', '-p', 'cloudtech-lab10']
checks = []
outputs = []

def run(*args):
    command = [*COMPOSE, *args]
    p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
    outputs.append({'command':command,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout

def record(name, detail):
    checks.append({'check':name,'result':'PASS','detail':detail})
    print('PASS:',name,'-',detail,flush=True)

run('config','--quiet')
record('Compose configuration', 'valid')
config = json.loads(run('config','--format','json'))
assert set(config['services']) == {'app1','app2','nginx'}
assert all(not config['services'][name].get('ports') for name in ('app1','app2'))
record('Backend isolation', 'app1/app2 have no published host ports')
ps_text=run('ps','--format','json')
try:
    services=json.loads(ps_text)
except json.JSONDecodeError:
    services=[json.loads(line) for line in ps_text.splitlines() if line.strip()]
if isinstance(services,dict):
    services=[services]
assert len(services)==3 and all(item['State']=='running' for item in services)
assert all(item.get('Health')=='healthy' for item in services if item['Service'] in ('app1','app2'))
record('Container state', 'three running; both Flask backends healthy')
nginx_test=run('exec','-T','nginx','nginx','-t')
record('nginx syntax', 'configuration test successful')
for name in ('app1','app2'):
    uid=run('exec','-T',name,'id','-u').strip()
    assert uid!='0'
    record(name+' user', 'uid='+uid)
    for route in ('/','/hello'):
        command="import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080"+route+"',timeout=3).read().decode())"
        text=run('exec','-T',name,'python3','-c',command)
        assert 'Hello World from '+name+'!' in text and '{{' not in text
    record(name+' templates/routes', '/ and /hello return their own name')
    cid=run('ps','-q',name).strip()
    p=subprocess.run(['docker','inspect','--format','{{json .Mounts}}',cid],capture_output=True,text=True,check=True)
    mounts=json.loads(p.stdout)
    assert any(m['Destination']=='/storage' and not m['RW'] for m in mounts)
    record(name+' shared storage', '/storage is mounted read-only')

# Берём из контейнера только сертификат, чтобы проверить HTTPS.
certificate_path=ROOT/'docs/localhost.crt'
certificate_path.parent.mkdir(exist_ok=True)
certificate_path.write_text(run('exec','-T','nginx','cat','/etc/nginx/certs/localhost.crt'),encoding='ascii')
context=ssl.create_default_context(cafile=str(certificate_path))
with socket.create_connection(('localhost',443),timeout=10) as connection:
    with context.wrap_socket(connection,server_hostname='localhost') as tls:
        certificate=tls.getpeercert()
        protocol=tls.version()
assert protocol in ('TLSv1.2','TLSv1.3')
assert ('DNS','localhost') in certificate['subjectAltName']
record('TLS certificate', 'hostname/chain verified; '+protocol)
opener=build_opener(ProxyHandler({}),HTTPSHandler(context=context))
requests=[]
for number in range(1,21):
    request=Request('https://localhost/',headers={'Connection':'close','Cache-Control':'no-cache'})
    with opener.open(request,timeout=10) as response:
        body=response.read().decode()
        assert response.status==200 and response.headers.get('Cache-Control')=='no-store'
        backend=re.search(r'Hello World from (app[12])!',body).group(1)
        requests.append({'request':number,'url':request.full_url,'status':response.status,'backend':backend,
                         'headers':dict(response.headers),'body':body})
        print(number,'HTTP',response.status,backend,flush=True)
sequence=[r['backend'] for r in requests]
assert all(a!=b for a,b in zip(sequence,sequence[1:])), sequence
assert Counter(sequence)=={'app1':10,'app2':10}
record('Round-robin', '20 HTTPS requests; strict alternation; app1=10, app2=10')
with opener.open('https://localhost/favicon.ico',timeout=10) as response:
    assert response.status==204
record('Browser favicon', '204, handled by nginx')
report={'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,
        'tls':{'protocol':protocol,'certificate':certificate},'services':services,
        'requests':requests,'command_outputs':outputs}
docs=ROOT/'docs'
docs.mkdir(exist_ok=True)
(docs/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALL CHECKS PASSED; evidence: docs/verification.json')
