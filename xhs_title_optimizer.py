#!/usr/bin/env python3
"""小红书标题优化器。
目标：减少模板腔和口号味，优先生成有对象、有变化、有后果的标题。
"""

import argparse
import json
import re
from pathlib import Path


DOMAIN_WORDS = {
    "ai": ["AI", "大模型", "ChatGPT", "OpenAI", "Claude", "Gemini", "模型", "广告", "Agent", "推理"],
    "news": ["更新", "发布", "测试", "变化", "功能", "服务"],
    "science": ["研究", "论文", "实验", "原理", "误区"],
    "travel": ["路线", "周末", "城市", "出发", "打卡"],
    "city": ["散步", "拍照", "路线", "周末", "街区"],
    "food": ["餐厅", "菜单", "排队", "人均", "口味"],
}


TITLE_PATTERNS = {
    "ai": [
        "别只看{subject}，先看{focus}",
        "{subject}的门槛在{focus}",
        "{subject}为什么值得盯",
        "{subject}真正难在{focus}",
        "{subject}背后的新信号",
        "{subject}，别忽略{focus}",
        "{subject}这次，变化在{focus}",
        "{subject}背后，是{judgment}",
        "{subject}不只是{focus}",
    ],
    "news": [
        "{subject}之后，{impact}",
        "{subject}，变化在{focus}",
        "{subject}背后，是{judgment}",
    ],
    "science": [
        "{subject}，关键不在{focus}",
        "{subject}背后，是{judgment}",
        "{subject}这件事，先看{focus}",
    ],
    "travel": [
        "{subject}，更适合这样走",
        "{subject}之后，路线要看{focus}",
        "{subject}这条线，重点在{focus}",
    ],
    "city": [
        "{subject}，更适合这样逛",
        "{subject}这次，别只看{focus}",
        "{subject}之后，拍照先看{focus}",
    ],
    "food": [
        "{subject}，重点在{focus}",
        "{subject}之后，先看{focus}",
        "{subject}背后，是{judgment}",
    ],
    "general": [
        "{subject}之后，{impact}",
        "{subject}，变化在{focus}",
        "{subject}背后，是{judgment}",
    ],
}


BAD_FRAGMENTS = [
    "开始",
    "开始像",
    "开始接",
    "开始拼",
    "也",
    "普通人",
    "记住这句",
    "重点不是",
    "别急着",
    "看完",
]

BAD_WORDS = [
    "震惊", "炸裂", "封神", "全网", "必看", "绝了", "天花板", "保姆级", "超详细",
]

STOP_ZH = {
    "这两天", "这次更新", "这个变化", "这件事", "很多人", "产品", "用户", "内容", "最近", "今天",
    "之后", "开始", "免费版", "普通人", "重点", "变化", "影响", "取舍",
}


def normalize(text):
    text = (text or "").replace("\\n", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact(text, limit=20):
    text = normalize(text)
    if len(text) <= limit:
        return text
    return text[:limit]


def find_subject(topic, body, domain):
    topic = normalize(topic)
    body = normalize(body)
    text = " ".join([topic, body])

    explicit_subjects = [
        r"ChatGPT",
        r"OpenAI",
        r"Claude(?: Code)?",
        r"Gemini",
        r"GPT-[0-9.]+",
        r"CAISI",
        r"NIST",
        r"Google DeepMind",
        r"Microsoft",
        r"xAI",
    ]
    for pattern in explicit_subjects:
        match = re.search(pattern, text, re.I)
        if match:
            subject = match.group(0)
            if domain == "ai" and "ChatGPT" in subject and "广告" in text:
                return "ChatGPT测试广告"
            return compact(subject, 14)

    for word in DOMAIN_WORDS.get(domain, []) + DOMAIN_WORDS.get("news", []):
        if word and word in text:
            if domain == "ai" and word in {"广告", "模型", "更新", "功能", "服务"}:
                continue
            return compact(word, 14)

    zh = re.findall(r"[\u4e00-\u9fffA-Za-z0-9.\-]{3,18}", text)
    for item in zh:
        item = item.strip("，。、“”‘’：:；;,.!?？")
        if not item or item in STOP_ZH:
            continue
        if "开始" in item or "普通人" in item:
            continue
        return compact(item, 14)

    return compact(topic or "这次更新", 14)


def infer_focus(topic, body, domain):
    text = normalize(" ".join([topic or "", body or ""]))
    focus_rules = [
        ("广告", "广告位"),
        ("额度", "额度"),
        ("限额", "限额"),
        ("免费", "免费版"),
        ("收费", "收费方式"),
        ("商业化", "商业化"),
        ("稳定", "稳定性"),
        ("语音", "语音能力"),
        ("安全", "安全评估"),
        ("评测", "上线前评测"),
        ("工具", "工具可用性"),
        ("回答", "回答本身"),
    ]
    for needle, label in focus_rules:
        if needle in text:
            return label
    default_focus = {
        "ai": "产品规则",
        "news": "实际影响",
        "science": "判断依据",
        "travel": "路线安排",
        "city": "出片点位",
        "food": "值不值得排队",
        "general": "真正变化",
    }
    return default_focus.get(domain, "真正变化")


def infer_impact(topic, body, domain):
    text = normalize(" ".join([topic or "", body or ""]))
    rules = [
        (("广告", "免费"), "免费版变了什么"),
        (("广告",), "真正变化不在回答里"),
        (("语音",), "开始往任务型工具走"),
        (("限额", "额度"), "先受影响的是重度用户"),
        (("安全", "评测"), "上线前评估正在前移"),
        (("稳定",), "比参数更影响体验"),
        (("商业化",), "产品比较维度变了"),
    ]
    for needles, impact in rules:
        if all(needle in text for needle in needles):
            return impact
    defaults = {
        "ai": "变化比参数更值得看",
        "news": "后续影响更值得看",
        "science": "误区往往比结论多",
        "travel": "路线安排比景点更重要",
        "city": "适合慢慢逛而不是赶点",
        "food": "决定体验的是细节",
        "general": "后果比表面更重要",
    }
    return defaults.get(domain, "后果比表面更重要")


def infer_judgment(topic, body, domain):
    text = normalize(" ".join([topic or "", body or ""]))
    if "广告" in text:
        return "免费AI进入产品经营期"
    if "额度" in text or "限额" in text:
        return "算力分配正在变成产品能力"
    if "安全" in text or "评测" in text:
        return "风险评估正在前置"
    if "语音" in text:
        return "语音助手开始卷交付能力"
    if "稳定" in text:
        return "稳定性比炫技更重要"
    defaults = {
        "ai": "AI产品竞争在转向细节",
        "news": "真正影响在后续落地",
        "science": "判断要回到证据",
        "general": "表面热闹不等于核心变化",
    }
    return defaults.get(domain, "核心变化不在表面")


def build_candidates(subject, focus, impact, judgment, domain):
    domain = domain if domain in TITLE_PATTERNS else "general"
    titles = []
    for pattern in TITLE_PATTERNS[domain] + TITLE_PATTERNS["general"]:
        title = pattern.format(
            subject=subject,
            focus=focus,
            impact=impact,
            judgment=judgment,
        )
        title = normalize(title)
        if len(title) > 20:
            continue
        titles.append(title)
    return titles


def score_title(title):
    score = 0
    length = len(title)
    if 10 <= length <= 18:
        score += 5
    elif length <= 20:
        score += 3
    else:
        score -= 3

    if any(word in title for word in ["变化", "影响", "背后", "取舍", "免费版", "门槛", "信号", "别只看", "为什么"]):
        score += 2
    if "，" in title:
        score += 1
    if any(fragment in title for fragment in BAD_FRAGMENTS):
        score -= 3
    if any(word in title for word in BAD_WORDS):
        score -= 5
    if title.count("了") >= 2:
        score -= 8
    if title.endswith("了"):
        score -= 20
    if re.search(r"(开始|变成|像|接|拼).{0,6}了$", title):
        score -= 12
    return score


def generate_titles(topic, body, domain="general", limit=8):
    subject = find_subject(topic, body, domain)
    focus = infer_focus(topic, body, domain)
    impact = infer_impact(topic, body, domain)
    judgment = infer_judgment(topic, body, domain)

    seen = set()
    titles = []
    for title in build_candidates(subject, focus, impact, judgment, domain):
        if title.endswith("了"):
            continue
        if title in seen:
            continue
        seen.add(title)
        titles.append({"title": title, "score": score_title(title)})
    titles.sort(key=lambda item: item["score"], reverse=True)
    return titles[:limit]


def main():
    parser = argparse.ArgumentParser(description="小红书标题优化器")
    parser.add_argument("--topic", default="")
    parser.add_argument("--body", default="")
    parser.add_argument("--body-file", default="")
    parser.add_argument("--domain", default="general")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    titles = generate_titles(args.topic, body, args.domain, args.limit)
    if args.json:
        print(json.dumps(titles, ensure_ascii=False, indent=2))
    else:
        for item in titles:
            print(f"{item['title']}  score={item['score']}")


if __name__ == "__main__":
    main()
