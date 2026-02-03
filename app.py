import streamlit as st
from openai import OpenAI
import sqlite3
import hashlib
import datetime
import pandas as pd
import time

# ==========================================
# ⚙️ SOZLAMALAR
# ==========================================

# ⚠️ GROQ KALITINI SHU YERGA QO'YASAN:
API_KEY = "YOUR_GROQ_API_KEY_HERE"
MODEL_NAME = "llama-3.3-70b-versatile"

st.set_page_config(page_title="Zukko School AI", page_icon="🎓", layout="wide")

# ==========================================
# 🗄️ BAZA VA XAVFSIZLIK (BACKEND)
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
# Adminni avtomatik yaratish (Login: admin / Parol: admin123)
add_user("admin", "admin123", "admin") 

# ==========================================
# 🧠 AI ENGINE
# ==========================================

class ZukkoEngine:
    def __init__(self):
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=API_KEY)

    def generate(self, messages, system_prompt):
        full_history = [{"role": "system", "content": system_prompt}] + messages
        try:
            stream = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=full_history,
                temperature=0.7,
                max_tokens=2000,
                stream=True,
            )
            return stream
        except Exception as e:
            return str(e)

# ==========================================
# 🎨 DIZAYN (CSS)
# ==========================================
st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    h1 { color: #1e3a8a; }
    .stSidebar { background-color: #1e3a8a; }
    .stSidebar .stMarkdown { color: white; }
    div[data-testid="stSidebarUserContent"] { color: white; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🖥️ ASOSIY DASTUR
# ==========================================

def main():
    st.title("🎓 Zukko Ta'lim Ekotizimi")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    # --- LOGIN / REGISTRATSIYA ---
    if not st.session_state.logged_in:
        menu = ["Kirish", "Ro'yxatdan o'tish"]
        choice = st.sidebar.selectbox("Menyu", menu)

        if choice == "Kirish":
            st.subheader("Tizimga kirish")
            username = st.text_input("Login")
            password = st.text_input("Parol", type='password')
            if st.button("Kirish"):
                result = login_user(username, password)
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = result[0][2]
                    add_log(username, "Tizimga kirdi")
                    st.rerun()
                else:
                    st.error("Xato login yoki parol")

        elif choice == "Ro'yxatdan o'tish":
            st.subheader("Yangi foydalanuvchi")
            new_user = st.text_input("Yangi Login")
            new_pass = st.text_input("Yangi Parol", type='password')
            if st.button("Yaratish"):
                if add_user(new_user, new_pass):
                    st.success("Akkaunt yaratildi! Endi 'Kirish' orqali kiring.")
                    add_log(new_user, "Ro'yxatdan o'tdi")
                else:
                    st.error("Login band!")

    # --- ICHKI TIZIM ---
    else:
        with st.sidebar:
            st.info(f"👤 Foydalanuvchi: {st.session_state.username}")
            
            # Agar Admin bo'lsa, ikkita rejim chiqadi
            if st.session_state.role == "admin":
                app_mode = st.radio("Rejim:", ["🤖 AI Chat", "🛡️ Admin Panel"])
            else:
                app_mode = "🤖 AI Chat"

            st.markdown("---")
            if st.button("Chiqish"):
                add_log(st.session_state.username, "Chiqdi")
                st.session_state.logged_in = False
                st.rerun()

        # --- ADMIN PANEL ---
        if st.session_state.role == "admin" and app_mode == "🛡️ Admin Panel":
            st.header("🛡️ Admin Boshqaruv")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Foydalanuvchilar")
                st.dataframe(view_all_users(), use_container_width=True)
            with col2:
                st.subheader("Loglar (Tarix)")
                st.dataframe(view_logs(), use_container_width=True)

        # --- AI CHAT (MAKTAB + UNIVERSAL) ---
        elif app_mode == "🤖 AI Chat":
            # YANGI RO'YXAT: UNIVERSAL + SINFLAR
            mode_choice = st.selectbox("Mavzuni tanlang:", 
                ["🌐 Universal Yordamchi", "1-sinf", "2-sinf", "3-sinf", "4-sinf"]
            )
            
            # Promptlar bazasi
            prompts = {
                "🌐 Universal Yordamchi": {
                    "role": "Super Intellekt",
                    "desc": "Istalgan mavzuda suhbat: Dasturlash, Sport, Kino, Maslahatlar...",
                    "prompt": "Sen Zukko AIsan. Sen O'zbekistondagi eng aqlli sun'iy intellektsan. Foydalanuvchi nima haqida so'rasa (xoh u fizika bo'lsin, xoh bugungi ob-havo, xoh shunchaki dardlashish), o'sha mavzuda aniq, londa va do'stona javob ber."
                },
                "1-sinf": {
                    "role": "Boshlang'ich O'qituvchi",
                    "desc": "Alifbo va o'qishni o'rganamiz.",
                    "prompt": "Sen mehribon o'qituvchisan. 1-sinf bolasiga oddiy so'zlar bilan tushuntir. Ko'p emoji ishlat."
                },
                "2-sinf": {
                    "role": "Matematika Ustoz",
                    "desc": "Qo'shish, ayirish, karra jadvali.",
                    "prompt": "Sen matematika o'qituvchisisan. Bolalarga hisob-kitobni qiziqarli o'rgat."
                },
                "3-sinf": {
                    "role": "Tabiatshunos",
                    "desc": "Hayvonlar va Olam sirlari.",
                    "prompt": "Tabiatshunoslik o'qituvchisi sifatida bolalarga dunyo sirlarini ochib ber."
                },
                "4-sinf": {
                    "role": "Ingliz tili & IT",
                    "desc": "Til va Kompyuter savodxonligi.",
                    "prompt": "4-sinf o'quvchisiga ingliz tili va kompyuter texnologiyalarini o'rgat."
                }
            }

            current = prompts[mode_choice]
            
            # Ekranga chiroyli ma'lumot chiqarish
            st.success(f"📌 **Rejim:** {current['role']} | ℹ️ **Tavsif:** {current['desc']}")

            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Tozalash tugmasi
            if st.sidebar.button("Tozalash"):
                st.session_state.messages = []
                st.rerun()

            # Chatni chiqarish
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Input
            if prompt := st.chat_input("Savolingizni yozing..."):
                add_log(st.session_state.username, f"Chat ({mode_choice}): {prompt[:15]}...")
                
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    engine = ZukkoEngine()
                    placeholder = st.empty()
                    full_text = ""
                    stream = engine.generate(st.session_state.messages, current['prompt'])
                    
                    if isinstance(stream, str):
                        st.error(stream)
                    else:
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_text += chunk.choices[0].delta.content
                                placeholder.markdown(full_text + "▌")
                        placeholder.markdown(full_text)
                
                st.session_state.messages.append({"role": "assistant", "content": full_text})

if __name__ == "__main__":
    main()