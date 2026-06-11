"""从 ESPN API 抓取世界杯比分并写入 scores.json"""
import json, urllib.request, os, re
from datetime import datetime, timezone

API = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
OUTPUT = "scores.json"

NAME_MAP = {
    "Mexico": "墨西哥", "South Africa": "南非", "South Korea": "韩国", "Czechia": "捷克",
    "Canada": "加拿大", "Bosnia & Herzegovina": "波黑", "Qatar": "卡塔尔",
    "Switzerland": "瑞士", "Brazil": "巴西", "Morocco": "摩洛哥",
    "Haiti": "海地", "Scotland": "苏格兰", "United States": "美国",
    "Paraguay": "巴拉圭", "Australia": "澳大利亚", "Turkey": "土耳其",
    "Germany": "德国", "Curaçao": "库拉索", "Ivory Coast": "科特迪瓦",
    "Ecuador": "厄瓜多尔", "Netherlands": "荷兰", "Japan": "日本", "Sweden": "瑞典",
    "Tunisia": "突尼斯", "Spain": "西班牙", "Cape Verde": "佛得角",
    "Saudi Arabia": "沙特", "Uruguay": "乌拉圭", "Belgium": "比利时", "Egypt": "埃及",
    "Iran": "伊朗", "New Zealand": "新西兰", "France": "法国", "Senegal": "塞内加尔",
    "Iraq": "伊拉克", "Norway": "挪威", "Argentina": "阿根廷", "Algeria": "阿尔及利亚",
    "Austria": "奥地利", "Jordan": "约旦", "Portugal": "葡萄牙",
    "DR Congo": "民主刚果", "Uzbekistan": "乌兹别克", "Colombia": "哥伦比亚",
    "England": "英格兰", "Croatia": "克罗地亚", "Ghana": "加纳", "Panama": "巴拿马",
}

# Build match map from HTML data
MATCH_MAP = {}
content = open("index.html", encoding="utf-8").read()
gm_start = content.find("const GM=[")
gm_end = content.find("];", gm_start) + 2
gm_code = content[gm_start:gm_end]
ns = {}
exec(gm_code, ns)

for m in ns["GM"]:
    mn, date, bj, local, t1, t2, g, rnd, skey, *_ = m
    t1n = re.sub(r"^[^一-鿿]*", "", t1)
    t2n = re.sub(r"^[^一-鿿]*", "", t2)
    d = date.split("(")[0]
    MATCH_MAP[(d, t1n, t2n)] = mn
    MATCH_MAP[(d, t2n, t1n)] = mn

print(f"Loaded {len(MATCH_MAP)} match mappings")

try:
    req = urllib.request.Request(API, headers={"User-Agent": "WC2026-Bot/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    events = data.get("events", [])
    print(f"Fetched {len(events)} events from ESPN")

    scores = {}
    for e in events:
        comp = e.get("competitions", [{}])[0]
        teams = comp.get("competitors", [])
        if len(teams) < 2:
            continue
        t1_en = teams[0].get("team", {}).get("displayName", "")
        t2_en = teams[1].get("team", {}).get("displayName", "")
        s1 = int(teams[0].get("score", "0") or 0)
        s2 = int(teams[1].get("score", "0") or 0)
        state = e.get("status", {}).get("type", {}).get("state", "pre")
        if state == "pre":
            continue

        t1_cn = NAME_MAP.get(t1_en, "")
        t2_cn = NAME_MAP.get(t2_en, "")
        if not t1_cn or not t2_cn:
            print(f"  Unknown: {t1_en} vs {t2_en}")
            continue

        found = False
        for key, mn in MATCH_MAP.items():
            d, tn1, tn2 = key
            if tn1 == t1_cn and tn2 == t2_cn:
                scores[mn] = {"t1s": s1, "t2s": s2}
                print(f"  {mn}: {t1_cn} {s1}-{s2} {t2_cn} [{state}]")
                found = True
                break
        if not found:
            print(f"  No match: {t1_en} vs {t2_en}")

    existing = {"updated": "", "source": "", "matches": {}}
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            existing = json.load(f)
    existing["matches"].update(scores)
    existing["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    existing["source"] = "ESPN API"
    with open(OUTPUT, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"Updated scores.json ({len(existing['matches'])} results)")

except Exception as ex:
    print(f"API error (non-fatal): {ex}")
