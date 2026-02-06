import streamlit as st
import io
import random
import time

# ⚠️ Streamlit Secrets
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("GROQ_API_KEY topilmadi!")
    st.stop()

from openai import OpenAI
import sqlite3
import hashlib
import datetime
import pandas as pd
from gtts import gTTS

MODEL_NAME = "llama-3.3-70b-versatile"
LOGO_URL = "https://i.imgur.com/eB4G86l.png"  # SIZNING YANGI LOGOINGIZ

# Page config
st.set_page_config(page_title="Sinai AI", page_icon=LOGO_URL, layout="wide")

# ==========================================
# 🎨 DIZAYN (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(to right, #ece9e6, #ffffff); }
    
    /* Login oynasi */
    .login-container {
        background-color: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 5px solid #764ba2;
    }
    
    /* Dashboard kartalari */
    .dashboard-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        text-align: center;
        flex: 1;
        transition: transform 0.3s;
    }
    .dashboard-card:hover { transform: translateY(-5px); }
    .card-title { color: #888; font-size: 14px; font-weight: 600; }
    .card-value { color: #2c3e50; font-size: 24px; font-weight: bold; }
    
    /* Chat bubbles */
    .stChatMessage {
        border-radius: 12px;
        border: 1px solid #eee;
        background-color: white;
    }
    div[data-testid="stChatMessage"][data-author="user"] { background-color: #f3e5f5; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🗄️ BAZA (BACKEND)
# ==========================================
def init_db():
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (username TEXT, action TEXT, time TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password, role="student"):
    username = username.lower().strip()
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, role) VALUES (?,?,?)', 
                  (username, make_hashes(password), role))
        conn.commit()
        return True
    except:
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
    c.execute('INSERT INTO logs(username, action, time) VALUES (?,?,?)', (username, action, now))
    conn.commit()
    conn.close()

def view_all_users():
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query("SELECT username, role FROM users", conn)
    conn.close()
    return df

def view_logs():
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY time DESC", conn)
    conn.close()
    return df

init_db()

if "ADMIN_PASSWORD" in st.secrets:
    real_pass = st.secrets["ADMIN_PASSWORD"]
    add_user("admin", real_pass, "admin")

# ==========================================
# 🎵 OVOZ VA AI
# ==========================================
def text_to_audio(text):
    try:
        if len(text) > 500: text = text[:500] + "..." 
        tts = gTTS(text=text, lang='tr', slow=False) 
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        return audio_bytes
    except:
        return None

class ZukkoEngine:
    def __init__(self):
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

    def generate(self, messages, system_prompt):
        full_history = [{"role": "system", "content": system_prompt}] + messages
        try:
            stream = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=full_history,
                temperature=0.7,
                max_tokens=1500,
                stream=True,
            )
            return stream
        except Exception as e:
            return str(e)

# ==========================================
# 🏠 DASHBOARD (LOGO BILAN)
# ==========================================
def show_dashboard(username):
    # HEADER: LOGO VA SALOMLASHISH (FLEXBOX)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; color: white; margin-bottom: 20px; display: flex; align-items: center; gap: 20px;">
        <img src="{LOGO_URL}" style="width: 120px; border-radius: 10px;">
        <div>
            <h1 style="color: white; margin:0;">Salom, {username.title()}! 👋</h1>
            <p style="margin:5px 0 0 0; opacity: 0.9;">Bugun nimani o'rganamiz?</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KARTALAR
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="dashboard-card" style="border-bottom: 4px solid #3498db;">
            <div style="font-size:30px">📅</div>
            <div class="card-title">Sana</div>
            <div class="card-value">{datetime.datetime.now().strftime("%d.%m.%Y")}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="dashboard-card" style="border-bottom: 4px solid #2ecc71;">
            <div style="font-size:30px">⚡</div>
            <div class="card-title">Tizim holati</div>
            <div class="card-value">Online</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        role_name = "Admin" if st.session_state.role == "admin" else "O'quvchi"
        st.markdown(f"""
        <div class="dashboard-card" style="border-bottom: 4px solid #9b59b6;">
            <div style="font-size:30px">🏆</div>
            <div class="card-title">Daraja</div>
            <div class="card-value">{role_name}</div>
        </div>
        """, unsafe_allow_html=True)

    # HIKMAT
    quotes = ["Bilim — aqlning chirog'i.", "Harakat qilsang, albatta yetasan.", "Kelajak bugun yaratiladi."]
    st.info(f"💡 **Kun hikmati:** {random.choice(quotes)}")

# ==========================================
# 🖥️ ASOSIY DASTUR
# ==========================================

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    # --- LOGIN OYNASI ---
    if not st.session_state.logged_in:
        col_left, col_center, col_right = st.columns([1, 2, 1])

        with col_center:
            # Login tepasida LOGO
            st.image(LOGO_URL, width=150) 
            st.markdown("""
            <div class="login-container">
                <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">SINAI AI</div>
                <div style="color: gray;">Kelajak ta'lim platformasi</div>
            </div>
            """, unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🔑 Kirish", "📝 Ro'yxatdan o'tish"])
            
            with tab1:
                username = st.text_input("Login", key="login_user")
                password = st.text_input("Parol", type='password', key="login_pass")
                if st.button("Kirish", use_container_width=True):
                    result = login_user(username, password)
                    if result:
                        st.session_state.logged_in = True
                        st.session_state.username = result[0][0]
                        st.session_state.role = result[0][2]
                        add_log(username, "Kirdi")
                        st.rerun()
                    else:
                        st.error("Login xato!")

            with tab2:
                new_user = st.text_input("Yangi Login", key="reg_user")
                new_pass = st.text_input("Yangi Parol", type='password', key="reg_pass")
                if st.button("Yaratish", use_container_width=True):
                    if add_user(new_user, new_pass):
                        st.success("Muvaffaqiyatli!")
                    else:
                        st.error("Login band!")

    # --- TIZIM ICHIDA ---
    else:
        with st.sidebar:
            # SIDEBAR LOGO
            st.image(LOGO_URL, width=120)
            st.caption(f"👤 {st.session_state.username}")
            
            page = st.radio("Menyu:", ["🏠 Dashboard", "🤖 AI Chat", "🛡️ Admin Panel"])
            st.markdown("---")
            if st.button("Chiqish 🚪"):
                st.session_state.logged_in = False
                st.rerun()

        if page == "🏠 Dashboard":
            show_dashboard(st.session_state.username)

        elif page == "🛡️ Admin Panel":
            if st.session_state.role == "admin":
                st.header("🛡️ Admin Panel")
                t1, t2 = st.tabs(["Userlar", "Loglar"])
                with t1: st.dataframe(view_all_users(), use_container_width=True)
                with t2: st.dataframe(view_logs(), use_container_width=True)
            else:
                st.error("⛔ Faqat Admin uchun!")

        elif page == "🤖 AI Chat":
            st.subheader("🤖 Sinai AI Chat")
            mode_choice = st.selectbox("Mavzu:", ["🌐 Universal", "1-sinf", "2-sinf", "3-sinf", "4-sinf"])
            
            prompts = {
                "🌐 Universal": {"role": "AI", "prompt": "Sen Sinai AIsan."},
                "1-sinf": {"role": "O'qituvchi", "prompt": "1-sinf bolaga sodda gapir."},
                "2-sinf": {"role": "Matematik", "prompt": "Matematika o'rgat."},
                "3-sinf": {"role": "Tabiatshunos", "prompt": "Tabiat haqida gapir."},
                "4-sinf": {"role": "IT Ustoz", "prompt": "IT o'rgat."}
            }
            
            if "messages" not in st.session_state: st.session_state.messages = []
            
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("🗑️ Tozalash"):
                    st.session_state.messages = []
                    st.rerun()
            with c2:
                if st.button("📝 Test tuzish"):
                    st.session_state.messages.append({"role": "user", "content": "3 ta test tuz."})

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

            if prompt := st.chat_input("Yozing..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)

                with st.chat_message("assistant"):
                    engine = ZukkoEngine()
                    placeholder = st.empty()
                    full_text = ""
                    stream = engine.generate(st.session_state.messages, prompts[mode_choice]['prompt'])
                    
                    if isinstance(stream, str):
                        st.error(stream)
                    else:
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_text += chunk.choices[0].delta.content
                                placeholder.markdown(full_text + "▌")
                        placeholder.markdown(full_text)
                        audio = text_to_audio(full_text)
                        if audio: st.audio(audio, format="audio/mp3")
                st.session_state.messages.append({"role": "assistant", "content": full_text})

if __name__ == "__main__":
    main()