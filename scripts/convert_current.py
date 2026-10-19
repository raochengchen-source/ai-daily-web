#!/usr/bin/env python3
"""convert_current.py — data_current.json → report_current.json（AI 每日行业简报结构）

读 fetch_daily.py 产出的 data_current.json（top3 + items，含 heat/tags/reason），
转换为简报结构：core_conclusions(3) / top3 / sections(4 板块) / observations / notes。
4 板块映射：companies=大模型+工具；apps=行业+商业；policy=(空)；research=研究+基础设施+观点。
"""
import json
import os
import re
import datetime

BASE = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
OUT = os.path.join(DATA_DIR, "report_current.json")

SECTIONS = [
    {"key": "companies", "name": "公司与产品", "color": "blue", "catKeys": {"model", "tool"}},
    {"key": "apps", "name": "应用与商业化", "color": "teal", "catKeys": {"industry", "biz"}},
    {"key": "policy", "name": "政策与监管", "color": "amber", "catKeys": set()},
    {"key": "research", "name": "研究与基础设施", "color": "violet", "catKeys": {"research", "infra", "opinion"}},
]

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0000200D\U0000200C]+"
)


def clean(s):
    return EMOJI_RE.sub("", str(s))


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    data = load(os.path.join(DATA_DIR, "data_current.json"), None)
    if not data:
        # 回退到最新一份 data_2*.json
        import glob
        cands = sorted(glob.glob(os.path.join(DATA_DIR, "data_2*.json")))
        data = load(cands[-1], {}) if cands else {}
    date = str(data.get("date", datetime.date.today().isoformat()))
    top3 = data.get("top3", [])
    items = data.get("items", [])

    # 核心结论：从 top3 提炼（标题 + 摘要，压缩至 60-120 字）
    core = []
    for t in top3:
        title = clean(t.get("title", ""))
        summary = clean(t.get("summary", ""))
        s = title
        if summary and len(s) < 40:
            s += "：" + summary
        if len(s) > 120:
            s = s[:117].rstrip("：;；,，。") + "…"
        if len(s) < 60:
            s = (s + "。" + summary) if summary else s
        if len(s) > 120:
            s = s[:117].rstrip("：;；,，。") + "…"
        core.append(s if s else title)

    # TOP3
    top3_out = []
    for t in top3:
        top3_out.append({
            "rank": t.get("rank", 0),
            "title": clean(t.get("title", "")),
            "url": t.get("url", ""),
            "summary": clean(t.get("summary", "")),
            "why": clean(t.get("reason", "")),
            "source": clean(t.get("source", "")),
            "time": str(t.get("time", "")),
            "heat": t.get("heat", 0),
            "tags": t.get("tags", []),
        })

    # 4 板块
    sections = []
    used = set()
    for sec in SECTIONS:
        sec_items = []
        for it in items:
            if it.get("catKey") in sec["catKeys"]:
                sec_items.append({
                    "title": clean(it.get("title", "")),
                    "url": it.get("url", ""),
                    "summary": clean(it.get("summary", "")),
                    "why": clean(it.get("reason", "")),
                    "source": clean(it.get("source", "")),
                    "time": str(it.get("time", "")),
                    "heat": it.get("heat", 0),
                    "tags": it.get("tags", []),
                })
                used.add(id(it))
        sections.append({
            "key": sec["key"], "name": sec["name"], "color": sec["color"],
            "items": sec_items,
        })

    report = {
        "title": "AI 每日行业简报",
        "date": date,
        "window": "近 3 天（自动抓取精选）",
        "item_count": len(top3) + len(items),
        "core_conclusions": core,
        "top3": top3_out,
        "sections": sections,
        "observations": [],
        "notes": f"数据源：aihot.virxact.com 精选资讯（自动抓取）；本页由 GitHub Actions 每日自动构建，核心结论由当日 TOP3 自动提炼。构建于 {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')}。",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[ok] report_current.json written: {OUT}")
    print(f"     date={date} core={len(core)} top3={len(top3_out)} items={sum(len(s['items']) for s in sections)}")


if __name__ == "__main__":
    main()
