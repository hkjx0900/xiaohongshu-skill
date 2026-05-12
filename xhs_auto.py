#!/usr/bin/env python3
"""
小红书全自动发布脚本 v3.0 (增强版)

支持：
1. 文字配图
2. AI 生成图片
3. 网页搜索并截取图片
4. 本地图片上传
"""

import argparse
import subprocess
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime


OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "output"


AI_STYLE_PATTERNS = [
    "希望能对大家有所帮助",
    "欢迎在评论区交流",
    "整体体验很棒",
    "真的太舒服了",
    "超详细",
    "绝了",
    "治愈系",
    "今日份好心情",
]


def normalize_text(text):
    """清理命令行转义、异常空白和模板痕迹。"""
    if not text:
        return ""
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_output_dir():
    """优先使用默认输出目录；无权限时回退到当前目录。"""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        probe = OUTPUT_DIR / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return OUTPUT_DIR
    except PermissionError:
        fallback = Path.cwd() / "xhs-output"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def lint_copywriting(title, body, tags=""):
    """发布前文案检查，返回清理后的文案与风险提示。"""
    title = normalize_text(title)
    body = normalize_text(body)
    tags = normalize_text(tags)
    warnings = []

    combined = f"{title}\n{body}\n{tags}"
    if "\\n" in combined or "\\r" in combined or "/n" in combined:
        warnings.append("发现疑似字面量换行符，已尝试转换为真实换行")
    for phrase in AI_STYLE_PATTERNS:
        if phrase in combined:
            warnings.append(f"文案包含模板感短语：{phrase}")
    if len(body) > 900:
        warnings.append("正文偏长，小红书图文建议压到 300-700 字")
    if body.count("#") > 10:
        warnings.append("标签偏多，建议控制在 5-8 个")
    if len(title) > 20:
        warnings.append("标题超过 20 字，发布端可能截断")

    return {
        "title": title,
        "body": body,
        "tags": tags,
        "warnings": warnings,
    }


def optimize_title(topic, body, domain="general"):
    """调用标题优化器，返回得分最高的标题。"""
    script_path = Path(__file__).parent / "xhs_title_optimizer.py"
    cmd = [
        sys.executable, str(script_path),
        "--topic", topic or "",
        "--body", body or "",
        "--domain", domain,
        "--limit", "1",
        "--json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return topic or ""
    try:
        titles = json.loads(result.stdout)
    except json.JSONDecodeError:
        return topic or ""
    if titles:
        return titles[0]["title"]
    return topic or ""


# 文案模板
COPYWRITING_TEMPLATES = {
    "天气": {
        "title": "{city}今日天气｜{temp}°C {feeling}",
        "content": """今天的天气真的太舒服了！出门心情都变好了～

🌤️ 天气实况
• 气温：{temp_min}-{temp_max}°C
• 天气：多云转晴
• 湿度：{humidity}%
• 体感：{feeling}

💡 出行建议：
🧥 早晚温差大，带件薄外套
☂️ 备把伞（防晒 + 防小雨）
💧 多喝水，注意补水

这种天气最适合出门走走啦～大家今天都去哪里玩了？

#天气 #天气预报 #日常生活 #治愈系 #今日份好心情""",
        "tags": "#天气 #天气预报 #日常生活 #治愈系"
    },
    "美食": {
        "title": "{city}这家{food_type}绝了{emoji}",
        "content": """终于来打卡这家收藏好久的店了！真的没有失望！

📍 店铺信息
• 店名：待补充
• 位置：待补充
• 人均：待补充

🥢 推荐菜品
• 招牌菜 1
• 招牌菜 2
• 招牌菜 3

整体体验很棒，味道正宗，服务也很好。推荐给喜欢{food_type}的姐妹们！

#美食探店 #美食分享 #吃货日常""",
        "tags": "#美食探店 #美食分享 #吃货日常"
    },
    "旅行": {
        "title": "{location}攻略｜{days}天{nights}夜超详细",
        "content": """刚从{location}回来，后劲太大了！分享一份超详细攻略～

📅 行程安排
Day1: 景点 1 → 景点 2 → 美食
Day2: 景点 3 → 景点 4 → 返程

🏨 住宿推荐
建议住在市中心/景点附近，交通便利

💰 费用参考
人均约 XXX 元（不含大交通）

💡 旅行小贴士：
• 最佳季节：X-X 月
• 必带物品：XXX
• 注意事项：XXX

#旅行攻略 #旅行 #旅游 #打卡""",
        "tags": "#旅行攻略 #旅行 #旅游"
    },
    "default": {
        "title": "关于{topic}的一些分享{emoji}",
        "content": """想和大家分享一下关于{topic}的一些想法～

这是最近的一些心得体会，希望能对大家有所帮助！

有什么想法欢迎在评论区交流哦～

#日常 #分享 #生活记录 #心得体会""",
        "tags": "#日常 #分享 #生活记录"
    }
}


def get_city_from_topic(topic):
    """从主题中提取城市名"""
    cities = ["成都", "上海", "北京", "广州", "深圳", "杭州", "南京", "重庆", "武汉", "西安"]
    for city in cities:
        if city in topic:
            return city
    return "上海"  # 默认


def generate_copywriting(topic):
    """根据主题生成文案"""
    print(f"\n✍️  生成文案 (主题：{topic})...")
    
    city = get_city_from_topic(topic)
    
    # 查找匹配的模板
    template = None
    for key in COPYWRITING_TEMPLATES:
        if key in topic or topic in key:
            template = COPYWRITING_TEMPLATES[key]
            break
    
    if not template:
        template = COPYWRITING_TEMPLATES["default"]
    
    import random
    emoji = random.choice(["✨", "🌟", "💫", "🌤️", "🍃", "📸"])
    
    # 生成标题（≤20 字）
    title = template["title"].format(
        topic=topic,
        city=city,
        temp="16-22",
        feeling="舒适",
        food_type="美食",
        location="目的地",
        days="3",
        nights="2",
        emoji=emoji
    )
    
    if len(title) > 20:
        title = title[:18] + "..."
    
    # 生成正文
    content = template["content"].format(
        topic=topic,
        city=city,
        temp_min="16",
        temp_max="22",
        humidity="65-95",
        food_type="美食",
        location="目的地",
        days="3",
        nights="2"
    )
    
    tags = template["tags"]
    
    copywriting = {
        "title": title,
        "body": content,
        "tags": tags,
        "full_content": content + "\n\n" + tags
    }
    checked = lint_copywriting(copywriting["title"], copywriting["body"], copywriting["tags"])
    copywriting.update({
        "title": checked["title"],
        "body": checked["body"],
        "tags": checked["tags"],
        "full_content": checked["body"] + ("\n\n" + checked["tags"] if checked["tags"] else ""),
    })
    
    print(f"   标题：{title}")
    print(f"   正文：{len(content)}字")
    print(f"   标签：{tags}")
    
    return copywriting


def fetch_images(topic, method="auto", count=3):
    """获取图片"""
    print(f"\n🖼️  获取图片 (主题：{topic}, 方法：{method})...")
    
    images = []
    
    # 使用 image_downloader 搜索并下载
    if method in ["auto", "web"]:
        print(f"\n  尝试搜索下载...")
        script_path = Path(__file__).parent / "image_downloader.py"
        cmd = [
            "python3", str(script_path),
            "--action", "fetch",
            "--topic", topic,
            "--count", str(min(count, 3))
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(result.stdout)
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('-') and ('.png' in line or '.jpg' in line):
                    images.append(line[1:].strip())
    
    return images


def playwright_publish_flow(copywriting, images=None, login_phone=None):
    """使用 Playwright 执行图文发布流程。"""
    print(f"\n🌐 启动 Playwright 发布流程...")
    print(f"   图片：{len(images) if images else 0}张")

    if not images:
        print("   ❌ Playwright 发布需要至少一张本地图片")
        return {
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
            "screenshot": None,
            "copywriting": copywriting,
            "images": [],
            "published": False,
            "error": "missing_images"
        }

    script_path = Path(__file__).parent / "xhs_playwright_publish.cjs"
    out_dir = OUTPUT_DIR / "playwright"
    workspace = str(Path(__file__).parent)
    cmd = [
        "node", str(script_path),
        "--title", copywriting["title"],
        "--content", copywriting["body"],
        "--tags", copywriting.get("tags", ""),
        "--workspace", workspace,
        "--out-dir", str(out_dir),
        "--images",
    ] + [str(p) for p in images[:4]]
    if login_phone:
        cmd += ["--login-phone", login_phone]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    published = result.returncode == 0 and (
        "published=true" in result.stdout
        or "/publish/success" in result.stdout
        or "submitted=true" in result.stdout
    )
    screenshot_path = out_dir / "06-after-submit.png"
    return {
        "status": "success" if published else "pending_verification",
        "timestamp": datetime.now().isoformat(),
        "screenshot": str(screenshot_path) if screenshot_path.exists() else None,
        "copywriting": copywriting,
        "images": images or [],
        "published": published,
        "browser_method": "playwright"
    }


def main():
    parser = argparse.ArgumentParser(description="📱 小红书全自动发布脚本 v3.0")
    
    parser.add_argument("--action", type=str, default="publish",
                       choices=["publish", "check-login", "login", "plan", "trends", "titles"],
                       help="操作类型")
    parser.add_argument("--topic", type=str, help="内容主题")
    parser.add_argument("--title", type=str, help="手动指定标题")
    parser.add_argument("--content", type=str, help="正文内容")
    parser.add_argument("--content-file", type=str, help="从文件读取正文，避免命令行换行转义")
    parser.add_argument("--auto-publish", action="store_true", help="自动发布")
    parser.add_argument("--dry-run", action="store_true", help="仅生成文案")
    parser.add_argument("--browser-method", type=str, default="playwright",
                       choices=["playwright"],
                       help="发布浏览器方式：playwright")
    parser.add_argument("--login-phone", type=str, help="Playwright 短信登录手机号")
    parser.add_argument("--city", type=str, help="城市，用于选题策略")
    parser.add_argument("--domain", type=str, default="general",
                       help="趋势领域：general/city/travel/science/ai/news/food/fashion/health/home/education")
    parser.add_argument("--format", type=str, default="note",
                       choices=["note", "video"], help="内容形态")
    parser.add_argument("--trend-note", type=str, default="", help="外部热点观察，传给策略生成器")
    parser.add_argument("--keywords", nargs="*", default=[], help="趋势采集关键词")
    parser.add_argument("--xhs-notes", nargs="*", default=[], help="手动导出的站内搜索结果")
    parser.add_argument("--public-notes", nargs="*", default=[], help="公开榜单/行业观察文本")
    parser.add_argument("--live-xhs", action="store_true", help="打开小红书站内搜索并采集页面文本")
    parser.add_argument("--include-history", action="store_true", help="趋势候选纳入历史发帖结果")
    parser.add_argument("--limit", type=int, default=10, help="趋势候选数量")
    parser.add_argument("--optimize-title", action="store_true", help="发布前自动优化标题")
    
    # 图片选项
    parser.add_argument("--images", type=str, nargs='+', help="本地图片路径")
    parser.add_argument("--image-method", type=str, default="auto",
                       choices=["auto", "ai", "web", "screenshot", "local", "none"],
                       help="图片/素材获取方法")
    parser.add_argument("--text-image", action="store_true", help="使用文字配图（无图片时）")
    
    args = parser.parse_args()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"📱 小红书全自动发布 v3.0")
    print(f"⏰ 时间：{timestamp}")
    print("=" * 50)
    
    # 检查登录
    if args.action == "check-login":
        script_path = Path(__file__).parent / "xhs_playwright_publish.cjs"
        cmd = ["node", str(script_path), "--login-only", "--workspace", str(Path(__file__).parent)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode
    
    if args.action == "login":
        if args.browser_method == "playwright":
            script_path = Path(__file__).parent / "xhs_playwright_publish.cjs"
            cmd = ["node", str(script_path), "--login-only", "--workspace", str(Path(__file__).parent)]
            if args.login_phone:
                cmd += ["--login-phone", args.login_phone]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return result.returncode

    if args.action == "plan":
        if not args.topic:
            print("❌ 请指定 --topic")
            return 1
        script_path = Path(__file__).parent / "xhs_content_strategy.py"
        cmd = [
            sys.executable, str(script_path),
            "--topic", args.topic,
            "--format", args.format,
            "--image-source", args.image_method,
            "--out-dir", str(OUTPUT_DIR),
        ]
        if args.city:
            cmd += ["--city", args.city]
        if args.trend_note:
            cmd += ["--trend-note", args.trend_note]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode

    if args.action == "trends":
        output_dir = get_output_dir()
        xhs_notes = list(args.xhs_notes or [])
        if args.live_xhs:
            keywords = args.keywords or ([args.topic] if args.topic else ["CityWalk", "ColorWalk", "周末去哪儿"])
            live_file = output_dir / f"xhs_live_{timestamp}.txt"
            live_script = Path(__file__).parent / "xhs_live_search_collect.cjs"
            live_cmd = [
                "node", str(live_script),
                "--out-file", str(live_file),
                "--profile-dir", str(Path(__file__).parent / "xhs-playwright-profile"),
                "--limit", "12",
                "--keywords",
            ] + keywords
            live_result = subprocess.run(live_cmd, capture_output=True, text=True, timeout=360)
            print(live_result.stdout)
            if live_result.stderr:
                print(live_result.stderr)
            if live_result.returncode != 0:
                return live_result.returncode
            xhs_notes.append(str(live_file))

        trend_script = Path(__file__).parent / "xhs_trend_collector.py"
        trend_cmd = [
            sys.executable, str(trend_script),
            "--city", args.city or "",
            "--domain", args.domain,
            "--out-dir", str(output_dir),
            "--limit", str(args.limit),
        ]
        if args.include_history:
            trend_cmd += ["--history-dir", str(output_dir)]
        if args.keywords:
            trend_cmd += ["--seeds"] + args.keywords
        if xhs_notes:
            trend_cmd += ["--xhs-notes"] + xhs_notes
        if args.public_notes:
            trend_cmd += ["--public-notes"] + args.public_notes
        trend_result = subprocess.run(trend_cmd, capture_output=True, text=True)
        print(trend_result.stdout)
        if trend_result.stderr:
            print(trend_result.stderr)
        return trend_result.returncode

    if args.action == "titles":
        body = args.content or ""
        if args.content_file:
            body = Path(args.content_file).read_text(encoding="utf-8")
        script_path = Path(__file__).parent / "xhs_title_optimizer.py"
        cmd = [
            sys.executable, str(script_path),
            "--topic", args.topic or args.title or "",
            "--body", body,
            "--domain", args.domain,
            "--limit", str(args.limit),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode
    
    if not args.topic and not args.title:
        print("❌ 请指定 --topic 或 --title")
        return 1
    
    # 步骤 1：确保登录
    print(f"\n🔐 步骤 1: 登录检查交给 Playwright 浏览器流程处理...")
    
    # 步骤 2：生成文案
    print(f"\n✍️  步骤 2: 生成文案...")
    if args.topic:
        copywriting = generate_copywriting(args.topic)
    else:
        content = args.content or ""
        if args.content_file:
            content = Path(args.content_file).read_text(encoding="utf-8")
        checked = lint_copywriting(args.title[:20], content, "")
        final_title = checked["title"]
        if args.optimize_title:
            final_title = optimize_title(final_title, checked["body"], args.domain)[:20]
        copywriting = {
            "title": final_title,
            "body": checked["body"],
            "tags": checked["tags"],
            "full_content": checked["body"]
        }
        if checked["warnings"]:
            print("   ⚠️  文案检查提示：")
            for warning in checked["warnings"]:
                print(f"      - {warning}")
    
    # 保存文案
    output_dir = get_output_dir()
    copywriting_file = output_dir / f"copywriting_{timestamp}.md"
    with open(copywriting_file, 'w', encoding='utf-8') as f:
        f.write(f"# {copywriting['title']}\n\n{copywriting['full_content']}")
    print(f"   ✅ 文案已保存：{copywriting_file}")
    
    if args.dry_run:
        print("\n🎉 演示模式结束")
        return 0
    
    # 步骤 3：获取图片
    images = args.images or []
    
    if not images and args.image_method != "none":
        print(f"\n🖼️  步骤 3: 获取图片...")
        images = fetch_images(args.topic, args.image_method, count=3)
    
    # 步骤 4：发布
    if args.auto_publish:
        print(f"\n🚀 步骤 4: 发布笔记...")
        result = playwright_publish_flow(copywriting, images, args.login_phone)
        
        # 保存结果
        result_file = output_dir / f"publish_result_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 50)
        print("🎉 发布流程完成！")
        print(f"📊 发布状态：{'✅ 成功' if result['published'] else '⚠️ 待验证'}")
        print(f"🖼️  图片数量：{len(result['images'])}")
        print("=" * 50)
    else:
        print("\n⚠️  未指定 --auto-publish，流程结束")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
