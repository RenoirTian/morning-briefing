#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Morning Briefing Script - HTML output"""

import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "briefing_" + datetime.now().strftime("%Y%m%d") + ".html")
REQUEST_TIMEOUT = 10
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def http_get(url, retries=1, referer="https://www.eastmoney.com/"):
    headers = {"User-Agent": UA, "Referer": referer}
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read()
                for enc in ["utf-8", "gbk", "gb2312", "gb18030"]:
                    try: return raw.decode(enc)
                    except: continue
                return raw.decode("utf-8", errors="replace")
        except Exception:
            if i == retries: return None
            time.sleep(1)
    return None

def fmt_num(n, decimals=2):
    if isinstance(n, (int, float)): return f"{n:.{decimals}f}"
    return str(n)

def fmt_change(val, is_pct=True):
    try:
        v = float(val); sign = "+" if v > 0 else ""
        return sign + (f"{v:.2f}%" if is_pct else f"{v:.2f}")
    except: return str(val)

def change_class(val):
    try:
        v = float(val)
        if v > 0: return "up"
        if v < 0: return "down"
        return ""
    except: return ""

# ---- A-share indices via Sina ----
SINA_INDICES = {
    "sh000001": "SH", "sz399001": "SZ", "sz399006": "CYB",
    "sh000688": "KC50", "sh000300": "HS300",
}

def fetch_a_indices():
    results = []
    codes = ",".join(SINA_INDICES.keys())
    text = http_get("http://hq.sinajs.cn/list=" + codes, referer="https://finance.sina.com.cn/")
    if not text: return results
    for code, tag in SINA_INDICES.items():
        try:
            prefix = "var hq_str_" + code + '="'
            start = text.index(prefix) + len(prefix)
            end = text.index('"', start)
            parts = text[start:end].split(",")
            if len(parts) >= 6:
                price = float(parts[1]) if parts[1] else 0
                prev = float(parts[2]) if parts[2] else 0
                change = price - prev if prev else 0
                change_pct = (change / prev * 100) if prev else 0
                high = float(parts[4]) if len(parts) > 4 and parts[4] else 0
                low = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                results.append({
                    "name": parts[0], "price": price, "change": change,
                    "change_pct": change_pct, "high": high, "low": low,
                })
        except: continue
    return results

# ---- US indices via Sina ----
US_SINA_CODES = {"gb_dji": "道琼斯", "gb_ixic": "纳斯达克", "gb_inx": "标普500"}

def fetch_us_indices():
    results = []
    codes = ",".join(US_SINA_CODES.keys())
    text = http_get("http://hq.sinajs.cn/list=" + codes, referer="https://finance.sina.com.cn/")
    if not text: return results
    for code, name in US_SINA_CODES.items():
        try:
            prefix = "var hq_str_" + code + '="'
            start = text.index(prefix) + len(prefix)
            end = text.index('"', start)
            parts = text[start:end].split(",")
            if len(parts) >= 5:
                price = float(parts[1]) if parts[1] else 0
                change_pct = float(parts[2]) if parts[2] else 0
                change = float(parts[4]) if parts[4] else 0
                results.append({"name": name, "price": price, "change": change, "change_pct": change_pct})
        except: continue
    return results

# ---- Top movers via Sina ----
def fetch_top_movers(sort_dir="desc", count=5):
    asc = "1" if sort_dir == "asc" else "0"
    url = (
        "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        "Market_Center.getHQNodeData?page=1&num=" + str(count + 5) +
        "&sort=changepercent&asc=" + asc + "&node=hs_a&symbol=&_s_r_a=auto"
    )
    text = http_get(url, referer="https://finance.sina.com.cn/")
    if not text: return []
    results = []
    try:
        for item in json.loads(text):
            pct = float(item.get("changepercent", 0))
            if sort_dir == "desc" and pct <= 0: continue
            if sort_dir == "asc" and pct >= 0: continue
            results.append({
                "code": item.get("symbol", ""),
                "name": item.get("name", ""),
                "price": item.get("price", item.get("trade", "N/A")),
                "change_pct": pct,
            })
            if len(results) >= count: break
    except: pass
    return results

# ---- New stocks / IPO via Sina ----
def fetch_new_stocks():
    url = (
        "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        "Market_Center.getHQNodeData?page=1&num=10&sort=changepercent&asc=0"
        "&node=new_stock&_s_r_a=auto"
    )
    text = http_get(url, referer="https://finance.sina.com.cn/")
    if not text: return []
    results = []
    try:
        for item in json.loads(text)[:6]:
            results.append({
                "code": item.get("symbol", ""),
                "name": item.get("name", ""),
                "price": item.get("trade", "N/A"),
                "change_pct": float(item.get("changepercent", 0)),
                "open": item.get("open", "N/A"),
            })
    except: pass
    return results

# ---- Finance news via Sina ----
def fetch_finance_news():
    items = []
    ts = int(time.time() * 1000)
    try:
        url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=8&page=1&_=" + str(ts)
        text = http_get(url, referer="https://finance.sina.com.cn/")
        if text:
            for item in json.loads(text).get("result", {}).get("data", [])[:8]:
                t = item.get("title", "").strip()
                u = item.get("url", "")
                if t: items.append({"title": t, "url": u, "source": "Sina"})
    except: pass
    return items

# ---- Tech news via IT之家 ----
def fetch_tech_news():
    items = []
    try:
        text = http_get("https://api.ithome.com/json/newslist/news?page=1", referer="https://www.ithome.com/")
        if text:
            ad_words = ["清仓", "元官方", "到手", "仅售", "秒杀", "立减", "大促", "神价"]
            for item in json.loads(text).get("newslist", []):
                t = item.get("title", "")
                api_url = item.get("url", "")
                nid = str(item.get("newsid", ""))
                # Skip ads (lapin subdomain = sponsored)
                if "lapin" in api_url:
                    continue
                if any(w in t for w in ad_words):
                    continue
                # Use API url field when it's a relative path (e.g. /0/961/118.htm)
                if api_url and api_url.startswith("/"):
                    url = "https://www.ithome.com" + api_url
                elif len(nid) >= 6:
                    url = "https://www.ithome.com/0/" + nid[:3] + "/" + nid[3:] + ".htm"
                else:
                    url = ""
                if t: items.append({"title": t, "url": url, "source": "ITHome"})
                if len(items) >= 6:
                    break
    except: pass
    return items

# ---- HTML Generation ----
CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #0a0e17;
    color: #c9d1d9;
    min-height: 100vh;
    padding: 20px;
}
.container { max-width: 960px; margin: 0 auto; }

.header {
    text-align: center;
    padding: 32px 20px 24px;
    background: linear-gradient(135deg, #0d1525 0%, #111b2e 50%, #0d1525 100%);
    border: 1px solid #1e2d45;
    border-radius: 16px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.header::before {
    content: "";
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #00d4ff, #7b61ff, #00d4ff, transparent);
}
.header h1 {
    font-size: 28px; font-weight: 700;
    background: linear-gradient(135deg, #00d4ff, #7b61ff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 4px;
}
.header .date { font-size: 14px; color: #5a6a85; letter-spacing: 1px; }
.header .time { font-size: 12px; color: #3d4f6b; margin-top: 4px; }

.section {
    background: #0d1525;
    border: 1px solid #1e2d45;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    transition: border-color 0.3s;
}
.section:hover { border-color: #2a3f5f; }
.section-title {
    font-size: 16px; font-weight: 600; color: #00d4ff;
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}
.section-title .icon { font-size: 18px; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.stat-card {
    background: #111b2e; border: 1px solid #1e2d45; border-radius: 10px;
    padding: 14px 16px; text-align: center;
    transition: transform 0.2s, border-color 0.2s;
}
.stat-card:hover { transform: translateY(-2px); border-color: #2a3f5f; }
.stat-card .label { font-size: 12px; color: #5a6a85; margin-bottom: 6px; letter-spacing: 0.5px; }
.stat-card .value { font-size: 22px; font-weight: 700; color: #e6edf3; font-variant-numeric: tabular-nums; }
.stat-card .change { font-size: 13px; margin-top: 4px; font-weight: 600; }
.stat-card .sub { font-size: 11px; color: #5a6a85; margin-top: 2px; }

table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; color: #5a6a85; font-weight: 500; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #1e2d45; }
td { padding: 10px 12px; border-bottom: 1px solid #111b2e; font-variant-numeric: tabular-nums; }
tr:hover td { background: #111b2e; }

.up { color: #00d4aa; }
.down { color: #ff4d6a; }

.news-list { list-style: none; }
.news-list li {
    padding: 10px 0; border-bottom: 1px solid #111b2e;
    font-size: 14px; line-height: 1.5; display: flex; gap: 10px; align-items: baseline;
}
.news-list li:last-child { border-bottom: none; }
.news-list .tag {
    display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 4px;
    font-weight: 600; letter-spacing: 0.5px; flex-shrink: 0;
}
.tag-sina { background: #1a2a3d; color: #00d4ff; }
.tag-ithome { background: #2d1a1a; color: #ff6b6b; }

.news-list a {
    color: #c9d1d9; text-decoration: none; transition: color 0.2s;
}
.news-list a:hover { color: #00d4ff; text-decoration: underline; }

.footer { text-align: center; padding: 16px; color: #3d4f6b; font-size: 11px; margin-top: 16px; }

.live-dot {
    display: inline-block; width: 8px; height: 8px; background: #00d4aa;
    border-radius: 50%; animation: pulse 2s infinite; margin-right: 4px;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

@media (max-width: 600px) {
    body { padding: 12px; }
    .header { padding: 20px 16px; }
    .header h1 { font-size: 22px; }
    .section { padding: 14px 16px; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    table { font-size: 12px; }
    th, td { padding: 8px 6px; }
}
"""

def generate_html(a, us, gainers, losers, new_stocks, fin_news, tech_news):
    now = datetime.now()
    wd = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][now.weekday()]
    cn_wd = ["一","二","三","四","五","六","日"][now.weekday()]

    h = ['<!DOCTYPE html><html lang="zh-CN"><head>']
    h.append('<meta charset="UTF-8">')
    h.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    h.append('<title>Morning Briefing - ' + now.strftime("%Y-%m-%d") + '</title>')
    h.append('<style>' + CSS + '</style>')
    h.append('</head><body><div class="container">')

    # Header
    h.append('<div class="header">')
    h.append('<h1><span class="live-dot"></span>Morning Briefing</h1>')
    h.append('<div class="date">' + now.strftime("%Y-%m-%d") + ' ' + wd + ' (' + cn_wd + ')</div>')
    h.append('<div class="time">Generated ' + now.strftime("%H:%M:%S") + ' HKT</div>')
    h.append('</div>')

    # A-Share Indices
    if a:
        h.append('<div class="section">')
        h.append('<div class="section-title"><span class="icon">&#x1f4c8;</span>A-Share Indices</div>')
        h.append('<div class="stats-grid">')
        for x in a:
            cls = change_class(x["change_pct"])
            si = ""
            if x.get("high") and x["high"] != "N/A":
                si = 'H ' + fmt_num(x["high"]) + ' / L ' + fmt_num(x["low"])
            h.append('<div class="stat-card"><div class="label">' + x["name"] + '</div>')
            h.append('<div class="value">' + fmt_num(x["price"]) + '</div>')
            h.append('<div class="change ' + cls + '">' + fmt_change(x["change_pct"]) + '</div>')
            if si: h.append('<div class="sub">' + si + '</div>')
            h.append('</div>')
        h.append('</div></div>')

    # US Indices
    if us:
        h.append('<div class="section">')
        h.append('<div class="section-title"><span class="icon">&#x1f1fa;&#x1f1f8;</span>US Indices</div>')
        h.append('<div class="stats-grid">')
        for x in us:
            cls = change_class(x["change_pct"])
            h.append('<div class="stat-card"><div class="label">' + x["name"] + '</div>')
            h.append('<div class="value">' + fmt_num(x["price"]) + '</div>')
            h.append('<div class="change ' + cls + '">' + fmt_change(x["change"], False) + ' (' + fmt_change(x["change_pct"]) + ')</div>')
            h.append('</div>')
        h.append('</div></div>')

    # Market Movers
    if gainers or losers:
        h.append('<div class="section">')
        h.append('<div class="section-title"><span class="icon">&#x26a1;</span>Market Movers</div>')
        if gainers:
            h.append('<div style="margin-bottom:20px">')
            h.append('<div style="font-size:14px;color:#00d4aa;margin-bottom:10px;font-weight:600">&#x1f680; Top Gainers</div>')
            h.append('<table><thead><tr><th>Code</th><th>Name</th><th>Price</th><th>Change</th></tr></thead><tbody>')
            for s in gainers:
                h.append('<tr><td>' + s["code"] + '</td><td>' + s["name"] + '</td><td>' + fmt_num(s["price"]) + '</td><td class="up">' + fmt_change(s["change_pct"]) + '</td></tr>')
            h.append('</tbody></table></div>')
        if losers:
            h.append('<div>')
            h.append('<div style="font-size:14px;color:#ff4d6a;margin-bottom:10px;font-weight:600">&#x1f4c9; Top Losers</div>')
            h.append('<table><thead><tr><th>Code</th><th>Name</th><th>Price</th><th>Change</th></tr></thead><tbody>')
            for s in losers:
                h.append('<tr><td>' + s["code"] + '</td><td>' + s["name"] + '</td><td>' + fmt_num(s["price"]) + '</td><td class="down">' + fmt_change(s["change_pct"]) + '</td></tr>')
            h.append('</tbody></table></div>')
        h.append('</div>')

    # New Stocks / IPO
    if new_stocks:
        h.append('<div class="section">')
        h.append('<div class="section-title"><span class="icon">&#x1f195;</span>New Stocks / IPO</div>')
        h.append('<table><thead><tr><th>Code</th><th>Name</th><th>Price</th><th>Change</th><th>Open</th></tr></thead><tbody>')
        for s in new_stocks:
            cls = change_class(s["change_pct"])
            h.append('<tr><td>' + s["code"] + '</td><td>' + s["name"] + '</td><td>' + fmt_num(s["price"]) + '</td><td class="' + cls + '">' + fmt_change(s["change_pct"]) + '</td><td>' + fmt_num(s["open"]) + '</td></tr>')
        h.append('</tbody></table></div>')

    # Finance News (with links)
    if fin_news:
        h.append('<div class="section">')
        h.append('<div class="section-title"><span class="icon">&#x1f4f0;</span>Finance Headlines</div>')
        h.append('<ul class="news-list">')
        for item in fin_news[:8]:
            tag_cls = "tag-sina"
            title_html = item["title"]
            if item.get("url"):
                title_html = '<a href="' + item["url"] + '" target="_blank" rel="noopener">' + item["title"] + '</a>'
            h.append('<li><span class="tag ' + tag_cls + '">' + item["source"] + '</span>' + title_html + '</li>')
        h.append('</ul></div>')

    # Tech News (with links)
    if tech_news:
        h.append('<div class="section">')
        h.append('<div class="section-title"><span class="icon">&#x1f4bb;</span>Tech News</div>')
        h.append('<ul class="news-list">')
        for item in tech_news[:6]:
            title_html = item["title"]
            if item.get("url"):
                title_html = '<a href="' + item["url"] + '" target="_blank" rel="noopener">' + item["title"] + '</a>'
            h.append('<li><span class="tag tag-ithome">' + item["source"] + '</span>' + title_html + '</li>')
        h.append('</ul></div>')

    # Footer
    h.append('<div class="footer">Auto-generated by Morning Briefing &middot; For reference only &middot; Not investment advice</div>')
    h.append('</div></body></html>')
    return "\n".join(h)

def main():
    print("=" * 50)
    print("  Morning Briefing - Generating HTML...")
    print("=" * 50)
    print("[1/7] A-Share indices...", end=" ", flush=True)
    a = fetch_a_indices()
    print(str(len(a)) + " found")
    print("[2/7] US indices...", end=" ", flush=True)
    us = fetch_us_indices()
    print(str(len(us)) + " found")
    print("[3/7] Top gainers...", end=" ", flush=True)
    gainers = fetch_top_movers("desc", 5)
    print(str(len(gainers)) + " found")
    print("[4/7] Top losers...", end=" ", flush=True)
    losers = fetch_top_movers("asc", 5)
    print(str(len(losers)) + " found")
    print("[5/7] New stocks...", end=" ", flush=True)
    ns = fetch_new_stocks()
    print(str(len(ns)) + " found")
    print("[6/7] Finance news...", end=" ", flush=True)
    fn = fetch_finance_news()
    print(str(len(fn)) + " found")
    print("[7/7] Tech news...", end=" ", flush=True)
    tn = fetch_tech_news()
    print(str(len(tn)) + " found")
    html = generate_html(a, us, gainers, losers, ns, fn, tn)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("")
    print("Report saved: " + OUTPUT_FILE)

if __name__ == "__main__":
    main()