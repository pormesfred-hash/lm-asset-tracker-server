from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timezone
import sqlite3, os

app=Flask(__name__)
DB='assets.db'
TOKEN=os.environ.get('LM_DEVICE_TOKEN','CHANGE-ME-DEVICE-TOKEN')
ADMIN=os.environ.get('LM_ADMIN_KEY','CHANGE-ME-ADMIN-KEY')

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=db(); c.execute('''CREATE TABLE IF NOT EXISTS devices(asset_id TEXT PRIMARY KEY, hostname TEXT, assigned_user TEXT, windows_user TEXT, local_ip TEXT, public_ip TEXT, latitude REAL, longitude REAL, location_source TEXT, last_seen TEXT)'''); c.commit(); c.close()
init()

@app.post('/api/checkin')
def checkin():
    if request.headers.get('X-Device-Token') != TOKEN: return jsonify(error='unauthorized'),401
    d=request.get_json(force=True); aid=d.get('asset_id')
    if not aid: return jsonify(error='asset_id required'),400
    now=datetime.now(timezone.utc).isoformat()
    c=db(); c.execute('''INSERT INTO devices(asset_id,hostname,assigned_user,windows_user,local_ip,public_ip,latitude,longitude,location_source,last_seen)
    VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(asset_id) DO UPDATE SET hostname=excluded.hostname,assigned_user=excluded.assigned_user,windows_user=excluded.windows_user,local_ip=excluded.local_ip,public_ip=excluded.public_ip,latitude=excluded.latitude,longitude=excluded.longitude,location_source=excluded.location_source,last_seen=excluded.last_seen''',
    (aid,d.get('hostname'),d.get('assigned_user'),d.get('windows_user'),d.get('local_ip'),request.headers.get('X-Forwarded-For',request.remote_addr),d.get('latitude'),d.get('longitude'),d.get('location_source'),now)); c.commit(); c.close()
    return jsonify(ok=True,last_seen=now)

@app.get('/api/devices')
def devices():
    if request.headers.get('X-Admin-Key') != ADMIN: return jsonify(error='unauthorized'),401
    c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM devices ORDER BY last_seen DESC')]; c.close(); return jsonify(rows)

@app.get('/')
def dashboard():
    if request.args.get('key') != ADMIN: return 'Unauthorized',401
    c=db(); rows=[dict(r) for r in c.execute('SELECT * FROM devices ORDER BY last_seen DESC')]; c.close()
    return render_template_string('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>LM Asset Tracker</title>
<style>body{font-family:Arial;margin:30px;background:#f4f6f8;color:#17202a}.card{background:white;padding:22px;border-radius:14px;box-shadow:0 2px 12px #0001}table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid #eee;text-align:left}th{background:#fafafa}.on{color:#087f23;font-weight:bold}a{color:#1261a0}</style>
<div class=card><h2>LM Asset Tracker V1</h2><p>Corporate device inventory & last-location dashboard</p><table><tr><th>Asset</th><th>Hostname</th><th>User</th><th>Local IP</th><th>Public IP</th><th>Last seen (UTC)</th><th>Location</th></tr>
{% for r in rows %}<tr><td>{{r.asset_id}}</td><td>{{r.hostname}}</td><td>{{r.assigned_user or r.windows_user}}</td><td>{{r.local_ip}}</td><td>{{r.public_ip}}</td><td class=on>{{r.last_seen}}</td><td>{% if r.latitude is not none %}<a target=_blank href="https://www.openstreetmap.org/?mlat={{r.latitude}}&mlon={{r.longitude}}#map=16/{{r.latitude}}/{{r.longitude}}">View map</a> ({{r.location_source}}){% else %}Unavailable{% endif %}</td></tr>{% endfor %}</table></div>''',rows=rows)

if __name__=='__main__': app.run(host='0.0.0.0',port=8080)
