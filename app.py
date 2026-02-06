import streamlit as st
import io
import random
import requests
import time
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
# 🎵 OVOZ FUNKSIYASI
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

# ==========================================
# 🎨 RASSOM FUNKSIYASI
# ==========================================
def generate_image(prompt):
    final_prompt = prompt.replace(" ", "%20")
    seed = random.randint(1, 10000)
    url = f"https://image.pollinations.ai/prompt/{final_prompt}?nospam={seed}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            return None
    except:
        return None

# ==========================================
# 🧠 AI ENGINE
# ==========================================
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
# 🎨 DIZAYN (CSS)
# ==========================================
st.markdown("""
<style>
    .metric-card {
        background-color: rgba(128, 128, 128, 0.1);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        text-align: center;
        margin-bottom: 10px;
    }
    .stChatMessage {
        background-color: transparent;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    div[data-testid="stChatMessage"][data-author="user"] {
        background-color: rgba(76, 175, 80, 0.1);
    }
    div[data-testid="stChatMessage"][data-author="assistant"] {
        background-color: rgba(33, 150, 243, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🏠 DASHBOARD
# ==========================================
def show_dashboard(username):
    st.header(f"👋 Xush kelibsiz, {username.title()}!")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><h3>📅 Sana</h3><h2>{datetime.datetime.now().strftime("%d-%m-%Y")}</h2></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="metric-card"><h3>⚡ Status</h3><h2>Online</h2></div>""", unsafe_allow_html=True)
    with col3:
        role_display = "Admin 🛡️" if st.session_state.role == "admin" else "O'quvchi 🎓"
        st.markdown(f"""<div class="metric-card"><h3>🏆 Rolingiz</h3><h2>{role_display}</h2></div>""", unsafe_allow_html=True)

# ==========================================
# 🖥️ ASOSIY DASTUR
# ==========================================

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    if not st.session_state.logged_in:
        st.title("🎓 Zukko AI Kirish")
        tab1, tab2 = st.tabs(["Kirish", "Ro'yxatdan o'tish"])
        with tab1:
            username = st.text_input("Login", key="login_user")
            password = st.text_input("Parol", type='password', key="login_pass")
            if st.button("Kirish"):
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
            if st.button("Yaratish"):
                if add_user(new_user, new_pass):
                    st.success("Yaratildi!")
                    add_log(new_user, "Ro'yxatdan o'tdi")
                else:
                    st.error("Login band!")

    else:
        with st.sidebar:
            st.title("Zukko AI")
            st.caption(f"Foydalanuvchi: {st.session_state.username}")
            page = st.radio("Bo'limlar:", ["🏠 Dashboard", "🤖 AI Chat", "🎨 AI Rassom", "🛡️ Admin Panel"])
            st.markdown("---")
            if st.button("Chiqish 🚪"):
                st.session_state.logged_in = False
                st.rerun()

        if page == "🏠 Dashboard":
            show_dashboard(st.session_state.username)

        elif page == "🛡️ Admin Panel":
            if st.session_state.role == "admin":
                st.header("🛡️ Admin Panel")
                st.dataframe(view_all_users(), use_container_width=True)
                st.dataframe(view_logs(), use_container_width=True)
            else:
                st.error("⛔ Siz Admin emassiz!")

        elif page == "🎨 AI Rassom":
            st.header("🎨 AI Rassom")
            st.info("Istalgan narsani yozing, sun'iy intellekt chizib beradi.")
            img_prompt = st.text_input("Nima chizamiz?", placeholder="Masalan: Future city, Flying cat...")
            if st.button("Chizish 🖌️"):
                if img_prompt:
                    with st.spinner("Rasm chizilmoqda..."):
                        image_data = generate_image(img_prompt)
                        if image_data:
                            st.image(image_data, caption=f"Natija: {img_prompt}", use_container_width=True)
                            add_log(st.session_state.username, f"Rasm chizdi: {img_prompt}")
                            st.balloons()
                        else:
                            st.error("Xatolik bo'ldi.")
                else:
                    st.warning("Yozishni unutmang!")

        # ==========================================
        # 🤖 YANGILANGAN AI CHAT (FANLAR BILAN)
        # ==========================================
        elif page == "🤖 AI Chat":
            st.subheader("🤖 AI bilan dars")
            
            # 1. SINF VA FANNI TANLASH
            col_sel1, col_sel2 = st.columns(2)
            
            with col_sel1:
                sinf = st.selectbox("Sinfni tanlang:", ["🌐 Universal Yordamchi", "1-sinf", "2-sinf", "3-sinf", "4-sinf"])
            
            with col_sel2:
                # Agar Universal bo'lmasa, Fanni tanlaydi
                if sinf != "🌐 Universal Yordamchi":
                    fan = st.selectbox("Fanni tanlang:", 
                        ["Matematika", "Ona tili", "Ingliz tili", "IT (Kompyuter)", "Fizika (Boshlang'ich)", "Biologiya (Tabiat)"])
                else:
                    fan = "Umumiy"

            # 2. PROMPTNI SOZLASH (Miya)
            if sinf == "🌐 Universal Yordamchi":
                system_prompt = "Sen Zukko AIsan. O'zbekistondagi eng aqlli yordamchisan. Istalgan mavzuda aniq va lo'nda javob ber."
                welcome_msg = "Salom! Men sizning universal yordamchingizman. Nima haqida gaplashamiz?"
            else:
                # Fanlarga mos promptlar
                subjects_logic = {
                    "Matematika": "Sen matematika o'qituvchisisan. Bolalarga misollarni, karra jadvalini va mantiqiy masalalarni qiziqarli tushuntir.",
                    "Ona tili": "Sen ona tili o'qituvchisisan. Alifbo, to'g'ri yozish qoidalari va chiroyli so'zlashishni o'rgat.",
                    "Ingliz tili": "Sen ingliz tili o'qituvchisisan. Bolalarga yangi so'zlarni o'rgat va ular bilan oddiy inglizcha dialog qur.",
                    "IT (Kompyuter)": "Sen IT o'qituvchisisan. Kompyuter qanday ishlashini, xavfsizlikni va dasturlashni sodda tilda tushuntir.",
                    "Fizika (Boshlang'ich)": "Sen bolalar uchun fizika o'qituvchisisan. Murakkab formulalar emas, tabiat hodisalarini (nega yomg'ir yog'adi, nega koptok tushadi) oddiy tushuntir.",
                    "Biologiya (Tabiat)": "Sen tabiatshunoslik o'qituvchisisan. Hayvonlar, o'simliklar va inson tanasi haqida qiziqarli faktlar aytib ber."
                }
                
                base_prompt = subjects_logic.get(fan, "Sen o'qituvchisan.")
                system_prompt = f"Sen {sinf} o'quvchilari uchun {fan} fanidan dars o'tmoqdasan. {base_prompt} Javoblaringda ko'p emoji ishlat va bolalar tilida sodda gapir."
                welcome_msg = f"Salom! Men {sinf} uchun {fan} o'qituvchisiman. Darsni boshlaymizmi?"

            st.info(f"💡 **Rejim:** {sinf} | **Fan:** {fan}")

            # 3. CHAT TARIXI
            if "messages" not in st.session_state: st.session_state.messages = []
            
            # Tozalash va Test
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("🗑️ Doskani tozalash"):
                    st.session_state.messages = []
                    # Birinchi salomni qo'shamiz
                    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                    st.rerun()
            with c2:
                if st.button("📝 Test tuzish"):
                    st.session_state.messages.append({"role": "user", "content": f"{fan} fanidan mavzuga oid 3 ta test tuzib ber (A,B,C variantlari bilan)."})

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

            # 4. INPUT
            if prompt := st.chat_input("Savol bering yoki javob yozing..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)

                with st.chat_message("assistant"):
                    engine = ZukkoEngine()
                    placeholder = st.empty()
                    full_text = ""
                    stream = engine.generate(st.session_state.messages, system_prompt)
                    
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