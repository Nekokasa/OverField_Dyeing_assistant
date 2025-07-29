import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt

class ParamOverlay(QWidget):
    def __init__(self, get_params_func, parent=None):
        super().__init__(parent)
        self.get_params_func = get_params_func
        self.setWindowTitle('参数可视化')
        # 设置为全屏遮罩，和主程序一致
        from PyQt5.QtWidgets import QApplication
        self.screen = QApplication.primaryScreen().geometry()
        self.setGeometry(self.screen)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.show()

    def paintEvent(self, event):
        params = self.get_params_func()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont()
        font.setPointSize(16)
        painter.setFont(font)
        # --- 画混色池矩形 ---
        try:
            x1 = int(params['pool_left'])
            y1 = int(params['pool_top'])
            x2 = int(params['pool_right'])
            y2 = int(params['pool_bottom'])
            painter.setPen(QPen(QColor(255,0,0), 3))
            painter.drawRect(x1, y1, x2-x1, y2-y1)
            painter.drawText(x1+20, y1-8, "混色池")
        except Exception:
            pass
        # --- 画滑块定位线 ---
        try:
            slider_x = int(params['slider_x'])
            painter.setPen(QPen(QColor(0,128,255), 2, Qt.DashLine))
            painter.drawLine(slider_x, y1, slider_x, y2)
            painter.drawText(slider_x-36, y1, "滑块")
        except Exception:
            pass
        # --- 画预览色点 ---
        try:
            painter.setPen(QPen(QColor(0,200,0), 3))
            def draw_point(x, y, label, above=True):
                painter.drawEllipse(x-8, y-8, 16, 16)
                if above:
                    painter.drawText(x-32, y-12, label)
                else:
                    painter.drawText(x-32, y+38, label)
            px = int(params['preview_x'])
            py = int(params['preview_y'])
            pw = int(params['preview_width'])
            for i in range(5):
                draw_point(px+pw*i, py, f"颜色{i+1}", above=(i%2==0))
        except Exception:
            pass
        # --- 其它主要点 ---
        try:
            painter.setPen(QPen(QColor(0,0,255), 2))
            draw_point(int(params['dye_x']), int(params['dye_y']), "换染色剂", above=True)
            draw_point(int(params['ok_x']), int(params['ok_y']), "确认键", above=True)
            draw_point(int(params['down_x']), int(params['down_y']), "下调滑块", above=True)
            draw_point(int(params['dye_start_x']), int(params['dye_start_y']), "开始染色", above=False)
        except Exception:
            pass
        # --- 染色A区矩形和标注 ---
        try:
            painter.setPen(QPen(QColor(255,128,0), 2))
            part_x = int(params['partA_X'])
            part_y = int(params['partA_Y'])
            part_w = int(params['part_width'])
            for i in range(7):
                draw_point(part_x+part_w*i, part_y, f"染色{chr(ord('A')+i)}区", above=(i%2==0))
        except Exception:
            pass
        # --- 装扮区 ---
        try:
            hat_x = int(params['hat_x'])
            hat_y = int(params['hat_Y'])
            hat_h = int(params['hat_high'])
            painter.setPen(QPen(QColor(128,0,255), 2))
            for i in range(4):
                draw_point(hat_x,hat_y+hat_h*i, f"装扮{i+1}")
        except Exception:
            pass
        # --- 染色方案 ---
        try:
            dsx = int(params['dye_scheme_x'])
            dsy = int(params['dye_scheme_y'])
            dsw = int(params['dye_scheme_width'])
            painter.setPen(QPen(QColor(0,180,180), 2))
            for i in range(5):
                draw_point(dsx+dsw*i, dsy, f"染色方案{i+1}",above=(i%2==0))
        except Exception:
            pass
        # --- 搭配方案 ---
        try:
            msx = int(params['match_scheme_x'])
            msy = int(params['match_scheme_y'])
            msw = int(params['match_scheme_width'])
            painter.setPen(QPen(QColor(255,0,0), 2))
            for i in range(3):
                draw_point(msx+msw*i, msy, f"搭配方案{i+1}",above=(i%2==0))
        except Exception:
            pass
        # --- 染色按钮 ---
        try:
            sthx = int(params['dye_sth_x'])
            sthy = int(params['dye_sth_y'])
            sthw = int(params['dye_sth_width'])
            painter.setPen(QPen(QColor(255,0,128), 2))
            for i in range(2):
                draw_point(sthx+sthw*i, sthy, f"染色按钮{i+1}")
        except Exception:
            pass
        painter.end()

class ParamTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('参数计算与可视化实验工具')
        layout = QVBoxLayout()
        # 输入区
        input_layout = QHBoxLayout()
        self.x_input = QLineEdit()
        self.y_input = QLineEdit()
        self.w_input = QLineEdit()
        self.h_input = QLineEdit()
        for label, widget in zip(['X', 'Y', '宽', '高'], [self.x_input, self.y_input, self.w_input, self.h_input]):
            input_layout.addWidget(QLabel(label))
            input_layout.addWidget(widget)
        layout.addLayout(input_layout)
        # 计算按钮
        btn_calc = QPushButton('一键填充参数')
        btn_calc.clicked.connect(self.on_calc)
        layout.addWidget(btn_calc)
        # 可视化按钮
        btn_vis = QPushButton('可视化参数位置')
        btn_vis.clicked.connect(self.on_toggle_visualize)
        self.btn_vis = btn_vis
        layout.addWidget(btn_vis)
        self.setLayout(layout)
        self.overlay = None
        self.last_params = {}
        # 参数输入框映射
        self.param_inputs = {}
        param_keys = [
            'slider_x','pool_left','pool_top','pool_right','pool_bottom',
            'preview_x','preview_y','preview_width',
            'dye_x','dye_y','ok_x','ok_y','down_x','down_y',
            'dye_start_x','dye_start_y',
            'partA_X','partA_Y','part_width',
            'hat_x','hat_Y','hat_high',
            'dye_scheme_x','dye_scheme_y','dye_scheme_width',
            'match_scheme_x','match_scheme_y','match_scheme_width',
            'dye_sth_x','dye_sth_y','dye_sth_width',
        ]
        # 动态生成参数输入区
        for k in param_keys:
            row = QHBoxLayout()
            label = QLabel(k)
            edit = QLineEdit()
            edit.setMinimumWidth(80)
            self.param_inputs[k] = edit
            row.addWidget(label)
            row.addWidget(edit)
            layout.addLayout(row)

    def on_calc(self):
        # 手动输入坐标和大小，自动填充所有参数输入框
        try:
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            w = int(self.w_input.text())
            h = int(self.h_input.text())
        except Exception:
            QMessageBox.warning(self, '输入错误', '请输入有效的整数！')
            return
        params = self.compute_params_by_rect(x, y, w, h)
        for k, v in params.items():
            if k in self.param_inputs:
                self.param_inputs[k].setText(str(v))


    def on_toggle_visualize(self):
        # 切换遮罩显示/隐藏
        if self.overlay is not None and self.overlay.isVisible():
            self.overlay.close()
            self.overlay = None
            self.btn_vis.setText("可视化参数位置")
            return
        # 从输入框收集所有参数，校验并可视化
        param_keys = [
            'slider_x','pool_left','pool_top','pool_right','pool_bottom',
            'preview_x','preview_y','preview_width',
            'dye_x','dye_y','ok_x','ok_y','down_x','down_y',
            'dye_start_x','dye_start_y',
            'partA_X','partA_Y','part_width',
            'hat_x','hat_Y','hat_high',
            'dye_scheme_x','dye_scheme_y','dye_scheme_width',
            'match_scheme_x','match_scheme_y','match_scheme_width',
            'dye_sth_x','dye_sth_y','dye_sth_width',
        ]
        params = {k: self.param_inputs[k].text() for k in param_keys}
        # 校验
        invalids = [(k, v) for k, v in params.items() if not (isinstance(v, str) and v.strip().lstrip('-').isdigit())]
        if invalids:
            msg = "部分坐标参数不是有效数字，无法显示位置！\n" + "\n".join([f"{k}: '{v}'" for k, v in invalids])
            QMessageBox.warning(self, "参数错误", msg)
            # 高亮第一个有问题的输入框
            key = invalids[0][0]
            self.param_inputs[key].setStyleSheet("background: #ffcccc;")
            self.param_inputs[key].setFocus()
            return
        # 恢复所有输入框背景
        for k, w in self.param_inputs.items():
            w.setStyleSheet("")
        # 转为int
        params = {k: int(v) for k, v in params.items()}
        self.last_params = params
        self.overlay = ParamOverlay(lambda: self.last_params)
        self.overlay.show()
        self.btn_vis.setText("取消坐标显示")

    @staticmethod
    def compute_params_by_rect(x, y, width, height):
        aspect = width / height if height else 0
        params = {}
        if aspect > 16/9:
            def f(expr):
                return eval(expr, {}, {'窗X':x, '窗Y':y, '宽':width, '高':height})
            params['down_x'] = int(f('窗X + 0.5 * 宽 - 981/1244 * 高'))
            params['down_y'] = int(f('窗Y + 1078/1244 * 高'))
            params['pool_left'] = int(f('窗X + 0.5 * 宽 - 1033/1244 * 高'))
            params['pool_top'] = int(f('窗Y + 283/1244 * 高'))
            params['pool_right'] = int(f('窗X + 0.5 * 宽 - 926/1244 * 高'))
            params['pool_bottom'] = int(f('窗Y + 1019/1244 * 高'))
            params['dye_x'] = int(f('窗X + 0.5 * 宽 - 595/1244 * 高'))
            params['dye_y'] = int(f('窗Y + 375/1244 * 高'))
            params['dye_start_x'] = int(f('窗X + 0.5 * 宽 + 782/1244 * 高'))
            params['dye_start_y'] = int(f('窗Y + 860/1244 * 高'))
            params['ok_x'] = int(f('窗X + 0.5 * 宽 + 542/1244 * 高'))
            params['ok_y'] = int(f('窗Y + 912/1244 * 高'))
            params['preview_x'] = int(f('窗X + 0.5 * 宽 - 710/1244 * 高'))
            params['preview_y'] = int(f('窗Y + 902/1244 * 高'))
            params['preview_width'] = int(f('115/1249 * 高'))
            params['slider_x'] = int(f('窗X + 0.5 * 宽 - 1061/1244 * 高'))
            params['partA_X'] = int(f('窗X + 0.5 * 宽 - 861/1249 * 高'))
            params['partA_Y'] = int(f('窗Y + 605/1249 * 高'))
            params['part_width'] = int(f('98/1249 * 高'))
            params['hat_x'] = int(f('窗X + 0.5 * 宽 - 1011/1244 * 高'))
            params['hat_Y'] = int(f('窗Y + 233/1244 * 高'))
            params['hat_high'] = int(f('110/1244 * 高'))
            params['dye_scheme_x'] = int(f('窗X + 0.5 * 宽 + 699/1249 * 高'))
            params['dye_scheme_y'] = int(f('窗Y + 1038/1249 * 高'))
            params['dye_scheme_width'] = int(f('79/1249 * 高'))
            params['match_scheme_x'] = int(f('窗X + 0.5 * 宽 + 745/1249 * 高'))
            params['match_scheme_y'] = int(f('窗Y + 868/1249 * 高'))
            params['match_scheme_width'] = int(f('123/1249 * 高'))
            params['dye_sth_x'] = int(f('窗X + 0.5 * 宽 - 902/1244 * 高'))
            params['dye_sth_y'] = int(f('窗Y + 451/1244 * 高'))
            params['dye_sth_width'] = int(f('245/1244 * 高'))
        else:
            def f(expr):
                return eval(expr, {}, {'窗X':x, '窗Y':y, '宽':width, '高':height})
            params['down_x'] = int(f('窗X + 145/2560 * 宽'))
            params['down_y'] = int(f('窗Y + 0.5*高 + 528/2560 * 宽'))
            params['pool_left'] = int(f('窗X + 84/2560 * 宽'))
            params['pool_top'] = int(f('窗Y + 0.5*高 - 393/2560 * 宽'))
            params['pool_right'] = int(f('窗X + 208/2560 * 宽'))
            params['pool_bottom'] = int(f('窗Y + 0.5*高 + 460/2560 * 宽'))
            params['dye_x'] = int(f('窗X + 591/2560 * 宽'))
            params['dye_y'] = int(f('窗Y + 0.5*高 - 287/2560 * 宽'))
            params['dye_start_x'] = int(f('窗X + 2180/2560 * 宽'))
            params['dye_start_y'] = int(f('窗Y + 高 - 439/2560 * 宽'))
            params['ok_x'] = int(f('窗X + 1908/2560 * 宽'))
            params['ok_y'] = int(f('窗Y + 0.5*高 + 336/2560 * 宽'))
            params['preview_x'] = int(f('窗X + 460/2560 * 宽'))
            params['preview_y'] = int(f('窗Y + 0.5*高 + 330/2560 * 宽'))
            params['preview_width'] = int(f('130/2560 * 宽'))
            params['slider_x'] = int(f('窗X + 50/2560 * 宽'))
            params['partA_X'] = int(f('窗X + 288/2560 * 宽'))
            params['partA_Y'] = int(f('窗Y + 0.5*高 - 21/2560 * 宽'))
            params['part_width'] = int(f('112/2560 * 宽'))
            params['hat_x'] = int(f('窗X + 109/2560 * 宽'))
            params['hat_Y'] = int(f('窗Y + 268/2560 * 宽'))
            params['hat_high'] = int(f('128/2560 * 宽'))
            params['dye_scheme_x'] = int(f('窗X + 2090/2560 * 宽'))
            params['dye_scheme_y'] = int(f('窗Y + 高 - 245/2560 * 宽'))
            params['dye_scheme_width'] = int(f('89/2560 * 宽'))
            params['match_scheme_x'] = int(f('窗X + 2140/2560 * 宽'))
            params['match_scheme_y'] = int(f('窗Y + 高 - 440/2560 * 宽'))
            params['match_scheme_width'] = int(f('142/2560 * 宽'))
            params['dye_sth_x'] = int(f('窗X + 243/2560 * 宽'))
            params['dye_sth_y'] = int(f('窗Y + 523/2560 * 宽'))
            params['dye_sth_width'] = int(f('283/2560 * 宽'))
        return params

# 用法示例

def my_callback():
    print("F10全局热键触发！")

try:
    import keyboard
    keyboard.add_hotkey('f10', my_callback)
except ImportError:
    print("未安装 keyboard 库，无法使用全局热键。请 pip install keyboard")
except Exception as e:
    print(f"注册全局热键失败: {e}")

from PyQt5 import QtCore

def main():
    app = QApplication(sys.argv)
    win = ParamTestWindow()
    win.show()
    sys.exit(app.exec_())

def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
    
if __name__ == "__main__":
    if not is_admin():
        # 重新以管理员权限启动
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, ' '.join(['"' + arg + '"' for arg in sys.argv]), None, 1)
        sys.exit(0)
    main()
