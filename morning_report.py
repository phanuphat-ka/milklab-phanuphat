"""MilkLab morning sales report.

Usage:
    python morning_report.py

Environment variables:
    TELEGRAM_BOT_TOKEN or LINE_CHANNEL_TOKEN
    TELEGRAM_CHAT_ID
    GOOGLE_SHEETS_URL or GOOGLE_SHEETS_ID
    GOOGLE_SHEETS_CREDENTIALS
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, date, timezone, timedelta
from typing import Any

import gspread
import requests
from dotenv import load_dotenv


DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
)
THAILAND_TZ = timezone(timedelta(hours=7))


def _sheet_target() -> str:
    target = os.environ.get("GOOGLE_SHEETS_URL", "").strip()
    if target:
        return target
    target = os.environ.get("GOOGLE_SHEETS_ID", "").strip()
    if target:
        return target
    raise RuntimeError("GOOGLE_SHEETS_URL or GOOGLE_SHEETS_ID is not set")


def _telegram_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or os.environ.get(
        "TELEGRAM_TOKEN", "").strip()


def _sheet_client() -> gspread.Client:
    raw_config = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "").strip()
    if not raw_config:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS is not set")
    if not (raw_config.startswith("{") or raw_config.startswith("[")):
        raise RuntimeError(
            "GOOGLE_SHEETS_CREDENTIALS must contain service account JSON")
    credentials_info = json.loads(raw_config)
    return gspread.service_account_from_dict(credentials_info)


def _open_worksheet() -> gspread.Worksheet:
    client = _sheet_client()
    target = _sheet_target()
    spreadsheet = client.open_by_url(target) if target.startswith(
        "http") else client.open_by_key(target)
    return spreadsheet.sheet1


def _parse_sales_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def load_today_sales() -> list[list[Any]]:
    worksheet = _open_worksheet()
    rows = worksheet.get_all_values()
    if not rows:
        return []

    today = datetime.now(THAILAND_TZ).date()
    result: list[list[Any]] = []
    for row in rows[1:]:
        if not row:
            continue
        row_date = _parse_sales_date(row[0])
        if row_date == today:
            result.append(row)
    return result


def build_report(rows: list[list[Any]]) -> str:
    if not rows:
        return "[Morning report] ไม่มีรายการขายของวันนี้"

    total_qty = 0
    total_amount = 0.0
    lines = ["[Morning report] สรุปยอดขายวันนี้"]

    for row in rows:
        timestamp = row[0] if len(row) > 0 else ""
        menu = row[1] if len(row) > 1 else ""
        qty = row[2] if len(row) > 2 else 0
        price = row[3] if len(row) > 3 else 0
        total = row[4] if len(row) > 4 else 0

        try:
            qty_value = int(float(qty))
        except (TypeError, ValueError):
            qty_value = 0
        try:
            total_value = float(total)
        except (TypeError, ValueError):
            total_value = 0.0

        total_qty += qty_value
        total_amount += total_value
        lines.append(
            f"- {timestamp} | {menu} x{qty_value} = {total_value:.0f} บาท")

    lines.append(f"รวมทั้งหมด: {total_qty} รายการ, {total_amount:.0f} บาท")
    return "\n".join(lines)


def send_telegram(message: str) -> None:
    token = _telegram_token()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if token and chat_id:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok", False):
            raise RuntimeError(payload.get(
                "description", "Telegram request failed"))
        return

    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is not set")


def main() -> int:
    load_dotenv(override=True)

    try:
        rows = load_today_sales()
        report = build_report(rows)
        send_telegram(report)
    except Exception as exc:
        print(f"[ERROR] morning report failed: {exc}", file=sys.stderr)
        return 1

    print("[OK] morning report sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
