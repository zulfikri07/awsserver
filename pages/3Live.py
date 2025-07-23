import streamlit as st
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from streamlit_autorefresh import st_autorefresh

# ==================== KONFIGURASI ====================
st.set_page_config(page_title="Dashboard AWS", layout="wide")

# Auto-refresh setiap 5 menit
st_autorefresh(interval=300000, key="auto_refresh_5min")

st.title("LIVE DATA MONITORING AWS")
st.sidebar.image("pages/logommi.jpeg")

# Tombol manual refresh
if st.button("🔄 Perbarui Data"):
    st.rerun()

# ==================== KONEKSI GOOGLE SHEET ====================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials_dict = dict(st.secrets["gcp_service_account"])
credentials_dict["private_key"] = credentials_dict["private_key"].replace("\\n", "\n")
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("servernew").sheet1

# ==================== BACA DATA TERAKHIR ====================
rows = sheet.get_all_values()
header, data = rows[0], rows[1:]
df = pd.DataFrame(data, columns=header)
latest = df.iloc[-1]

# ==================== GAYA ====================
st.markdown("""
    <style>
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 10px;
            text-align: center;
        }
        .label {
            font-size: 16px;
            color: #666;
        }
        .value {
            font-size: 28px;
            font-weight: bold;
            color: #111;
        }
    </style>
""", unsafe_allow_html=True)

def display_card(title, value, satuan="", icon=""):
    return f"""
        <div class="card">
            <div class="label">{icon} {title}</div>
            <div class="value">{value} {satuan}</div>
        </div>
    """

# ==================== TAMPILKAN ====================
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(display_card("Tanggal", latest["Tanggal"], "", "📅"), unsafe_allow_html=True)
with col2:
    st.markdown(display_card("Waktu", latest["Waktu"], "", "🕒"), unsafe_allow_html=True)
with col3:
    st.markdown(display_card("Signal", latest["Signal"], "", "📶"), unsafe_allow_html=True)

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(display_card("Suhu", latest["Suhu"], "°C", "🌡️"), unsafe_allow_html=True)
with col2:
    st.markdown(display_card("Kelembapan", latest["Kelembapan"], "%", "💧"), unsafe_allow_html=True)
with col3:
    st.markdown(display_card("Curah Hujan", latest["Hujan"], "mm", "🌧️"), unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(display_card("Kecepatan Angin", latest["W_Speed"], "m/s", "💨"), unsafe_allow_html=True)
with col2:
    st.markdown(display_card("Arah Angin", latest["W_Dir"], "°", "🧭"), unsafe_allow_html=True)
with col3:
    st.markdown(display_card("Tekanan", latest["Tekanan"], "hPa", "📈"), unsafe_allow_html=True)

col1, _, col3 = st.columns([1, 1, 1])
with col1:
    st.markdown(display_card("Radiasi", latest["Rad"], "W/m²", "☀️"), unsafe_allow_html=True)

st.caption(f"⏱️ Terakhir diperbarui: {latest['Tanggal']} {latest['Waktu']}")
