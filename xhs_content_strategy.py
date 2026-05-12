#!/usr/bin/env python3
"""小红书选题与素材策略生成器。

该模块不直接联网，负责把近期沉淀的趋势打法转成可执行 brief。
联网搜集热点可以由外层代理完成，再把观察结果写入 --trend-note。
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "output"


TREND_PLAYBOOK = [
    "真实体验优先：少写广告腔，多写具体场景、路线、花费、避坑和个人感受。",
    "标题前 12 字给出强利益点：省钱、避坑、清单、路线、模板、对比、今日可用。",
    "城市生活内容适合绑定天气、通勤、citywalk、周末、穿搭、拍照光线。",
    "图文封面要像可保存的小卡片：一句结论 + 关键数字 + 城市/场景信号。",
    "正文结构用 3-5 个短段：现状判断、适合谁、怎么做、注意事项、互动问题。",
    "标签组合避免堆砌：2 个大词 + 2 个场景词 + 1 个城市/人群词。",
    "视频预留同一主题的 15-30 秒脚本：开头 2 秒给结论，中段 3 个镜头，结尾 CTA。",
]


TOPIC_ANGLES = {
    "天气": [
        "今日出门穿搭建议",
        "通勤/下班路上的体感提醒",
        "适合拍照或 citywalk 的时间段",
        "早晚温差和随身物品清单",
    ],
    "城市": [
        "本地人半日路线",
        "不踩雷周末安排",
        "低预算城市散步",
        "适合一个人的放空地点",
    ],
    "美食": [
        "人均预算和点单公式",
        "排队/预约/避雷信息",
        "适合拍照的座位和时间",
        "同价位替代选择",
    ],
    "AI": [
        "普通人今天就能用的工作流",
        "前后对比案例",
        "提示词模板",
        "省时间的具体数字",
    ],
}


def infer_bucket(topic: str) -> str:
    for key in TOPIC_ANGLES:
        if key in topic:
            return key
    return "城市"


def build_strategy(topic, city, content_format, image_source, trend_note):
    bucket = infer_bucket(topic)
    angles = TOPIC_ANGLES[bucket]
    city_part = city or "本地"
    title_templates = [
        f"{city_part}今天适合这样安排｜{topic}",
        f"{city_part}{topic}：出门前先看这篇",
        f"{city_part}今日可用清单｜{topic}",
    ]

    image_plan = {
        "ai": "生成 3:4 封面，文字包含城市、结论和关键数字；画面要有真实城市信号。",
        "web": "搜索公开网页图片并优化成 3:4，避免侵权风险，优先用可授权或自制素材。",
        "screenshot": "截取天气/地图/公开页面的关键信息区域，再做封面化裁切和标注。",
        "auto": "优先 AI 生成图；需要事实背书时补充官方网页截图或真实信息源；再考虑信息图排版、本地图片或网页素材。",
        "local": "使用本地图片，保持 3:4 和高可读封面文字。",
        "none": "只生成选题和文案策略，暂不规划图片素材。",
    }.get(image_source, "使用本地图片，保持 3:4 和高可读封面文字。")

    video_plan = [
        "0-2s：直接给结论，画面放城市/天气/核心场景。",
        "3-12s：三个镜头说明体感、穿搭、适合安排。",
        "13-20s：给避坑提醒或保存理由。",
        "结尾：一句互动问题，比如“你今天准备去哪？”",
    ]

    return {
        "topic": topic,
        "city": city,
        "format": content_format,
        "recommended_angle": angles[0],
        "angles": angles,
        "title_candidates": title_templates,
        "cover_rule": "封面=一句结论 + 关键数字 + 城市信号；宁可信息密度高，也不要纯氛围图。",
        "image_source": image_source,
        "image_plan": image_plan,
        "body_structure": [
            "一句话结论",
            "具体场景与体感",
            "3 条可执行建议",
            "提醒或避坑",
            "互动问题",
        ],
        "tags": [f"#{city_part}生活", f"#{topic}", "#今日可用", "#周末出门", "#实用分享"],
        "video_plan": video_plan,
        "trend_playbook": TREND_PLAYBOOK,
        "trend_note": trend_note,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def write_markdown(strategy, path):
    lines = [
        f"# 小红书内容策略｜{strategy['topic']}",
        "",
        f"- 城市：{strategy['city'] or '未指定'}",
        f"- 推荐角度：{strategy['recommended_angle']}",
        f"- 素材方式：{strategy['image_source']} - {strategy['image_plan']}",
        "",
        "## 标题候选",
    ]
    lines.extend(f"- {title}" for title in strategy["title_candidates"])
    lines.extend(["", "## 正文结构"])
    lines.extend(f"- {item}" for item in strategy["body_structure"])
    lines.extend(["", "## 视频预案"])
    lines.extend(f"- {item}" for item in strategy["video_plan"])
    lines.extend(["", "## 标签", " ".join(strategy["tags"])])
    lines.extend(["", "## 趋势打法"])
    lines.extend(f"- {item}" for item in strategy["trend_playbook"])
    if strategy["trend_note"]:
        lines.extend(["", "## 外部趋势观察", strategy["trend_note"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="小红书内容策略生成器")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--city", default="")
    parser.add_argument("--format", choices=["note", "video"], default="note")
    parser.add_argument("--image-source", choices=["auto", "ai", "web", "screenshot", "local", "none"], default="auto")
    parser.add_argument("--trend-note", default="")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    strategy = build_strategy(args.topic, args.city, args.format, args.image_source, args.trend_note)
    output_dir = Path(args.out_dir)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = output_dir / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except PermissionError:
        output_dir = Path.cwd() / "xhs-output"
        output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"strategy_{stamp}.json"
    md_path = output_dir / f"strategy_{stamp}.md"
    json_path.write_text(json.dumps(strategy, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(strategy, md_path)

    if args.json:
        print(json.dumps(strategy, ensure_ascii=False, indent=2))
    else:
        print(f"策略已保存：{md_path}")
        print(f"JSON 已保存：{json_path}")
        print(f"推荐角度：{strategy['recommended_angle']}")


if __name__ == "__main__":
    main()
