# notifier.py
import sys
import platform
from datetime import datetime
import os


def send_notification(title, message, is_important=False):
    """
    Отправляет системное уведомление.
    Работает на Windows, Linux (GNOME/KDE), MacOS.
    """
    # Windows
    if platform.system() == "Windows":
        try:
            import ctypes
            # MB_OK = 0x00, MB_ICONINFORMATION = 0x40
            ctypes.windll.user32.MessageBoxW(
                0,
                message,
                title,
                0x40 | 0x00  # Информация + OK
            )
        except Exception as e:
            print(f"⚠️ Ошибка уведомления Windows: {e}")
    
    # Linux (notify-send)
    elif platform.system() == "Linux":
        try:
            import subprocess
            urgency = "critical" if is_important else "normal"
            subprocess.run([
                "notify-send",
                title,
                message,
                f"--urgency={urgency}",
                "--icon=info"
            ], timeout=2)
        except Exception as e:
            print(f"⚠️ Ошибка уведомления Linux: {e}")
    
    # MacOS
    elif platform.system() == "Darwin":
        try:
            import subprocess
            subprocess.run([
                "osascript",
                "-e",
                f'display notification "{message}" with title "{title}"'
            ], timeout=2)
        except Exception as e:
            print(f"⚠️ Ошибка уведомления MacOS: {e}")
    
    # Если ничего не сработало — выводим в консоль
    else:
        print("\n" + "=" * 50)
        print(f"🔔 {title}")
        print("-" * 50)
        print(message)
        print("=" * 50 + "\n")


def notify_position_change(program_title, old_position, new_position, old_real, new_real):
    """Уведомление об изменении позиции."""
    message = f"📌 По списку: {old_position} → {new_position}\n"
    message += f"🎯 Реальное место: {old_real} → {new_real}"
    
    send_notification(f"📊 {program_title}", message)


def notify_status_change(program_title, is_safe, position, places):
    """Уведомление об изменении статуса."""
    if is_safe:
        message = f"🎉 Вы проходите!\n📌 Реальное место: {position} из {places}"
        send_notification(f"✅ {program_title}", message, is_important=True)
    else:
        message = f"🔥 Вы в зоне риска!\n📌 Реальное место: {position} из {places}\n"
        message += f"💡 Нужно, чтобы {position - places} человек ушли"
        send_notification(f"⚠️ {program_title}", message, is_important=True)