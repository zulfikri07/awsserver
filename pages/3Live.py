import streamlit as st
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import threading
import time
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh



# ==================== KONFIGURASI MQTT ====================
MQTT_BROKER = "mqtt-dashboard.com"
MQTT_PORT = 1883
MQTT_TOPIC = "AWS@port"

st.set_page_config(page_title="Data_Live", layout="wide")

# 🔁 Tambahkan auto-refresh setiap 5 menit (300.000 ms)
st_autorefresh(interval=300000, key="auto_refresh_5min")

st.title("LIVE DATA MONITORING AWS")
st.caption(f"Topik MQTT: {MQTT_TOPIC}")
st.sidebar.image("pages/logommi.jpeg")

# Tombol manual refresh
if st.button("🔄 Perbarui Data"):
    st.rerun()

placeholder = st.empty()

# ==================== GOOGLE SHEET ====================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
credentials_dict = dict(st.secrets["gcp_service_account"])
credentials_dict["private_key"] = credentials_dict["private_key"].replace("\\n", "\n")
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
sheet_client = gspread.authorize(creds)
spreadsheet = sheet_client.open("server")
sheet = spreadsheet.sheet1

# ==================== GLOBAL VARIABEL ====================
mqtt_data = {"message": "Menunggu data..."}
last_saved_time = 0  # Epoch time

# ==================== PARSE DATA MQTT ====================
def parse_sensor_data(text):
    try:
        data = {}
        time_match = re.search(r'(\d{2}:\d{2}:\d{2}) (\d{2}-\d{2}-\d{4})', text)
        if time_match:
            data["waktu"] = time_match.group(1)
            data["tanggal"] = time_match.group(2)
        data["temp"] = float(re.search(r"Temp\s*=\s*([\d.]+)", text).group(1))
        data["kelembaban"] = int(re.search(r"Kelembaban\s*=\s*(\d+)", text).group(1))
        data["w_speed"] = float(re.search(r"W\.Speed\s*=\s*([\d.]+)", text).group(1))
        data["w_dir"] = int(re.search(r"W\.Dir\s*=\s*(\d+)", text).group(1))
        data["press"] = float(re.search(r"Press\s*=\s*([\d.]+)", text).group(1))
        data["hujan"] = float(re.search(r"Hujan\s*=\s*([\d.]+)", text).group(1))
        data["rad"] = float(re.search(r"Rad\s*=\s*([\d.]+)", text).group(1))
        data["signal"] = int(re.search(r"Signal\s*=\s*(\d+)", text).group(1))
        return data
    except Exception as e:
        return {"error": str(e)}

# ==================== SIMPAN KE GOOGLE SHEET ====================
def save_to_google_sheet(data):
    global last_saved_row, last_saved_date, last_saved_time
    try:
        current_date = data.get("tanggal")

        # Reset hujan saat ganti hari
        if last_saved_date != current_date:
            last_saved_date = current_date
            data["hujan"] = 0.0  # Set hujan ke 0 jika hari berganti

        # Format baris data
        current_row = [
            str(data.get("tanggal")).strip(), str(data.get("waktu")).strip(),
            f"{data.get('temp'):.1f}", str(data.get("kelembaban")),
            f"{data.get('w_speed'):.1f}", str(data.get("w_dir")),
            f"{data.get('press'):.1f}", f"{data.get('hujan'):.1f}",
            f"{data.get('rad'):.1f}", str(data.get("signal"))
        ]

        now = time.time()
        elapsed = now - last_saved_time

        # Simpan jika data berbeda dari sebelumnya atau sudah lebih dari 60 detik
        if current_row != last_saved_row and elapsed > 60:
            sheet.append_row(current_row)
            last_saved_row = current_row
            last_saved_time = now
        else:
            print("⛔ Duplikat atau terlalu cepat, tidak disimpan")

    except Exception as e:
        print(f"Gagal menyimpan ke Google Sheet: {e}")


# ==================== STYLE ====================
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

# Ambil baris terakhir dari Google Sheet
def get_latest_row():
    rows = sheet.get_all_values()
    if len(rows) > 1:
        return rows[-1]
    return None

# Simpan baris terakhir di session_state agar bisa dibandingkan
if "last_row" not in st.session_state:
    st.session_state["last_row"] = None

# Ambil data baru
latest_row = get_latest_row()

# Jika data berubah, tampilkan
if latest_row and latest_row != st.session_state["last_row"]:
    st.session_state["last_row"] = latest_row  # update session

    # Parsing data
    latest_data = {
        "tanggal": latest_row[0],
        "waktu": latest_row[1],
        "temp": float(latest_row[2]),
        "kelembaban": int(latest_row[3]),
        "w_speed": float(latest_row[4]),
        "w_dir": int(latest_row[5]),
        "press": float(latest_row[6]),
        "hujan": float(latest_row[7]),
        "rad": float(latest_row[8]),
        "signal": int(latest_row[9]),
    }

    # ===================== TAMPILKAN DATA =====================
    with placeholder.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(display_card("Waktu", latest_data["waktu"], "", "🕒"), unsafe_allow_html=True)
        with col2:
            st.markdown(display_card("Tanggal", latest_data["tanggal"], "", "📅"), unsafe_allow_html=True)
        with col3:
            st.markdown(display_card("Signal", latest_data["signal"], "", "📶"), unsafe_allow_html=True)

        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(display_card("Suhu", latest_data["temp"], "°C", "🌡️"), unsafe_allow_html=True)
        with col2:
            st.markdown(display_card("Kelembaban", latest_data["kelembaban"], "%", "💧"), unsafe_allow_html=True)
        with col3:
            st.markdown(display_card("Curah Hujan", latest_data["hujan"], "mm", "🌧️"), unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(display_card("Kecepatan Angin", latest_data["w_speed"], "m/s", "💨"), unsafe_allow_html=True)
        with col2:
            st.markdown(display_card("Arah Angin", latest_data["w_dir"], "°", "🧭"), unsafe_allow_html=True)
        with col3:
            st.markdown(display_card("Tekanan", latest_data["press"], "hPa", "📈"), unsafe_allow_html=True)

        col1, _, col3 = st.columns([1, 1, 1])
        with col1:
            st.markdown(display_card("Radiasi", latest_data["rad"], "W/m²", "☀️"), unsafe_allow_html=True)

    st.caption(f"⏱️ Terakhir diperbarui: {latest_data['tanggal']} {latest_data['waktu']}")

else:
    st.info("📌 Belum ada data baru dari Google Sheet. Tekan tombol di atas untuk memperbarui.")
