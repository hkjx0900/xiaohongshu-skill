#!/usr/bin/env python3
"""小红书趋势采集与选题候选生成。

目标：把“站内观察/公开榜单/关键词热度/历史发帖”整理成可执行选题。

当前默认不自动刷小红书站内页面，避免账号被判定为脚本行为。站内搜索结果
先通过 --xhs-notes 文本文件导入：把搜索页标题、笔记标题、话题词、互动数等
复制成 txt/md 即可纳入评分。
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "output"

STOPWORDS = {
    "一个", "这个", "那个", "今天", "真的", "可以", "适合", "感觉", "分享", "一下",
    "小红书", "笔记", "发布", "内容", "推荐", "看看", "怎么", "什么", "自己",
}

DOMAIN_RULES = {
    "general": [
        ("今日可用清单", ["清单", "今日", "方法", "步骤", "模板"], "{prefix}{keyword}｜今天就能用", "给一个能立刻照做的清单。"),
        ("真实体验/避坑", ["避坑", "真实", "体验", "后悔", "踩雷"], "{prefix}{keyword}，我会注意这几点", "先说真实结论，再说具体细节。"),
        ("反直觉发现", ["反直觉", "误区", "原来", "真相"], "{keyword}这件事，很多人理解反了", "用一个常见误区开头。"),
    ],
    "city": [
        ("今日可用清单", ["清单", "今日", "周末", "出门", "路线", "攻略", "半日"], "{prefix}{keyword}｜今天就能照着走", "把今天能直接用的安排放在首屏。"),
        ("低预算快乐", ["低预算", "省钱", "免费", "平价", "人均", "不花钱"], "{prefix}低预算{keyword}，不用赶路", "给出花费、时间和适合人群。"),
        ("颜色/视觉主题", ["ColorWalk", "颜色", "蓝色", "绿色", "九宫格", "拍照", "出片"], "{prefix}{keyword}，周末拍一组同色系", "封面用统一色块，正文讲怎么找细节。"),
    ],
    "travel": [
        ("小众路线", ["小众", "错峰", "高铁", "短途", "周末", "路线"], "{keyword}，这条路线比热门景点轻松", "先给适合人群和时间成本。"),
        ("预算清单", ["预算", "人均", "省钱", "平价", "花费"], "{keyword}预算清单，出发前先看", "把交通、住宿、吃饭拆成清单。"),
        ("避坑攻略", ["避坑", "排队", "预约", "踩雷"], "{keyword}避坑，我会提前做这几件事", "写真实限制，不夸张推荐。"),
    ],
    "science": [
        ("反直觉科普", ["反直觉", "误区", "原理", "真相", "为什么"], "{keyword}这件事，很多人理解反了", "用生活例子解释一个原理。"),
        ("三点讲清", ["科普", "知识", "解释", "区别", "判断"], "{keyword}，用 3 点讲明白", "每点只讲一句人话。"),
        ("新闻拆解", ["新闻", "报告", "研究", "发布", "发现"], "{keyword}新闻，普通人看这一点就够了", "不堆术语，讲影响和边界。"),
    ],
    "ai": [
        ("AI 新闻拆解", ["AI", "模型", "OpenAI", "Anthropic", "Google", "发布", "新闻"], "{keyword}这条 AI 新闻，重点不是炫技", "讲清发生了什么、为什么重要、普通人怎么理解。"),
        ("工具工作流", ["工具", "工作流", "Agent", "自动化", "效率"], "{keyword}能省时间，但别先急着上手", "给一个前后对比场景。"),
        ("风险/边界", ["安全", "漏洞", "评估", "风险", "隐私", "版权"], "{keyword}提醒我：AI 也要看边界", "把风险说成人能懂的场景。"),
    ],
    "news": [
        ("一分钟新闻", ["新闻", "发布", "报告", "宣布", "更新"], "{keyword}，一分钟讲清楚", "先讲结论，再讲影响。"),
        ("普通人影响", ["影响", "变化", "政策", "行业"], "{keyword}和普通人有什么关系", "把宏大新闻落到生活/工作场景。"),
    ],
    "food": [
        ("点单公式", ["点单", "菜单", "人均", "探店", "平价"], "{keyword}点单，我会这样选", "给预算和避雷菜。"),
        ("家常复刻", ["家常", "教程", "复刻", "减脂", "便当"], "{keyword}，家里也能做个七八分", "步骤不要太整齐，保留真实口感。"),
    ],
    "fashion": [
        ("场景穿搭", ["穿搭", "通勤", "显瘦", "显高", "配色"], "{keyword}穿搭，今天这样出门", "讲天气、场景和一个关键单品。"),
    ],
    "health": [
        ("误区澄清", ["健康", "误区", "指标", "习惯", "睡眠"], "{keyword}这个误区，先别急着照做", "避免医疗建议，讲信息来源和就医边界。"),
    ],
    "home": [
        ("前后对比", ["收纳", "小户型", "改造", "动线", "好物"], "{keyword}前后对比，变化最大的是这里", "封面用对比，正文写真实尺寸和预算。"),
    ],
    "education": [
        ("阶段清单", ["学习", "教育", "孩子", "英语", "考试"], "{keyword}，这个阶段先抓 3 件事", "给阶段、问题和可执行动作。"),
    ],
}

DOMAIN_ALIASES = {
    "科普": "science",
    "科学": "science",
    "旅游": "travel",
    "旅行": "travel",
    "AI": "ai",
    "人工智能": "ai",
    "新闻": "news",
    "美食": "food",
    "穿搭": "fashion",
    "健康": "health",
    "家居": "home",
    "教育": "education",
    "城市": "city",
}

SOURCE_WEIGHTS = {
    "xhs_notes": 1.5,
    "public_notes": 1.1,
    "history": 0.9,
    "seed": 0.7,
}


def safe_output_dir(path):
    output_dir = Path(path)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = output_dir / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return output_dir
    except PermissionError:
        fallback = Path.cwd() / "xhs-output"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def read_text_files(paths):
    items = []
    for raw in paths or []:
        path = Path(raw)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line:
                items.append(line)
    return items


def load_history(paths):
    items = []
    for base in paths or []:
        root = Path(base)
        if not root.exists():
            continue
        for path in list(root.glob("copywriting_*.md")) + list(root.glob("publish_result_*.json")):
            try:
                if path.suffix == ".json":
                    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
                    copy = data.get("copywriting", {})
                    text = "\n".join(str(copy.get(k, "")) for k in ["title", "body", "tags"])
                else:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                items.extend(line.strip() for line in text.splitlines() if line.strip())
            except Exception:
                continue
    return items


def tokenize(text):
    words = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9#+-]{1,}|[\u4e00-\u9fff]{2,}", text):
        if token in STOPWORDS:
            continue
        if len(token) > 18 and re.fullmatch(r"[\u4e00-\u9fff]+", token):
            for i in range(0, len(token) - 1, 2):
                words.append(token[i:i + 4])
        else:
            words.append(token)
    return words


def extract_metrics(text):
    score = 0
    for number, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(万|w|W|k|K)?", text):
        value = float(number)
        if unit in {"万", "w", "W"}:
            value *= 10000
        elif unit in {"k", "K"}:
            value *= 1000
        if value >= 1000:
            score += min(value / 10000, 20)
    return score


def build_records(seeds, xhs_notes, public_notes, history):
    records = []
    for source, lines in [
        ("seed", seeds or []),
        ("xhs_notes", xhs_notes),
        ("public_notes", public_notes),
        ("history", history),
    ]:
        for line in lines:
            records.append({
                "source": source,
                "text": line,
                "tokens": tokenize(line),
                "metric_score": extract_metrics(line),
            })
    return records


def score_keywords(records):
    weighted = Counter()
    examples = defaultdict(list)
    for record in records:
        weight = SOURCE_WEIGHTS.get(record["source"], 1.0)
        weight += record["metric_score"] * 0.05
        for token in record["tokens"]:
            weighted[token] += weight
            if len(examples[token]) < 3:
                examples[token].append(record["text"])
    return weighted, examples


def normalize_domain(domain):
    if not domain:
        return "general"
    return DOMAIN_ALIASES.get(domain, domain if domain in DOMAIN_RULES else "general")


def domain_rules(domain):
    key = normalize_domain(domain)
    rules = DOMAIN_RULES.get(key, DOMAIN_RULES["general"])
    if key != "general":
        rules = rules + DOMAIN_RULES["general"]
    return [
        {
            "name": name,
            "keywords": keywords,
            "formats": ["note", "video"],
            "title": title,
            "hook": hook,
        }
        for name, keywords, title, hook in rules
    ]


def match_angles(keyword, domain):
    matched = []
    for rule in domain_rules(domain):
        if any(k.lower() in keyword.lower() or keyword.lower() in k.lower() for k in rule["keywords"]):
            matched.append(rule)
    return matched or [domain_rules(domain)[0]]


def make_candidates(keyword_scores, examples, city, domain, limit):
    candidates = []
    prefix = city or ""
    for keyword, score in keyword_scores.most_common(80):
        if city and keyword == city:
            continue
        if city and keyword.startswith(city):
            keyword = keyword[len(city):] or keyword
        if keyword in STOPWORDS or len(keyword) < 2:
            continue
        if any(item["keyword"] == keyword for item in candidates):
            continue
        for rule in match_angles(keyword, domain):
            title = rule["title"].format(prefix=prefix, city=prefix, keyword=keyword)
            candidate = {
                "domain": normalize_domain(domain),
                "keyword": keyword,
                "score": round(score, 2),
                "angle": rule["name"],
                "formats": rule["formats"],
                "title": title[:28],
                "hook": rule["hook"],
                "cover": f"首屏放“{keyword} + 一句话结论/关键数字/影响”，配 3:4 高可读封面",
                "image_source": "ai、screenshot 或 web；新闻/科普类优先信息图和网页截图二次整理",
                "note_outline": ["发生了什么", "为什么值得看", "普通人怎么理解", "风险/边界或下一步"],
                "video_opening": f"先说结论：{keyword}这件事，重点不只是热闹。",
                "evidence": examples.get(keyword, [])[:3],
            }
            candidates.append(candidate)
            break
        if len(candidates) >= limit:
            break
    return candidates


def write_markdown(payload, path):
    lines = [
        f"# 小红书趋势候选｜{payload['domain']}｜{payload['city'] or '不限城市'}",
        "",
        f"- 生成时间：{payload['generated_at']}",
        f"- 数据源：{', '.join(payload['sources'])}",
        "",
        "## 选题候选",
    ]
    for i, item in enumerate(payload["candidates"], 1):
        lines.extend([
            "",
            f"### {i}. {item['title']}",
            f"- 关键词：{item['keyword']}",
            f"- 分数：{item['score']}",
            f"- 角度：{item['angle']}",
            f"- 适合形态：{', '.join(item['formats'])}",
            f"- 开头：{item['hook']}",
            f"- 封面：{item['cover']}",
            f"- 笔记结构：{' / '.join(item['note_outline'])}",
            f"- 视频开头：{item['video_opening']}",
        ])
        if item["evidence"]:
            lines.append("- 证据样例：")
            lines.extend(f"  - {e}" for e in item["evidence"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="小红书趋势采集与选题候选生成")
    parser.add_argument("--city", default="")
    parser.add_argument("--domain", default="general", help="领域：general/city/travel/science/ai/news/food/fashion/health/home/education")
    parser.add_argument("--seeds", nargs="*", default=[])
    parser.add_argument("--xhs-notes", nargs="*", default=[], help="手动导出的站内搜索/话题结果 txt/md")
    parser.add_argument("--public-notes", nargs="*", default=[], help="公开榜单/行业观察 txt/md")
    parser.add_argument("--history-dir", nargs="*", default=[], help="历史发布输出目录，默认不纳入，避免跨领域污染")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    xhs_notes = read_text_files(args.xhs_notes)
    public_notes = read_text_files(args.public_notes)
    history = load_history(args.history_dir)
    records = build_records(args.seeds, xhs_notes, public_notes, history)

    if not records:
        records = build_records(
            ["周末去哪儿", "CityWalk", "ColorWalk", "低预算快乐", "今日可用清单", "拍照灵感"],
            [],
            [],
            [],
        )

    keyword_scores, examples = score_keywords(records)
    candidates = make_candidates(keyword_scores, examples, args.city, args.domain, args.limit)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "domain": normalize_domain(args.domain),
        "city": args.city,
        "sources": sorted({record["source"] for record in records}),
        "record_count": len(records),
        "top_keywords": [{"keyword": k, "score": round(v, 2)} for k, v in keyword_scores.most_common(30)],
        "candidates": candidates,
    }

    output_dir = safe_output_dir(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"trends_{stamp}.json"
    md_path = output_dir / f"trends_{stamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(payload, md_path)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"趋势候选已保存：{md_path}")
        print(f"JSON 已保存：{json_path}")
        for item in candidates[:5]:
            print(f"- {item['title']} ({item['angle']}, score={item['score']})")


if __name__ == "__main__":
    main()
