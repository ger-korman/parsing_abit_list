import sys
import platform

def send_notification(title, message, is_important=False):
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x00)
        except:
            pass
    elif platform.system() == "Linux":
        try:
            import subprocess
            urgency = "critical" if is_important else "normal"
            subprocess.run(["notify-send", title, message, f"--urgency={urgency}"], timeout=2)
        except:
            pass
    elif platform.system() == "Darwin":
        try:
            import subprocess
            subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], timeout=2)
        except:
            pass
    print(f"\n🔔 {title}\n{message}\n")

def notify_position_change(title, old_pos, new_pos, old_real, new_real):
    message = f"По списку: {old_pos} → {new_pos}\nРеальное: {old_real} → {new_real}"
    send_notification(f"📊 {title}", message)

def notify_status_change(title, is_safe, pos, places):
    if is_safe:
        message = f"🎉 Вы проходите! Место {pos} из {places}"
    else:
        message = f"⚠️ Вы в зоне риска! Место {pos} из {places}"
    send_notification(f"{'✅' if is_safe else '⚠️'} {title}", message, not is_safe)