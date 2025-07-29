import configparser
import os
import win32gui
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

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
# 配置文件相关

def get_default_config(config_fields):
    # 先用固定窗口参数计算能算出来的
    params = calc_params_by_rect(0, 34, 2560, 1494, config_fields)
    # 对于无法通过窗口计算的参数，补充静态默认值
    static_defaults = {
        #主界面
        'search_mode': 'true',
        'fast_match': 'true',
        'drag_match': 'true',
        'scan_match': 'false',
        'sim': '0.9',
        'pool_sim': '0.5',
        'step': '1',
        'radius': '10',
        'slider_delay': '0',
        #常规设置
        'font_size': '12',
        'sim_step': '0.05',
        'topmost': 'true',
        'maximize': 'true',
        'auto_save_config': 'true',
        'reset_layout': 'true',
        'check_color_card': 'true',
        'random_color': 'true',
        'random_color_k': 'Q',
        'close_popup': 'false',
        'use_script_shortcut':'true',
        'script_toggle':'F10',
        'save_log': 'true',
        #防呆设置
        'prevent_duplicate': 'true',
        'confirm_delete': 'true',
        'confirm_delete_proxy_data': 'true',
        'confirm_diff_scheme': 'true',
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
            'down_x': int(f('窗X + 0.5 * 宽 - 981/1244 * 高')),
            'down_y': int(f('窗Y + 1078/1244 * 高')),
            'pool_left': int(f('窗X + 0.5 * 宽 - 1033/1244 * 高')),
            'pool_top': int(f('窗Y + 283/1244 * 高')),
            'pool_right': int(f('窗X + 0.5 * 宽 - 926/1244 * 高')),
            'pool_bottom': int(f('窗Y + 1019/1244 * 高')),
            'dye_x': int(f('窗X + 0.5 * 宽 - 595/1244 * 高')),
            'dye_y': int(f('窗Y + 375/1244 * 高')),
            'dye_start_x': int(f('窗X + 0.5 * 宽 + 782/1244 * 高')),
            'dye_start_y': int(f('窗Y + 860/1244 * 高')),
            'ok_x': int(f('窗X + 0.5 * 宽 + 542/1244 * 高')),
            'ok_y': int(f('窗Y + 912/1244 * 高')),
            'preview_x': int(f('窗X + 0.5 * 宽 - 710/1244 * 高')),
            'preview_y': int(f('窗Y + 902/1244 * 高')),
            'preview_width': int(f('115/1249 * 高')),
            'slider_x': int(f('窗X + 0.5 * 宽 - 1061/1244 * 高')),
            'partA_X': int(f('窗X + 0.5 * 宽 - 861/1249 * 高')),
            'partA_Y': int(f('窗Y + 605/1249 * 高')),
            'part_width': int(f('98/1249 * 高')),
            'hat_x': int(f('窗X + 0.5 * 宽 - 1011/1244 * 高')),
            'hat_y': int(f('窗Y + 233/1244 * 高')),
            'hat_height': int(f('110/1244 * 高')),
            'dye_scheme_x': int(f('窗X + 0.5 * 宽 + 699/1249 * 高')),
            'dye_scheme_y': int(f('窗Y + 1038/1249 * 高')),
            'dye_scheme_width': int(f('79/1249 * 高')),
            'match_scheme_x': int(f('窗X + 0.5 * 宽 + 745/1249 * 高')),
            'match_scheme_y': int(f('窗Y + 868/1249 * 高')),
            'match_scheme_width': int(f('123/1249 * 高')),
            'dye_sth_x': int(f('窗X + 0.5 * 宽 - 902/1244 * 高')),
            'dye_sth_y': int(f('窗Y + 451/1244 * 高')),
            'dye_sth_width': int(f('245/1244 * 高')),
            'dye_color_x': int(f('窗X + 0.5 * 宽 - 290/575 * 高')),
            'dye_color_y': int(f('窗Y + 379/575 * 高')),
            'save_color_x': int(f('窗X + 0.5 * 宽 - 221/575 * 高')),
            'save_color_y': int(f('窗Y + 469/575 * 高')),
            'save_color_width': int(f('144/575 * 高')),
        })
    else:
        def f(expr):
            return eval(expr, {}, {'窗X':x, '窗Y':y, '宽':width, '高':height})
        params.update({
            'down_x': int(f('窗X + 145/2560 * 宽')),
            'down_y': int(f('窗Y + 0.5*高 + 528/2560 * 宽')),
            'pool_left': int(f('窗X + 84/2560 * 宽')),
            'pool_top': int(f('窗Y + 0.5*高 - 393/2560 * 宽')),
            'pool_right': int(f('窗X + 208/2560 * 宽')),
            'pool_bottom': int(f('窗Y + 0.5*高 + 460/2560 * 宽')),
            'dye_x': int(f('窗X + 591/2560 * 宽')),
            'dye_y': int(f('窗Y + 0.5*高 - 287/2560 * 宽')),
            'dye_start_x': int(f('窗X + 2180/2560 * 宽')),
            'dye_start_y': int(f('窗Y + 高 - 439/2560 * 宽')),
            'ok_x': int(f('窗X + 1908/2560 * 宽')),
            'ok_y': int(f('窗Y + 0.5*高 + 336/2560 * 宽')),
            'preview_x': int(f('窗X + 460/2560 * 宽')),
            'preview_y': int(f('窗Y + 0.5*高 + 330/2560 * 宽')),
            'preview_width': int(f('130/2560 * 宽')),
            'slider_x': int(f('窗X + 50/2560 * 宽')),
            'partA_X': int(f('窗X + 288/2560 * 宽')),
            'partA_Y': int(f('窗Y + 0.5*高 - 21/2560 * 宽')),
            'part_width': int(f('112/2560 * 宽')),
            'hat_x': int(f('窗X + 109/2560 * 宽')),
            'hat_y': int(f('窗Y + 268/2560 * 宽')),
            'hat_height': int(f('128/2560 * 宽')),
            'dye_scheme_x': int(f('窗X + 2090/2560 * 宽')),
            'dye_scheme_y': int(f('窗Y + 高 - 245/2560 * 宽')),
            'dye_scheme_width': int(f('89/2560 * 宽')),
            'match_scheme_x': int(f('窗X + 2140/2560 * 宽')),
            'match_scheme_y': int(f('窗Y + 高 - 440/2560 * 宽')),
            'match_scheme_width': int(f('142/2560 * 宽')),
            'dye_sth_x': int(f('窗X + 243/2560 * 宽')),
            'dye_sth_y': int(f('窗Y + 523/2560 * 宽')),
            'dye_sth_width': int(f('283/2560 * 宽')),
            'dye_color_x': int(f('窗X + 555/2560 * 宽')),
            'dye_color_y': int(f('窗Y + 0.5*高 + 231/2560 * 宽')),
            'save_color_x': int(f('窗X + 730/2560 * 宽')),
            'save_color_y': int(f('窗Y + 高 - 266/2560 * 宽')),
            'save_color_width': int(f('358/2560 * 宽')),
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
            # step=0: 选择服装界面
            if self.step == 0:
                # 帽子装扮
                hat_x = int(self.params['hat_x'])
                hat_y = int(self.params['hat_y'])
                hat_h = int(self.params['hat_height'])
                painter.setPen(QPen(QColor(128,0,255), 2))
                for i in range(4):
                    self.draw_point(painter, hat_x, hat_y+hat_h*i, f"装扮{i+1}")
                # 染色按钮
                sthx = int(self.params['dye_sth_x'])
                sthy = int(self.params['dye_sth_y'])
                sthw = int(self.params['dye_sth_width'])
                painter.setPen(QPen(QColor(255,0,128), 2))
                for i in range(2):
                    self.draw_point(painter, sthx+sthw*i, sthy, f"染色按钮{i+1}")
                # 搭配方案
                msx = int(self.params['match_scheme_x'])
                msy = int(self.params['match_scheme_y'])
                msw = int(self.params['match_scheme_width'])
                painter.setPen(QPen(QColor(30,30,255), 2))
                for i in range(3):
                    self.draw_point(painter, msx+msw*i, msy, f"搭配方案{i+1}", above=(i%2==0))
            # step=1: 选择染色剂界面
            elif self.step == 1:
                painter.setPen(QPen(QColor(255,0,255), 2))
                self.draw_point(painter, int(self.params['dye_x']), int(self.params['dye_y']), "选择染色剂", above=True)
                self.draw_point(painter, int(self.params['ok_x']), int(self.params['ok_y']), "确认键", above=True)
            # step=2: 选色界面
            elif self.step == 2:
                painter.setPen(QPen(QColor(255,0,255), 2))
                self.draw_point(painter, int(self.params['dye_x']), int(self.params['dye_y']), "换染色剂", above=True)
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
                painter.setPen(QPen(QColor(255,0,255), 2))
                self.draw_point(painter, int(self.params['down_x']), int(self.params['down_y']), "下调滑块", above=True)
                self.draw_point(painter, int(self.params['dye_start_x']), int(self.params['dye_start_y']), "开始染色", above=False)
                painter.setPen(QPen(QColor(255,128,0), 2))
                part_x = int(self.params['partA_X'])
                part_y = int(self.params['partA_Y'])
                part_w = int(self.params['part_width'])
                for i in range(7):
                    self.draw_point(painter, part_x+part_w*i, part_y, f"染色{chr(ord('A')+i)}区", above=(i%2==0))
                dsx = int(self.params['dye_scheme_x'])
                dsy = int(self.params['dye_scheme_y'])
                dsw = int(self.params['dye_scheme_width'])
                painter.setPen(QPen(QColor(0,180,180), 2))
                for i in range(5):
                    self.draw_point(painter, dsx+dsw*i, dsy, f"染色方案{i+1}", above=(i%2==0))
            # step=3: 确认染色界面
            elif self.step == 3:
                painter.setPen(QPen(QColor(2,192,250), 2))
                self.draw_point(painter, int(self.params['dye_color_x']), int(self.params['dye_color_y']), f"染色颜色")
                scx = int(self.params['save_color_x'])
                scy = int(self.params['save_color_y'])
                scw = int(self.params['save_color_width'])
                painter.setPen(QPen(QColor(0,85,217), 2))
                self.draw_point(painter, scx, scy, f"保存颜色")
                self.draw_point(painter, scx-scw, scy, f"放弃保存")
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
    return overlay, 4
