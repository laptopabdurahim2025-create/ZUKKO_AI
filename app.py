import streamlit as st
import io

# ⚠️ Streamlit Secrets dan API keyni olish
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("GROQ_API_KEY topilmadi! .streamlit/secrets.toml faylini tekshiring.")
    st.stop()

# ==========================================
# ➕ YANGI KUTUBXONALAR (QO'SHILDI)
# ==========================================
from openai import OpenAI
import sqlite3
import hashlib
import datetime
import pandas as pd
import time
from PyPDF2 import PdfReader # PDF o'qish uchun
from gtts import gTTS # Ovozga aylantirish uchun

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
add_user("admin", "admin123", "admin") 

# ==========================================
# ➕ YANGI YORDAMCHI FUNKSIYALAR (QO'SHILDI)
# ==========================================

def get_pdf_text(pdf_file):
    """PDF fayldan matnni sug'urib olish"""
    text = ""
    pdf_reader = PdfReader(pdf_file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def text_to_audio(text):
    """Matnni ovozli faylga aylantirish (gTTS)"""
    # gTTS o'zbek tilini 'tr' (turkcha) intonatsiyasiga yaqin o'qiydi yoki 'en'
    try:
        tts = gTTS(text=text, lang='tr', slow=False) 
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
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

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
    /* Quiz tugmasi uchun */
    .stButton>button {
        background-color: #4CAF50; 
        color: white; 
        font-weight: bold;
    }
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
            
            if st.session_state.role == "admin":
                app_mode = st.radio("Rejim:", ["🤖 AI Chat", "🛡️ Admin Panel"])
            else:
                app_mode = "🤖 AI Chat"

            st.markdown("---")
            
            # ➕ PDF YUKLASH QISMI (QO'SHILDI)
            st.markdown("### 📂 Kitob Yuklash (PDF)")
            uploaded_file = st.file_uploader("Darslikni yuklang", type="pdf")
            pdf_text = ""
            if uploaded_file is not None:
                with st.spinner("PDF o'qilmoqda..."):
                    pdf_text = get_pdf_text(uploaded_file)
                st.success("Kitob yuklandi! Endi shu bo'yicha savol bering.")

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
            mode_choice = st.selectbox("Mavzuni tanlang:", 
                ["🌐 Universal Yordamchi", "1-sinf", "2-sinf", "3-sinf", "4-sinf"]
            )
            
            prompts = {
                "🌐 Universal Yordamchi": {
                    "role": "Super Intellekt",
                    "desc": "Istalgan mavzuda suhbat...",
                    "prompt": "Sen Zukko AIsan. Foydalanuvchi nima haqida so'rasa aniq javob ber."
                },
                "1-sinf": {
                    "role": "Boshlang'ich O'qituvchi",
                    "desc": "Alifbo va o'qish.",
                    "prompt": "Sen mehribon o'qituvchisan. 1-sinf bolasiga sodda tushuntir. Ko'p emoji ishlat."
                },
                "2-sinf": {
                    "role": "Matematika Ustoz",
                    "desc": "Qo'shish, ayirish, karra.",
                    "prompt": "Sen matematika o'qituvchisisan. Hisob-kitobni qiziqarli o'rgat."
                },
                "3-sinf": {
                    "role": "Tabiatshunos",
                    "desc": "Hayvonlar va Olam.",
                    "prompt": "Tabiatshunoslik o'qituvchisi sifatida dunyo sirlarini ochib ber."
                },
                "4-sinf": {
                    "role": "Ingliz tili & IT",
                    "desc": "Til va Kompyuter.",
                    "prompt": "4-sinf o'quvchisiga ingliz tili va kompyuterni o'rgat."
                }
            }

            current = prompts[mode_choice]
            
            # ➕ PDF TEXTNI PROMPTGA QO'SHISH
            final_system_prompt = current['prompt']
            if pdf_text:
                final_system_prompt += f"\n\nDIQQAT: Foydalanuvchi quyidagi kitobni yukladi. Javob berishda mana shu ma'lumotdan foydalan:\n{pdf_text[:4000]}..." 
            
            st.success(f"📌 **Rejim:** {current['role']} | ℹ️ **Tavsif:** {current['desc']}")

            if "messages" not in st.session_state:
                st.session_state.messages = []

            # ➕ QUIZ (TEST) TUGMASI (QO'SHILDI)
            col_q1, col_q2 = st.columns([1, 4])
            with col_q1:
                if st.button("📝 Test tuzish"):
                    prompt = "Menga hozirgi mavzu yoki umumiy bilim bo'yicha 3 ta qiziqarli test tuzib ber (A, B, C variantlari bilan)."
                    st.session_state.messages.append({"role": "user", "content": prompt})
            with col_q2:
                if st.sidebar.button("Tozalash"):
                    st.session_state.messages = []
                    st.rerun()

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if prompt := st.chat_input("Savolingizni yozing..."):
                add_log(st.session_state.username, f"Chat ({mode_choice}): {prompt[:15]}...")
                
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    engine = ZukkoEngine()
                    placeholder = st.empty()
                    full_text = ""
                    stream = engine.generate(st.session_state.messages, final_system_prompt)
                    
                    if isinstance(stream, str):
                        st.error(stream)
                    else:
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_text += chunk.choices[0].delta.content
                                placeholder.markdown(full_text + "▌")
                        placeholder.markdown(full_text)
                        
                        # ➕ OVOZLI REJIM (TTS) QO'SHILDI
                        # Javob to'liq bo'lgach, ovoz chiqarish tugmasi chiqadi
                        audio_data = text_to_audio(full_text)
                        if audio_data:
                            st.audio(audio_data, format="audio/mp3")

                
                st.session_state.messages.append({"role": "assistant", "content": full_text})

if __name__ == "__main__":
    main()