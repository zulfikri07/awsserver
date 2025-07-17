import streamlit as st

# Konfigurasi halaman
st.set_page_config(page_title="Login App", layout="centered")

# Simulasi database user (username: password)
USER_CREDENTIALS = {
    "admin": "admin123",
    "user1": "password1",
    "zulfikri": "rahasia"
}

# Fungsi untuk proses login
def login(username, password):
    if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
        return True
    else:
        return False

# UI Login
st.title("Login Page")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if login(username, password):
        st.success(f"Selamat datang, {username}!")
        st.session_state["login_success"] = True
        st.session_state["user"] = username
    else:
        st.error("Username atau password salah!")

# Jika sudah login, tampilkan konten utama
if st.session_state.get("login_success"):
    st.write("selamat datang")
