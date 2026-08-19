import os
import json
import requests
from playwright.sync_api import sync_playwright

# --- CONFIG & SECRETS FROM GITHUB ---
URL_LOGIN = os.environ.get("URL_LOGIN", "https://devicelocator.bri.co.id/")
URL_MONITORING = os.environ.get("URL_MONITORING", "https://devicelocator.bri.co.id/home.php?dev=cari_atm&title=Cari%20ATM")

PORTAL_USER = os.environ.get("PORTAL_USER")
PORTAL_PASS = os.environ.get("PORTAL_PASS")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SESSION_DATA_RAW = os.environ.get("SESSION_DATA")

# Daftar TID ATM yang dipantau (Tambahkan TID lain di dalam array jika ada, contoh: ["440409", "123456"])
TID_LIST = ["440409"]

def send_telegram_msg(message):
    """Mengirim notifikasi ke Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram token/chat_id belum dikonfigurasi.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("📩 Pesan berhasil dikirim ke Telegram.")
        else:
            print(f"⚠️ Respon Telegram error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Gagal mengirim Telegram: {e}")

def auto_relogin(page):
    """Melakukan login ulang otomatis jika sesi expired"""
    print("🔄 Melakukan Auto-Relogin ke portal Device Locator...")
    page.goto(URL_LOGIN)
    page.wait_for_load_state("networkidle")

    # Mengisi form login
    page.fill("input[name='username']", PORTAL_USER)
    page.fill("input[name='password']", PORTAL_PASS)
    page.click("button[type='submit'], input[type='submit']")
    page.wait_for_load_state("networkidle")
    print("✅ Auto-Relogin berhasil!")

def scrape_atm_detail(page, tid):
    """Membaca seluruh isi template detail ATM & kirim pesan lengkap jika ada problem"""
    print(f"🔍 Memeriksa status TID: {tid}...")
    page.goto(URL_MONITORING)
    page.wait_for_load_state("networkidle")

    # 1. Input TID & Cari
    page.fill("input[name='keyword']", tid)
    page.click("input[value='Search'], button:has-text('Search')")
    page.wait_for_load_state("networkidle")

    # 2. Klik Detail
    detail_button = page.query_selector("input[value='Detail'], button:has-text('Detail')")
    if not detail_button:
        print(f"⚠️ TID {tid} tidak ditemukan dalam daftar.")
        return

    detail_button.click()
    page.wait_for_load_state("networkidle")

    # 3. Parsing Seluruh Data Sesuai Template Web
    page_text = page.inner_text("body")

    def get_val(label):
        for line in page_text.split("\n"):
            if line.strip().startswith(label):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return "-"

    # Ambil seluruh baris data persis seperti di web
    status       = get_val("Status")
    update       = get_val("Update")
    tid_val      = get_val("TID") if get_val("TID") != "-" else tid
    kanwil       = get_val("Kanwil")
    lokasi       = get_val("Lokasi")
    pengelola    = get_val("Pengelola")
    supervisi    = get_val("Supervisi")
    pet_it       = get_val("Pet IT")
    mesin        = get_val("Mesin")
    denom        = get_val("Denom")
    ip           = get_val("IP")
    db           = get_val("DB")
    host         = get_val("Host")
    port         = get_val("Port")
    last_com     = get_val("Last COM")
    com          = get_val("COM")
    oos          = get_val("OOS")
    ccr          = get_val("CCR")
    epp          = get_val("EPP")
    prt          = get_val("PRT")
    spv          = get_val("SPV")
    cl           = get_val("CL")
    co           = get_val("CO")
    df           = get_val("DF")
    trx_tunai    = get_val("Trx Tunai")
    lembar_keluar= get_val("Lembar Keluar")
    kaset1       = get_val("Kaset 1")
    kaset2       = get_val("Kaset 2")
    kaset3       = get_val("Kaset 3")
    kaset4       = get_val("Kaset 4")
    lembar1      = get_val("Lembar 1")
    lembar2      = get_val("Lembar 2")
    lembar3      = get_val("Lembar 3")
    lembar4      = get_val("Lembar 4")
    remark       = get_val("Remark")

    # 4. Deteksi Apakah Ada Problem/Kendala
    all_statuses = [com, oos, ccr, epp, prt, spv, cl, co, df, kaset1, kaset2, kaset3, kaset4]
    
    # Kriteria Problem: Ada sensor yang nilainya FAIL/Bukan OK/Bukan '-', ATAU Status utama bukan NORMAL/OK
    is_problem = any(s not in ["OK", "-"] for s in all_statuses) or status not in ["NORMAL", "OK"]

    # 5. Kirim Notifikasi LENGKAP jika Terdeteksi Problem
    if is_problem:
        print(f"🚨 PROBLEM TERDETEKSI pada TID {tid}! Mengirim template lengkap ke Telegram...")

        # Membuat Template Lengkap Persis Seperti Tampilan Web
        pesan = (
            f"⚠️ <b>[ NOTIFIKASI PROBLEM ATM ]</b>\n\n"
            f"<b>Status :</b> {status}\n"
            f"<b>Update :</b> {update}\n"
            f"<b>TID :</b> {tid_val}\n"
            f"<b>Kanwil :</b> {kanwil}\n"
            f"<b>Lokasi :</b> {lokasi}\n"
            f"<b>Pengelola :</b> {pengelola}\n"
            f"<b>Supervisi :</b> {supervisi}\n"
            f"<b>Pet IT :</b> {pet_it}\n"
            f"<b>Mesin :</b> {mesin}\n"
            f"<b>Denom :</b> {denom}\n"
            f"<b>IP :</b> {ip}\n"
            f"<b>DB :</b> {db}\n"
            f"<b>Host :</b> {host}\n"
            f"<b>Port :</b> {port}\n"
            f"<b>Last COM :</b> {last_com}\n"
            f"<b>COM :</b> {com}\n"
            f"<b>OOS :</b> {oos}\n"
            f"<b>CCR :</b> {ccr}\n"
            f"<b>EPP :</b> {epp}\n"
            f"<b>PRT :</b> {prt}\n"
            f"<b>SPV :</b> {spv}\n"
            f"<b>CL :</b> {cl}\n"
            f"<b>CO :</b> {co}\n"
            f"<b>DF :</b> {df}\n"
            f"<b>Trx Tunai :</b> {trx_tunai}\n"
            f"<b>Lembar Keluar :</b> {lembar_keluar}\n"
            f"<b>Kaset 1 :</b> {kaset1}\n"
            f"<b>Kaset 2 :</b> {kaset2}\n"
            f"<b>Kaset 3 :</b> {kaset3}\n"
            f"<b>Kaset 4 :</b> {kaset4}\n"
            f"<b>Lembar 1 :</b> {lembar1}\n"
            f"<b>Lembar 2 :</b> {lembar2}\n"
            f"<b>Lembar 3 :</b> {lembar3}\n"
            f"<b>Lembar 4 :</b> {lembar4}\n"
            f"<b>Remark :</b> {remark}"
        )

        send_telegram_msg(pesan)
    else:
        print(f"✅ TID {tid} dalam keadaan NORMAL. Tidak ada pesan dikirim ke Telegram.")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # Load Sesi Cookie dari GitHub Secret jika ada
        if SESSION_DATA_RAW:
            try:
                cookies = json.loads(SESSION_DATA_RAW)
                context.add_cookies(cookies)
                print("🔑 Sesi cookie berhasil dimuat.")
            except Exception as e:
                print(f"⚠️ Gagal memuat cookie: {e}")

        page = context.new_page()

        try:
            page.goto(URL_MONITORING)
            page.wait_for_load_state("networkidle")

            # Cek Sesi Expired
            if "login" in page.url.lower() or "session" in page.content().lower():
                print("⚠️ Sesi EXPIRED terdeteksi!")
                if PORTAL_USER and PORTAL_PASS:
                    auto_relogin(page)
                else:
                    send_telegram_msg("⚠️ <b>SESSION DEVICE LOCATOR EXPIRED!</b>\nSilakan perbarui Secret di GitHub.")
                    return

            # Cek Setiap TID
            for tid in TID_LIST:
                scrape_atm_detail(page, tid)

        except Exception as e:
            print(f"❌ Terjadi kesalahan execution: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
