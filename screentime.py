import time
from datetime import datetime
import json
import os
import win32gui
import win32process
import psutil
import requests

# 1단계에서 복사한 디스코드 웹훅 주소를 아래 큰따옴표 안에 넣으세요.
# 디스코드 알림이 필요 없으면 "" 그대로 비워두시면 됩니다.
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1544697243058176150/NsyAoho8A1xXGURDfojgAI4nB0-a1kGltYiJ8rvyeVte8Pw3jSfs32qXbe2wCc6eqNu7"

LOG_TXT_FILE = "screentime_history.txt"
SUMMARY_JSON_FILE = "screentime_summary.json"


def get_active_window_info():
    """현재 활성화된 창의 프로세스명과 창 제목을 가져옵니다."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "Unknown", "알 수 없는 창"
        
        title = win32gui.GetWindowText(hwnd)
        if not title:
            title = "제목 없는 창"
            
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            pname = proc.name()
        except Exception:
            pname = "Unknown"
            
        return pname, title
    except Exception:
        return "Error", "감지 실패"


def save_history_log(start_time, end_time, process_name, title, duration):
    """시간대별 사용 내역 텍스트 기록"""
    start_str = start_time.strftime("%H:%M:%S")
    end_str = end_time.strftime("%H:%M:%S")
    date_str = start_time.strftime("%Y-%m-%d")
    
    log_line = f"[{date_str} {start_str} ~ {end_str}] ({duration}초) [{process_name}] {title}\n"
    
    with open(LOG_TXT_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)


def update_summary_json(title, duration):
    """창 제목별 누적 사용 시간 JSON 기록"""
    summary = {}
    if os.path.exists(SUMMARY_JSON_FILE):
        try:
            with open(SUMMARY_JSON_FILE, "r", encoding="utf-8") as f:
                summary = json.load(f)
        except Exception:
            summary = {}
            
    summary[title] = summary.get(title, 0) + int(duration)
    
    with open(SUMMARY_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def send_discord_alert(message):
    """디스코드 웹훅 알림 전송"""
    if DISCORD_WEBHOOK_URL.strip() and "discord.com" in DISCORD_WEBHOOK_URL:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        except Exception:
            pass


def main():
    curr_pname, curr_title = get_active_window_info()
    start_time = datetime.now()
    
    send_discord_alert("🟢 **[스크린타임] 감지 프로그램이 시작되었습니다.**")
    
    while True:
        try:
            time.sleep(1)  # 1초 간격 감시
            new_pname, new_title = get_active_window_info()
            
            if new_title != curr_title:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # 2초 이상 열어둔 창만 기록
                if duration >= 2:
                    save_history_log(start_time, end_time, curr_pname, curr_title, int(duration))
                    update_summary_json(curr_title, duration)
                    
                    # 유튜브 감지 시 디스코드 알림
                    if "YouTube" in curr_title or "유튜브" in curr_title:
                        send_discord_alert(
                            f"⚠️ **[딴짓 경고]** 친구가 유튜브를 보고 있습니다!\n"
                            f"• 사용 시간: {int(duration)}초\n"
                            f"• 창 제목: `{curr_title}`"
                        )
                
                curr_pname, curr_title = new_pname, new_title
                start_time = end_time
        except Exception:
            pass


if __name__ == "__main__":
    main()
