"""اختبار: هل Flet يقدر يقرأ حرارة الجوال؟ (أندرويد وآيفون)

الشاشة تعرض القراءة كل 3 ثواني. إذا صار خطأ يظهر نصه كامل على الشاشة،
صوّره وأرسله.
"""
import asyncio
import traceback

import flet as ft

import sensors

LEVEL_AR = {"normal": "عادية", "warm": "دافئة", "hot": "حارة", "critical": "حرجة"}
LEVEL_COLOR = {"normal": "#2E8B57", "warm": "#D9A400", "hot": "#E8590C", "critical": "#C92A2A"}


def platform_key(page: ft.Page) -> str:
    if page.platform == ft.PagePlatform.ANDROID:
        return "android"
    if page.platform == ft.PagePlatform.IOS:
        return "ios"
    return "desktop"


async def main(page: ft.Page):
    page.title = "Harara Test"
    page.rtl = True
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    plat = platform_key(page)

    title = ft.Text("اختبار حرارة الجوال", size=24, weight=ft.FontWeight.BOLD)
    platform_text = ft.Text(f"المنصة: {plat}", size=16)
    temp_text = ft.Text("--", size=64, weight=ft.FontWeight.BOLD)
    level_text = ft.Text("", size=22)
    details = ft.Text("", size=16, selectable=True)
    error_text = ft.Text("", size=13, color="#C92A2A", selectable=True)
    counter = {"n": 0}

    def show(data: dict):
        t = data.get("temp_c")
        temp_text.value = f"{t:.1f}°C" if t is not None else "لا يوجد رقم"
        lv = data["level"]
        level_text.value = f"المستوى: {LEVEL_AR[lv]}"
        level_text.color = LEVEL_COLOR[lv]
        lines = [
            f"المصدر: {data['source']}",
            f"حالة النظام الحرارية: {data.get('thermal')}",
            f"البطارية: {data.get('battery')}%",
            f"على الشاحن: {'نعم' if data.get('charging') else 'لا'}",
            f"آخر تحديث: {data['time']} (القراءة رقم {counter['n']})",
        ]
        for k in ("sdk", "battery_state"):
            if k in data:
                lines.append(f"{k}: {data[k]}")
        details.value = "\n".join(lines)
        error_text.value = ""

    def read_once():
        counter["n"] += 1
        try:
            show(sensors.read(plat))
        except Exception:  # noqa: BLE001
            temp_text.value = "خطأ"
            level_text.value = ""
            details.value = f"المنصة: {plat}، القراءة رقم {counter['n']}"
            error_text.value = traceback.format_exc()
        page.update()

    async def on_click(_):
        read_once()

    page.add(
        title,
        platform_text,
        ft.Container(height=10),
        temp_text,
        level_text,
        ft.Container(height=10),
        details,
        ft.Container(height=10),
        ft.FilledButton(content=ft.Text("اقرأ الآن"), on_click=on_click),
        ft.Container(height=10),
        error_text,
    )
    read_once()
    while True:
        await asyncio.sleep(3)
        read_once()


if __name__ == "__main__":
    ft.run(main)
