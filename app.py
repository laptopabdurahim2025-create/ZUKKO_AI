import streamlit as st
import io
import random
import time

# ⚠️ Streamlit Secrets
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    # Lokalda ishlatish uchun:
    # GROQ_API_KEY = "gsk_..."
    st.error("GROQ_API_KEY topilmadi!")
    st.stop()

from openai import OpenAI
import sqlite3
import hashlib
import datetime
import pandas as pd
from gtts import gTTS

MODEL_NAME = "llama-3.3-70b-versatile"

# Page config: Title va Icon
st.set_page_config(page_title="Zukko AI", page_icon="🎓", layout="wide")

# ==========================================
# 🎨 1. SUPER DIZAYN (CSS)
# ==========================================
st.markdown("""
<style>
    /* Umumiy fon */
    .stApp {
        background: linear-gradient(to right, #ece9e6, #ffffff);
    }

    /* --- LOGIN QISMI UCHUN STIL --- */
    .login-container {
        background-color: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 5px solid #4CAF50;
    }
    .login-header {
        font-size: 28px;
        font-weight: bold;
        color: #333;
        margin-bottom: 10px;
    }
    .login-sub {
        color: #666;
        font-size: 14px;
        margin-bottom: 20px;
    }

    /* --- DASHBOARD KARTALARI --- */
    .card-container {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 30px;
    }
    .dashboard-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        text-align: center;
        flex: 1;
        transition: transform 0.3s;
    }
    .dashboard-card:hover {
        transform: translateY(-5px);
    }
    .card-icon { font-size: 30px; margin-bottom: 10px; }
    .card-title { color: #888; font-size: 14px; font-weight: 600; }
    .card-value { color: #2c3e50; font-size: 24px; font-weight: bold; margin-top: 5px; }

    /* Rangli chiziqlar */
    .border-blue { border-bottom: 4px solid #3498db; }
    .border-green { border-bottom: 4px solid #2ecc71; }
    .border-purple { border-bottom: 4px solid #9b59b6; }

    /* --- CHAT STILI --- */
    .stChatMessage {
        border-radius: 12px;
        border: 1px solid #eee;
        background-color: white;
    }
    div[data-testid="stChatMessage"][data-author="user"] {
        background-color: #f0f9ff; /* Och ko'k */
    }
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

# Admin paroli (Secrets dan)
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
# 🏠 DASHBOARD (YANGILANGAN)
# ==========================================
def show_dashboard(username):
    # Salomlashish (Hero Section)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; color: white; margin-bottom: 20px;">
        <h1 style="color: white; margin:0;">Salom, {username.title()}! 👋</h1>
        <p style="margin:5px 0 0 0; opacity: 0.9;">Bugun nimani o'rganamiz?</p>
    </div>
    """, unsafe_allow_html=True)

    # Statistika Kartalari
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="dashboard-card border-blue">
            <div class="card-icon">📅</div>
            <div class="card-title">Sana</div>
            <div class="card-value">{datetime.datetime.now().strftime("%d.%m.%Y")}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="dashboard-card border-green">
            <div class="card-icon">⚡</div>
            <div class="card-title">Tizim holati</div>
            <div class="card-value">Online</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        role_icon = "🛡️" if st.session_state.role == "admin" else "🎓"
        role_name = "Admin" if st.session_state.role == "admin" else "O'quvchi"
        st.markdown(f"""
        <div class="dashboard-card border-purple">
            <div class="card-icon">{role_icon}</div>
            <div class="card-title">Sizning rolingiz</div>
            <div class="card-value">{role_name}</div>
        </div>
        """, unsafe_allow_html=True)

    # Kun hikmati
    quotes = [
        "Bilim — aqlning chirog'idir. 💡",
        "Harakat qilsang, albatta yetasan. 🚀",
        "Xato qilishdan qo'rqma, to'xtab qolishdan qo'rq. 🛑",
        "Bugungi dars — ertangi kelajak. 📚"
    ]
    st.info(f"💡 **Kun hikmati:** {random.choice(quotes)}")

# ==========================================
# 🖥️ ASOSIY DASTUR (APP)
# ==========================================

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    # --- LOGIN SAHIFASI (MARKAZLASHTIRILGAN) ---
    if not st.session_state.logged_in:
        # Ekranni 3 ga bo'lamiz, o'rtasiga Login qo'yamiz
        col_left, col_center, col_right = st.columns([1, 2, 1])

        with col_center:
            st.markdown("""
            <div class="login-container">
                <div class="login-header">🎓 Zukko AI</div>
                <div class="login-sub">Kelajak ta'lim platformasiga xush kelibsiz</div>
            </div>
            """, unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🔑 Kirish", "📝 Ro'yxatdan o'tish"])
            
            with tab1:
                username = st.text_input("Login", key="login_user", placeholder="Loginingiz...")
                password = st.text_input("Parol", type='password', key="login_pass", placeholder="Parolingiz...")
                
                # Kirish tugmasini chiroyli qilish
                if st.button("Tizimga kirish", use_container_width=True):
                    result = login_user(username, password)
                    if result:
                        st.session_state.logged_in = True
                        st.session_state.username = result[0][0]
                        st.session_state.role = result[0][2]
                        add_log(username, "Kirdi")
                        st.rerun()
                    else:
                        st.error("Login yoki parol xato!")

            with tab2:
                new_user = st.text_input("Yangi Login", key="reg_user")
                new_pass = st.text_input("Yangi Parol", type='password', key="reg_pass")
                if st.button("Akkaunt yaratish", use_container_width=True):
                    if add_user(new_user, new_pass):
                        st.success("Muvaffaqiyatli! Endi Kirish bo'limiga o'ting.")
                        add_log(new_user, "Ro'yxatdan o'tdi")
                    else:
                        st.error("Bu login band!")

    # --- TIZIM ICHIDA ---
    else:
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80)
            st.title("Zukko AI")
            st.caption(f"👤 {st.session_state.username}")
            
            page = st.radio("Menyu:", ["🏠 Dashboard", "🤖 AI Chat", "🛡️ Admin Panel"])
            
            st.markdown("---")
            if st.button("Chiqish 🚪"):
                st.session_state.logged_in = False
                st.rerun()

        # 1. DASHBOARD
        if page == "🏠 Dashboard":
            show_dashboard(st.session_state.username)

        # 2. ADMIN PANEL
        elif page == "🛡️ Admin Panel":
            if st.session_state.role == "admin":
                st.header("🛡️ Admin Panel")
                tab_u, tab_l = st.tabs(["Foydalanuvchilar", "Tarix"])
                with tab_u:
                    st.dataframe(view_all_users(), use_container_width=True)
                with tab_l:
                    st.dataframe(view_logs(), use_container_width=True)
            else:
                st.error("⛔ Bu bo'lim faqat Admin uchun!")

        # 3. AI CHAT
        elif page == "🤖 AI Chat":
            st.subheader("🤖 AI bilan suhbat")
            mode_choice = st.selectbox("Mavzu:", ["🌐 Universal Yordamchi", "1-sinf", "2-sinf", "3-sinf", "4-sinf"])
            
            prompts = {
                "🌐 Universal Yordamchi": {"role": "AI", "prompt": "Sen Zukko AIsan."},
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
                    st.session_state.messages.append({"role": "user", "content": "Mavzu bo'yicha 3 ta test tuzib ber."})

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

            if prompt := st.chat_input("Savol bering..."):
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