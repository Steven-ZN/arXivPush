# state.py
import json, os
from pathlib import Path
from typing import Optional

BASE = Path("storage")
BASE.mkdir(parents=True, exist_ok=True)

class PeriodState:
    def __init__(self, period: str):
        # period: 2025-10-09_AM 或 2025-10-09_PM
        self.dir = BASE / period
        self.dir.mkdir(parents=True, exist_ok=True)

    @property
    def raw_json(self):
        return self.dir / "raw_papers.json"

    @property
    def report_md(self):
        return self.dir / "report_zh_en.md"

    @property
    def prompt_context(self):
        return self.dir / "prompt_context.txt"

    @property
    def chat_dir(self):
        d = self.dir / "chat"
        d.mkdir(exist_ok=True)
        return d

    def save_raw(self, data):
        self.raw_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_report(self, md: str):
        self.report_md.write_text(md, encoding="utf-8")

    def save_prompt(self, txt: str):
        self.prompt_context.write_text(txt, encoding="utf-8")

    def append_chat(self, author: str, msg: str):
        idx = len(list(self.chat_dir.glob("*.txt"))) + 1
        (self.chat_dir / f"{idx:03d}_{author}.txt").write_text(msg, encoding="utf-8")

# 最近一期（<=12 小时内）检索
from datetime import datetime, timedelta

def latest_active_period(now_dt, hours=12) -> Optional[str]:
    # 遍历 storage 目录，找到最近且在 12h 内的 period
    cand = sorted([p.name for p in BASE.glob("*_AM")] + [p.name for p in BASE.glob("*_PM")])
    cand = sorted(cand, reverse=True)
    for name in cand:
        # 解析日期
        day, ap = name.split("_")
        if ap not in ("AM", "PM"): continue
        # 估计期点（10:00 AM 或 10:00 PM）
        hour = 10 if ap == "AM" else 22
        try:
            # 添加时区信息以匹配 now_dt
            from dateutil import tz
            dt = datetime.fromisoformat(day)
            dt = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
            # 添加时区信息
            dt = dt.replace(tzinfo=tz.gettz("America/New_York"))
        except:
            continue
        if now_dt - dt <= timedelta(hours=hours):
            return name
    return None