"""
Move Hermes — 系统托盘图标管理
用于后台静默运行服务器，提供托盘图标退出功能
"""
import sys
import os
import time
import subprocess
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[WARN] pystray 未安装，跳过托盘功能")
    print("   安装命令: pip install pystray pillow")
    sys.exit(1)


class ServerTrayManager:
    """服务器托盘管理器"""

    def __init__(self, port=8080):
        self.port = port
        self.server_process = None
        self.tray_icon = None
        self.is_running = False
        self.project_root = Path(__file__).parent.parent.resolve()

    def _create_default_icon(self):
        """创建默认托盘图标（蓝色圆形 + H 字母）"""
        size = 64
        image = Image.new('RGB', (size, size), color=(30, 64, 175))
        draw = ImageDraw.Draw(image)
        draw.ellipse([0, 0, size, size], fill=(30, 64, 175))
        draw.ellipse([2, 2, size-2, size-2], outline=(255, 255, 255), width=2)
        
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except Exception:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), "H", font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2 - bbox[0]
        y = (size - text_height) // 2 - bbox[1]
        draw.text((x, y), "H", fill=(255, 255, 255), font=font)
        
        return image

    def _on_open_browser(self, icon, item):
        """打开浏览器回调"""
        import webbrowser
        webbrowser.open("http://localhost:{}/".format(self.port))

    def _on_health_check(self, icon, item):
        """健康检查回调"""
        try:
            import urllib.request
            import json
            response = urllib.request.urlopen(
                "http://localhost:{}/health".format(self.port), timeout=5
            )
            data = json.loads(response.read().decode())
            status = data.get("status", "unknown")
            print("[OK] 健康检查: {}".format(status))
        except Exception as e:
            print("[FAIL] 健康检查失败: {}".format(e))

    def _on_quit(self, icon, item):
        """退出回调 — 先停止图标线程，再终止服务器，最后退出"""
        print("\n[STOP] 正在关闭服务器...")
        self.is_running = False
        
        # 终止服务器子进程
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except Exception:
                try:
                    self.server_process.kill()
                except Exception:
                    pass
        
        # 停止图标（这会从系统托盘移除图标）
        if icon:
            icon.stop()
        
        # 退出程序
        print("[OK] 服务器已停止")
        sys.exit(0)

    def _start_server(self):
        """启动服务器子进程"""
        main_py = self.project_root / "backend" / "main.py"
        self.server_process = subprocess.Popen(
            [sys.executable, str(main_py)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return self.server_process

    def run(self):
        """运行托盘管理器"""
        print("=" * 50)
        print("  [OK] Move Hermes — 托盘模式启动")
        print("=" * 50)
        print("  端口: {}".format(self.port))
        print("  访问: http://localhost:{}".format(self.port))
        print("  提示: 服务器将在后台运行")
        print("=" * 50)

        # 创建托盘图标
        icon_image = self._create_default_icon()
        menu = pystray.Menu(
            pystray.MenuItem("打开浏览器", lambda i, item: self._on_open_browser(i, item)),
            pystray.MenuItem("健康检查", lambda i, item: self._on_health_check(i, item)),
            pystray.MenuItem("-", lambda i: None),
            pystray.MenuItem("退出服务器", lambda i, item: self._on_quit(i, item)),
        )

        self.tray_icon = pystray.Icon(
            "move-hermes",
            icon_image,
            title="Move Hermes",
            menu=menu,
        )

        # 启动服务器子进程
        self._start_server()
        self.is_running = True

        # 等待服务器启动
        for i in range(30):
            time.sleep(1)
            try:
                import urllib.request
                response = urllib.request.urlopen(
                    "http://localhost:{}/health".format(self.port), timeout=2
                )
                if response.status == 200:
                    print("[OK] 服务器启动成功")
                    break
            except Exception:
                pass
        else:
            print("[WARN] 服务器启动超时，请检查日志")

        # 显示托盘图标（阻塞直到用户退出）
        self.tray_icon.run()


if __name__ == "__main__":
    manager = ServerTrayManager(port=int(os.environ.get("PORT", 8080)))
    manager.run()
