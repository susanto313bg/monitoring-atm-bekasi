import os
import json
import asyncio
import re
import requests
from playwright.async_api import async_playwright

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SESSION_DATA = os.environ.get("SESSION_DATA")

LAST_STATUS_FILE = "last_status.json"

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[-] Bot Token / Chat ID belum diset.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"[-] Gagal kirim Telegram: {e}")

def load_last_status():
    if os.path.exists(LAST_STATUS_FILE):
        try:
            with open(LAST_STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_last_status(data):
    with open(LAST_STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def run_monitoring():
    if not SESSION_DATA:
        send_telegram("⚠️ <b>SESSION MISSING:</b> Secret SESSION_DATA belum diisi!")
        return

    with open("session.json", "w") as f:
        f.write(SESSION_DATA)

    last_status = load_last_status()
    current_status = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="session.json")
        page = await context.new_page()

        print("[*] Membuka portal Device Locator...")
        await page.goto("https://devicelocator.bri.co.id", wait_until="networkidle")

        if "login" in page.url.lower():
            send_telegram("⚠️ <b>SESSION DEVICE LOCATOR EXPIRED!</b>\nSilakan update secret SESSION_DATA di GitHub.")
            await browser.close()
            return

        await page.wait_for_selector("table tbody tr")
        rows = await page.query_selector_all("table tbody tr")

        trouble_keywords = ["FAIL", "LOW", "OFFLINE", "ERROR", "ON_PROGRESS", "TROUBLE"]

        for row in rows:
            cols = await row.query_selector_all("td")
            if len(cols) >= 5:
                tid = (await cols[1].inner_text()).strip()
                lokasi = (await cols[3].inner_text()).strip()
                status_utama = (await cols[4].inner_text()).strip()

                current_status[tid] = status_utama
                previous_status = last_status.get(tid, "NORMAL")

                if status_utama != previous_status or status_utama in trouble_keywords:
                    detail_btn = await row.query_selector("button:has-text('Detail'), input[value='Detail']")
                    if detail_btn:
                        await detail_btn.click()
                        await page.wait_for_timeout(1500)

                        detail_elem = await page.query_selector("body")
                        detail_text = await detail_elem.inner_text() if detail_elem else ""

                        if any(kw in detail_text.upper() for kw in trouble_keywords):
                            def get_val(label, default="-"):
                                match = re.search(fr"{label}\s*:\s*(.*)", detail_text)
                                return match.group(1).strip() if match else default

                            msg = (
                                f"🚨 <b>ATM PARAMETER TROUBLE DETECTED</b>\n\n"
                                f"<b>TID:</b> <code>{tid}</code>\n"
                                f"<b>Lokasi:</b> {lokasi}\n"
                                f"<b>Status Utama:</b> {status_utama}\n"
                                f"<b>Supervisi:</b> {get_val('Supervisi')}\n"
                                f"<b>Pengelola:</b> {get_val('Pengelola')}\n"
                                f"<b>Pet IT:</b> {get_val('Pet IT')}\n"
                                f"<b>Mesin / IP:</b> {get_val('Mesin')} ({get_val('IP')})\n\n"
                                f"<b>Status Jaringan & Hardware:</b>\n"
                                f"• COM: {get_val('COM')} | OOS: {get_val('OOS')} | CCR: {get_val('CCR')}\n"
                                f"• EPP: {get_val('EPP')} | PRT: {get_val('PRT')} | SPV: {get_val('SPV')}\n\n"
                                f"<b>Status Kaset:</b>\n"
                                f"• Kaset 1: {get_val('Kaset 1')}\n"
                                f"• Kaset 2: {get_val('Kaset 2')}\n"
                                f"• Kaset 3: {get_val('Kaset 3')}\n"
                                f"• Kaset 4: {get_val('Kaset 4')}\n"
                                f"• Trx Terakhir: {get_val('Trx Tunai')}\n"
                            )
                            send_telegram(msg)

                        close_btn = await page.query_selector("button:has-text('Close'), .close")
                        if close_btn:
                            await close_btn.click()

        save_last_status(current_status)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_monitoring())
