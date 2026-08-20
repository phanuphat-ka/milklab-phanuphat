"""GuitarLab Caption Generator (S1).

Usage:
    python caption_generator.py

Reads GOOGLE_API_KEY from env. Generates a Thai caption for a guitar or accessory.
"""

import os
import sys

from dotenv import load_dotenv
from google import genai


PROMPT_TEMPLATE = """\
คุณคือ social media manager ของร้าน GuitarLab ร้านขายและซ่อมกีต้าร์

จงเขียนแคปชั่นภาษาไทย 2 ถึง 3 ประโยคโปรโมตสินค้า/บริการ: {menu}

เงื่อนไข:
- โทนสนุกและเป็นกันเองกับนักดนตรี ใช้คำง่าย ใส่ emoji ได้
- ต้องมี call-to-action ปิดท้าย เช่น สั่งซื้อเลย หรือ ทักแชทสอบถาม
- ห้ามใช้ em dash
"""


def generate_caption(menu: str, api_key: str | None = None) -> str:
    """Generate a Thai caption for the given guitar item/service."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not set in env or argument")
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=PROMPT_TEMPLATE.format(menu=menu),
    )
    return response.text or ""


def main() -> int:
    load_dotenv()
    menu = input("สินค้าหรือบริการที่จะโปรโมต: ").strip()
    if not menu:
        print("กรุณาใส่ชื่อเมนู")
        return 1
    caption = generate_caption(menu)
    print()
    print(caption)
    return 0


if __name__ == "__main__":
    sys.exit(main())
