#!/usr/bin/env python3
"""build_single.py — 生成 AI 每日行业简报 index.html（宫格版，含核心结论/TOP3/4 板块/数据说明）

读 data/report_current.json（convert_current.py 产物）+ scripts/template.public.html，
输出 BASE/index.html；归档见 archive.html（build_archive.py 独立生成）。
"""
import html as html_mod
import json
import os
import re
import sys
import time
import datetime

BUILD_TS = str(int(time.time()))
BASE = os.environ.get("AI_DAILY_BASE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.public.html")
REPORT = os.path.join(BASE, "data", "report_current.json")
OUT = os.path.join(BASE, "index.html")

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0000200D\U0000200C]+"
)


def clean(s):
    return EMOJI_RE.sub("", str(s))


def esc(s):
    return html_mod.escape(clean(s), quote=False)


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def build():
    report = load(REPORT, None)
    if not report:
        print(f"ERROR build_single: {REPORT} not found (先跑 convert_current.py)", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(TPL):
        print(f"ERROR build_single: template not found: {TPL}", file=sys.stderr)
        sys.exit(1)
    with open(TPL, encoding="utf-8") as f:
        tpl = f.read()

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    WEEK = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    date_cn = f"{now.year}年{now.month}月{now.day}日 · {WEEK[now.weekday()]}"
    build_stamp = now.strftime("%Y-%m-%d %H:%M +08:00")

    # 核心结论
    core_html = ""
    for i, c in enumerate(report.get("core_conclusions", []), 1):
        core_html += f'<div class="core-item"><div class="num">{i}</div><p>{esc(c)}</p></div>\n'

    # TOP3 宫格卡（含热度）
    top3_html = ""
    for i, t in enumerate(report.get("top3", []), 1):
        heat = t.get("heat")
        heat_html = f'<span class="heat">🔥 {esc(str(heat))}</span>' if heat else ""
        top3_html += (
            f'<a class="t3" href="{esc(t.get("url", ""))}" target="_blank" rel="noopener">'
            f'<span class="rk">TOP {i:02d}</span>'
            f'<h3>{esc(t.get("title", ""))}</h3>'
            f'<p class="sum">{esc(t.get("summary", ""))}</p>'
            f'<div class="w"><span class="lb">值得跟进</span>{esc(t.get("why", ""))}</div>'
            f'<span class="foot"><span>{esc(t.get("source", ""))} · {esc(t.get("time", ""))}</span>{heat_html}</span>'
            f'<span class="go">打开来源 ↗</span>'
            f"</a>\n"
        )

    # 4 板块（policy 无数据时给占位说明）
    sections_html = ""
    sec_num = 2
    for s in report.get("sections", []):
        sec_num += 1
        color = s.get("color", "blue")
        items = s.get("items", [])
        if not items:
            sections_html += (
                f'<section id="s-{esc(s.get("key"))}">'
                f'<div class="sec-head"><span class="no">{sec_num:02d}</span><h2>{esc(s.get("name", ""))}</h2>'
                f'<span class="desc">0 条</span></div>'
                f'<div class="empty-note">近 3 天未检索到高置信新增动态。</div></section>\n'
            )
            continue
        items_html = ""
        for it in items:
            heat_html = f'<span class="heat">🔥 {esc(str(it.get("heat", "")))}</span>' if it.get("heat") else ""
            tags_html = "".join(f'<span class="tag">#{esc(t)}</span>' for t in it.get("tags", [])[:3])
            items_html += (
                '<div class="item"><div class="head">'
                f'<span class="chip {color}">{esc(s.get("name", ""))}</span>'
                f'<span class="dot"></span><span>{esc(it.get("time", ""))}</span>'
                f'<span class="dot"></span><span class="src">{esc(it.get("source", ""))}</span>'
                f"{heat_html}"
                "</div>"
                f'<h3><a href="{esc(it.get("url", ""))}" target="_blank" rel="noopener">{esc(it.get("title", ""))}</a></h3>'
                f'<p class="sum">{esc(it.get("summary", ""))}</p>'
                f'<div class="why {color}"><span class="lb">值得跟进</span><p>{esc(it.get("why", ""))}</p></div>'
                f'<div class="foot"><span>{tags_html or esc(it.get("source", ""))}</span>'
                f'<a href="{esc(it.get("url", ""))}" target="_blank" rel="noopener">打开来源 ↗</a></div>'
                "</div>\n"
            )
        sections_html += (
            f'<section id="s-{esc(s.get("key"))}">'
            f'<div class="sec-head"><span class="no">{sec_num:02d}</span><h2>{esc(s.get("name", ""))}</h2>'
            f'<span class="desc">{len(items)} 条</span></div>'
            f'<div class="items">{items_html}</div></section>\n'
        )

    # 观察点（自动管道为空，移除区块）
    obs_html = ""
    for o in report.get("observations", []):
        obs_html += f'<li><span class="dot"></span><span>{esc(o)}</span></li>\n'

    # 渲染
    html = tpl
    repl = {
        "{{TITLE}}": esc(report.get("title", "AI 每日行业简报")),
        "{{DATE_CN}}": date_cn,
        "{{WINDOW}}": esc(report.get("window", "")),
        "{{COUNT}}": str(report.get("item_count", "")),
        "{{BUILD}}": build_stamp,
        "{{CORE}}": core_html,
        "{{TOP3}}": top3_html,
        "{{SECTIONS}}": sections_html,
        "{{OBSERVATIONS}}": obs_html,
        "{{NOTES}}": esc(report.get("notes", "")),
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    # 观察点为空则移除整区块
    if not obs_html.strip():
        html = re.sub(r'<section id="obs">.*?</section>\n', "", html, flags=re.S)
    # 防缓存版本标记
    html = html.replace("<head>", f'<head>\n<meta name="ai-daily-build" content="{now.strftime("%Y-%m-%d")}|{BUILD_TS}">')
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[ok] index.html written ({os.path.getsize(OUT)} bytes) | date={report.get('date')} core={len(report.get('core_conclusions', []))} top3={len(report.get('top3', []))} items={sum(len(s.get('items', [])) for s in report.get('sections', []))}")


if __name__ == "__main__":
    build()
