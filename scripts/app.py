import sys
import os

# บังคับชี้เป้าให้เห็นไฟล์ agent_harness.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import telebot
from dotenv import load_dotenv
from agent_harness import run_agent 

# โหลดค่า Token จากไฟล์ .env
load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    print("❌ Error: ไม่พบ TELEGRAM_TOKEN กรุณาตรวจสอบไฟล์ .env")
    exit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)

print("🤖 บอท MilkLab Agent ออนไลน์แล้ว! (กด Ctrl+C เพื่อหยุดทำงาน)")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_text = message.text
    print(f"\n[Telegram User]: {user_text}")
    
    # ส่งสัญญาณ "กำลังพิมพ์..."
    bot.send_chat_action(message.chat.id, 'typing')
    
    # ประมวลผลด้วย Agent
    agent_reply = run_agent(user_text)
    print(f"[Agent Reply]: {agent_reply}")
    
    # ตอบกลับแชท
    bot.reply_to(message, agent_reply)

if __name__ == "__main__":
    bot.infinity_polling()