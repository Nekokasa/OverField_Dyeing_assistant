import configparser
import os
import win32gui
import win32ui
import win32con
import numpy as np
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
import math
# 参数校验相关

def is_valid_hex_color(s):
    if not isinstance(s, str):
        return False
    s = s.strip().upper()
    if s.startswith('#'):
        s = s[1:]
    if len(s) != 6:
        return False
    try:
        int(s, 16)
        return True
    except:
        return False

def is_valid_similarity(s):
    try:
        v = float(s)
        return 0 <= v <= 1
    except:
        return False

def is_valid_int(s):
    try:
        int(s)
        return True
    except:
        return False

def is_dark_color(hex_str):
    """
    判断颜色是否为暗色。
    暗色定义为RGB值的平均值小于128。
    """
    if not is_valid_hex_color(hex_str):
        raise ValueError("无效的颜色代码，必须为6位16进制字符串")
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    avg = (r + g + b) / 3
    return avg < 128
def find_all_windows(class_name, window_title):
    hwnds = []
    def callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            if win32gui.GetClassName(hwnd) == class_name and win32gui.GetWindowText(hwnd) == window_title:
                hwnds.append(hwnd)
    win32gui.EnumWindows(callback, None)
    return hwnds

def close_window(hwnd):
    if hwnd:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

def set_window_topmost(hwnd):
        # 置顶
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)

def maximize_window(hwnd):
        # 最大化
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
def hex_to_rgb(s):
    s = s.strip().lstrip('#')
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)

def calc_similarity(hex1, hex2):
    def hex_to_rgb(hex_color):
        hex_color = hex_color.strip().lstrip('#')
        if len(hex_color) != 6:
            raise ValueError('颜色码必须为6位十六进制')
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )
    
    R1, G1, B1 = hex_to_rgb(hex1)
    R2, G2, B2 = hex_to_rgb(hex2)
    
    rmean = (R1 + R2) / 2
    dR = R1 - R2
    dG = G1 - G2
    dB = B1 - B2
    
    # 原始距离公式
    distance = math.sqrt((2 + rmean/256) * (dR**2) + 4 * (dG**2) + (2 + (255 - rmean)/256) * (dB**2))
    # 计算理论最大距离（当颜色为#000000和#FFFFFF时）
    max_rmean = (0 + 255) / 2
    max_distance = math.sqrt((2 + max_rmean/256)*255**2 + 4*255**2 + (2 + (255 - max_rmean)/256)*255**2)
    return 1 - (distance / max_distance)  # 归一化到0~1

def is_similarity_enough(hex1, hex2, threshold):
    """
    判断两个颜色的相似度是否大于等于阈值。
    """
    sim = calc_similarity(hex1, hex2)
    return sim >= threshold


def find_similar_color(x1, y1, x2, y2, target_hex, threshold=0.9):
    width = x2 - x1 + 1
    height = y2 - y1 + 1
    rgb_arr = fast_grab_pixels(x1, y1, width, height)  # shape: (height, width, 3)
    target_hex = target_hex.lstrip('#')
    for y in range(height):
        for x in range(width):
            pixel = rgb_arr[y, x]  # RGB
            pixel_hex = '%02X%02X%02X' % tuple(pixel)
            sim = calc_similarity(pixel_hex, target_hex)
            if sim >= threshold:
                # 返回屏幕上的实际坐标
                return x1 + x, y1 + y
    return None  # 没找到
def fast_grab_pixels(left, top, width, height):
    """使用Windows API快速获取屏幕像素
    返回numpy数组，shape为(height, width, 3)，RGB格式
    """
    # 获取桌面窗口句柄
    hdesktop = win32gui.GetDesktopWindow()

    
    # 创建设备上下文（DC）
    desktop_dc = win32gui.GetWindowDC(hdesktop)
    img_dc = win32ui.CreateDCFromHandle(desktop_dc)
    mem_dc = img_dc.CreateCompatibleDC()
    
    # 创建位图对象
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(img_dc, width, height)
    mem_dc.SelectObject(bitmap)
    
    # 复制屏幕到位图
    mem_dc.BitBlt((0, 0), (width, height), img_dc, (left, top), win32con.SRCCOPY)
    
    # 获取位图信息
    bmpinfo = bitmap.GetInfo()
    bmpstr = bitmap.GetBitmapBits(True)
    img = np.frombuffer(bmpstr, dtype=np.uint8)
    img.shape = (height, width, 4)  # BGRA format
    
    # 清理资源
    mem_dc.DeleteDC()
    win32gui.DeleteObject(bitmap.GetHandle())
    img_dc.DeleteDC()
    win32gui.ReleaseDC(hdesktop, desktop_dc)
    
    # 转换BGR为RGB
    bgr = img[:, :, :3]  # 只取前3个通道（BGR）
    rgb = bgr[..., ::-1]  # 反转通道顺序，变成RGB
    return rgb  # 返回RGB格式

# 配置文件相关
def get_default_config(config_fields):
    # 先用固定窗口参数计算能算出来的
    params = calc_params_by_rect(0, 34, 2560, 1494, config_fields)
    # 对于无法通过窗口计算的参数，补充静态默认值
    static_defaults = {
        #主界面
        'fast_match': 'true',
        'drag_match': 'true',
        'scan_match': 'false',
        'sim': '0.9',
        'pool_sim': '0.5',
        'step': '1',
        'radius': '10',
        #常规设置
        'font_size': '12',
        'sim_step': '0.05',
        'topmost': 'true',
        'maximize': 'true',
        'auto_save_config': 'true',
        'reset_layout': 'true',
        'check_color_card': 'true',
        'auto_remove_color':'false',
        'random_color': 'true',
        'play_music': 'true',
        'music_volume': '100',
        'random_color_k': 'Q',
        'close_popup': 'false',
        'use_script_shortcut':'true',
        'script_toggle':'F10',
        'save_log': 'true',
        #防呆设置
        'prevent_duplicate': 'true',
        'confirm_delete': 'true',
        'confirm_config': 'true',
        #其它参数
        'delay': '100',
        'skip_similar': '5',
    }
    for k in config_fields:
        if not params.get(k):
            params[k] = static_defaults.get(k, '0')
    return params

def load_config_from_file(path, config_fields):
    config = configparser.ConfigParser()
    defaults = get_default_config(config_fields)
    if os.path.exists(path):
        config.read(path, encoding='utf-8')
        data = config['DEFAULT']
    else:
        data = {}
    # 对每个参数，优先取配置文件值，否则取默认值
    return {k: data.get(k, defaults.get(k, '')) or defaults.get(k, '') for k in config_fields}

def save_config_to_file(path, data, config_fields):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {k: str(data.get(k, '')) for k in config_fields}
    with open(path, 'w', encoding='utf-8') as f:
        config.write(f)

# 参数自动计算（窗口坐标等）
def get_game_hwnd():
    # 获取“开放空间”窗口句柄
    return win32gui.FindWindow("UnityWndClass", "开放空间")

def get_window_rect(hwnd):
    # 返回窗口客户区左上角x, y, width, height
    rect = win32gui.GetClientRect(hwnd)
    left, top = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
    right, bottom = win32gui.ClientToScreen(hwnd, (rect[2], rect[3]))
    width = right - left
    height = bottom - top
    return left, top, width, height

def calc_params_by_rect(x, y, width, height, config_fields):
    aspect = width / height if height else 0
    params = {'game_x': x, 'game_y': y, 'game_width': width, 'game_height': height}
    if aspect > 16/9:
        def f(expr):
            return eval(expr, {}, {'窗X':x, '窗Y':y, '宽':width, '高':height})
        params.update({
            'down_y': int(f('窗Y + 986/1212 * 高')),
            'pool_left': int(f('窗X + 0.5 * 宽 - 1007/1212 * 高')),
            'pool_top': int(f('窗Y + 243/1212 * 高')),
            'pool_right': int(f('窗X + 0.5 * 宽 - 902/1212 * 高')),
            'pool_bottom': int(f('窗Y + 960/1212 * 高')),
            'change_pool_y': int(f('窗Y + 1048/1212 * 高')),
            'preview_x': int(f('窗X + 0.5 * 宽 - 699/1212 * 高')),
            'preview_y': int(f('窗Y + 902/1244 * 高')),
            'preview_width': int(f('115/1249 * 高')),
            'slider_x': int(f('窗X + 0.5 * 宽 - 1061/1244 * 高')),
        })
    else:
        def f(expr):
            return eval(expr, {}, {'窗X':x, '窗Y':y, '宽':width, '高':height})
        params.update({
            'down_y': int(f('窗Y + 0.5*高 + 450/2560 * 宽')),
            'pool_left': int(f('窗X + 84/2560 * 宽')),
            'pool_top': int(f('窗Y + 0.5*高 - 431/2560 * 宽')),
            'pool_right': int(f('窗X + 208/2560 * 宽')),
            'pool_bottom': int(f('窗Y + 0.5*高 + 420/2560 * 宽')),
            'change_pool_y': int(f('窗Y + 0.5*高 + 525/2560 * 宽')),
            'preview_x': int(f('窗X + 450/2560 * 宽')),
            'preview_y': int(f('窗Y + 0.5*高 + 330/2560 * 宽')),
            'preview_width': int(f('130/2560 * 宽')),
            'slider_x': int(f('窗X + 50/2560 * 宽')),
        })
    # 只返回config_fields中有的
    for k in config_fields:
        if k in params:
            params[k] = str(params[k])
    return params

def show_param_overlay(parent, params, btn=None, step=0):
    class ParamOverlay(QWidget):
        font_size = int(params.get('font_size', '12'))
        def __init__(self, parent, params, btn, step):
            super().__init__(None)
            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_DeleteOnClose)
            self.params = params
            self.screen = QApplication.primaryScreen().geometry()
            self.setGeometry(self.screen)
            self.btn = btn
            self.step = step
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            font = QFont()
            font.setPointSize(self.font_size)
            painter.setFont(font)
            # step=0: 主界面
            if self.step == 0:
                pool_middle = (int(self.params['pool_left']) + int(self.params['pool_right'])) // 2
                painter.setPen(QPen(QColor(0,0,255), 2))
                self.draw_point(painter, int(pool_middle), int(self.params['change_pool_y']), "换染色池", above=True)
                painter.setPen(QPen(QColor(255,0,0), 3))
                x1 = int(self.params['pool_left'])
                y1 = int(self.params['pool_top'])
                x2 = int(self.params['pool_right'])
                y2 = int(self.params['pool_bottom'])
                painter.drawRect(x1, y1, x2-x1, y2-y1)
                painter.drawText(x1+20, y1-8, "混色池")
                slider_x = int(self.params['slider_x'])
                painter.setPen(QPen(QColor(0,128,255), 2, Qt.DashLine))
                painter.drawLine(slider_x, y1, slider_x, y2)
                painter.drawText(slider_x-36, y1, "滑块")
                painter.setPen(QPen(QColor(0,200,0), 3))
                px = int(self.params['preview_x'])
                py = int(self.params['preview_y'])
                pw = int(self.params['preview_width'])
                for i in range(5):
                    self.draw_point(painter, px+pw*i, py, f"颜色{i+1}", above=(i%2==0))
                painter.setPen(QPen(QColor(0,114,255), 2))
                self.draw_point(painter, int(pool_middle), int(self.params['down_y']), "下调滑块", above=True)
                
                

        def draw_point(self, painter, x, y, label, above=True):
            size = self.font_size
            painter.drawEllipse(x-size//2, y-size//2, size, size)
            # 根据label长度动态调整x偏移，使点在label中间
            metrics = painter.fontMetrics()
            text_width = metrics.width(label)
            offset = text_width // 2
            if above:
                painter.drawText(x - offset, y - size, label)
            else:
                painter.drawText(x - offset, y + 2*size + size//2, label)
    overlay = ParamOverlay(parent, params, btn, step)
    overlay.show()
    return overlay, 1
