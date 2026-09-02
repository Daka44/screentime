import time
from datetime import datetime
import json
import os
import win32gui
import win32process
import psutil
import requests

# =========================================================
# [설정] 디스코드 웹훅 주소
# 필요 없으면 "" 빈 문자열로 두세요.
# =========================================================
DISCORD_WEBHOOK_URL = "여기에_디스코드_웹훅_주소를_붙여넣으세요"

LOG_TXT_FILE = "screentime_history.txt"
SUMMARY_JSON_FILE = "screentime_summary.json"

# =========================================================
# [허용 목록] 여기 없는 프로그램/사이트는 전부 알림 대상입니다.
# =========================================================

# 1) 프로세스 이름만으로 허용할 프로그램 (전부 소문자로 입력)
#    작업 관리자 -> 자세히 탭에서 정확한 exe 이름을 확인할 수 있어요.
ALLOWED_PROCESSES = {
    "code.exe",         # VS Code
    "winword.exe",      # MS Word
    "excel.exe",        # MS Excel
    "powerpnt.exe",     # MS PowerPoint
    "notion.exe",       # Notion 앱
    "acrord32.exe",     # Adobe Reader
    "explorer.exe",     # 파일 탐색기
}

# 2) 브라우저 창 "제목"에 아래 키워드가 포함되면 허용 (소문자로 비교)
#    브라우저는 탭 제목이 곧 창 제목이라 이런 방식으로만 판단 가능해요.
ALLOWED_TITLE_KEYWORDS = [
    "docs.google.com",
    "google docs",
    "github",
    "stack overflow",
    "notion",
    "wikipedia",
    "위키백과",
    "khan academy",
    "coursera",
    "인프런",
    # 공부용으로 자주 쓰는 사이트/키워드를 여기에 계속 추가하세요.
]

# 3) 위 제목 키워드 검사를 적용할 브라우저 프로세스 목록
BROWSER_PROCESSES = {"chrome.exe", "msedge.exe", "whale.exe", "firefox.exe", "opera.exe"}


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


def is_allowed(pname, title):
    """허용 목록에 해당하면 True, 아니면 False(=알림 대상)"""
    pname_lower = (pname or "").lower()
    title_lower = (title or "").lower()

    # 프로세스 자체가 허용 목록에 있으면 통과
    if pname_lower in ALLOWED_PROCESSES:
        return True

    # 브라우저라면 제목에 허용 키워드가 있는지 확인
    if pname_lower in BROWSER_PROCESSES:
        return any(keyword.lower() in title_lower for keyword in ALLOWED_TITLE_KEYWORDS)

    # 그 외(게임, 인스타그램 앱, 디스코드, 카톡 등)는 전부 알림 대상
    return False


def save_history_log(start_time, end_time, process_name, title, duration, flagged):
    start_str = start_time.strftime("%H:%M:%S")
    end_str = end_time.strftime("%H:%M:%S")
    date_str = start_time.strftime("%Y-%m-%d")
    mark = "🚫" if flagged else "✅"

    log_line = f"[{date_str} {start_str} ~ {end_str}] ({duration}초) {mark} [{process_name}] {title}\n"

    with open(LOG_TXT_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)


def update_summary_json(title, duration):
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

                # 2초 이상 켜둔 창만 기록 (단순히 스쳐 지나간 창 제외)
                if duration >= 2:
                    flagged = not is_allowed(curr_pname, curr_title)
                    save_history_log(start_time, end_time, curr_pname, curr_title, int(duration), flagged)
                    update_summary_json(curr_title, duration)

                    if flagged:
                        send_discord_alert(
                            f"🚫 **[허용되지 않은 사용 감지]**\n"
                            f"• 프로그램: `{curr_pname}`\n"
                            f"• 창 제목: `{curr_title}`\n"
                            f"• 사용 시간: {int(duration)}초"
                        )

                curr_pname, curr_title = new_pname, new_title
                start_time = end_time
        except Exception:
            pass


if __name__ == "__main__":
    main()
