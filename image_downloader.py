#!/usr/bin/env python3
"""
小红书图片下载工具 v2.0

使用 Bing 图片搜索并下载高清图片
"""

import argparse
import subprocess
import time
import json
import sys
from pathlib import Path
from datetime import datetime
import urllib.request
import ssl


OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "output" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 禁用 SSL 验证
ssl._create_default_https_context = ssl._create_unverified_context


def run_browser_cmd(args_list):
    """执行 openclaw browser 命令"""
    cmd = ["openclaw", "browser"] + args_list
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result


def get_bing_image_urls(keyword, count=5):
    """从 Bing 获取图片 URL"""
    print(f"\n🔍 Bing 图片搜索：{keyword}...")
    
    # 构造 Bing 图片搜索 URL
    search_url = f"https://cn.bing.com/images/search?q={keyword}&FORM=HDRSC2"
    
    print(f"   导航到：{search_url}")
    result = run_browser_cmd(["navigate", search_url])
    
    if result.returncode != 0:
        print(f"   ❌ 导航失败")
        return []
    
    time.sleep(5)  # 等待页面加载
    
    # 使用 JavaScript 获取图片 URL
    js_code = f"""
    () => {{
        const imgs = document.querySelectorAll('img.mimg');
        return Array.from(imgs).slice(0,{count}).map(i => i.src).filter(s => s && s.startsWith('http'));
    }}
    """
    
    result = run_browser_cmd(["evaluate", "--fn", js_code])
    
    if result.returncode == 0:
        try:
            # 解析 JSON 数组
            urls = json.loads(result.stdout.strip())
            print(f"   ✅ 找到 {len(urls)} 个图片 URL")
            for url in urls:
                print(f"      - {url[:80]}...")
            return urls
        except:
            print(f"   ⚠️  解析失败：{result.stdout[:200]}")
    
    return []


def download_image(url, output_name=None):
    """下载图片"""
    print(f"\n📥 下载：{url[:60]}...")
    
    if not output_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"downloaded_{timestamp}.jpg"
    
    output_path = OUTPUT_DIR / output_name
    
    try:
        # 下载图片
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        
        # 检查文件大小
        size = output_path.stat().st_size
        if size > 10000:  # 至少 10KB
            print(f"   ✅ 下载成功：{output_path} ({size} bytes)")
            return str(output_path)
        else:
            print(f"   ⚠️  文件太小 ({size} bytes)，删除")
            output_path.unlink()
    except Exception as e:
        print(f"   ❌ 下载失败：{e}")
        if output_path.exists():
            output_path.unlink()
    
    return None


def optimize_image(input_path, output_name=None):
    """优化图片为小红书格式 (3:4)"""
    print(f"\n✨ 优化图片：{input_path}")
    
    if not Path(input_path).exists():
        print(f"   ❌ 文件不存在")
        return None
    
    if not output_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"optimized_{timestamp}.png"
    
    output_path = OUTPUT_DIR / output_name
    
    # 小红书推荐：1080x1440 (3:4)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", "scale=1080:1440:force_original_aspect_ratio=decrease,pad=1080:1440:(ow-iw)/2:(oh-ih)/2",
        "-q:v", "2",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0 and output_path.exists():
        size = output_path.stat().st_size
        print(f"   ✅ 优化完成：{output_path} ({size} bytes)")
        return str(output_path)
    
    print(f"   ❌ 优化失败")
    return None


def fetch_images_for_topic(topic, count=5):
    """根据主题获取图片"""
    print(f"\n🎨 获取图片 (主题：{topic})...")
    
    # 构建搜索关键词（英文效果更好）
    keywords = {
        "天气": "beautiful sky clouds sunshine landscape 4k",
        "美食": "delicious food chinese cuisine restaurant 4k",
        "旅行": "travel scenery landscape tourism 4k",
        "成都": "chengdu china panda food street 4k",
        "上海": "shanghai china bund city skyline night 4k",
        "北京": "beijing china forbidden city great wall 4k",
        "成都美食": "chengdu food sichuan cuisine hotpot 4k",
        "成都天气": "chengdu weather sky clouds 4k",
    }
    
    keyword = keywords.get(topic, f"{topic} 4k")
    
    # 获取图片 URL
    urls = get_bing_image_urls(keyword, count)
    
    if not urls:
        print(f"\n  ⚠️  未找到图片 URL")
        return []
    
    # 下载图片
    images = []
    for i, url in enumerate(urls[:count]):
        output_name = f"bing_{topic}_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        img_path = download_image(url, output_name)
        if img_path:
            images.append(img_path)
        time.sleep(1)
    
    if images:
        # 优化图片
        print(f"\n  优化图片...")
        optimized = []
        for i, img in enumerate(images[:3]):
            opt_name = f"xhs_{topic}_{i+1}.png"
            opt = optimize_image(img, opt_name)
            if opt:
                optimized.append(opt)
        return optimized
    
    return []


def main():
    parser = argparse.ArgumentParser(description="📸 小红书图片下载工具")
    
    parser.add_argument("--action", type=str, required=True,
                       choices=["search", "download", "optimize", "fetch"],
                       help="操作类型")
    parser.add_argument("--keyword", type=str, help="搜索关键词")
    parser.add_argument("--url", type=str, help="图片 URL")
    parser.add_argument("--topic", type=str, help="内容主题")
    parser.add_argument("--count", type=int, default=5, help="图片数量")
    parser.add_argument("--input", type=str, help="输入图片路径")
    parser.add_argument("--output", type=str, help="输出文件名")
    
    args = parser.parse_args()
    
    if args.action == "search":
        if not args.keyword:
            print("❌ 需要指定 --keyword")
            return 1
        urls = get_bing_image_urls(args.keyword, args.count)
        print(f"\n📊 结果:")
        for url in urls:
            print(f"   - {url}")
    
    elif args.action == "download":
        if not args.url:
            print("❌ 需要指定 --url")
            return 1
        img = download_image(args.url, args.output)
        if img:
            print(f"\n📊 下载成功：{img}")
    
    elif args.action == "optimize":
        if not args.input:
            print("❌ 需要指定 --input")
            return 1
        img = optimize_image(args.input, args.output)
        if img:
            print(f"\n📊 优化完成：{img}")
    
    elif args.action == "fetch":
        if not args.topic:
            print("❌ 需要指定 --topic")
            return 1
        images = fetch_images_for_topic(args.topic, args.count)
        print(f"\n📊 获取结果:")
        for img in images:
            print(f"   - {img}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
