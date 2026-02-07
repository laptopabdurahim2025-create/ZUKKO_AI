import streamlit as st
import io
import random
import time
import json
from openai import OpenAI
import sqlite3
import hashlib
import datetime
import pandas as pd
from gtts import gTTS

# ⚠️ Streamlit Secrets
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("GROQ_API_KEY topilmadi! .streamlit/secrets.toml faylini tekshiring.")
    st.stop()

MODEL_NAME = "llama-3.3-70b-versatile"

st.set_page_config(page_title="Zukko AI", page_icon="⚡", layout="wide")

# ==========================================
# 🗄️ BAZA (BACKEND)
# ==========================================
def init_db():
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()

    # Asosiy users jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')

    # Yangi ustunlarni qo'shish (agar mavjud bo'lmasa)
    existing = [row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()]

    new_columns = [
        ("xp", "INTEGER DEFAULT 0"),
        ("streak", "INTEGER DEFAULT 0"),
        ("last_active", "TEXT DEFAULT ''"),
        ("level", "INTEGER DEFAULT 1"),
        ("badges", "TEXT DEFAULT '[]'"),
        ("total_messages", "INTEGER DEFAULT 0"),
        ("joined", "TEXT DEFAULT ''"),
    ]
    for col_name, col_type in new_columns:
        if col_name not in existing:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")

    # Logs jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (username TEXT, action TEXT, time TEXT)''')

    # Quiz scores jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS quiz_scores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT, subject TEXT, score INTEGER,
                  total INTEGER, time TEXT)''')

    # Notes jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT, title TEXT, content TEXT,
                  subject TEXT, time TEXT)''')

    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password, role="student"):
    username = username.lower().strip()
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute('''INSERT INTO users(username, password, role, xp, streak,
                     last_active, level, badges, total_messages, joined)
                     VALUES (?,?,?,?,?,?,?,?,?,?)''',
                  (username, make_hashes(password), role, 0, 0, now, 1, '[]', 0, now))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        st.error(f"Xatolik: {e}")
        return False
    finally:
        conn.close()

def login_user(username, password):
    username = username.lower().strip()
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password = ?',
              (username, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data

def add_log(username, action):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO logs(username, action, time) VALUES (?,?,?)',
              (username, action, now))
    conn.commit()
    conn.close()

def view_all_users():
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    existing = [row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()]
    if "xp" in existing:
        df = pd.read_sql_query(
            "SELECT username, role, xp, level, streak, total_messages, joined FROM users",
            conn)
    else:
        df = pd.read_sql_query("SELECT username, role FROM users", conn)
    conn.close()
    return df

def view_logs():
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY time DESC LIMIT 100", conn)
    conn.close()
    return df

# ==========================================
# 🏆 XP VA DARAJALAR TIZIMI
# ==========================================
def add_xp(username, amount):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET xp = COALESCE(xp,0) + ?, total_messages = COALESCE(total_messages,0) + 1 WHERE username = ?',
                  (amount, username))
        c.execute('SELECT xp FROM users WHERE username = ?', (username,))
        row = c.fetchone()
        if row:
            xp = row[0] if row[0] else 0
            new_level = max(1, xp // 100 + 1)
            c.execute('UPDATE users SET level = ? WHERE username = ?',
                      (new_level, username))
        conn.commit()
    except Exception as e:
        pass
    finally:
        conn.close()

def get_user_stats(username):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT xp, streak, level, badges, total_messages, joined
                     FROM users WHERE username = ?''', (username,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "xp": row[0] if row[0] else 0,
                "streak": row[1] if row[1] else 0,
                "level": row[2] if row[2] else 1,
                "badges": json.loads(row[3]) if row[3] and row[3] != '' else [],
                "total_messages": row[4] if row[4] else 0,
                "joined": row[5] if row[5] else ""
            }
    except Exception:
        conn.close()
    return {"xp": 0, "streak": 0, "level": 1, "badges": [],
            "total_messages": 0, "joined": ""}

def update_streak(username):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute('SELECT last_active FROM users WHERE username = ?', (username,))
        row = c.fetchone()
        if row and row[0] and row[0].strip() != '':
            try:
                last = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                diff = (now.date() - last.date()).days
                if diff == 1:
                    c.execute('''UPDATE users SET streak = COALESCE(streak,0) + 1,
                                last_active = ? WHERE username = ?''',
                              (now_str, username))
                elif diff > 1:
                    c.execute('''UPDATE users SET streak = 1,
                                last_active = ? WHERE username = ?''',
                              (now_str, username))
                else:
                    c.execute('UPDATE users SET last_active = ? WHERE username = ?',
                              (now_str, username))
            except ValueError:
                c.execute('''UPDATE users SET streak = 1,
                            last_active = ? WHERE username = ?''',
                          (now_str, username))
        else:
            c.execute('''UPDATE users SET streak = 1,
                        last_active = ? WHERE username = ?''',
                      (now_str, username))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def add_badge(username, badge):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    try:
        c.execute('SELECT badges FROM users WHERE username = ?', (username,))
        row = c.fetchone()
        if row:
            badges = json.loads(row[0]) if row[0] and row[0] != '' else []
            if badge not in badges:
                badges.append(badge)
                c.execute('UPDATE users SET badges = ? WHERE username = ?',
                          (json.dumps(badges), username))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def check_achievements(username):
    stats = get_user_stats(username)
    earned = []
    checks = [
        (stats["total_messages"] >= 1, "🌟 Birinchi Qadam"),
        (stats["total_messages"] >= 10, "💬 Suhbatdosh"),
        (stats["total_messages"] >= 50, "🔥 Faol O'quvchi"),
        (stats["total_messages"] >= 100, "🏆 Zukko Master"),
        (stats["streak"] >= 3, "📅 3 Kunlik Streak"),
        (stats["streak"] >= 7, "🔥 Haftalik Streak"),
        (stats["level"] >= 5, "⭐ 5-Daraja"),
        (stats["level"] >= 10, "👑 10-Daraja"),
    ]
    for condition, badge_name in checks:
        if condition and badge_name not in stats["badges"]:
            add_badge(username, badge_name)
            earned.append(badge_name)
    return earned

# ==========================================
# 📝 NOTES TIZIMI
# ==========================================
def save_note(username, title, content, subject):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO notes(username, title, content, subject, time)
                 VALUES (?,?,?,?,?)''',
              (username, title, content, subject, now))
    conn.commit()
    conn.close()

def get_notes(username):
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query(
        "SELECT id, title, subject, time FROM notes WHERE username = ? ORDER BY time DESC",
        conn, params=(username,))
    conn.close()
    return df

def get_note_content(note_id):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    c.execute('SELECT title, content, subject, time FROM notes WHERE id = ?',
              (note_id,))
    row = c.fetchone()
    conn.close()
    return row

def delete_note(note_id):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    c.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()

# ==========================================
# 📊 QUIZ TIZIMI
# ==========================================
def save_quiz_score(username, subject, score, total):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO quiz_scores(username, subject, score, total, time)
                 VALUES (?,?,?,?,?)''',
              (username, subject, score, total, now))
    conn.commit()
    conn.close()

def get_quiz_history(username):
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query(
        "SELECT subject, score, total, time FROM quiz_scores WHERE username = ? ORDER BY time DESC LIMIT 20",
        conn, params=(username,))
    conn.close()
    return df

def get_leaderboard():
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    existing = [row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()]
    if "xp" in existing:
        df = pd.read_sql_query(
            "SELECT username, xp, level, streak FROM users WHERE role != 'admin' ORDER BY xp DESC LIMIT 10",
            conn)
    else:
        df = pd.DataFrame(columns=["username", "xp", "level", "streak"])
    conn.close()
    return df

# DB ni ishga tushirish
init_db()

# Admin foydalanuvchi
if "ADMIN_PASSWORD" in st.secrets:
    real_pass = st.secrets["ADMIN_PASSWORD"]
    add_user("admin", real_pass, "admin")

# ==========================================
# 🎵 OVOZ FUNKSIYASI
# ==========================================
def text_to_audio(text):
    try:
        clean = text.replace("```", "").replace("#", "").replace("*", "")
        if len(clean) > 500:
            clean = clean[:500] + "..."
        tts = gTTS(text=clean, lang='tr', slow=False)
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        return audio_bytes
    except:
        return None

# ==========================================
# 🧠 AI ENGINE
# ==========================================
class ZukkoEngine:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY)

    def generate(self, messages, system_prompt):
        full_history = [{"role": "system", "content": system_prompt}] + messages
        try:
            stream = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=full_history,
                temperature=0.6,
                max_tokens=1500,
                stream=True,
            )
            return stream
        except Exception as e:
            return str(e)

# ==========================================
# 🎨 MEGA DIZAYN (CSS)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] .stMarkdown label {
        color: #ffffff !important;
    }

    .metric-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.1) 100%);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid rgba(139,92,246,0.2);
        text-align: center;
        margin-bottom: 12px;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(139,92,246,0.25);
        border-color: rgba(139,92,246,0.4);
    }
    .metric-card h3 {
        font-size: 14px; font-weight: 500; opacity: 0.8; margin-bottom: 8px;
    }
    .metric-card h2 {
        font-size: 28px; font-weight: 800; margin: 0;
    }

    .xp-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 24px; border-radius: 16px; color: white;
        text-align: center; margin: 12px 0;
        box-shadow: 0 6px 20px rgba(102,126,234,0.4);
    }
    .xp-card h2 { margin: 0; font-size: 32px; font-weight: 900; }
    .xp-card p { margin: 4px 0 0 0; opacity: 0.9; font-size: 14px; }

    .streak-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px; border-radius: 16px; color: white;
        text-align: center; margin: 12px 0;
        box-shadow: 0 6px 20px rgba(245,87,108,0.4);
    }
    .streak-card h2 { margin: 0; font-size: 32px; font-weight: 900; }
    .streak-card p { margin: 4px 0 0 0; opacity: 0.9; font-size: 14px; }

    .level-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 20px; border-radius: 16px; color: white;
        text-align: center; margin: 12px 0;
        box-shadow: 0 6px 20px rgba(79,172,254,0.4);
    }
    .level-card h2 { margin: 0; font-size: 32px; font-weight: 900; }
    .level-card p { margin: 4px 0 0 0; opacity: 0.9; font-size: 14px; }

    .badge-box {
        background: linear-gradient(135deg, rgba(255,215,0,0.1) 0%, rgba(255,165,0,0.1) 100%);
        padding: 20px; border-radius: 16px;
        border: 1px solid rgba(255,215,0,0.3);
        margin: 12px 0; text-align: center;
    }
    .badge-item {
        display: inline-block; background: rgba(255,215,0,0.15);
        padding: 8px 16px; border-radius: 25px; margin: 4px;
        font-size: 14px; border: 1px solid rgba(255,215,0,0.3);
        transition: all 0.2s ease;
    }
    .badge-item:hover {
        transform: scale(1.1); background: rgba(255,215,0,0.25);
    }

    .progress-container {
        background: rgba(128,128,128,0.15);
        border-radius: 12px; padding: 4px; margin: 10px 0;
    }
    .progress-bar {
        height: 20px; border-radius: 10px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        transition: width 0.8s ease;
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 11px; font-weight: 700;
        min-width: 30px;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 16px !important; margin: 8px 0 !important;
        padding: 16px !important;
        border: 1px solid rgba(128,128,128,0.15) !important;
        backdrop-filter: blur(10px); transition: all 0.2s ease;
    }
    div[data-testid="stChatMessage"]:hover {
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    div[data-testid="stChatMessage"][data-author="user"] {
        background: linear-gradient(135deg, rgba(76,175,80,0.08) 0%, rgba(129,199,132,0.08) 100%) !important;
        border-left: 3px solid #4CAF50 !important;
    }
    div[data-testid="stChatMessage"][data-author="assistant"] {
        background: linear-gradient(135deg, rgba(33,150,243,0.08) 0%, rgba(100,181,246,0.08) 100%) !important;
        border-left: 3px solid #2196F3 !important;
    }

    .stButton > button {
        border-radius: 12px !important; padding: 8px 20px !important;
        font-weight: 600 !important; transition: all 0.3s ease !important;
        border: 1px solid rgba(139,92,246,0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 15px rgba(139,92,246,0.3) !important;
    }

    .stSelectbox > div > div { border-radius: 12px !important; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px; padding: 8px 20px; font-weight: 600;
    }

    .glow-title {
        text-align: center; font-size: 42px; font-weight: 900;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; margin-bottom: 8px;
        animation: glow-pulse 3s ease-in-out infinite;
    }
    @keyframes glow-pulse {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.2); }
    }

    .subtitle {
        text-align: center; font-size: 16px; opacity: 0.7; margin-bottom: 30px;
    }

    .note-card {
        background: rgba(128,128,128,0.08); padding: 16px;
        border-radius: 12px; border: 1px solid rgba(128,128,128,0.15);
        margin: 8px 0; transition: all 0.2s ease;
    }
    .note-card:hover {
        background: rgba(128,128,128,0.12); transform: translateX(4px);
    }

    .leader-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 12px 16px; background: rgba(128,128,128,0.06);
        border-radius: 12px; margin: 6px 0;
        border: 1px solid rgba(128,128,128,0.1); transition: all 0.2s ease;
    }
    .leader-row:hover {
        background: rgba(139,92,246,0.1); border-color: rgba(139,92,246,0.3);
    }
    .leader-rank { font-size: 24px; font-weight: 900; width: 40px; }
    .leader-name { font-weight: 600; font-size: 16px; flex: 1; margin-left: 12px; }
    .leader-xp { font-weight: 700; color: #764ba2; font-size: 16px; }

    .glass-box {
        background: rgba(255,255,255,0.05); backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px; padding: 24px; margin: 12px 0;
    }

    .fancy-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, rgba(139,92,246,0.5) 50%, transparent 100%);
        margin: 20px 0; border: none;
    }

    .pulse-dot {
        display: inline-block; width: 10px; height: 10px;
        border-radius: 50%; background: #4CAF50;
        animation: pulse 1.5s ease-in-out infinite; margin-right: 8px;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.3); opacity: 0.7; }
    }

    .feature-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.05) 100%);
        padding: 20px; border-radius: 16px;
        border: 1px solid rgba(139,92,246,0.15);
        text-align: center; transition: all 0.3s ease; height: 100%;
    }
    .feature-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 12px 30px rgba(139,92,246,0.2);
        border-color: rgba(139,92,246,0.4);
    }
    .feature-icon { font-size: 40px; margin-bottom: 10px; }
    .feature-title { font-weight: 700; font-size: 16px; margin-bottom: 6px; }
    .feature-desc { font-size: 13px; opacity: 0.7; }

    .welcome-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px; border-radius: 20px; color: white;
        margin-bottom: 20px;
        box-shadow: 0 8px 30px rgba(102,126,234,0.4);
    }
    .welcome-banner h2 { margin: 0; font-size: 28px; font-weight: 800; color: white !important; }
    .welcome-banner p { margin: 8px 0 0 0; opacity: 0.9; font-size: 15px; color: white !important; }

    .status-online {
        display: inline-flex; align-items: center;
        background: rgba(76,175,80,0.15); padding: 6px 14px;
        border-radius: 20px; color: #4CAF50;
        font-weight: 600; font-size: 13px;
        border: 1px solid rgba(76,175,80,0.3);
    }

    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(139,92,246,0.3); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(139,92,246,0.5); }

    .stChatInput > div {
        border-radius: 16px !important;
        border: 2px solid rgba(139,92,246,0.2) !important;
    }
    .stChatInput > div:focus-within {
        border-color: rgba(139,92,246,0.5) !important;
        box-shadow: 0 0 15px rgba(139,92,246,0.15) !important;
    }

    .stAlert { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🏠 DASHBOARD
# ==========================================
def show_dashboard(username):
    stats = get_user_stats(username)

    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting = "Xayrli tong"
        greet_emoji = "🌅"
    elif hour < 18:
        greeting = "Xayrli kun"
        greet_emoji = "☀️"
    else:
        greeting = "Xayrli kech"
        greet_emoji = "🌙"

    st.markdown(f"""
    <div class="welcome-banner">
        <h2>{greet_emoji} {greeting}, {username.title()}!</h2>
        <p>Bugun ham bilim olishga tayyormisiz? Zukko AI sizga yordam berishga tayyor!</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="xp-card">
            <h2>⚡ {stats['xp']}</h2>
            <p>Jami XP</p>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="level-card">
            <h2>🎯 {stats['level']}</h2>
            <p>Daraja</p>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="streak-card">
            <h2>🔥 {stats['streak']}</h2>
            <p>Kunlik Streak</p>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h2>💬 {stats['total_messages']}</h2>
            <p style="margin:4px 0 0 0; font-size:14px;">Xabarlar</p>
        </div>""", unsafe_allow_html=True)

    xp_in_level = stats['xp'] % 100
    pct = max(xp_in_level, 2)
    st.markdown(f"""
    <div style="margin: 16px 0;">
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <span style="font-weight:600;">Daraja {stats['level']}</span>
            <span style="opacity:0.7;">{xp_in_level}/100 XP</span>
        </div>
        <div class="progress-container">
            <div class="progress-bar" style="width: {pct}%;">{xp_in_level}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.markdown("### 🏅 Yutuqlar va Nishonlar")
        if stats["badges"]:
            badges_html = "".join(
                [f'<span class="badge-item">{b}</span>' for b in stats["badges"]])
            st.markdown(f'<div class="badge-box">{badges_html}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="badge-box">
                <p style="opacity:0.6;">Hali nishon yo'q. AI Chat orqali savol bering va nishon yutib oling! 🎯</p>
            </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("### 📊 Tezkor Ma'lumot")
        st.markdown(f"""
        <div class="metric-card">
            <h3>📅 Sana</h3>
            <h2>{datetime.datetime.now().strftime("%d.%m.%Y")}</h2>
        </div>""", unsafe_allow_html=True)

        role_display = "Admin 🛡️" if st.session_state.role == "admin" else "O'quvchi 🎓"
        st.markdown(f"""
        <div class="metric-card">
            <h3>👤 Rol</h3>
            <h2>{role_display}</h2>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    st.markdown("### 🚀 Imkoniyatlar")
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🤖</div>
            <div class="feature-title">AI Chat</div>
            <div class="feature-desc">6 ta fan bo'yicha AI mentor bilan suhbat</div>
        </div>""", unsafe_allow_html=True)
    with fc2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📝</div>
            <div class="feature-title">Eslatmalar</div>
            <div class="feature-desc">Muhim ma'lumotlarni saqlang</div>
        </div>""", unsafe_allow_html=True)
    with fc3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🏆</div>
            <div class="feature-title">Reyting</div>
            <div class="feature-desc">Top o'quvchilar reytingi</div>
        </div>""", unsafe_allow_html=True)
    with fc4:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">Yutuqlar</div>
            <div class="feature-desc">Badge va XP tizimi</div>
        </div>""", unsafe_allow_html=True)

    quotes = [
        "Language is the road map of a culture. 🌍",
        "Kod — bu kelajak tili. 💻",
        "Ona tili — millatning ruhi. 🇺🇿",
        "Bilim olishdan to'xtama! 🚀",
        "Har kuni 1% yaxshilaning — yil oxirida 37x bo'lasiz! 📈",
        "Xato qilishdan qo'rqmang — xatolardan o'rganasiz. 🧠",
        "Kichik qadamlar — katta natijalarga olib keladi. 🏔️",
        "O'qish — eng yaxshi investitsiya. 📚",
    ]
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    st.info(f"💡 **Kun hikmati:** {random.choice(quotes)}")

# ==========================================
# 🏆 REYTING SAHIFASI
# ==========================================
def show_leaderboard():
    st.markdown(
        '<h2 style="text-align:center;">🏆 Top O\'quvchilar Reytingi</h2>',
        unsafe_allow_html=True)
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    df = get_leaderboard()
    if df.empty:
        st.info("Hali reyting ma'lumotlari yo'q.")
        return

    medals = ["🥇", "🥈", "🥉"]
    for i, row in df.iterrows():
        rank = medals[i] if i < 3 else f"#{i+1}"
        xp_val = row.get('xp', 0) if row.get('xp') else 0
        lvl_val = row.get('level', 1) if row.get('level') else 1
        str_val = row.get('streak', 0) if row.get('streak') else 0
        st.markdown(f"""
        <div class="leader-row">
            <div class="leader-rank">{rank}</div>
            <div class="leader-name">{row['username'].title()}</div>
            <div class="leader-xp">⚡{xp_val} XP · Lvl {lvl_val} · 🔥{str_val}</div>
        </div>""", unsafe_allow_html=True)

# ==========================================
# 📝 ESLATMALAR SAHIFASI
# ==========================================
def show_notes(username):
    st.markdown("### 📝 Eslatmalar")
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    tab_add, tab_view = st.tabs(["➕ Yangi Eslatma", "📂 Eslatmalarim"])

    with tab_add:
        with st.form("note_form"):
            title = st.text_input("Sarlavha",
                                  placeholder="Masalan: Python asoslari")
            subject = st.selectbox("Fan", [
                "Umumiy", "Ingliz tili", "IT", "Ona tili",
                "Matematika", "Fizika", "Boshqa"])
            content = st.text_area("Matn", height=200,
                                   placeholder="Eslatma matnini yozing...")
            submitted = st.form_submit_button("💾 Saqlash")
            if submitted:
                if title and content:
                    save_note(username, title, content, subject)
                    st.success("✅ Eslatma saqlandi!")
                    st.rerun()
                else:
                    st.warning("Sarlavha va matn to'ldiring!")

    with tab_view:
        notes_df = get_notes(username)
        if notes_df.empty:
            st.info("Hali eslatma yo'q. Yangi eslatma qo'shing! ✍️")
        else:
            for _, row in notes_df.iterrows():
                with st.expander(
                    f"📌 {row['title']} — [{row['subject']}] — {row['time'][:10]}"):
                    note_data = get_note_content(row['id'])
                    if note_data:
                        st.markdown(note_data[1])
                        c1d, c2d = st.columns([4, 1])
                        with c2d:
                            if st.button("🗑️ O'chirish",
                                         key=f"del_{row['id']}"):
                                delete_note(row['id'])
                                st.rerun()

# ==========================================
# 📊 STATISTIKA SAHIFASI
# ==========================================
def show_statistics(username):
    st.markdown("### 📊 Shaxsiy Statistika")
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    stats = get_user_stats(username)

    col1, col2 = st.columns(2)
    with col1:
        joined_display = stats['joined'][:10] if stats['joined'] else 'N/A'
        st.markdown(f"""
        <div class="glass-box">
            <h4>📈 Umumiy Ko'rsatkichlar</h4>
            <p>⚡ Jami XP: <strong>{stats['xp']}</strong></p>
            <p>🎯 Daraja: <strong>{stats['level']}</strong></p>
            <p>🔥 Streak: <strong>{stats['streak']} kun</strong></p>
            <p>💬 Jami xabarlar: <strong>{stats['total_messages']}</strong></p>
            <p>📅 Qo'shilgan: <strong>{joined_display}</strong></p>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("#### 🏅 Barcha Nishonlar")
        all_badges = [
            ("🌟 Birinchi Qadam", "1 ta xabar yozing"),
            ("💬 Suhbatdosh", "10 ta xabar yozing"),
            ("🔥 Faol O'quvchi", "50 ta xabar yozing"),
            ("🏆 Zukko Master", "100 ta xabar yozing"),
            ("📅 3 Kunlik Streak", "3 kun ketma-ket kiring"),
            ("🔥 Haftalik Streak", "7 kun ketma-ket kiring"),
            ("⭐ 5-Daraja", "5-darajaga yeting"),
            ("👑 10-Daraja", "10-darajaga yeting"),
        ]
        for badge_name, desc in all_badges:
            earned = "✅" if badge_name in stats["badges"] else "🔒"
            st.markdown(f"""
            <div class="note-card">
                <span>{earned} <strong>{badge_name}</strong></span>
                <br><small style="opacity:0.6;">{desc}</small>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    st.markdown("#### 📝 Quiz Tarixi")
    quiz_df = get_quiz_history(username)
    if quiz_df.empty:
        st.info("Hali quiz ishlanmagan.")
    else:
        st.dataframe(quiz_df, use_container_width=True)

# ==========================================
# 🖥️ ASOSIY DASTUR
# ==========================================
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    # --- KIRISH QISMI ---
    if not st.session_state.logged_in:
        st.markdown(
            '<div class="glow-title">⚡ Zukko AI</div>',
            unsafe_allow_html=True)
        st.markdown(
            '<div class="subtitle">Aqlli ta\'lim platformasi — AI bilan o\'rganish!</div>',
            unsafe_allow_html=True)
        st.markdown('<div class="fancy-divider"></div>',
                    unsafe_allow_html=True)

        col_left, col_center, col_right = st.columns([1, 2, 1])
        with col_center:
            tab1, tab2 = st.tabs(["🔑 Kirish", "📝 Ro'yxatdan o'tish"])
            with tab1:
                username = st.text_input("👤 Login", key="login_user",
                                         placeholder="Login kiriting...")
                password = st.text_input("🔒 Parol", type='password',
                                         key="login_pass",
                                         placeholder="Parolingiz...")
                st.markdown("")
                if st.button("🚀 Kirish", use_container_width=True):
                    if not username or not password:
                        st.warning("Login va parolni to'ldiring!")
                    else:
                        result = login_user(username, password)
                        if result:
                            st.session_state.logged_in = True
                            st.session_state.username = result[0][0]
                            st.session_state.role = result[0][2]
                            update_streak(username.lower().strip())
                            add_log(username, "Kirdi")
                            st.rerun()
                        else:
                            st.error("❌ Login yoki parol xato!")

            with tab2:
                new_user = st.text_input("👤 Yangi Login", key="reg_user",
                                         placeholder="Login tanlang...")
                new_pass = st.text_input("🔒 Yangi Parol", type='password',
                                         key="reg_pass",
                                         placeholder="Parol yarating...")
                new_pass2 = st.text_input("🔒 Parolni tasdiqlang",
                                          type='password', key="reg_pass2",
                                          placeholder="Parolni qaytaring...")
                st.markdown("")
                if st.button("✨ Ro'yxatdan o'tish",
                             use_container_width=True):
                    if not new_user or not new_pass:
                        st.warning("Barcha maydonlarni to'ldiring!")
                    elif len(new_pass) < 4:
                        st.warning("Parol kamida 4 ta belgidan iborat bo'lsin!")
                    elif new_pass != new_pass2:
                        st.error("Parollar mos kelmaydi!")
                    elif add_user(new_user, new_pass):
                        st.success(
                            "✅ Akkaunt yaratildi! Endi kirish bo'limiga o'ting.")
                        add_log(new_user, "Ro'yxatdan o'tdi")
                    else:
                        st.error("❌ Bu login band!")

    # --- TIZIM ICHIDA ---
    else:
        with st.sidebar:
            st.markdown(f"""
            <div style="text-align:center; padding: 20px 0;">
                <div style="font-size:36px; font-weight:900;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;">⚡ Zukko AI</div>
                <div style="margin-top:8px;">
                    <span class="status-online">
                        <span class="pulse-dot"></span> Online
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="fancy-divider"></div>',
                        unsafe_allow_html=True)

            stats = get_user_stats(st.session_state.username)
            st.markdown(f"""
            <div style="text-align:center; padding: 10px;">
                <p style="font-weight:700; font-size:16px; color:white !important;">
                    👤 {st.session_state.username.title()}</p>
                <p style="opacity:0.7; font-size:13px; color:white !important;">
                    ⚡{stats['xp']} XP · Lvl {stats['level']} · 🔥{stats['streak']}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="fancy-divider"></div>',
                        unsafe_allow_html=True)

            page = st.radio("📂 Bo'limlar:", [
                "🏠 Dashboard",
                "🤖 AI Chat",
                "📝 Eslatmalar",
                "🏆 Reyting",
                "📊 Statistika",
                "🛡️ Admin Panel"
            ], label_visibility="collapsed")

            st.markdown('<div class="fancy-divider"></div>',
                        unsafe_allow_html=True)

            if st.button("🚪 Chiqish", use_container_width=True):
                add_log(st.session_state.username, "Chiqdi")
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.role = ""
                st.rerun()

        # Sahifalar
        if page == "🏠 Dashboard":
            show_dashboard(st.session_state.username)

        elif page == "🏆 Reyting":
            show_leaderboard()

        elif page == "📝 Eslatmalar":
            show_notes(st.session_state.username)

        elif page == "📊 Statistika":
            show_statistics(st.session_state.username)

        elif page == "🛡️ Admin Panel":
            if st.session_state.role == "admin":
                st.markdown("### 🛡️ Admin Panel")
                st.markdown('<div class="fancy-divider"></div>',
                            unsafe_allow_html=True)

                admin_tab1, admin_tab2, admin_tab3 = st.tabs(
                    ["👥 Foydalanuvchilar", "📋 Loglar", "📊 Statistika"])

                with admin_tab1:
                    st.dataframe(view_all_users(),
                                 use_container_width=True)

                with admin_tab2:
                    st.dataframe(view_logs(), use_container_width=True)

                with admin_tab3:
                    users_df = view_all_users()
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Jami Foydalanuvchilar</h3>
                        <h2>{len(users_df)}</h2>
                    </div>""", unsafe_allow_html=True)

                    logs_df = view_logs()
                    today = datetime.datetime.now().strftime("%Y-%m-%d")
                    if not logs_df.empty:
                        today_logs = logs_df[
                            logs_df['time'].str.startswith(today)]
                    else:
                        today_logs = pd.DataFrame()
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>Bugungi Faollik</h3>
                        <h2>{len(today_logs)} ta</h2>
                    </div>""", unsafe_allow_html=True)
            else:
                st.error("⛔ Siz Admin emassiz!")

        # ==========================================
        # 🤖 AI CHAT
        # ==========================================
        elif page == "🤖 AI Chat":
            st.markdown("### 🤖 AI Mentor")
            st.markdown('<div class="fancy-divider"></div>',
                        unsafe_allow_html=True)

            mentor_type = st.selectbox("🎓 Yordamchi turini tanlang:", [
                "🌐 Universal Yordamchi",
                "🇬🇧 Ingliz tili (Speaking)",
                "💻 IT va Dasturlash",
                "📚 Ona tili va Adabiyot",
                "📐 Matematika va Fizika",
                "🏫 Boshlang'ich Sinflar (1-4)"
            ])

            system_prompt = ""

            if mentor_type == "🌐 Universal Yordamchi":
                system_prompt = """Sen Zukko AI — O'zbekistondagi eng aqlli ta'lim yordamchisisan.
                Har qanday mavzuda aniq, tushunarli va do'stona javob ber.
                Javoblaringni strukturali yoz, emoji ishlat, misollar keltir.
                O'zbek tilida javob ber (agar boshqa til so'ralmasa)."""

            elif mentor_type == "🇬🇧 Ingliz tili (Speaking)":
                system_prompt = """You are Zukko AI — a friendly English teacher for Uzbek students.
                Speak mostly in English but explain grammar in Uzbek when needed.
                Correct mistakes politely with explanations.
                Help with IELTS, speaking practice, vocabulary.
                Use examples and encourage the student."""

            elif mentor_type == "💻 IT va Dasturlash":
                system_prompt = """Sen Zukko AI — Senior Full-Stack Developer va IT Mentorsan.
                Python, JavaScript, Web, Mobile, Database — barchasi bo'yicha yordam ber.
                Kod yozishda: to'liq ishlashi mumkin bo'lgan kod ber.
                Har bir kodni izohla. Amaliy loyihalar taklif qil."""

            elif mentor_type == "📚 Ona tili va Adabiyot":
                system_prompt = """Sen Zukko AI — Ona tili va Adabiyot ustozisan.
                Grammatika qoidalari, imlo, tinish belgilari bo'yicha yordam ber.
                Alisher Navoiy, Abdulla Qodiriy, Cho'lpon asarlarini tahlil qil.
                Insho yozishda yordam ber."""

            elif mentor_type == "📐 Matematika va Fizika":
                system_prompt = """Sen Zukko AI — Matematika va Fizika bo'yicha aniq fanlar ustozisan.
                Formulalarni tushuntir, misollar yech, qadamma-qadam ko'rsat.
                Hayotiy misollar bilan tushuntir."""

            elif mentor_type == "🏫 Boshlang'ich Sinflar (1-4)":
                grade = st.selectbox("📖 Sinfni tanlang:",
                                     ["1-sinf", "2-sinf", "3-sinf", "4-sinf"])
                system_prompt = f"""Sen Zukko AI — {grade} uchun eng yaxshi o'qituvchisan.
                Bolalar tilida, juda sodda va emojilar bilan gapir.
                Har bir javobda rag'batlantir.
                Qisqa va tushunarli javob ber."""

            mentor_colors = {
                "🌐 Universal Yordamchi": "rgba(99,102,241,0.1)",
                "🇬🇧 Ingliz tili (Speaking)": "rgba(76,175,80,0.1)",
                "💻 IT va Dasturlash": "rgba(33,150,243,0.1)",
                "📚 Ona tili va Adabiyot": "rgba(255,152,0,0.1)",
                "📐 Matematika va Fizika": "rgba(244,67,54,0.1)",
                "🏫 Boshlang'ich Sinflar (1-4)": "rgba(156,39,176,0.1)"
            }
            bg = mentor_colors.get(mentor_type, "rgba(128,128,128,0.1)")
            st.markdown(f"""
            <div style="background:{bg}; padding:12px 20px; border-radius:12px;
                        margin:10px 0;
                        border: 1px solid rgba(128,128,128,0.15);">
                📌 <strong>Tanlandi:</strong> {mentor_type}
            </div>""", unsafe_allow_html=True)

            if "messages" not in st.session_state:
                st.session_state.messages = []
            if "current_mentor" not in st.session_state:
                st.session_state.current_mentor = mentor_type

            if st.session_state.current_mentor != mentor_type:
                st.session_state.messages = []
                st.session_state.current_mentor = mentor_type

            bcol1, bcol2, bcol3, bcol4 = st.columns(4)
            with bcol1:
                if st.button("🗑️ Tozalash", use_container_width=True):
                    st.session_state.messages = []
                    st.rerun()
            with bcol2:
                if st.button("📝 Test tuzish", use_container_width=True):
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "Mavzu bo'yicha 5 ta test savol tuzib ber (A, B, C, D variantlar bilan). Oxirida javoblarini ber."
                    })
                    st.rerun()
            with bcol3:
                if st.button("💡 Mavzu taklif", use_container_width=True):
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "Menga o'rganish uchun qiziqarli mavzular taklif qil (hozirgi fan bo'yicha). Har biriga qisqa izoh ber."
                    })
                    st.rerun()
            with bcol4:
                if st.button("📖 Xulosa", use_container_width=True):
                    if st.session_state.messages:
                        st.session_state.messages.append({
                            "role": "user",
                            "content": "Shu suhbatimiz bo'yicha qisqa xulosa yozib ber — asosiy fikrlar, o'rganilgan narsalar."
                        })
                        st.rerun()

            st.markdown('<div class="fancy-divider"></div>',
                        unsafe_allow_html=True)

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if prompt := st.chat_input("💬 Savolingizni yozing..."):
                st.session_state.messages.append(
                    {"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    engine = ZukkoEngine()
                    placeholder = st.empty()
                    full_text = ""
                    stream = engine.generate(
                        st.session_state.messages, system_prompt)

                    if isinstance(stream, str):
                        st.error(f"⚠️ Xatolik: {stream}")
                        full_text = "Xatolik yuz berdi."
                    else:
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_text += chunk.choices[0].delta.content
                                placeholder.markdown(full_text + "▌")
                        placeholder.markdown(full_text)

                        audio = text_to_audio(full_text)
                        if audio:
                            st.audio(audio, format="audio/mp3")

                st.session_state.messages.append(
                    {"role": "assistant", "content": full_text})

                add_xp(st.session_state.username, 10)
                add_log(st.session_state.username, f"Chat: {mentor_type}")
                new_badges = check_achievements(st.session_state.username)
                if new_badges:
                    for b in new_badges:
                        st.toast(f"🎉 Yangi nishon: {b}", icon="🏅")

if __name__ == "__main__":
    main()