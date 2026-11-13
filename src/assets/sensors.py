"""قراءة حالة الحرارة والبطارية من نظام الجوال.

أندرويد: pyjnius (BatteryManager + PowerManager).
آيفون: pyobjus (NSProcessInfo.thermalState + UIDevice).
كل دالة ترجع قاموسًا بسيطًا، وأي خطأ يطلع كنص بدل ما يوقف التطبيق.
"""
import os
import time

LEVELS = ["normal", "warm", "hot", "critical"]


def level_from_temp(temp_c: float) -> str:
    if temp_c >= 45:
        return "critical"
    if temp_c >= 40:
        return "hot"
    if temp_c >= 35:
        return "warm"
    return "normal"


def level_from_android_status(status: int) -> str:
    if status <= 0:
        return "normal"
    if status <= 2:
        return "warm"
    if status == 3:
        return "hot"
    return "critical"


def worst(*levels):
    present = [lv for lv in levels if lv]
    return max(present, key=LEVELS.index) if present else "normal"


def read_android() -> dict:
    from jnius import autoclass

    host = autoclass(os.environ["MAIN_ACTIVITY_HOST_CLASS_NAME"])
    ctx = host.mActivity
    Intent = autoclass("android.content.Intent")
    IntentFilter = autoclass("android.content.IntentFilter")
    BM = autoclass("android.os.BatteryManager")
    sdk = autoclass("android.os.Build$VERSION").SDK_INT

    intent = ctx.registerReceiver(None, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
    raw = intent.getIntExtra(BM.EXTRA_TEMPERATURE, -1000)
    temp_c = raw / 10.0 if raw > -1000 else None
    level_pct = intent.getIntExtra(BM.EXTRA_LEVEL, -1)
    scale = intent.getIntExtra(BM.EXTRA_SCALE, 100) or 100
    plugged = intent.getIntExtra(BM.EXTRA_PLUGGED, 0) > 0

    thermal = None
    if sdk >= 29:
        pm = ctx.getSystemService("power")
        thermal = int(pm.getCurrentThermalStatus())

    level = worst(
        level_from_temp(temp_c) if temp_c is not None else None,
        level_from_android_status(thermal) if thermal is not None else None,
    )
    return {
        "source": "android",
        "temp_c": temp_c,
        "thermal": thermal,
        "level": level,
        "battery": int(level_pct * 100 / scale) if level_pct >= 0 else None,
        "charging": plugged,
        "sdk": int(sdk),
    }


def _ios_get(obj, name, default):
    """pyobjus يعرض خصائص Objective-C كقيم، وأحيانًا كدوال."""
    try:
        value = getattr(obj, name)
        return value() if callable(value) else value
    except Exception as exc:  # noqa: BLE001
        return f"ERR {name}: {exc}"


def read_ios() -> dict:
    from pyobjus import autoclass
    from pyobjus.dylib_manager import INCLUDE, load_framework

    load_framework(INCLUDE.Foundation)
    load_framework(INCLUDE.UIKit)
    info = autoclass("NSProcessInfo").processInfo()
    device = autoclass("UIDevice").currentDevice()
    device.setBatteryMonitoringEnabled_(True)

    state = _ios_get(info, "thermalState", 0)
    battery = _ios_get(device, "batteryLevel", -1.0)
    bstate = _ios_get(device, "batteryState", 0)
    try:
        state_i = max(0, min(3, int(state)))
    except (TypeError, ValueError):
        state_i = 0
    try:
        battery_pct = int(float(battery) * 100) if float(battery) >= 0 else None
    except (TypeError, ValueError):
        battery_pct = None
    return {
        "source": "ios",
        "temp_c": None,
        "thermal": state,
        "level": LEVELS[state_i],
        "battery": battery_pct,
        "charging": bstate in (2, 3),
        "battery_state": bstate,
    }


def read_simulated() -> dict:
    return {"source": "desktop", "temp_c": 38.0, "thermal": None, "level": "warm",
            "battery": 70, "charging": False}


def read(platform: str) -> dict:
    if platform == "android":
        data = read_android()
    elif platform == "ios":
        data = read_ios()
    else:
        data = read_simulated()
    data["time"] = time.strftime("%H:%M:%S")
    return data
