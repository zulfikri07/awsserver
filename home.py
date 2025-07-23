import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import pydeck as pdk
from streamlit_option_menu import option_menu
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import pytz
import time
from io import BytesIO
import altair as alt
import locale
import json
from streamlit_gsheets import GSheetsConnection

# Konfigurasi Streamlit
st.set_page_config(page_title="AWS 2025", layout="wide",)

st.title ( "AUTOMATIC WEATHER STATION ( AWS ) 2025" )
st.sidebar.image("pages/logommi.jpeg")
# Data
df = pd.DataFrame({
    'lat': [-6.275762],
    'lon': [106.7760],
    'label': ['Lokasi Stasiun AWS (lat : -6.275762, '
    'lon : 106.7760)']
})

# Tambah kolom posisi & icon
df["icon_data"] = [{
    "url": "https://img.icons8.com/emoji/48/228B22/green-circle-emoji.png",  # ikon titik merah
    "width": 15,
    "height": 30,
    "anchorY": 20,
}]

# IconLayer
icon_layer = pdk.Layer(
    type="IconLayer",
    data=df,
    get_icon="icon_data",
    get_size=4,
    size_scale=7,
    get_position='[lon, lat]',
    pickable=True
)

# ViewState tetap seluruh Indonesia
view_state = pdk.ViewState(
    latitude=-2.5,
    longitude=118,
    zoom=4,
    pitch=0
)

# Render Peta
r = pdk.Deck(
    layers=[icon_layer],
    initial_view_state=view_state,
    tooltip={"text": "{label}"}
)

st.pydeck_chart(r)



st.title ("Visualisasi Grafik Parameter Sensor")

# Setup koneksi Google Sheets
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials_dict = dict(st.secrets["gcp_service_account"])
credentials_dict["private_key"] = credentials_dict["private_key"].replace("\\n", "\n")  # ← ini WAJIB
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)

# Ambil data dari sheet
sheet = client.open("servernew").sheet1
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Konversi kolom angka desimal dari string dengan koma menjadi float
kolom_angka = ['Suhu', 'Kelembapan', 'W_Speed', 'W_Dir','Tekanan', 'Rad', 'Signal']  # Sesuaikan nama kolom

for kolom in kolom_angka:
    if kolom in df.columns:
        df[kolom] = df[kolom].astype(str).str.replace(',', '.', regex=False).astype(float)


# Gabungkan Tanggal dan Waktu jadi satu kolom datetime (jika perlu)
df['Datetime'] = pd.to_datetime(df['Tanggal'] + ' ' + df['Waktu'], format="%d-%m-%Y %H:%M:%S")

# Contoh: Pastikan kolom tanggal dan waktu digabung
df['Tanggal'] = df['Tanggal'].astype(str)
df['Waktu'] = df['Waktu'].astype(str)                                                                                           
df['Datetime'] = pd.to_datetime(df['Tanggal'] + ' ' + df['Waktu'], format="%d-%m-%Y %H:%M:%S")

# Pilih parameter
parameter_list = ['Suhu', 'Kelembapan', 'W_Speed', 'W_Dir', 'Tekanan', 'Hujan', 'Rad', 'Signal']
selected = st.multiselect("Pilih Parameter yang Ditampilkan", parameter_list, default=['Suhu'])

# Tampilkan grafik satu per satu
if selected:
    for param in selected:
        st.subheader(f"📊 {param}")
        st.line_chart(df.set_index('Datetime')[param])
else:
    st.warning("Silakan pilih minimal satu parameter.")
    


# Gabungkan Tanggal dan Waktu
df['Tanggal'] = df['Tanggal'].astype(str)
df['Waktu'] = df['Waktu'].astype(str)
df['Datetime'] = pd.to_datetime(df['Tanggal'] + ' ' + df['Waktu'], format="%d-%m-%Y %H:%M:%S")

# --- FILTER TANGGAL ---
st.sidebar.markdown("### 📅 Filter Tanggal")
min_date = df['Datetime'].min().date()
max_date = df['Datetime'].max().date()
start_date = st.sidebar.date_input("Dari", min_date)
end_date = st.sidebar.date_input("Sampai", max_date)

df_filtered = df[(df['Datetime'].dt.date >= start_date) & (df['Datetime'].dt.date <= end_date)]

# --- PILIH PARAMETER ---
parameter_list = ['Suhu', 'Kelembapan', 'W_Speed', 'W_Dir', 'Tekanan', 'Hujan', 'Rad', 'Signal']
selected = st.multiselect("📌 Pilih Parameter", parameter_list, default=['Hujan'])

if selected and not df_filtered.empty:
    for param in selected:
        if param not in df_filtered.columns:
            st.warning(f"Parameter `{param}` tidak tersedia dalam data.")
            continue

        st.subheader(f"📊 Bar Chart: {param} ({start_date} s.d. {end_date})")

        # Ambil 10 data terakhir yang valid
        df_chart = (
            df_filtered[['Datetime', param]]
            .dropna()
            .sort_values(by="Datetime", ascending=False)
            .head(10)
        )

        if df_chart.empty:
            st.info(f"Tidak ada data untuk parameter `{param}` dalam rentang tanggal yang dipilih.")
            continue

        chart = alt.Chart(df_chart).mark_bar().encode(
            x=alt.X('Datetime:T', title='Waktu'),
            y=alt.Y(f'{param}:Q', title=param),
            color=alt.Color(f'{param}:Q', scale=alt.Scale(scheme='tealblues')),
            tooltip=['Datetime', param]
        ).properties(
            width='container',
            height=300
        )

        st.altair_chart(chart, use_container_width=True)
elif not selected:
    st.info("Silakan pilih minimal satu parameter.")
elif df_filtered.empty:
    st.warning("Data kosong untuk rentang tanggal yang dipilih.")


# === DOWNLOAD EXCEL DATA FILTERED ===
if selected and not df_filtered.empty:
    export_cols = ['Datetime'] + selected
    df_export = df_filtered[export_cols].copy()

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name="Data Filtered")
    buffer.seek(0)

    st.download_button(
        label="📥 Download Data (Excel)",
        data=buffer,
        file_name="data_sensor_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )