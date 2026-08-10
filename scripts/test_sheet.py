import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 📌 1. ใส่ ID ของ Google Sheet (เอามาจาก URL ระหว่าง /d/ ถึง /edit)
SPREADSHEET_ID = "13FAjNsLgNrXqfsgfKb5zUP5o-gy068R35EhMvhQ_A8c"


def test_google_sheet_connection():
    print("🔍 กำลังเริ่มทดสอบการเชื่อมต่อ Google Sheet...")

    # เช็คว่ามีไฟล์ credentials.json หรือไม่
    creds_path = "credentials.json"
    if not os.path.exists(creds_path):
        print(f"❌ Error: ไม่พบไฟล์ '{creds_path}' ใน Root Directory")
        return

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        # ยืนยันตัวตน
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            creds_path, scope)
        client = gspread.authorize(creds)

        # เปิด Sheet ตาม ID
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.sheet1  # เลือก Tab แรก

        print(
            f"✅ เชื่อมต่อไฟล์สำเร็จ: '{spreadsheet.title}' (Tab: '{sheet.title}')")

        # ข้อมูลทดสอบส่ง
        test_data = ["ทดสอบระบบ", 1, 35, 35]

        print(f"📤 กำลังเขียนข้อมูล: {test_data}")
        sheet.append_row(test_data)

        print("\n🎉 บันทึกสำเร็จ! กรุณาเปิดหน้า Google Sheet ดูว่าแถวใหม่ขึ้นหรือไม่")

    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาดในการเชื่อมต่อ:")
        print(e)


if __name__ == "__main__":
    test_google_sheet_connection()
