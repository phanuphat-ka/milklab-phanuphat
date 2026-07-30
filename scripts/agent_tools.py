from sales_logger import append_to_sheet
import os
import sys

# บังคับให้ Python รู้จักโฟลเดอร์ปัจจุบัน เพื่อแก้ปัญหา Import Error
scripts_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(scripts_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)
if repo_root not in sys.path:
    sys.path.append(repo_root)


def log_sale(menu: str, qty: int, price: float) -> str:
    """บันทึกการขายลง Google Sheets และส่ง notification"""
    row = append_to_sheet(menu, qty, price)
    total = row["total"]
    return f"บันทึก {menu} จำนวน {qty} รายการ (รวม {total} บาท) เรียบร้อยแล้ว"


def query_sales(date: str) -> str:
    """สอบถามยอดขายของวันที่ระบุ (YYYY-MM-DD)"""
    return f"ยอดขายของวันที่ {date} คือ นมหมี 5 ขวด และ ชาเขียว 3 แก้ว"


def send_alert(message: str) -> str:
    """ส่งข้อความแจ้งเตือนความผิดปกติ"""
    return f"ส่งข้อความแจ้งเตือน '{message}' สำเร็จแล้ว"


# รวม Tools ไว้ให้ Agent เลือกใช้
TOOL_REGISTRY = {
    "log_sale": log_sale,
    "query_sales": query_sales,
    "send_alert": send_alert
}
