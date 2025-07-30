import os
import shutil
from PyInstaller.__main__ import run

def clean_build_folders():
    """清理构建文件夹"""
    folders = ['build', 'dist']
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"已清理 {folder} 文件夹")

def build_app():
    """构建应用程序"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    clean_build_folders()
    app_name = "开放空间染色助手v1.0.0"
    icon_path = os.path.join(current_dir, "icon", "icon.png")
    main_script = os.path.join(current_dir, "rsc", "color_matcher_mini.py")

    params = [
        main_script,
        f'--name={app_name}',
        '--onedir',
        # '--console',  # 调试时建议保留控制台
        f'--icon={icon_path}',
        '--noconfirm',
        '--exclude-module=cv2',
        '--exclude-module=PIL'
        
        f'--add-data={os.path.join(current_dir, "config")};config',
        # f'--add-data={os.path.join(current_dir, "rsc")};rsc',
        f'--add-data={os.path.join(current_dir, "icon")};icon',
        # f'--add-data={os.path.join(current_dir, "log")};log',
        # '--hidden-import=PyQt5',
        # '--hidden-import=PyQt5.QtCore',
        # '--hidden-import=PyQt5.QtGui',
        # '--hidden-import=PyQt5.QtWidgets',
        # '--hidden-import=PyQt5.sip',
        # '--hidden-import=keyboard',
        # '--hidden-import=win32api',
        # '--hidden-import=win32gui',
        # '--hidden-import=win32event',
        # '--hidden-import=winerror',
        # '--hidden-import=win32con',
        # '--hidden-import=ui_logic_mini',
        # '--hidden-import=color_card_util',
        # '--hidden-import=logger_util',
        # '--collect-all=PyQt5',
    ]

    print("开始打包...")
    try:
        run(params)
        print(f"打包完成！程序位于 dist/{app_name} 文件夹中")
    except Exception as e:
        print(f"打包失败: {str(e)}")

if __name__ == "__main__":
    build_app()