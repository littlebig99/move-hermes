"""
Move Hermes — 桌面应用启动器
功能：
1. 启动时弹出窗口显示状态
2. 关闭窗口最小化到系统托盘（不退出服务器）
3. 托盘右键菜单退出服务器
"""
import os
import sys
import threading
import webbrowser
from pathlib import Path

# ==================== 路径配置 ====================
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)

# ==================== 导入依赖 ====================
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("错误: 需要 tkinter 库")
    sys.exit(1)

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("错误: 需要 pystray 和 pillow")
    print("安装命令: pip install pystray pillow")
    sys.exit(1)

try:
    import uvicorn
except ImportError:
    print("错误: 需要 uvicorn")
    print("安装命令: pip install uvicorn")
    sys.exit(1)

# ==================== 全局变量 ====================
server_process = None
tray_icon = None
app_window = None
is_running = False


def create_default_icon():
    """创建默认托盘图标（蓝色圆形 H 字母）"""
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
    
    bbox = draw.textbbox((0, 0), "H", font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2 - bbox[0]
    y = (size - text_height) // 2 - bbox[1]
    draw.text((x, y), "H", fill=(255, 255, 255), font=font)
    
    return image


def start_server():
    """在后台线程启动 FastAPI 服务器"""
    global is_running
    
    # 添加 backend 到路径
    backend_dir = SCRIPT_DIR / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    try:
        # 导入并初始化数据库
        try:
            from backend import database as db
        except ImportError:
            import database as db
        
        db.init_db()
        
        # 导入 app
        try:
            from backend.main import app
        except ImportError:
            from main import app
        
        port = int(os.environ.get("PORT", 8080))
        print(f"正在启动服务器，端口: {port}")
        
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            use_colors=False
        )
        
    except Exception as e:
        print(f"服务器启动失败: {e}")
        is_running = False


def on_open_browser(icon=None):
    """打开浏览器"""
    webbrowser.open("http://localhost:8080")


def on_show_window(icon=None):
    """显示主窗口"""
    global app_window
    if app_window and app_window.winfo_exists():
        app_window.deiconify()
        app_window.lift()
        app_window.focus()


def on_quit(icon=None):
    """退出服务器"""
    global is_running, server_process
    
    print("正在关闭服务器...")
    is_running = False
    
    # 关闭窗口
    if app_window and app_window.winfo_exists():
        app_window.destroy()
    
    # 停止托盘
    if tray_icon:
        tray_icon.stop()
    
    print("服务器已停止")


def on_close_window(event=None):
    """关闭窗口时最小化到托盘"""
    global app_window
    
    if app_window:
        app_window.withdraw()  # 隐藏窗口（不销毁）


def create_main_window():
    """创建主窗口"""
    global app_window
    
    root = tk.Tk()
    root.title("Move Hermes — 智能订单管理系统")
    root.geometry("500x300")
    root.resizable(False, False)
    
    # 设置窗口图标
    try:
        icon_image = create_default_icon()
        icon_image.save(str(SCRIPT_DIR / "temp_icon.ico"))
        root.iconbitmap(str(SCRIPT_DIR / "temp_icon.ico"))
        os.remove(str(SCRIPT_DIR / "temp_icon.ico"))
    except:
        pass
    
    # 绑定关闭事件
    root.protocol("WM_DELETE_WINDOW", on_close_window)
    
    # 创建界面
    frame = tk.Frame(root, bg="#0f172a", padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    # 标题
    title_label = tk.Label(
        frame,
        text="Move Hermes",
        font=("Microsoft YaHei UI", 16, "bold"),
        fg="#38bdf8",
        bg="#0f172a"
    )
    title_label.pack(pady=(0, 20))
    
    # 状态信息
    status_frame = tk.Frame(frame, bg="#1e293b", padx=15, pady=15)
    status_frame.pack(fill=tk.X, pady=10)
    
    status_text = tk.Text(
        status_frame,
        height=6,
        width=50,
        bg="#1e293b",
        fg="#e2e8f0",
        font=("Microsoft YaHei UI", 10),
        state=tk.DISABLED,
        wrap=tk.WORD
    )
    status_text.pack(fill=tk.BOTH, expand=True)
    
    def set_status(text):
        status_text.config(state=tk.NORMAL)
        status_text.delete(1.0, tk.END)
        status_text.insert(1.0, text)
        status_text.config(state=tk.DISABLED)
    
    set_status("=" * 40 + "\n")
    set_status("  系统状态\n")
    set_status("=" * 40 + "\n\n")
    set_status("[OK] 应用程序已启动\n")
    set_status("[OK] 服务器正在运行\n")
    set_status("[OK] 数据目录已就绪\n\n")
    set_status("提示:\n")
    set_status("- 关闭窗口将最小化到系统托盘\n")
    set_status("- 右键托盘图标可退出服务器\n")
    set_status("- 点击'打开浏览器'访问系统\n")
    
    # 按钮框架
    btn_frame = tk.Frame(frame, bg="#0f172a")
    btn_frame.pack(pady=20)
    
    # 打开浏览器按钮
    open_btn = tk.Button(
        btn_frame,
        text="打开浏览器",
        font=("Microsoft YaHei UI", 10),
        bg="#3b82f6",
        fg="white",
        activebackground="#2563eb",
        activeforeground="white",
        command=on_open_browser,
        padx=20,
        pady=8,
        cursor="hand2"
    )
    open_btn.pack(side=tk.LEFT, padx=10)
    
    # 退出按钮
    quit_btn = tk.Button(
        btn_frame,
        text="退出服务器",
        font=("Microsoft YaHei UI", 10),
        bg="#ef4444",
        fg="white",
        activebackground="#dc2626",
        activeforeground="white",
        command=lambda: on_quit(),
        padx=20,
        pady=8,
        cursor="hand2"
    )
    quit_btn.pack(side=tk.LEFT, padx=10)
    
    app_window = root
    return root


def show_tray_icon():
    """显示系统托盘图标"""
    global tray_icon
    
    menu = pystray.Menu(
        pystray.MenuItem("打开浏览器", on_open_browser),
        pystray.MenuItem("显示窗口", on_show_window),
        pystray.MenuItem("-", lambda icon, item: None),
        pystray.MenuItem("退出服务器", on_quit)
    )
    
    icon_image = create_default_icon()
    
    tray_icon = pystray.Icon(
        "move-hermes",
        icon_image,
        title="Move Hermes",
        menu=menu
    )
    
    tray_icon.run_detached()


def main():
    """主函数"""
    global is_running
    
    print("=" * 50)
    print("  Move Hermes — 智能订单管理系统")
    print("=" * 50)
    print(f"  数据目录: {DATA_DIR}")
    print(f"  访问地址: http://localhost:8080")
    print("=" * 50)
    
    # 启动服务器线程
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    is_running = True
    
    # 等待服务器启动
    import time
    for i in range(30):
        time.sleep(1)
        try:
            import urllib.request
            response = urllib.request.urlopen("http://localhost:8080/health", timeout=2)
            if response.status == 200:
                print("✅ 服务器启动成功")
                break
        except:
            pass
    else:
        print("⚠️ 服务器启动超时")
    
    # 创建主窗口
    root = create_main_window()
    
    # 显示托盘图标
    show_tray_icon()
    
    # 运行主窗口
    root.mainloop()


if __name__ == "__main__":
    main()
