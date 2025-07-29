import PyInstaller.__main__
import os
import importlib.util
import keyboard

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 获取 keyboard 模块的位置
keyboard_path = os.path.dirname(keyboard.__file__)
winkeyboard_path = os.path.join(keyboard_path, '_winkeyboard.cp312-win_amd64.pyd')

# 定义资源文件
resources = [
    os.path.join(current_dir, 'config'),  # config 文件夹
    os.path.join(current_dir, 'rsc'),     # rsc 文件夹
]

# 打包参数
params = [
    os.path.join(current_dir, 'rsc', 'color_matcher_mini.py'),  # 主程序
    '--name=开发空间染色助手_v1.0',           # 生成的exe名称
    '--noconsole',              # 不显示控制台
    '--icon=' + os.path.join(current_dir, 'rsc', 'icon.png'),  # 程序图标
    '--hidden-import=keyboard',  # keyboard模块
    '--hidden-import=win32api',  # win32api模块
    '--manifest=' + os.path.join(current_dir, 'app.manifest'),   # 管理员权限manifest
    '--noconfirm',              # 覆盖已存在的输出目录
    '--clean',                  # 清理临时文件
]

# 添加资源文件
for res in resources:
    if os.path.isdir(res):
        params.append(f'--add-data={res};{os.path.basename(res)}')

# 运行打包
PyInstaller.__main__.run(params)

print("打包完成!")
