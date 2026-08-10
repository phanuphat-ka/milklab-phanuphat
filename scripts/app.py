from dotenv import load_dotenv
import telebot
import os
import sys
import traceback

scripts_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(scripts_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)
if repo_root not in sys.path:
    sys.path.append(repo_root)


try:
    from scripts.agent_harness import run_agent
except ModuleNotFoundError:
    # Fallback for direct execution from scripts/.
    from agent_harness import run_agent

# โหลดค่า Token จากไฟล์ .env
load_dotenv(os.path.join(repo_root, ".env"))
TELEGRAM_TOKEN = (
    os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    or os.environ.get("TELEGRAM_TOKEN", "").strip()
)

if not TELEGRAM_TOKEN:
    print("❌ Error: ไม่พบ TELEGRAM_BOT_TOKEN หรือ TELEGRAM_TOKEN กรุณาตรวจสอบไฟล์ .env")
    raise SystemExit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        user_text = (message.text or "").strip()
        if not user_text:
            bot.reply_to(message, "กรุณาส่งข้อความตัวอักษรเพื่อบันทึกยอดขาย")
            return

        print(f"\n[Telegram User]: {user_text}")

        # ส่งสัญญาณ "กำลังพิมพ์..."
        bot.send_chat_action(message.chat.id, "typing")

        # ประมวลผลด้วย Agent
        agent_reply = run_agent(user_text)
        print(f"[Agent Reply]: {agent_reply}")

        # ตอบกลับแชท
        bot.reply_to(message, agent_reply)
    except Exception as exc:
        print("❌ Telegram handler error:")
        print(traceback.format_exc())
        try:
            bot.reply_to(
                message,
                f"เกิดข้อผิดพลาดระหว่างประมวลผล: {exc}",
            )
        except Exception:
            pass


def main() -> int:
    print("🤖 บอท MilkLab Agent ออนไลน์แล้ว! (กด Ctrl+C เพื่อหยุดทำงาน)")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
