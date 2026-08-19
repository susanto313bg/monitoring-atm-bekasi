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

# Keyword Pencarian Otomatis Seluruh Kelolaan BG Bekasi
KEYWORD_PENGELOLA = "BG BEKASI"

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
            print("📩 Notifikasi problem berhasil dikirim ke Telegram.")
        else:
            print(f"⚠️ Respon Telegram error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Gagal mengirim Telegram: {e}")

def auto_relogin(page):
    """Melakukan login ulang otomatis ke portal Device Locator"""
    print("🔄 Sesi kedaluwarsa. Mencoba Auto-Relogin...")
    if not PORTAL_USER or not PORTAL_PASS:
        print("❌ PORTAL_USER atau PORTAL_PASS tidak ditemukan di Secrets GitHub!")
        return False

    try:
        page.goto(URL_LOGIN, timeout=30000)
        page.wait_for_load_state("networkidle")

        page.fill("input[name='username']", PORTAL_USER)
        page.fill("input[name='password']", PORTAL_PASS)
        
        login_btn = page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Login')")
        if login_btn:
            login_btn.click()
        else:
            page.keyboard.press("Enter")

        page.wait_for_load_state("networkidle")

        if "login" not in page.url.lower():
            print("✅ Auto-Relogin Berhasil!")
            return True
        else:
            print("❌ Auto-Relogin Gagal. Cek username/password di Secret.")
            return False
    except Exception as e:
        print(f"❌ Error saat Auto-Relogin: {e}")
        return False

def check_and_scrape_detail(page, row_index, tid_code):
    """Membuka detail ATM dan mengirim pesan lengkap jika terdeteksi problem"""
    print(f"🔍 Memeriksa Detail ATM TID: {tid_code}...")
    
    # Ambil ulang semua tombol Detail di tabel hasil
    detail_buttons = page.query_selector_all("input[value='Detail'], button:has-text('Detail')")
    if row_index < len(detail_buttons):
        detail_buttons[row_index].click()
        page.wait_for_load_state("networkidle")
    else:
        return

    # Parsing Data Detail
    page_text = page.inner_text("body")

    def get_val(label):
        for line in page_text.split("\n"):
            if line.strip().startswith(label):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return "-"

    status       = get_val("Status")
    update       = get_val("Update")
    tid_val      = get_val("TID") if get_val("TID") != "-" else tid_code
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

    # Deteksi Problem (Sensors != OK/- OR Status != NORMAL/OK)
    all_statuses = [com, oos, ccr, epp, prt, spv, cl, co, df, kaset1, kaset2, kaset3, kaset4]
    is_problem = any(s not in ["OK", "-"] for s in all_statuses) or status not in ["NORMAL", "OK"]

    if is_problem:
        print(f"🚨 PROBLEM TERDETEKSI pada TID {tid_val}! Mengirim ke Telegram...")
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
        print(f"✅ TID {tid_val} Normal.")

def scan_all_bg_bekasi(page):
    """Mencari seluruh ATM kelolaan BG Bekasi secara otomatis"""
    print(f"🔎 Mencari seluruh ATM Kelolaan BG Bekasi...")
    page.goto(URL_MONITORING, timeout=30000)
    page.wait_for_load_state("networkidle")

    # 1. Pilih Filter By -> Pengelola / Kriteria pencarian
    select_elem = page.query_selector("select")
    if select_elem:
        # Mencoba pilih option Pengelola jika ada, atau biarkan default
        try:
            page.select_option("select", label="Pengelola")
        except:
            pass

    # 2. Input Keyword BG BEKASI & Search
    page.fill("input[name='keyword']", KEYWORD_PENGELOLA)
    page.click("input[value='Search'], button:has-text('Search')")
    page.wait_for_load_state("networkidle")

    # 3. Ambil seluruh baris hasil tabel
    rows = page.query_selector_all("table tr")
    print(f"📊 Ditemukan {len(rows)-1} baris ATM pada tabel hasil.")

    # Kumpulkan daftar TID dari tabel ringkasan
    tid_list = []
    for row in rows[1:]:
        cols = row.query_selector_all("td")
        if len(cols) >= 2:
            tid_text = cols[1].inner_text().strip()
            status_text = cols[4].inner_text().strip() if len(cols) >= 5 else ""
            tid_list.append((tid_text, status_text))

    # 4. Iterasi dan cek detail setiap ATM
    for idx, (tid, status_ringkas) in enumerate(tid_list):
        # Kembali ke halaman hasil jika sudah masuk ke detail sebelumnya
        if idx > 0:
            page.goto(URL_MONITORING, timeout=30000)
            page.wait_for_load_state("networkidle")
            page.fill("input[name='keyword']", KEYWORD_PENGELOLA)
            page.click("input[value='Search'], button:has-text('Search')")
            page.wait_for_load_state("networkidle")

        check_and_scrape_detail(page, idx, tid)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        if SESSION_DATA_RAW:
            try:
                cookies = json.loads(SESSION_DATA_RAW)
                context.add_cookies(cookies)
            except Exception as e:
                print(f"⚠️ Gagal memuat cookie: {e}")

        page = context.new_page()

        try:
            page.goto(URL_MONITORING, timeout=30000)
            page.wait_for_load_state("networkidle")

            if "login" in page.url.lower() or "session" in page.content().lower():
                login_success = auto_relogin(page)
                if not login_success:
                    send_telegram_msg("⚠️ <b>GAGAL LOGIN OTOMATIS!</b>\nMohon periksa PORTAL_USER dan PORTAL_PASS pada GitHub Secrets.")
                    return

            # Jalankan pencarian otomatis seluruh BG Bekasi
            scan_all_bg_bekasi(page)

        except Exception as e:
            print(f"❌ Error execution: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
