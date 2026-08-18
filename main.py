import os
import json
import requests
from playwright.sync_api import sync_playwright

# 1. Konfigurasi Environment & Secrets
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SESSION_DATA = os.getenv("SESSION_DATA")

STATUS_FILE = "last_status.json"
SESSION_FILE = "session.json"

def send_telegram(message):
    """Fungsi mengirim notifikasi ke Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration is missing.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def main():
    # Buat file session.json dari Secret jika file belum ada
    if SESSION_DATA and not os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "w") as f:
            f.write(SESSION_DATA)

    if not os.path.exists(SESSION_FILE):
        send_telegram("⚠️ <b>SESSION DEVICE LOCATOR EXPIRED!</b>\nSilakan perbarui secret SESSION_DATA di GitHub.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        try:
            # Muat sesi login dari file session.json
            context = browser.new_context(storage_state=SESSION_FILE)
            page = context.new_page()

            # Buka portal Device Locator
            page.goto("https://devicelocator.bri.co.id/", wait_until="networkidle", timeout=60000)

            # Cek apakah terlempar ke halaman login (sesi kedaluwarsa)
            if "login" in page.url.lower():
                print("Session expired.")
                send_telegram("⚠️ <b>SESSION DEVICE LOCATOR EXPIRED!</b>\nSilakan perbarui secret SESSION_DATA di GitHub.")
                browser.close()
                return

            print("Sesi valid! Berhasil masuk ke portal.")

            # --- PROSES PEMANTAUAN ATM DI SINI ---
            # Skrip membaca data status ATM...
            
            # -------------------------------------

            # OTOMATISASI: Simpan state cookie/sesi terbaru agar tidak expired
            context.storage_state(path=SESSION_FILE)
            print("Sesi terbaru berhasil diperbarui dan disimpan ke session.json.")

        except Exception as e:
            print(f"Error during execution: {e}")
            send_telegram(f"⚠️ <b>TERJADI ERROR SKRIP:</b>\n<code>{e}</code>")
        
        finally:
            browser.close()

if __name__ == "__main__":
    main()
