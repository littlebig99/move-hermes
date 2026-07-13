"""
Move Hermes — 系统托盘图标管理
用于后台静默运行服务器，提供托盘图标退出功能
"""
import sys
import os
import threading
import uvicorn
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("⚠️ pystray 未安装，跳过托盘功能")
    print("   安装命令: pip install pystray pillow")
    sys.exit(1)


class ServerTrayManager:
    """服务器托盘管理器"""
    
    def __init__(self, port=8080):
        self.port = port
        self.server_process = None
        self.tray_icon = None
        self.is_running = False
        
        # 获取脚本目录
        self.project_root = Path(__file__).parent.parent.resolve()
        
    def _create_default_icon(self):
        """创建默认托盘图标（蓝色圆形 + H 字母）"""
        size = 64
        image = Image.new('RGB', (size, size), color=(30, 64, 175))
        draw = ImageDraw.Draw(image)
        
        # 画圆形背景
        draw.ellipse([0, 0, size, size], fill=(30, 64, 175))
        
        # 画白色边框
        draw.ellipse([2, 2, size-2, size-2], outline=(255, 255, 255), width=2)
        
        # 画 H 字母
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        # 计算文字位置居中
        bbox = draw.textbbox((0, 0), "H", font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2 - bbox[0]
        y = (size - text_height) // 2 - bbox[1]
        draw.text((x, y), "H", fill=(255, 255, 255), font=font)
        
        return image
    
    def _on_quit(self, icon=None):
        """退出回调"""
        print("\n🔴 正在关闭服务器...")
        self.is_running = False
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except:
                self.server_process.kill()
        print("✅ 服务器已停止")
        if icon:
            icon.stop()
    
    def _start_server_thread(self):
        """在后台线程启动服务器"""
        def run_server():
            try:
                from backend.main import app
                uvicorn.run(
                    app,
                    host="127.0.0.1",
                    port=self.port,
                    log_level="warning",  # 静默模式
                    use_colors=False
                )
            except Exception as e:
                print(f"❌ 服务器启动失败: {e}")
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return thread
    
    def run(self):
        """运行托盘管理器"""
        print("=" * 50)
        print("  🚀 Move Hermes — 托盘模式启动")
        print("=" * 50)
        print(f"  端口: {self.port}")
        print(f"  访问: http://localhost:{self.port}")
        print(f"  提示: 服务器将在后台运行")
        print("=" * 50)
        
        # 创建托盘图标
        icon_image = self._create_default_icon()
        menu = pystray.Menu(
            pystray.MenuItem("打开浏览器", lambda icon, item: self._open_browser()),
            pystray.MenuItem("健康检查", lambda icon, item: self._health_check()),
            pystray.MenuItem("-", lambda icon, item: None),  # 分隔符
            pystray.MenuItem("退出服务器", self._on_quit)
        )
        
        self.tray_icon = pystray.Icon(
            "move-hermes",
            icon_image,
            title="Move Hermes",
            menu=menu
        )
        
        # 启动服务器线程
        server_thread = self._start_server_thread()
        self.is_running = True
        
        # 等待服务器启动
        import time
        for i in range(30):  # 最多等 30 秒
            time.sleep(1)
            try:
                import urllib.request
                response = urllib.request.urlopen(f"http://localhost:{self.port}/health", timeout=2)
                if response.status == 200:
                    print("✅ 服务器启动成功")
                    break
            except:
                pass
        else:
            print("⚠️ 服务器启动超时，请检查日志")
        
        # 显示托盘图标
        self.tray_icon.run()


def _open_browser():
    """打开浏览器"""
    import webbrowser
    webbrowser.open("http://localhost:8080")


def _health_check():
    """健康检查"""
    import urllib.request
    import json
    try:
        response = urllib.request.urlopen("http://localhost:8080/health", timeout=5)
        data = json.loads(response.read().decode())
        status = data.get("status", "unknown")
        print(f"📊 健康检查: {status}")
        return f"状态: {status}"
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return f"错误: {e}"


if __name__ == "__main__":
    manager = ServerTrayManager(port=int(os.environ.get("PORT", 8080)))
    manager.run()
