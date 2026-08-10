# MilkLab° Solopreneur Starter (Course 69-1)

Template repo สำหรับวิชา 31-407-106-406 : AI for Solopreneurs

## เริ่มต้น

1. **Use this template** then Create a new repository (ตั้งชื่อ `milklab-<ชื่อ>`)
2. เปิด **Codespaces** จาก repo ใหม่
3. ตั้ง user-level Codespaces secret `GOOGLE_API_KEY` (ดู Quickstart)
4. รัน `python scripts/verify_setup.py` ใน terminal

## Environment

คัดลอก [`.env.example`](.env.example) ไปเป็น `.env` แล้วใส่ค่าจริงของตัวเอง โดยชื่อที่ใช้กับ S2 คือ `TELEGRAM_BOT_TOKEN` และ `TELEGRAM_CHAT_ID` (ถ้าไฟล์เดิมใช้ `TELEGRAM_TOKEN` สคริปต์ morning report ยังรองรับเป็น alias)

สำหรับ S2 Google Sheets ให้ใส่ `GOOGLE_SHEETS_CREDENTIALS` เป็น service account JSON แบบบรรทัดเดียว และ `GOOGLE_SHEETS_URL` เป็น URL หรือ ID ของชีตเป้าหมาย

ตัวอย่างทดสอบ Telegram:

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
	-d "chat_id=$TELEGRAM_CHAT_ID&text=hello"
```

## ไฟล์หลัก

| ไฟล์ | Session | คำอธิบาย |
|---|---|---|
| `caption_generator.py` | S1 | สร้างแคปชั่นให้โพสต์ MilkLab |
| `sales_logger.py` | S2 | บันทึกยอดขายลง Google Sheets |
| `agent_harness.py` | S2 | รับคำสั่งภาษาไทย เรียก tool |
| `app.py` | S3 | Streamlit RAG chatbot |

## เครื่องมือ

- Python 3.11
- Gemini API (google-genai)
- Streamlit (S3)
- gspread (S2)

## ดูคอร์ส

[course-691-stsw](https://github.com/<owner>/course-691-stsw) (link จะ update ตอนสร้าง public repo)
