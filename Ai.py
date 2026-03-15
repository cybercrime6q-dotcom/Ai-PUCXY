import os, json, time, base64, uuid, urllib.request, urllib.error
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL   = "claude-haiku-4-5-20251001"
HISTORY_FILE = "chat_history.json"

# =============================================
# PERSONAS
# =============================================
PERSONAS = {
    "default":   {"name": "Asisten AI",     "emoji": "ðŸ¤–", "system": "Kamu adalah asisten AI yang ramah, cerdas, dan membantu. Jawab dalam Bahasa Indonesia yang natural."},
    "guru":      {"name": "Guru",            "emoji": "ðŸ‘¨â€ðŸ«", "system": "Kamu adalah guru yang sabar dan pandai menjelaskan hal kompleks dengan cara sederhana. Gunakan analogi dan contoh nyata."},
    "programmer":{"name": "Senior Dev",      "emoji": "ðŸ’»", "system": "Kamu adalah senior software engineer berpengalaman. Jawab pertanyaan teknis dengan tepat, berikan contoh kode jika perlu."},
    "kreatif":   {"name": "Penulis Kreatif", "emoji": "âœï¸", "system": "Kamu adalah penulis kreatif yang imajinatif. Bantu menulis cerita, puisi, ide, dan konten kreatif lainnya."},
    "santai":    {"name": "Teman Ngobrol",   "emoji": "ðŸ˜Ž", "system": "Kamu adalah teman ngobrol yang asyik, santai, dan menggunakan bahasa gaul Indonesia. Jangan terlalu formal."},
}

# =============================================
# HISTORY
# =============================================
def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return []

def save_history(sessions):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    except: pass

# =============================================
# CLAUDE API
# =============================================
def call_claude(messages, system, image_b64=None, image_type=None):
    if not API_KEY:
        return None, "ANTHROPIC_API_KEY belum diset"

    # Build messages - add image to last user message if provided
    msgs = []
    for i, m in enumerate(messages):
        if i == len(messages) - 1 and image_b64 and m["role"] == "user":
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": image_type or "image/jpeg", "data": image_b64}},
                {"type": "text", "text": m["content"]}
            ]
            msgs.append({"role": "user", "content": content})
        else:
            msgs.append({"role": m["role"], "content": m["content"]})

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 1500,
        "system": system,
        "messages": msgs
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": API_KEY},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode("utf-8"))
            return result["content"][0]["text"], None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode())
        return None, f"API Error {e.code}: {err.get('error',{}).get('message','Unknown')}"
    except Exception as e:
        return None, str(e)

# =============================================
# HTML
# =============================================
HTML = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Python AI Chat</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
:root{
  --bg:#0a0a0f;--panel:#12121a;--card:#1a1a26;--border:#2a2a3d;
  --accent:#7c5cfc;--accent2:#fc5c7d;--tx:#e8e8f0;--muted:#6b6b8a;
  --user-bg:linear-gradient(135deg,#7c5cfc,#fc5c7d);
  --ai-bg:#1a1a26;--radius:16px;
}
body{font-family:'Syne',sans-serif;background:var(--bg);color:var(--tx);height:100vh;display:flex;flex-direction:column;overflow:hidden;}

/* HEADER */
.header{padding:14px 20px;background:var(--panel);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;flex-shrink:0;}
.logo{font-size:22px;font-weight:800;background:linear-gradient(135deg,#7c5cfc,#fc5c7d);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.persona-select{margin-left:auto;background:var(--card);border:1px solid var(--border);color:var(--tx);font-family:'Syne',sans-serif;font-size:13px;padding:6px 10px;border-radius:8px;cursor:pointer;outline:none;}
.persona-select:focus{border-color:var(--accent);}
.history-btn{background:var(--card);border:1px solid var(--border);color:var(--muted);font-size:12px;padding:6px 12px;border-radius:8px;cursor:pointer;transition:.2s;}
.history-btn:hover{color:var(--tx);border-color:var(--accent);}

/* MAIN */
.main{display:flex;flex:1;overflow:hidden;}

/* SIDEBAR */
.sidebar{width:240px;background:var(--panel);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;}
.sidebar-header{padding:14px 16px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border);}
.sessions{flex:1;overflow-y:auto;padding:8px;}
.session-item{padding:10px 12px;border-radius:10px;cursor:pointer;margin-bottom:4px;transition:.15s;border:1px solid transparent;}
.session-item:hover{background:var(--card);border-color:var(--border);}
.session-item.active{background:var(--card);border-color:var(--accent);}
.session-title{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.session-meta{font-size:11px;color:var(--muted);margin-top:2px;}
.new-chat-btn{margin:10px;padding:10px;background:linear-gradient(135deg,#7c5cfc22,#fc5c7d22);border:1px solid var(--accent);color:var(--accent);border-radius:10px;cursor:pointer;font-family:'Syne',sans-serif;font-weight:700;font-size:13px;transition:.2s;}
.new-chat-btn:hover{background:linear-gradient(135deg,#7c5cfc44,#fc5c7d44);}

/* CHAT */
.chat-area{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.messages{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:16px;}
.messages::-webkit-scrollbar{width:4px;}
.messages::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}

/* BUBBLES */
.msg{display:flex;gap:10px;max-width:80%;animation:fadeUp .3s ease;}
.msg.user{align-self:flex-end;flex-direction:row-reverse;}
.msg.ai{align-self:flex-start;}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
.avatar{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;margin-top:2px;}
.avatar.user-av{background:var(--user-bg);}
.avatar.ai-av{background:var(--card);border:1px solid var(--border);}
.bubble{padding:12px 16px;border-radius:var(--radius);line-height:1.6;font-size:14px;white-space:pre-wrap;word-break:break-word;}
.msg.user .bubble{background:var(--user-bg);color:#fff;border-bottom-right-radius:4px;}
.msg.ai .bubble{background:var(--ai-bg);border:1px solid var(--border);border-bottom-left-radius:4px;}
.bubble img{max-width:100%;border-radius:8px;margin-bottom:6px;display:block;}
.bubble code{background:#0a0a14;padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:12px;color:#a78bfa;}
.bubble pre{background:#0a0a14;padding:12px;border-radius:8px;overflow-x:auto;margin:8px 0;}
.bubble pre code{background:none;padding:0;color:#e8e8f0;}
.msg-time{font-size:10px;color:var(--muted);margin-top:4px;text-align:right;}
.msg.ai .msg-time{text-align:left;}

/* TYPING */
.typing-bubble{background:var(--ai-bg);border:1px solid var(--border);padding:12px 16px;border-radius:var(--radius);border-bottom-left-radius:4px;display:flex;gap:5px;align-items:center;}
.dot{width:7px;height:7px;background:var(--muted);border-radius:50%;animation:bounce .8s infinite;}
.dot:nth-child(2){animation-delay:.15s;}
.dot:nth-child(3){animation-delay:.3s;}
@keyframes bounce{0%,80%,100%{transform:translateY(0);}40%{transform:translateY(-6px);}}

/* IMAGE PREVIEW */
.img-preview{padding:8px 20px;background:var(--panel);border-top:1px solid var(--border);display:none;align-items:center;gap:10px;}
.img-preview.show{display:flex;}
.img-preview img{height:60px;border-radius:8px;object-fit:cover;}
.img-preview-name{font-size:12px;color:var(--muted);flex:1;}
.img-remove{background:none;border:none;color:var(--muted);cursor:pointer;font-size:18px;padding:4px;}
.img-remove:hover{color:#fc5c7d;}

/* INPUT */
.input-area{padding:16px 20px;background:var(--panel);border-top:1px solid var(--border);flex-shrink:0;}
.input-row{display:flex;gap:10px;align-items:flex-end;}
.input-wrap{flex:1;background:var(--card);border:1px solid var(--border);border-radius:14px;display:flex;align-items:flex-end;padding:4px 4px 4px 12px;transition:.2s;gap:4px;}
.input-wrap:focus-within{border-color:var(--accent);}
textarea{flex:1;background:none;border:none;color:var(--tx);font-family:'Syne',sans-serif;font-size:14px;resize:none;outline:none;padding:8px 0;max-height:120px;line-height:1.5;}
textarea::placeholder{color:var(--muted);}
.img-btn{width:36px;height:36px;background:none;border:none;color:var(--muted);cursor:pointer;border-radius:8px;font-size:18px;display:flex;align-items:center;justify-content:center;transition:.2s;flex-shrink:0;}
.img-btn:hover{color:var(--accent);background:var(--accent)22;}
.send-btn{width:44px;height:44px;border-radius:12px;border:none;background:linear-gradient(135deg,#7c5cfc,#fc5c7d);color:#fff;cursor:pointer;font-size:20px;display:flex;align-items:center;justify-content:center;transition:.2s;flex-shrink:0;}
.send-btn:hover{transform:scale(1.05);}
.send-btn:disabled{opacity:.4;transform:none;cursor:not-allowed;}
#file-input{display:none;}

/* EMPTY */
.empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--muted);gap:12px;text-align:center;padding:40px;}
.empty-icon{font-size:52px;opacity:.3;}
.empty h2{font-size:20px;font-weight:800;color:var(--tx);opacity:.4;}
.empty p{font-size:13px;max-width:280px;}

/* HISTORY PANEL */
.hist-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:500;display:none;align-items:center;justify-content:center;}
.hist-overlay.open{display:flex;}
.hist-panel{background:var(--panel);border:1px solid var(--border);border-radius:20px;width:420px;max-height:80vh;display:flex;flex-direction:column;overflow:hidden;}
.hist-head{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.hist-head h3{font-size:16px;font-weight:800;}
.hist-close{background:none;border:none;color:var(--muted);font-size:22px;cursor:pointer;}
.hist-list{overflow-y:auto;padding:12px;}
.hist-item{padding:14px;border-radius:12px;cursor:pointer;border:1px solid var(--border);margin-bottom:8px;transition:.15s;}
.hist-item:hover{border-color:var(--accent);background:var(--card);}
.hist-item-title{font-weight:700;font-size:14px;margin-bottom:4px;}
.hist-item-meta{font-size:12px;color:var(--muted);}
.hist-empty{padding:40px;text-align:center;color:var(--muted);}

@media(max-width:600px){
  .sidebar{display:none;}
  .msg{max-width:95%;}
}
</style>
</head>
<body>

<div class="header">
  <div class="logo">âš¡ AI Chat</div>
  <select class="persona-select" id="persona-sel" onchange="setPersona(this.value)">
    <option value="default">ðŸ¤– Asisten AI</option>
    <option value="guru">ðŸ‘¨â€ðŸ« Guru</option>
    <option value="programmer">ðŸ’» Senior Dev</option>
    <option value="kreatif">âœï¸ Penulis Kreatif</option>
    <option value="santai">ðŸ˜Ž Teman Ngobrol</option>
  </select>
  <button class="history-btn" onclick="openHistory()">ðŸ“‹ Riwayat</button>
</div>

<div class="main">
  <div class="sidebar">
    <div class="sidebar-header">Sesi Chat</div>
    <button class="new-chat-btn" onclick="newChat()">+ Chat Baru</button>
    <div class="sessions" id="session-list"></div>
  </div>

  <div class="chat-area">
    <div class="messages" id="messages">
      <div class="empty" id="empty-state">
        <div class="empty-icon">ðŸ’¬</div>
        <h2>Mulai Ngobrol</h2>
        <p>Ketik pesan, kirim gambar, atau pilih persona AI yang kamu mau</p>
      </div>
    </div>

    <div class="img-preview" id="img-preview">
      <img id="img-thumb" src="">
      <span class="img-preview-name" id="img-name"></span>
      <button class="img-remove" onclick="removeImage()">âœ•</button>
    </div>

    <div class="input-area">
      <div class="input-row">
        <div class="input-wrap">
          <textarea id="msg-input" placeholder="Ketik pesan..." rows="1"
            onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
          <button class="img-btn" onclick="document.getElementById('file-input').click()" title="Kirim Gambar">ðŸ–¼</button>
        </div>
        <button class="send-btn" id="send-btn" onclick="sendMessage()">âž¤</button>
      </div>
      <input type="file" id="file-input" accept="image/*" onchange="onImageSelect(event)">
    </div>
  </div>
</div>

<!-- History Panel -->
<div class="hist-overlay" id="hist-overlay" onclick="if(event.target===this)closeHistory()">
  <div class="hist-panel">
    <div class="hist-head">
      <h3>ðŸ“‹ Riwayat Chat</h3>
      <button class="hist-close" onclick="closeHistory()">Ã—</button>
    </div>
    <div class="hist-list" id="hist-list"></div>
  </div>
</div>

<script>
// =============================================
// STATE
// =============================================
let sessions = [];       // semua sesi dari server
let currentId = null;    // ID sesi aktif
let messages = [];       // pesan sesi aktif
let persona = 'default';
let pendingImage = null; // {b64, type, name}
let sending = false;

const PERSONAS = {
  default:    {name:'Asisten AI',   emoji:'ðŸ¤–'},
  guru:       {name:'Guru',         emoji:'ðŸ‘¨â€ðŸ«'},
  programmer: {name:'Senior Dev',   emoji:'ðŸ’»'},
  kreatif:    {name:'Penulis Kreatif',emoji:'âœï¸'},
  santai:     {name:'Teman Ngobrol',emoji:'ðŸ˜Ž'},
};

// =============================================
// INIT
// =============================================
async function init() {
  await loadSessions();
  if (sessions.length > 0) {
    loadSession(sessions[0].id);
  }
}

// =============================================
// SESSIONS
// =============================================
async function loadSessions() {
  try {
    const r = await fetch('/api/sessions');
    const d = await r.json();
    sessions = d.sessions || [];
    renderSidebar();
  } catch(e) {}
}

function renderSidebar() {
  const el = document.getElementById('session-list');
  if (!sessions.length) {
    el.innerHTML = '<div style="padding:16px;text-align:center;color:var(--muted);font-size:12px;">Belum ada sesi</div>';
    return;
  }
  el.innerHTML = sessions.map(s => `
    <div class="session-item${s.id===currentId?' active':''}" onclick="loadSession('${s.id}')">
      <div class="session-title">${escHtml(s.title||'Chat Baru')}</div>
      <div class="session-meta">${s.count} pesan Â· ${fmtDate(s.updated_at)}</div>
    </div>`).join('');
}

async function newChat() {
  currentId = null;
  messages = [];
  persona = 'default';
  document.getElementById('persona-sel').value = 'default';
  pendingImage = null;
  removeImage();
  renderMessages();
  renderSidebar();
  document.getElementById('msg-input').focus();
}

async function loadSession(id) {
  try {
    const r = await fetch('/api/session/' + id);
    const d = await r.json();
    currentId = id;
    messages = d.messages || [];
    persona = d.persona || 'default';
    document.getElementById('persona-sel').value = persona;
    renderMessages();
    renderSidebar();
  } catch(e) {}
}

// =============================================
// SEND
// =============================================
async function sendMessage() {
  if (sending) return;
  const inp = document.getElementById('msg-input');
  const text = inp.value.trim();
  if (!text && !pendingImage) return;

  sending = true;
  document.getElementById('send-btn').disabled = true;
  inp.value = '';
  autoResize(inp);

  // Add user message to UI
  const userMsg = {role:'user', content: text || '(Gambar)', image: pendingImage ? pendingImage.b64 : null, image_type: pendingImage ? pendingImage.type : null, time: Date.now()};
  messages.push(userMsg);
  renderMessages();
  showTyping();

  try {
    const body = {
      text: text,
      persona: persona,
      session_id: currentId,
      image_b64: pendingImage ? pendingImage.b64 : null,
      image_type: pendingImage ? pendingImage.type : null,
    };
    pendingImage = null;
    removeImage();

    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    hideTyping();

    if (d.ok) {
      currentId = d.session_id;
      messages.push({role:'assistant', content: d.reply, time: Date.now()});
      await loadSessions();
    } else {
      messages.push({role:'assistant', content:'âŒ Error: ' + d.error, time: Date.now()});
    }
  } catch(e) {
    hideTyping();
    messages.push({role:'assistant', content:'âŒ Gagal terhubung ke server', time: Date.now()});
  }

  renderMessages();
  sending = false;
  document.getElementById('send-btn').disabled = false;
  inp.focus();
}

// =============================================
// RENDER
// =============================================
function renderMessages() {
  const area = document.getElementById('messages');
  const empty = document.getElementById('empty-state');

  if (!messages.length) {
    empty.style.display = 'flex';
    area.innerHTML = '';
    area.appendChild(empty);
    return;
  }

  empty.style.display = 'none';
  const p = PERSONAS[persona] || PERSONAS.default;

  area.innerHTML = messages.map(m => {
    const isUser = m.role === 'user';
    const av = isUser ? 'ðŸ‘¤' : p.emoji;
    const avClass = isUser ? 'user-av' : 'ai-av';
    const imgHtml = m.image ? `<img src="data:${m.image_type||'image/jpeg'};base64,${m.image}" alt="gambar">` : '';
    const txt = formatText(m.content || '');
    const t = m.time ? fmtTime(m.time) : '';
    return `<div class="msg ${isUser?'user':'ai'}">
      <div class="avatar ${avClass}">${av}</div>
      <div>
        <div class="bubble">${imgHtml}${txt}</div>
        <div class="msg-time">${t}</div>
      </div>
    </div>`;
  }).join('');

  area.scrollTop = area.scrollHeight;
}

function showTyping() {
  const area = document.getElementById('messages');
  const p = PERSONAS[persona] || PERSONAS.default;
  const div = document.createElement('div');
  div.className = 'msg ai';
  div.id = 'typing-indicator';
  div.innerHTML = `<div class="avatar ai-av">${p.emoji}</div>
    <div class="typing-bubble"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

// =============================================
// IMAGE
// =============================================
function onImageSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    const b64 = ev.target.result.split(',')[1];
    pendingImage = {b64, type: file.type, name: file.name};
    document.getElementById('img-thumb').src = ev.target.result;
    document.getElementById('img-name').textContent = file.name;
    document.getElementById('img-preview').classList.add('show');
  };
  reader.readAsDataURL(file);
  e.target.value = '';
}

function removeImage() {
  pendingImage = null;
  document.getElementById('img-preview').classList.remove('show');
  document.getElementById('img-thumb').src = '';
}

// =============================================
// HISTORY PANEL
// =============================================
function openHistory() {
  const el = document.getElementById('hist-overlay');
  const list = document.getElementById('hist-list');
  el.classList.add('open');
  if (!sessions.length) {
    list.innerHTML = '<div class="hist-empty">Belum ada riwayat chat</div>';
    return;
  }
  list.innerHTML = sessions.map(s => `
    <div class="hist-item" onclick="closeHistory();loadSession('${s.id}')">
      <div class="hist-item-title">${escHtml(s.title||'Chat Baru')}</div>
      <div class="hist-item-meta">${s.count} pesan Â· ${s.persona||'default'} Â· ${fmtDate(s.updated_at)}</div>
    </div>`).join('');
}

function closeHistory() {
  document.getElementById('hist-overlay').classList.remove('open');
}

// =============================================
// PERSONA
// =============================================
function setPersona(p) {
  persona = p;
}

// =============================================
// UTILS
// =============================================
function formatText(text) {
  // code blocks
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  // inline code
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  // bold
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // newlines
  text = text.replace(/\n/g, '<br>');
  return text;
}

function escHtml(t) {
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function fmtTime(ts) {
  const d = new Date(ts);
  return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
}

function fmtDate(ts) {
  if (!ts) return '';
  const d = new Date(ts * 1000);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return fmtTime(ts * 1000);
  return d.getDate() + '/' + (d.getMonth()+1);
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// =============================================
// START
// =============================================
init();
</script>
</body>
</html>"""

# =============================================
# ROUTES
# =============================================
@app.route("/")
def index():
    resp = make_response(HTML)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route("/api/sessions")
def api_sessions():
    sessions = load_history()
    summary = []
    for s in sessions:
        msgs = s.get("messages", [])
        first_user = next((m["content"][:40] for m in msgs if m["role"]=="user"), "Chat Baru")
        summary.append({
            "id": s["id"],
            "title": first_user,
            "count": len(msgs),
            "persona": s.get("persona", "default"),
            "updated_at": s.get("updated_at", 0)
        })
    summary.sort(key=lambda x: x["updated_at"], reverse=True)
    return jsonify({"sessions": summary})

@app.route("/api/session/<sid>")
def api_session(sid):
    sessions = load_history()
    s = next((x for x in sessions if x["id"] == sid), None)
    if not s:
        return jsonify({"messages": [], "persona": "default"})
    return jsonify({"messages": s.get("messages", []), "persona": s.get("persona","default")})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    text       = (data.get("text") or "").strip()
    persona_id = data.get("persona", "default")
    session_id = data.get("session_id")
    image_b64  = data.get("image_b64")
    image_type = data.get("image_type", "image/jpeg")

    if not text and not image_b64:
        return jsonify({"ok": False, "error": "Pesan kosong"})

    p = PERSONAS.get(persona_id, PERSONAS["default"])
    system = p["system"]

    # Load or create session
    sessions = load_history()
    if session_id:
        session = next((s for s in sessions if s["id"] == session_id), None)
    else:
        session = None

    if not session:
        session = {"id": str(uuid.uuid4()), "persona": persona_id, "messages": [], "updated_at": int(time.time())}
        sessions.append(session)

    # Build messages for API (text only in history, image only in current)
    api_messages = []
    for m in session["messages"][-20:]:  # max 20 history
        api_messages.append({"role": m["role"], "content": m.get("content", "")})

    # Add current user message
    user_content = text or "(Gambar terkirim)"
    api_messages.append({"role": "user", "content": user_content})

    # Call Claude
    reply, error = call_claude(api_messages, system, image_b64, image_type)
    if error:
        return jsonify({"ok": False, "error": error})

    # Save to session
    ts = int(time.time() * 1000)
    session["messages"].append({"role": "user", "content": user_content,
                                 "image": image_b64, "image_type": image_type, "time": ts})
    session["messages"].append({"role": "assistant", "content": reply, "time": ts+1})
    session["updated_at"] = int(time.time())
    session["persona"] = persona_id

    save_history(sessions)
    return jsonify({"ok": True, "reply": reply, "session_id": session["id"]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"ðŸš€ AI Chatbot running at http://localhost:{port}")
    if not API_KEY:
        print("âš ï¸  Set ANTHROPIC_API_KEY environment variable!")
    app.run(host="0.0.0.0", port=port, debug=False)