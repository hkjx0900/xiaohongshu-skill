#!/usr/bin/env python3
"""
小红书图片获取模块 v2.0

支持：
1. AI 生成图片（调用 image_generate）
2. 网页搜索并截取图片
3. 本地图片上传
"""

import argparse
import subprocess
import time
import json
import sys
from pathlib import Path
from datetime import datetime


OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "output" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def try_ai_generate(prompt, count=3):
    """尝试 AI 生成图片"""
    print(f"\n🎨 尝试 AI 生成图片...")
    print(f"   提示词：{prompt[:50]}...")
    
    # 使用 openclaw image_generate 命令
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_hint = f"xhs_ai_{timestamp}"
    
    cmd = [
        "openclaw", "image_generate",
        "--prompt", prompt,
        "--aspectRatio", "3:4",
        "--outputFormat", "png",
        "--count", str(min(count, 4)),
        "--filename", filename_hint
    ]
    
    print(f"   执行：{' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        output = result.stdout.strip()
        # 解析 MEDIA:路径
        if "MEDIA:" in output:
            media_paths = [line.split("MEDIA:")[1].strip() for line in output.split('\n') if "MEDIA:" in line]
            print(f"   ✅ AI 生成成功：{len(media_paths)}张")
            for p in media_paths:
                print(f"      - {p}")
            return media_paths
    
    print(f"   ⚠️  AI 生成失败：{result.stderr[:200] if result.stderr else '未知错误'}")
    return None


def web_search_images(keyword, count=5):
    """搜索网页并获取图片 URL"""
    print(f"\n🔍 搜索图片：{keyword}...")
    
    cmd = ["openclaw", "web_search", "--query", f"{keyword} 高清图片", "--count", "5"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    urls = []
    if result.returncode == 0:
        # 解析搜索结果
        try:
            # 尝试解析 JSON
            if "{" in result.stdout:
                search_results = json.loads(result.stdout.strip())
                if "results" in search_results:
                    urls = [r.get("url", "") for r in search_results["results"][:count]]
        except:
            pass
    
    print(f"   找到 {len(urls)} 个相关网页")
    return urls


def capture_images_from_url(url, keyword=None, count=3):
    """从指定 URL 截取图片"""
    print(f"\n📸 从网页截取图片：{url}")
    
    script_path = Path(__file__).parent / "image_capture.py"
    cmd = [
        "python3", str(script_path),
        "--action", "capture",
        "--url", url,
        "--count", str(count)
    ]
    
    if keyword:
        cmd.extend(["--keyword", keyword])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    images = []
    if result.returncode == 0:
        # 解析输出中的图片路径
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('-') and ('.png' in line or '.jpg' in line):
                images.append(line[1:].strip())
    
    print(f"   ✅ 截取 {len(images)} 张图片")
    return images


def fetch_images_for_topic(topic, method="auto", count=3):
    """
    根据主题获取图片
    
    方法：
    - auto: 先尝试 AI 生成，失败则网页搜索
    - ai: 仅 AI 生成
    - web: 仅网页搜索截取
    """
    print(f"\n🖼️  获取图片 (主题：{topic}, 方法：{method})...")
    
    # 构建图片搜索关键词
    image_keywords = {
        "天气": "风景 天空 云朵 阳光",
        "美食": "美食 料理 餐厅",
        "旅行": "风景 旅游 景点",
        "成都": "成都 风景 美食 熊猫",
        "上海": "上海 风景 外滩 城市",
        "北京": "北京 风景 故宫 城市",
    }
    
    keyword = image_keywords.get(topic, topic + " 风景")
    
    # 方法 1: AI 生成
    if method in ["auto", "ai"]:
        ai_prompt = f"beautiful {keyword} photo, high quality, professional photography, 3:4 aspect ratio"
        images = try_ai_generate(ai_prompt, count)
        if images:
            return images
    
    # 方法 2: 网页搜索 + 截取
    if method in ["auto", "web"]:
        print(f"\n  尝试网页搜索...")
        search_urls = web_search_images(keyword, count=3)
        
        all_images = []
        for url in search_urls[:2]:  # 最多处理 2 个网页
            images = capture_images_from_url(url, keyword.split()[0], count=2)
            all_images.extend(images)
            if len(all_images) >= count:
                break
        
        if all_images:
            return all_images[:count]
    
    print(f"\n  ⚠️  无法获取图片，将使用文字配图")
    return None


def upload_image_to_browser(image_path):
    """上传图片到小红书"""
    print(f"\n📎 上传图片：{image_path}")
    
    if not Path(image_path).exists():
        print(f"   ❌ 文件不存在：{image_path}")
        return False
    
    # 使用 openclaw browser upload 命令
    cmd = ["openclaw", "browser", "upload", image_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0:
        print(f"   ✅ 上传成功")
        time.sleep(3)
        return True
    else:
        print(f"   ❌ 上传失败：{result.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="📸 小红书图片获取工具")
    
    parser.add_argument("--action", type=str, required=True,
                       choices=["fetch", "generate", "search", "capture", "upload"],
                       help="操作类型")
    parser.add_argument("--topic", type=str, help="内容主题")
    parser.add_argument("--prompt", type=str, help="AI 生成提示词")
    parser.add_argument("--url", type=str, help="目标网址")
    parser.add_argument("--keyword", type=str, help="搜索关键词")
    parser.add_argument("--count", type=int, default=3, help="图片数量")
    parser.add_argument("--method", type=str, default="auto",
                       choices=["auto", "ai", "web"],
                       help="获取方法")
    parser.add_argument("--file", type=str, help="上传文件路径")
    
    args = parser.parse_args()
    
    if args.action == "fetch":
        if not args.topic:
            print("❌ 需要指定 --topic")
            return 1
        images = fetch_images_for_topic(args.topic, args.method, args.count)
        if images:
            print(f"\n📊 获取结果:")
            for img in images:
                print(f"   - {img}")
        else:
            print("\n⚠️  无图片可用")
    
    elif args.action == "generate":
        prompt = args.prompt or "beautiful scenery"
        images = try_ai_generate(prompt, args.count)
        if images:
            print(f"\n📊 生成结果:")
            for img in images:
                print(f"   - {img}")
    
    elif args.action == "search":
        if not args.keyword:
            print("❌ 需要指定 --keyword")
            return 1
        urls = web_search_images(args.keyword, args.count)
        print(f"\n📊 搜索结果:")
        for url in urls:
            print(f"   - {url}")
    
    elif args.action == "capture":
        if not args.url:
            print("❌ 需要指定 --url")
            return 1
        images = capture_images_from_url(args.url, args.keyword, args.count)
        print(f"\n📊 截取结果:")
        for img in images:
            print(f"   - {img}")
    
    elif args.action == "upload":
        if not args.file:
            print("❌ 需要指定 --file")
            return 1
        upload_image_to_browser(args.file)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
