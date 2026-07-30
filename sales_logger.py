"""MilkLab Sales Logger (S2).

Usage:
    python sales_logger.py --menu "นมหมีฮอกไกโด" --qty 2 --price 65

Reads GOOGLE_SHEETS_CREDENTIALS and TELEGRAM_BOT_TOKEN (or LINE_CHANNEL_TOKEN) from env.
Appends row [timestamp, menu, qty, price, total] to a Google Sheet,
then sends a notification via Telegram or LINE bot.

นักศึกษาต้องเติม TODO ใน 4 จุดด้านล่างใน Session 2 Lab 1.3
"""

import argparse
import json
import os
import sys
from datetime import datetime

import gspread
import requests
from dotenv import load_dotenv


def append_to_sheet(menu: str, qty: int, price: float) -> dict:
    """TODO 1: ใช้ gspread เปิด Sheet ของตัวเอง แล้ว append_row ด้วย [timestamp, menu, qty, price, total]

    Returns dict {timestamp, menu, qty, price, total} ที่ append แล้ว
    Raises RuntimeError ถ้า credentials ไม่มี หรือ Sheet ไม่ accessible
    """
    raw_config = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "").strip()
    sheet_target = os.environ.get("GOOGLE_SHEETS_URL", "").strip()

    if not raw_config:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS is not set")

    if not sheet_target:
        raise RuntimeError("GOOGLE_SHEETS_URL is not set")

    if not (raw_config.startswith("{") or raw_config.startswith("[")):
        raise RuntimeError(
            "GOOGLE_SHEETS_CREDENTIALS must contain service account JSON")

    credentials_info = json.loads(raw_config)
    client = gspread.service_account_from_dict(credentials_info)
    spreadsheet = client.open_by_url(sheet_target) if sheet_target.startswith(
        "http") else client.open_by_key(sheet_target)

    worksheet = spreadsheet.sheet1
    timestamp = datetime.now().isoformat(timespec="seconds")
    total = qty * price
    row = [timestamp, menu, qty, price, total]
    worksheet.append_row(row, value_input_option="USER_ENTERED")
    return {
        "timestamp": timestamp,
        "menu": menu,
        "qty": qty,
        "price": price,
        "total": total,
    }


def send_notification(message: str) -> str:
    """TODO 2: ส่ง message ไปยัง Telegram bot (ใช้ TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)
    หรือ LINE bot (ใช้ LINE_CHANNEL_TOKEN) เลือกตัวใดตัวหนึ่ง

    Returns: provider name ที่ใช้ ("telegram" หรือ "line")
    Raises RuntimeError ถ้า no credentials
    """
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    line_token = os.environ.get("LINE_CHANNEL_TOKEN", "").strip()

    if telegram_token and telegram_chat_id:
        response = requests.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            data={"chat_id": telegram_chat_id, "text": message},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok", False):
            raise RuntimeError(payload.get(
                "description", "Telegram request failed"))
        return "telegram"

    if line_token:
        response = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {line_token}"},
            data={"message": message},
            timeout=15,
        )
        response.raise_for_status()
        return "line"

    raise RuntimeError("No Telegram or LINE credentials configured")


def main() -> int:
    # Load .env directly to avoid shell parsing issues with JSON credentials.
    load_dotenv(override=True)

    parser = argparse.ArgumentParser(description="MilkLab Sales Logger")
    parser.add_argument("--menu", required=True, help="ชื่อเมนู")
    parser.add_argument("--qty", type=int, required=True, help="จำนวนขวด")
    parser.add_argument("--price", type=float,
                        required=True, help="ราคาต่อขวด")
    args = parser.parse_args()

    try:
        # TODO 3: เรียก append_to_sheet แล้ว extract total
        row = append_to_sheet(args.menu, args.qty, args.price)
        total = row["total"]
    except Exception as exc:
        print(f"[ERROR] บันทึก Sheet ล้มเหลว: {exc}", file=sys.stderr)
        print("[HINT] ตรวจ GOOGLE_SHEETS_CREDENTIALS และ share Sheet กับ service account email", file=sys.stderr)
        return 1

    try:
        # TODO 4: เรียก send_notification ด้วย message ที่บอกยอดที่บันทึก
        provider = send_notification(
            f"บันทึก {args.menu} x{args.qty} = {total} บาท")
    except Exception as exc:
        print(
            f"[WARN] บันทึก Sheet สำเร็จแต่ส่งแจ้งเตือนล้มเหลว: {exc}", file=sys.stderr)
        return 0

    print(f"[OK] บันทึกและแจ้งเตือนผ่าน {provider} เรียบร้อย ยอด {total} บาท")
    return 0


if __name__ == "__main__":
    sys.exit(main())
