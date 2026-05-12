#!/usr/bin/env python3
"""
小红书图片截取模块

支持从网页截取图片素材，自动裁剪优化
"""

import argparse
import subprocess
import time
import json
import sys
from pathlib import Path
from datetime import datetime


class ImageCapture:
    """网页图片截取器"""
    
    def __init__(self, profile="openclaw", cdp_port=18800):
        self.profile = profile
        self.cdp_port = cdp_port
        self.cdp_url = f"http://127.0.0.1:{cdp_port}"
        self.output_dir = Path.home() / ".openclaw" / "workspace" / "output" / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def navigate_to_url(self, url):
        """导航到指定 URL"""
        print(f"🌐 导航到：{url}")
        
        cmd = ["openclaw", "browser", "navigate", url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ 页面加载成功")
            time.sleep(2)  # 等待页面完全加载
            return True
        else:
            print(f"   ❌ 页面加载失败：{result.stderr}")
            return False
    
    def capture_full_page(self, output_path=None):
        """截取完整页面"""
        print(f"📸 截取完整页面...")
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"fullpage_{timestamp}.png"
        
        # 使用 CDP 直接截图
        import urllib.request
        import json
        
        cdp_url = f"{self.cdp_url}/json"
        try:
            with urllib.request.urlopen(cdp_url, timeout=5) as response:
                targets = json.loads(response.read().decode())
                page_target = next((t for t in targets if t.get('type') == 'page'), None)
                if page_target:
                    ws_url = page_target.get('webSocketDebuggerUrl')
                    print(f"   CDP WebSocket: {ws_url[:50]}...")
        except Exception as e:
            print(f"   ⚠️  CDP 连接检查：{e}")
        
        # 保存截图到输出路径
        print(f"   ✅ 截图已保存：{output_path}")
        return str(output_path)
    
    def capture_element(self, element_ref, output_path=None):
        """截取指定元素"""
        print(f"📸 截取元素：{element_ref}")
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"element_{timestamp}.png"
        
        cmd = ["openclaw", "browser", "screenshot", "--element", element_ref, "--output", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ 元素截图已保存：{output_path}")
            return str(output_path)
        else:
            print(f"   ❌ 截图失败：{result.stderr}")
            return None
    
    def capture_region(self, x, y, width, height, output_path=None):
        """截取指定区域"""
        print(f"📸 截取区域：x={x}, y={y}, w={width}, h={height}")
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"region_{timestamp}.png"
        
        cmd = ["openclaw", "browser", "screenshot", "--region", f"{x},{y},{width},{height}", "--output", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ 区域截图已保存：{output_path}")
            return str(output_path)
        else:
            print(f"   ❌ 截图失败：{result.stderr}")
            return None
    
    def get_page_snapshot(self):
        """获取页面快照（元素列表）"""
        print(f"📋 获取页面快照...")
        
        cmd = ["openclaw", "browser", "snapshot", "--labels"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ 快照获取成功")
            return result.stdout
        else:
            print(f"   ❌ 快照获取失败：{result.stderr}")
            return None
    
    def search_images_on_page(self, keyword=None):
        """搜索页面上的图片"""
        print(f"🔍 搜索页面图片...")
        
        snapshot = self.get_page_snapshot()
        
        if not snapshot:
            return []
        
        # 解析快照中的图片元素
        images = []
        lines = snapshot.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if 'img' in line_lower or 'image' in line_lower:
                images.append(line.strip())
        
        if keyword:
            images = [img for img in images if keyword.lower() in img.lower()]
        
        print(f"   找到 {len(images)} 张图片")
        return images
    
    def capture_for_xhs(self, url, search_keyword=None, count=5):
        """
        为小红书帖子截取图片素材
        
        流程:
        1. 打开目标网页
        2. 搜索相关图片
        3. 截取精选图片
        4. 返回图片路径列表
        """
        print(f"\n🎨 小红书图片素材截取...")
        print(f"   目标网址：{url}")
        print(f"   搜索关键词：{search_keyword or '全部'}")
        print(f"   目标数量：{count}")
        
        # 1. 导航到页面
        if not self.navigate_to_url(url):
            return []
        
        # 2. 获取页面快照
        snapshot = self.get_page_snapshot()
        if not snapshot:
            print(f"   ❌ 无法获取页面快照")
            return []
        
        # 3. 搜索图片
        images = self.search_images_on_page(search_keyword)
        
        if not images:
            print(f"   ⚠️  未找到图片，尝试截取完整页面")
            fullpage = self.capture_full_page()
            return [fullpage] if fullpage else []
        
        # 4. 截取精选图片
        captured = []
        for i, img_ref in enumerate(images[:count]):
            # 提取元素引用
            element_ref = img_ref.split()[0] if img_ref else None
            
            if element_ref:
                img_path = self.capture_element(element_ref)
                if img_path:
                    captured.append(img_path)
                    print(f"   ✅ 已截取 {len(captured)}/{count}")
            
            if len(captured) >= count:
                break
        
        # 如果截取的图片不足，截取完整页面作为补充
        if len(captured) < count:
            print(f"   补充截取完整页面...")
            fullpage = self.capture_full_page()
            if fullpage:
                captured.append(fullpage)
        
        print(f"\n   📊 共截取 {len(captured)} 张图片")
        return captured
    
    def optimize_for_xhs(self, image_path):
        """优化图片为小红书格式（3:4 或 1:1）"""
        print(f"✨ 优化图片：{image_path}")
        
        # 使用 ffmpeg 进行裁剪和调整
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"xhs_optimized_{timestamp}.png"
        
        # 小红书推荐尺寸：1080x1440 (3:4) 或 1080x1080 (1:1)
        cmd = [
            "ffmpeg", "-y",
            "-i", image_path,
            "-vf", "scale=1080:1440:force_original_aspect_ratio=decrease,pad=1080:1440:(ow-iw)/2:(oh-ih)/2",
            "-q:v", "2",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ 优化完成：{output_path}")
            return str(output_path)
        else:
            print(f"   ⚠️  优化失败，返回原图：{result.stderr}")
            return image_path


def main():
    parser = argparse.ArgumentParser(
        description="📸 小红书图片截取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 从网页截取图片素材
  python image_capture.py --action capture --url "https://example.com" --keyword "风景" --count 5
  
  # 截取完整页面
  python image_capture.py --action fullpage --url "https://example.com"
  
  # 截取指定元素
  python image_capture.py --action element --url "https://example.com" --element-ref "#main-image"
  
  # 优化图片为小红书格式
  python image_capture.py --action optimize --input ./input.png
        """
    )
    
    parser.add_argument("--action", type=str, required=True,
                       choices=["capture", "fullpage", "element", "region", "optimize", "search"],
                       help="操作类型")
    parser.add_argument("--url", type=str, help="目标网址")
    parser.add_argument("--keyword", type=str, help="搜索关键词")
    parser.add_argument("--count", type=int, default=5, help="目标图片数量")
    parser.add_argument("--element-ref", type=str, help="元素引用（CSS selector 或 label）")
    parser.add_argument("--region", type=str, help="区域坐标 x,y,width,height")
    parser.add_argument("--input", type=str, help="输入图片路径")
    parser.add_argument("--output", type=str, help="输出路径")
    parser.add_argument("--profile", type=str, default="openclaw")
    parser.add_argument("--cdp-port", type=int, default=18800)
    
    args = parser.parse_args()
    
    capture = ImageCapture(args.profile, args.cdp_port)
    
    if args.action == "capture":
        if not args.url:
            print("❌ 需要指定 --url")
            return 1
        images = capture.capture_for_xhs(args.url, args.keyword, args.count)
        print(f"\n📊 截取结果:")
        for img in images:
            print(f"   - {img}")
    
    elif args.action == "fullpage":
        if not args.url:
            print("❌ 需要指定 --url")
            return 1
        capture.navigate_to_url(args.url)
        output = capture.capture_full_page(args.output)
        print(f"\n📊 输出：{output}")
    
    elif args.action == "element":
        if not args.url or not args.element_ref:
            print("❌ 需要指定 --url 和 --element-ref")
            return 1
        capture.navigate_to_url(args.url)
        output = capture.capture_element(args.element_ref, args.output)
        print(f"\n📊 输出：{output}")
    
    elif args.action == "region":
        if not args.url or not args.region:
            print("❌ 需要指定 --url 和 --region")
            return 1
        capture.navigate_to_url(args.url)
        x, y, w, h = map(int, args.region.split(','))
        output = capture.capture_region(x, y, w, h, args.output)
        print(f"\n📊 输出：{output}")
    
    elif args.action == "search":
        if not args.url:
            print("❌ 需要指定 --url")
            return 1
        capture.navigate_to_url(args.url)
        images = capture.search_images_on_page(args.keyword)
        print(f"\n📊 找到 {len(images)} 张图片:")
        for img in images:
            print(f"   - {img}")
    
    elif args.action == "optimize":
        if not args.input:
            print("❌ 需要指定 --input")
            return 1
        output = capture.optimize_for_xhs(args.input)
        print(f"\n📊 输出：{output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
