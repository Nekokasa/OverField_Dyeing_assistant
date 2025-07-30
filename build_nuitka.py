import os
import shutil
import subprocess
import sys

def clean_build_folders():
    """清理构建文件夹"""
    folders = ['build', 'dist']
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"已清理 {folder} 文件夹")

def build_with_nuitka():
    """使用 Nuitka 打包应用程序"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    clean_build_folders()
    app_name = "OpenFieldDyeingAssistant_v1.0.0"
    main_script = os.path.join(current_dir, "rsc", "color_matcher_mini.py")
    icon_path = os.path.join(current_dir, "icon", "favicon.ico")
    # Nuitka 打包命令
    # 自动查找 PyQt5 platforms 路径
    try:
        import PyQt5
        pyqt5_dir = os.path.dirname(PyQt5.__file__)
        platforms_dir = os.path.join(pyqt5_dir, 'Qt5', 'plugins', 'platforms')
        platforms_param = f'--include-plugin-directory={platforms_dir}'
    except Exception:
        platforms_param = None

    cmd = [
        sys.executable, "-m", "nuitka",
        "--show-progress",
        "--standalone",
        f"--output-dir={os.path.join(current_dir, 'dist')}",
        f"--windows-icon-from-ico={icon_path}",
        f"--output-filename={app_name}",
        "--remove-output",
        "--enable-plugin=pyqt5",
        "--windows-console-mode=disable",
        "--nofollow-import-to=cv2",      # 排除 cv2
        "--nofollow-import-to=PIL",       # 排除 PIL
        "--include-data-dir=%s=icon" % os.path.join(current_dir, "icon"),
        "--include-data-dir=%s=config" % os.path.join(current_dir, "config")
    ]
    if platforms_param:
        cmd.append(platforms_param)
    cmd.append(main_script)
    print("开始 Nuitka 打包...")
    try:
        subprocess.run(cmd, check=True)
        print(f"Nuitka 打包完成！程序位于 dist 文件夹中")
    except Exception as e:
        print(f"Nuitka 打包失败: {str(e)}")

if __name__ == "__main__":
    build_with_nuitka()
