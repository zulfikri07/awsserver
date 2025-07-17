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

# ==================== KONFIGURASI MQTT ====================
MQTT_BROKER = "mqtt-dashboard.com"
MQTT_PORT = 1883
MQTT_TOPIC = "AWS@port"

st.set_page_config(page_title="Data_Live", layout="wide")
st.title("LIVE DATA MONITORING AWS")
st.caption(f"Topik MQTT: {MQTT_TOPIC}")
st.sidebar.image("pages/logommi.jpeg")
placeholder = st.empty()


# Setup koneksi Google Sheets
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials_dict = dict(st.secrets["gcp_service_account"])
credentials_dict["private_key"] = credentials_dict["private_key"].replace("\\n", "\n")  # ← ini WAJIB
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
sheet_client = gspread.authorize(creds)


# Buka spreadsheet
spreadsheet = sheet_client.open("server")  # Nama Google Sheet
sheet = spreadsheet.sheet1  # Atau pakai .worksheet("NamaSheet")

# ==================== GLOBAL DATA ====================
mqtt_data = {"message": "Menunggu data..."}
data_cache = set()  # Hindari duplikat

# ==================== PARSE DATA ====================
def parse_sensor_data(text):
    try:
        data = {}
        # Ambil waktu dan tanggal
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
    try:
        current_row = [
            str(data.get("tanggal")), str(data.get("waktu")), str(data.get("temp")),
            str(data.get("kelembaban")), str(data.get("w_speed")), str(data.get("w_dir")),
            str(data.get("press")), str(data.get("hujan")), str(data.get("rad")), str(data.get("signal"))
        ]

        # Ambil semua data dari sheet
        all_rows = sheet.get_all_values()
        if all_rows:
            last_row = all_rows[-1]
            if current_row == last_row:
                return  # ⛔ Duplikat, jangan simpan

        # ✅ Tidak duplikat → simpan ke sheet
        sheet.append_row(current_row)

    except Exception as e:
        print(f"Gagal menyimpan ke Google Sheet: {e}")



# ==================== MQTT CALLBACK ====================
def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    parsed = parse_sensor_data(payload)
    mqtt_data.clear()
    mqtt_data.update(parsed)
    if "error" not in parsed:
        save_to_google_sheet(parsed)

def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_forever()

# ==================== STREAMLIT START ====================
if "mqtt_started" not in st.session_state:
    threading.Thread(target=mqtt_thread, daemon=True).start()
    st.session_state["mqtt_started"] = True


# Tambahkan header jika belum ada (cek kolom pertama)
if len(sheet.row_values(1)) < 10:
    headers = ["Tanggal", "Waktu", "Suhu", "Kelembaban", "W.Speed", "W.Dir", "Tekanan", "Hujan", "Rad", "Signal"]
    sheet.insert_row(headers, 1)

# Tambahkan CSS untuk desain kartu yang menarik
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

while True:
    with placeholder.container():
        if "error" in mqtt_data:
            st.error(f"❌ Parsing Error: {mqtt_data['error']}")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(display_card("Waktu", mqtt_data.get("waktu", "-"), "", "🕒"), unsafe_allow_html=True)
            with col2:
                st.markdown(display_card("Tanggal", mqtt_data.get("tanggal", "-"), "", "📅"), unsafe_allow_html=True)
            with col3:
                st.markdown(display_card("Signal", mqtt_data.get("signal", "-"), "", "📶"), unsafe_allow_html=True)

            st.divider()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(display_card("Suhu", mqtt_data.get("temp", "-"), "°C", "🌡️"), unsafe_allow_html=True)
            with col2:
                st.markdown(display_card("Kelembaban", mqtt_data.get("kelembaban", "-"), "%", "💧"), unsafe_allow_html=True)
            with col3:
                st.markdown(display_card("Curah Hujan", mqtt_data.get("hujan", "-"), "mm", "🌧️"), unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(display_card("Kecepatan Angin", mqtt_data.get("w_speed", "-"), "m/s", "💨"), unsafe_allow_html=True)
            with col2:
                st.markdown(display_card("Arah Angin", mqtt_data.get("w_dir", "-"), "°", "🧭"), unsafe_allow_html=True)
            with col3:
                st.markdown(display_card("Tekanan", mqtt_data.get("press", "-"), "hPa", "📈"), unsafe_allow_html=True)

            col1, _, col3 = st.columns([1,1,1])
            with col1:
                st.markdown(display_card("Radiasi", mqtt_data.get("rad", "-"), "W/m²", "☀️"), unsafe_allow_html=True)
    time.sleep(1)

