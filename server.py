#!/usr/bin/env python3
"""
PESA CHAPCHAP - Production Server (Render.com)
- Reads PORT from environment (Render sets this automatically)
- Africa's Talking real SMS OTP
- Admin panel: /admin
- No ngrok needed — Render provides the public URL
"""

import http.server
import socketserver
import json
import urllib.request
import urllib.parse
import threading
import time
import os
import re
import string
import random
import hashlib
from datetime import datetime

# ══════════════════════════════════════════
#  RENDER.COM: reads PORT from environment
#  Render sets PORT automatically — do NOT hardcode
# ══════════════════════════════════════════
PORT = int(os.environ.get("PORT", 8080))

# ══════════════════════════════════════════
#  AFRICA'S TALKING — set via Render env vars
#  In Render dashboard: Settings → Environment
# ══════════════════════════════════════════
AT_USERNAME  = os.environ.get("AT_USERNAME",  "pesachapchap")
AT_API_KEY   = os.environ.get("AT_API_KEY",   "")
AT_SENDER_ID = os.environ.get("AT_SENDER_ID", "PESACHAP")
AT_API_URL   = "https://api.africastalking.com/version1/messaging"

# ══════════════════════════════════════════
#  ADMIN — set via Render env vars
# ══════════════════════════════════════════
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "PesaAdmin@2026")
ADMIN_PATH     = "/admin"

# ══════════════════════════════════════════
#  IN-MEMORY STORES (thread-safe)
# ══════════════════════════════════════════
otp_store      = {}
admin_sessions = {}
player_store   = {}
store_lock     = threading.Lock()
admin_lock     = threading.Lock()
player_lock    = threading.Lock()

game_state = {
    "current_multiplier": 1.00,
    "game_status":        "waiting",
    "last_crash":         None,
    "next_crash":         None,
    "round_number":       1,
    "updated_at":         time.time(),
}
game_lock = threading.Lock()

# Rate limits
MAX_OTP_PER_PHONE   = 3
RATE_WINDOW_MINS    = 10
OTP_EXPIRY_SECS     = 300
MAX_VERIFY_ATTEMPTS = 5
GLOBAL_COOLDOWN     = 30


# ══════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def generate_token():
    return hashlib.sha256(f"{time.time()}{random.random()}".encode()).hexdigest()[:32]

def send_sms_at(phone, message):
    """Send SMS via Africa's Talking production API."""
    if not AT_API_KEY:
        print("[AT] No API key set — SMS not sent")
        return False, "AT_API_KEY not configured"

    # Normalise to international format
    if phone.startswith('07') or phone.startswith('01'):
        phone = '+254' + phone[1:]
    elif phone.startswith('254') and not phone.startswith('+'):
        phone = '+' + phone
    elif not phone.startswith('+'):
        phone = '+254' + phone

    params = urllib.parse.urlencode({
        'username': AT_USERNAME,
        'to':       phone,
        'message':  message,
        'from':     AT_SENDER_ID,
    }).encode('utf-8')

    headers = {
        'apiKey':       AT_API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept':       'application/json',
    }

    req = urllib.request.Request(AT_API_URL, data=params, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode('utf-8')
            data = json.loads(body)
            recs = data.get('SMSMessageData', {}).get('Recipients', [])
            if recs and recs[0].get('statusCode') == 101:
                return True, 'sent'
            return False, body
    except Exception as e:
        return False, str(e)

def cleanup_expired():
    now = time.time()
    with store_lock:
        for k in [k for k, v in otp_store.items() if v.get('expires', 0) < now - 3600]:
            del otp_store[k]
    with admin_lock:
        for k in [k for k, v in admin_sessions.items() if v < now]:
            del admin_sessions[k]

def valid_admin_token(token):
    if not token:
        return False
    with admin_lock:
        exp = admin_sessions.get(token)
        return bool(exp and exp > time.time())


# ══════════════════════════════════════════
#  ADMIN HTML
# ══════════════════════════════════════════
def render_admin_login():
    return """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin – PESACHAPCHAP</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0d0d1a;color:#e0e0ff;font-family:'Segoe UI',sans-serif;
     display:flex;align-items:center;justify-content:center;min-height:100vh;}
.card{background:#1a1a35;border:1px solid #2a2a50;border-radius:16px;padding:32px;width:100%;max-width:380px;}
h1{font-family:monospace;font-size:20px;color:#e53935;margin-bottom:6px;text-align:center;}
.sub{font-size:11px;color:#5a5a90;text-align:center;margin-bottom:24px;letter-spacing:2px;}
label{font-size:11px;color:#5a5a90;display:block;margin-bottom:5px;text-transform:uppercase;}
input{width:100%;background:#141428;border:1px solid #2a2a50;border-radius:8px;color:#fff;
      font-size:15px;padding:11px;outline:none;margin-bottom:14px;}
input:focus{border-color:#e53935;}
button{width:100%;padding:13px;border:none;border-radius:10px;
       background:linear-gradient(135deg,#e53935,#b71c1c);color:#fff;
       font-size:14px;font-weight:700;cursor:pointer;}
.err{color:#e53935;font-size:12px;text-align:center;margin-top:8px;}
</style></head><body>
<div class="card">
  <h1>✈ ADMIN PANEL</h1>
  <div class="sub">PESACHAPCHAP.COM</div>
  <label>Admin Password</label>
  <input type="password" id="pw" placeholder="Enter admin password"
         onkeydown="if(event.key==='Enter')login()">
  <button onclick="login()">🔓 LOGIN</button>
  <div class="err" id="err"></div>
</div>
<script>
async function login(){
  const pw=document.getElementById('pw').value.trim();
  if(!pw){document.getElementById('err').textContent='Enter password.';return;}
  const res=await fetch('/api/admin/login',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({password:pw})
  });
  const data=await res.json();
  if(res.ok){localStorage.setItem('adminToken',data.token);location.href='/admin/dashboard';}
  else document.getElementById('err').textContent=data.error||'Invalid password.';
}
</script></body></html>"""


def render_admin_dashboard(players, game):
    total   = len(players)
    w_bal   = sum(1 for p in players.values() if p.get('balance',0)>0)
    t_bal   = sum(p.get('balance',0)   for p in players.values())
    t_wag   = sum(p.get('totalWagered',0) for p in players.values())
    t_won   = sum(p.get('totalWon',0)  for p in players.values())
    h_prof  = t_wag - t_won
    rnd     = game.get('round_number',1)
    status  = game.get('game_status','unknown')
    mult    = game.get('current_multiplier',1.00)
    lcrash  = game.get('last_crash')
    ncrash  = game.get('next_crash')

    sc = {'flying':'#00e676','crashed':'#e53935','waiting':'#5a5a90'}.get(status,'#5a5a90')

    if ncrash:
        if ncrash<1.5:   nc,nt = '#e53935',f'{ncrash:.2f}x — CRASH INCOMING!'
        elif ncrash<3:   nc,nt = '#ff9800',f'{ncrash:.2f}x — Low'
        elif ncrash<10:  nc,nt = '#ffd600',f'{ncrash:.2f}x — Medium'
        else:            nc,nt = '#00e676',f'{ncrash:.2f}x — HIGH MULTIPLIER!'
    else:
        nc,nt = '#5a5a90','Waiting for next round...'

    rows = ""
    for p in sorted(players.values(), key=lambda x: x.get('balance',0), reverse=True)[:300]:
        nm  = p.get('name','—')
        ph  = p.get('phone','—')
        bal = p.get('balance',0)
        w   = p.get('wins',0)
        l   = p.get('losses',0)
        net = p.get('netProfit',0)
        bx  = p.get('bestX',0)
        rnds= p.get('rounds',0)
        snc = p.get('since','—')
        ls  = p.get('last_seen','—')
        bc  = '#00e676' if bal>0 else '#5a5a90'
        nc2 = '#00e676' if net>=0 else '#e53935'
        rows += f"""<tr>
          <td>{nm}</td>
          <td style="color:#888;font-size:11px;">{ph}</td>
          <td style="color:{bc};font-weight:700;">{bal:.2f}</td>
          <td style="color:#00e676;">{w}</td>
          <td style="color:#e53935;">{l}</td>
          <td style="color:{nc2};font-weight:700;">{'+' if net>=0 else ''}{net:.2f}</td>
          <td style="color:#ffd600;">{bx:.2f}x</td>
          <td style="color:#40c4ff;">{rnds}</td>
          <td style="color:#5a5a90;font-size:10px;">{snc}</td>
          <td style="color:#5a5a90;font-size:10px;">{ls}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="10" style="text-align:center;color:#5a5a90;padding:24px;">No players yet — share your link!</td></tr>'

    hp_color = '#00e676' if h_prof>=0 else '#e53935'

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin Dashboard – PESACHAPCHAP</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#0d0d1a;color:#e0e0ff;font-family:'Segoe UI',sans-serif;font-size:14px;}}
.hdr{{background:#08081a;padding:12px 20px;border-bottom:1px solid #2a2a50;
       display:flex;align-items:center;justify-content:space-between;
       position:sticky;top:0;z-index:20;}}
.hdr h1{{font-family:monospace;font-size:15px;color:#e53935;}}
.hdr-right{{display:flex;gap:8px;align-items:center;}}
.ts{{font-size:11px;color:#5a5a90;}}
.btn{{padding:6px 14px;border:none;border-radius:7px;cursor:pointer;font-size:11px;font-weight:700;}}
.btn-ref{{background:#7c4dff;color:#fff;}}
.btn-out{{background:#2a2a50;color:#aaa;}}
.btn-out:hover{{background:#e53935;color:#fff;}}
.wrap{{padding:16px;max-width:1300px;margin:0 auto;}}
/* STAT CARDS */
.sgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:18px;}}
.sc{{background:#1a1a35;border:1px solid #2a2a50;border-radius:11px;padding:14px;text-align:center;}}
.sv{{font-family:monospace;font-size:20px;font-weight:700;}}
.sl{{font-size:9px;color:#5a5a90;margin-top:3px;text-transform:uppercase;letter-spacing:1px;}}
/* SECTIONS */
.sec{{background:#1a1a35;border:1px solid #2a2a50;border-radius:12px;padding:16px;margin-bottom:16px;}}
.sec h2{{font-family:monospace;font-size:12px;color:#7c4dff;margin-bottom:12px;letter-spacing:1px;text-transform:uppercase;}}
.lgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;}}
.li{{background:#141428;border-radius:8px;padding:10px 14px;}}
.ll{{font-size:9px;color:#5a5a90;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;}}
.lv{{font-family:monospace;font-size:18px;font-weight:700;}}
/* NEXT ODDS BOX */
.odds-box{{background:#0a0a1e;border:2px solid {nc};border-radius:12px;
           padding:18px;text-align:center;margin-top:12px;}}
.odds-lbl{{font-size:10px;color:#5a5a90;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;}}
.odds-val{{font-family:monospace;font-size:32px;font-weight:900;color:{nc};}}
.odds-sub{{font-size:11px;color:{nc};margin-top:6px;opacity:.8;}}
/* TABLE */
.tbl-wrap{{overflow:auto;max-height:480px;border-radius:8px;}}
table{{width:100%;border-collapse:collapse;font-size:12px;min-width:900px;}}
th{{font-size:9px;color:#5a5a90;text-align:left;padding:7px 9px;
    border-bottom:1px solid #2a2a50;letter-spacing:.5px;text-transform:uppercase;
    background:#1a1a35;position:sticky;top:0;}}
td{{padding:7px 9px;border-bottom:1px solid rgba(42,42,80,.45);vertical-align:middle;}}
tr:hover td{{background:rgba(124,77,255,.06);}}
.search{{width:100%;background:#141428;border:1px solid #2a2a50;border-radius:8px;
          color:#fff;font-size:13px;padding:9px 12px;outline:none;margin-bottom:10px;}}
.search:focus{{border-color:#7c4dff;}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;}}
.b-fly{{background:rgba(0,230,118,.2);color:#00e676;animation:bl .8s infinite alternate;}}
.b-wait{{background:rgba(90,90,144,.2);color:#5a5a90;}}
.b-crash{{background:rgba(229,57,53,.15);color:#ff8a80;}}
@keyframes bl{{from{{opacity:1;}}to{{opacity:.4;}}}}
</style></head>
<body>
<div class="hdr">
  <h1>✈ PESACHAPCHAP — ADMIN</h1>
  <div class="hdr-right">
    <span class="ts" id="ts">Auto-refreshing...</span>
    <button class="btn btn-ref" onclick="refresh()">⟳ Refresh</button>
    <button class="btn btn-out" onclick="logout()">Logout</button>
  </div>
</div>

<div class="wrap">
  <!-- SUMMARY -->
  <div class="sgrid">
    <div class="sc"><div class="sv" style="color:#00e676;">{total}</div><div class="sl">Players</div></div>
    <div class="sc"><div class="sv" style="color:#40c4ff;">{w_bal}</div><div class="sl">With Balance</div></div>
    <div class="sc"><div class="sv" style="color:#ffd600;">{t_bal:.0f}</div><div class="sl">KES in Wallets</div></div>
    <div class="sc"><div class="sv" style="color:#00e676;">{t_wag:.0f}</div><div class="sl">Total Wagered</div></div>
    <div class="sc"><div class="sv" style="color:{hp_color};">{h_prof:.0f}</div><div class="sl">House Profit</div></div>
    <div class="sc"><div class="sv" style="color:#7c4dff;">{rnd}</div><div class="sl">Round No.</div></div>
  </div>

  <!-- LIVE STATUS -->
  <div class="sec">
    <h2>🔴 Live Game Status</h2>
    <div class="lgrid">
      <div class="li">
        <div class="ll">Status</div>
        <div class="lv" style="color:{sc};" id="dStatus">
          {status.upper()}
          <span class="badge {'b-fly' if status=='flying' else 'b-crash' if status=='crashed' else 'b-wait'}">{status}</span>
        </div>
      </div>
      <div class="li">
        <div class="ll">Current Multiplier</div>
        <div class="lv" style="color:#00e676;" id="dMult">{mult:.2f}x</div>
      </div>
      <div class="li">
        <div class="ll">Round</div>
        <div class="lv" style="color:#7c4dff;" id="dRound">#{rnd}</div>
      </div>
      <div class="li">
        <div class="ll">Last Crash</div>
        <div class="lv" style="color:#e53935;" id="dLast">{f"{lcrash:.2f}x" if lcrash else "—"}</div>
      </div>
    </div>

    <!-- NEXT ODDS -->
    <div class="odds-box" id="oddsBox">
      <div class="odds-lbl">⚡ NEXT ROUND CRASH POINT — ADMIN ONLY</div>
      <div class="odds-val" id="oddsVal">{nt}</div>
      <div class="odds-sub" id="oddsSub">Pre-generated before round starts</div>
    </div>
  </div>

  <!-- PLAYERS -->
  <div class="sec">
    <h2>👥 All Registered Players ({total})</h2>
    <input class="search" placeholder="🔍 Search by name or phone..."
           oninput="filterPlayers(this.value)">
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Name</th><th>Phone</th><th>Balance KES</th>
          <th>Wins</th><th>Losses</th><th>Net KES</th>
          <th>Best X</th><th>Rounds</th><th>Since</th><th>Last Seen</th>
        </tr></thead>
        <tbody id="pTbody">{rows}</tbody>
      </table>
    </div>
  </div>
</div>

<script>
const tok=localStorage.getItem('adminToken');
if(!tok)location.href='/admin';

function logout(){{localStorage.removeItem('adminToken');location.href='/admin';}}

function filterPlayers(q){{
  document.querySelectorAll('#pTbody tr').forEach(r=>{{
    r.style.display=r.textContent.toLowerCase().includes(q.toLowerCase())?'':'none';
  }});
}}

async function refresh(){{
  try{{
    const r=await fetch('/api/admin/data',{{headers:{{'X-Admin-Token':tok}}}});
    if(r.status===401){{logout();return;}}
    const d=await r.json();
    const g=d.game;
    // Update live fields
    document.getElementById('dMult').textContent=g.current_multiplier.toFixed(2)+'x';
    document.getElementById('dRound').textContent='#'+g.round_number;
    document.getElementById('dStatus').innerHTML=g.game_status.toUpperCase()+' <span class="badge '+(g.game_status==='flying'?'b-fly':g.game_status==='crashed'?'b-crash':'b-wait')+'">'+g.game_status+'</span>';
    if(g.last_crash)document.getElementById('dLast').textContent=g.last_crash.toFixed(2)+'x';
    // Next odds
    if(g.next_crash){{
      const nc=g.next_crash;let col='#5a5a90',txt=nc.toFixed(2)+'x';
      if(nc<1.5){{col='#e53935';txt=nc.toFixed(2)+'x — CRASH INCOMING!';}}
      else if(nc<3){{col='#ff9800';txt=nc.toFixed(2)+'x — Low';}}
      else if(nc<10){{col='#ffd600';txt=nc.toFixed(2)+'x — Medium';}}
      else{{col='#00e676';txt=nc.toFixed(2)+'x — HIGH MULTIPLIER!';}}
      const ov=document.getElementById('oddsVal');
      ov.textContent=txt;ov.style.color=col;
      document.getElementById('oddsBox').style.borderColor=col;
    }}
    document.getElementById('ts').textContent='Updated '+new Date().toLocaleTimeString();
  }}catch(e){{console.error(e);}}
}}

// Auto-refresh every 2s
setInterval(refresh,2000);
</script>
</body></html>"""


# ══════════════════════════════════════════
#  HTTP HANDLER
# ══════════════════════════════════════════
class Handler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Only log errors
        if args and str(args[1]) not in ('200','304'):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]}")

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]

        if path in ('/admin', '/admin/'):
            return self._html(render_admin_login())

        if path == '/admin/dashboard':
            # Token passed as query param or header
            token = self._get_token()
            if not valid_admin_token(token):
                return self._html('<script>location.href="/admin"</script>')
            with player_lock: p = dict(player_store)
            with game_lock:   g = dict(game_state)
            return self._html(render_admin_dashboard(p, g))

        # Static files
        if path == '/':
            self.path = '/index.html'
        http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        length  = int(self.headers.get('Content-Length', 0))
        raw     = self.rfile.read(length).decode('utf-8')
        try:    payload = json.loads(raw) if raw else {}
        except: payload = {}
        path = self.path.split('?')[0]

        routes = {
            '/api/send-otp':       self.h_send_otp,
            '/api/verify-otp':     self.h_verify_otp,
            '/api/admin/login':    self.h_admin_login,
            '/api/admin/data':     self.h_admin_data,
            '/api/game/sync':      self.h_game_sync,
            '/api/player/sync':    self.h_player_sync,
        }
        handler = routes.get(path)
        if handler:
            handler(payload)
        else:
            self.json_resp(404, {'error': 'Not found'})

    # ─── OTP ───
    def h_send_otp(self, p):
        phone = str(p.get('phone','')).strip()
        if not re.match(r'^(07|01)\d{8}$', phone):
            return self.json_resp(400, {'error': 'Invalid Safaricom number.'})
        cleanup_expired()
        now = time.time()
        with store_lock:
            rec = otp_store.get(phone)
            if rec:
                wait = GLOBAL_COOLDOWN - (now - rec.get('last_sent',0))
                if wait > 0:
                    return self.json_resp(429, {'error': f'Wait {int(wait)}s before requesting again.'})
                w_start = now - RATE_WINDOW_MINS*60
                if len([t for t in rec.get('sent_times',[]) if t>w_start]) >= MAX_OTP_PER_PHONE:
                    return self.json_resp(429, {'error': f'Too many requests. Try in {RATE_WINDOW_MINS} mins.'})
            otp = generate_otp()
            rec = otp_store.get(phone, {'sent_times':[],'attempts':0})
            rec.update({'otp':otp,'expires':now+OTP_EXPIRY_SECS,'last_sent':now,'attempts':0})
            st = [t for t in rec.get('sent_times',[]) if t>now-RATE_WINDOW_MINS*60]
            st.append(now); rec['sent_times']=st
            otp_store[phone]=rec

        msg = f"Karibu PESA CHAPCHAP!\nYour code: {otp}\nValid 5 mins. Do NOT share.\nPESACHAPCHAP.COM"
        ok, info = send_sms_at(phone, msg)
        if ok:
            print(f"[OTP] Sent to {phone[:4]}****{phone[-2:]}")
            self.json_resp(200, {'message': 'OTP sent.'})
        else:
            with store_lock:
                otp_store.pop(phone, None)
            print(f"[OTP ERROR] {phone}: {info}")
            self.json_resp(500, {'error': 'SMS failed. Check AT credentials in Render env vars.'})

    def h_verify_otp(self, p):
        phone   = str(p.get('phone','')).strip()
        entered = str(p.get('otp','')).strip()
        if not re.match(r'^(07|01)\d{8}$', phone):
            return self.json_resp(400, {'error': 'Invalid phone.'})
        if not re.match(r'^\d{6}$', entered):
            return self.json_resp(400, {'error': 'OTP must be 6 digits.'})
        now = time.time()
        with store_lock:
            rec = otp_store.get(phone)
            if not rec:
                return self.json_resp(400, {'error': 'No OTP for this number. Request a new one.'})
            if now > rec.get('expires',0):
                otp_store.pop(phone,None)
                return self.json_resp(400, {'error': 'OTP expired. Request a new one.'})
            if rec.get('attempts',0) >= MAX_VERIFY_ATTEMPTS:
                otp_store.pop(phone,None)
                return self.json_resp(429, {'error': 'Too many wrong attempts. Request new OTP.'})
            if entered != rec['otp']:
                rec['attempts'] = rec.get('attempts',0)+1
                left = MAX_VERIFY_ATTEMPTS - rec['attempts']
                return self.json_resp(400, {'error': f'Wrong OTP. {left} attempt{"s" if left!=1 else ""} left.'})
            otp_store.pop(phone,None)
        print(f"[VERIFY] {phone[:4]}****{phone[-2:]} verified")
        self.json_resp(200, {'message': 'Verified successfully.'})

    # ─── ADMIN ───
    def h_admin_login(self, p):
        if p.get('password') == ADMIN_PASSWORD:
            tok = generate_token()
            with admin_lock:
                admin_sessions[tok] = time.time() + 86400
            print(f"[ADMIN] Login from {self.client_address[0]}")
            self.json_resp(200, {'token': tok})
        else:
            self.json_resp(401, {'error': 'Invalid password.'})

    def h_admin_data(self, _p):
        if not valid_admin_token(self._get_token()):
            return self.json_resp(401, {'error': 'Unauthorized'})
        with player_lock: players = dict(player_store)
        with game_lock:   game    = dict(game_state)
        self.json_resp(200, {
            'game':    game,
            'summary': {
                'total_players':   len(players),
                'total_balance':   sum(p.get('balance',0)    for p in players.values()),
                'total_wagered':   sum(p.get('totalWagered',0) for p in players.values()),
                'house_profit':    sum(p.get('totalWagered',0) - p.get('totalWon',0) for p in players.values()),
            },
        })

    # ─── GAME SYNC ───
    def h_game_sync(self, p):
        with game_lock:
            game_state.update({
                'current_multiplier': float(p.get('multiplier', 1.00)),
                'game_status':        str(p.get('status', 'waiting')),
                'round_number':       int(p.get('round', 1)),
                'updated_at':         time.time(),
            })
            if p.get('last_crash') is not None:
                game_state['last_crash'] = float(p['last_crash'])
            if p.get('next_crash') is not None:
                game_state['next_crash'] = float(p['next_crash'])
        self.json_resp(200, {'ok': True})

    # ─── PLAYER SYNC ───
    def h_player_sync(self, p):
        phone = str(p.get('phone','')).strip()
        if not phone:
            return self.json_resp(400, {'error': 'Phone required'})
        with player_lock:
            player_store[phone] = {
                'name':          p.get('name','—'),
                'phone':         phone,
                'balance':       float(p.get('balance',0)),
                'wins':          int(p.get('wins',0)),
                'losses':        int(p.get('losses',0)),
                'netProfit':     float(p.get('netProfit',0)),
                'bestX':         float(p.get('bestX',0)),
                'rounds':        int(p.get('rounds',0)),
                'since':         p.get('since','—'),
                'totalWagered':  float(p.get('totalWagered',0)),
                'totalWon':      float(p.get('totalWon',0)),
                'last_seen':     datetime.now().strftime('%d/%m %H:%M'),
            }
        self.json_resp(200, {'ok': True})

    # ─── HELPERS ───
    def _get_token(self):
        t = self.headers.get('X-Admin-Token')
        if t: return t
        if '?' in self.path:
            for part in self.path.split('?',1)[1].split('&'):
                if part.startswith('token='):
                    return part[6:]
        return None

    def _html(self, html):
        body = html.encode('utf-8')
        self.send_response(200); self._cors()
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,X-Admin-Token')

    def json_resp(self, code, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code); self._cors()
        self.send_header('Content-Type',   'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)


# ══════════════════════════════════════════
#  MAIN — Render.com compatible
# ══════════════════════════════════════════
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print(f"""
╔══════════════════════════════════════════╗
║   ✈  PESA CHAPCHAP SERVER               ║
╠══════════════════════════════════════════╣
║  Port   : {PORT:<31}║
║  AT User: {AT_USERNAME:<31}║
║  Sender : {AT_SENDER_ID:<31}║
║  AT Key : {'SET ✅' if AT_API_KEY else 'NOT SET ⚠️  — add to Render env vars':<31}║
╚══════════════════════════════════════════╝
""")

    # Render.com requires binding to 0.0.0.0
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"🚀 Listening on 0.0.0.0:{PORT}")
        print(f"🔐 Admin: <your-render-url>/admin\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
