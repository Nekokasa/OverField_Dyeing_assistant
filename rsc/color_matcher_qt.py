import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QCheckBox, QRadioButton, QButtonGroup, QMessageBox, QGridLayout,
    QSizePolicy, QScrollArea, QComboBox, QFileDialog, QKeySequenceEdit, QShortcut, QSystemTrayIcon, QStyle
)
from PyQt5.QtGui import QColor,QFont, QKeySequence
from PyQt5.QtCore import Qt, QRect, QEvent, QEventLoop,QTimer
import ui_logic
from search_util import ScriptWorker
import color_card_util
import os
import keyboard
from logger_util import logger_manager
from PyQt5.QtCore import QThread, pyqtSignal
import importlib

def excepthook(exc_type, exc_value, exc_traceback):
    logger = logger_manager.setup_logger()
    import traceback
    logger.error("程序异常：\n" + ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

sys.excepthook = excepthook

class LoopSpinBox(QSpinBox):
    def stepBy(self, steps):
        val = self.value() + steps
        if val < self.minimum():
            self.setValue(self.maximum())
        elif val > self.maximum():
            self.setValue(self.minimum())
        else:
            super().stepBy(steps)
    def stepEnabled(self):
        # 始终允许加减按钮可用，实现环绕
        return QSpinBox.StepUpEnabled | QSpinBox.StepDownEnabled

class SyncWidthWidget(QWidget):
    def __init__(self, left_widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.left_widget = left_widget

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.left_widget:
            self.left_widget.setFixedWidth(self.width()+26)
            # 26是滚动条宽度

class ColorMatcherApp(QMainWindow):
    askUserSignal = pyqtSignal(str, str, object)
    showMessageSignal = pyqtSignal(str, str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("开放空间染色助手")
        self.init_ui()
        self.reset_config()  # 初始化时直接加载config.ini
        self.apply_font_size()  # 应用默认字体大小
        self.askUserSignal.connect(self.handle_ask_user)
        self.showMessageSignal.connect(self.show_message)
        self.script_thread = None
        # 读取“保存日志文件”复选框状态，决定是否保存日志
        enable_log = True  # 默认开启
        try:
            enable_log = self.save_log_cb.isChecked()
        except Exception:
            pass
        logger_manager.setup_logger(enable_file=enable_log)
        

    def get_param_keys(self):
        return [
            'slider_x','pool_left','pool_top','pool_right','pool_bottom',
            'preview_x','preview_y','preview_width',
            'dye_x','dye_y','ok_x','ok_y','down_x','down_y',
            'dye_start_x','dye_start_y',
            'partA_X','partA_Y','part_width',
            'hat_x','hat_y','hat_height',
            'game_x','game_y','game_width','game_height',
            'dye_scheme_x','dye_scheme_y','dye_scheme_width',
            'match_scheme_x','match_scheme_y','match_scheme_width',
            'dye_sth_x','dye_sth_y','dye_sth_width',
            'dye_color_x','dye_color_y',
            'save_color_x','save_color_y','save_color_width',
        ]

    def get_config_fields(self):
        # 所有参数字段名，顺序与界面一致，补全所有坐标相关参数
        base_fields = [
            # 工作模式相关
            'search_mode', 'proxy_mode',
            # 基础设置
            'topmost', 'maximize', 'font_size','sim_step',
            'reset_layout', 'auto_save_config','check_color_card',
            'random_color','random_color_k',
            'use_script_shortcut','script_toggle',
            'close_popup',
            'save_log',
            # 防呆设置
            'prevent_duplicate','confirm_delete_proxy_data',
            'confirm_diff_scheme','confirm_config','confirm_delete',
            'window_x', 'window_y', 'window_width', 'window_height',
            # 其它参数
            'delay', 'skip_similar',
            # 匹配模式相关
            'fast_match', 'drag_match', 'scan_match',
            'pool_sim', 'step', 'radius', 'slider_delay', 
            'sim'
        ]
        param_keys = self.get_param_keys()
        # 去除重复
        base_fields = [k for k in base_fields if k not in param_keys]
        return base_fields + param_keys

    def apply_font_size(self):
        size = self.font_size_input.value()
        font = QFont()
        font.setPointSize(size)
        QApplication.setFont(font)
        # 预览区字体大小
        self.hex_preview.setFixedSize(int(size * 2), 3 * max(int(size * 2.5), 32) + 18)
        # 控件高度自适应字体
        for widget in self.findChildren((QLineEdit, QPushButton, QSpinBox, QCheckBox,QDoubleSpinBox, QComboBox)):
            widget.setMinimumHeight(max(int(size * 2.5), 32))
        if hasattr(self, 'table'):
            self.table.verticalHeader().setDefaultSectionSize(int(size * 2.7))
        # 分区标题加粗，内容区不加粗
        # 自动收集所有QGroupBox并统一设置字体
        group_boxes = [v for v in self.__dict__.values() if isinstance(v, QGroupBox)]
        for group in group_boxes:
            font_bold = group.font()
            font_bold.setPointSize(size)
            font_bold.setBold(True)
            group.setFont(font_bold)
            font_normal = group.font()
            font_normal.setPointSize(size)
            font_normal.setBold(False)
            for child in group.findChildren(QWidget):
                child.setFont(font_normal)
        # self.param_box.setMaximumWidth(self.input_box.minimumSizeHint().width())
        if hasattr(self, 'left_widget'):
            boxes = self.left_widget.findChildren(QGroupBox)
            # for box in boxes:
            #     print(box.title(), ":", box.minimumSizeHint().width())
            if boxes:
                # 找出最大的minimumSizeHint宽度
                min_width = max(box.minimumSizeHint().width() for box in boxes)
                # print("最大的minimumSizeHint宽度:", min_width)
                # 设置所有box的最大宽度和尺寸策略
                for box in boxes:
                    box.setMaximumWidth(min_width)
                    box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

    def init_ui(self):
        self.tabs = QTabWidget()
        # 连接标签页切换信号
        self.setCentralWidget(self.tabs)
        self.create_search_tab()
        self.create_settings_tab()
        self.tabs.currentChanged.connect(lambda: self.apply_font_size())

    def on_hex_changed(self):
        text = self.hex_input.text().strip().upper()
        # 允许#，自动去除
        if text.startswith('#'):
            text = text[1:]
        # 只保留0-9A-F字符
        text = ''.join([c for c in text if c in '0123456789ABCDEF'])
        # 自动补0到高位，始终6位
        text = text[-6:].rjust(6, '0')
        if self.hex_input.text() != text:
            self.hex_input.blockSignals(True)
            self.hex_input.setText(text)
            self.hex_input.blockSignals(False)
        if len(text) == 6:
            try:
                r = int(text[0:2], 16)
                g = int(text[2:4], 16)
                b = int(text[4:6], 16)
                for sb, val in zip((self.r_input, self.g_input, self.b_input), (r, g, b)):
                    sb.blockSignals(True)
                    sb.setValue(val)
                    sb.blockSignals(False)
                self.hex_preview.setStyleSheet(f"background:#{text};border:1px solid #ccc;")
            except:
                self.hex_preview.setStyleSheet("background:white;border:1px solid #ccc;")
        else:
            self.hex_preview.setStyleSheet("background:white;border:1px solid #ccc;")

    def on_rgb_changed(self):
        r, g, b = self.r_input.value(), self.g_input.value(), self.b_input.value()
        hex_str = f"{r:02X}{g:02X}{b:02X}"
        self.hex_input.blockSignals(True)
        self.hex_input.setText(hex_str)
        self.hex_input.blockSignals(False)
        self.hex_preview.setStyleSheet(f"background:#{hex_str};border:1px solid #ccc;")

    def insert_or_update_row(self, row, color_name, hex_str, similarity, match_str=None, type_str=None, scheme_str=None, part_str=None, guarantee_priority=None):
        """插入或更新表格一行，支持代理染色和查找模式。"""
        if row >= self.table.rowCount():
            self.table.insertRow(row)
        # 色块
        color_item = QTableWidgetItem()
        color_item.setBackground(QColor(f"#{hex_str}"))
        color_item.setText(color_name)
        color_item.setForeground(QColor("white") if ui_logic.is_dark_color(hex_str) else QColor("black"))
        self.table.setItem(row, 0, color_item)
        # 颜色值
        item_color = QTableWidgetItem(hex_str)
        self.table.setItem(row, 1, item_color)
        # 相似度
        item_sim = QTableWidgetItem(f"{float(similarity):.2f}"if similarity else 0.0)
        self.table.setItem(row, 2, item_sim)
        # 代理染色模式下填充后五列
        if self.proxy_mode_rb.isChecked() and self.table.columnCount() > 3:
            item_match = QTableWidgetItem(match_str if match_str else "")
            self.table.setItem(row, 3, item_match)
            item_type = QTableWidgetItem(type_str if type_str else "")
            self.table.setItem(row, 4, item_type)
            item_scheme = QTableWidgetItem(scheme_str if scheme_str else "")
            self.table.setItem(row, 5, item_scheme)
            item_part = QTableWidgetItem(part_str if part_str else "")
            self.table.setItem(row, 6, item_part)
            item_guarantee = QTableWidgetItem(guarantee_priority if guarantee_priority else "")
            self.table.setItem(row, 7, item_guarantee)

    def get_current_row_inputs(self):
        """
        获取当前输入区的所有插入/更新参数：
        返回元组 (preview_str,hex_str, similarity,match_str, type_str,  scheme_str,part_str, guarantee_priority)
        查找模式后三项为空字符串。
        输入校验失败时弹窗并返回 (None)
        """
        input_data = []
        input_data.append(self.preview_input.text().strip())
        # 校验16进制颜色
        
        if not ui_logic.is_valid_hex_color(self.hex_input.text()):
            QMessageBox.warning(self, "错误", "请输入6位16进制颜色")
            return (None)
        else:input_data.append(self.hex_input.text().strip().upper())
        # 校验相似度
        if not (0 <= self.sim_input.value() <= 1):
            QMessageBox.warning(self, "错误", "相似度必须为0-1之间的小数")
            return (None)
        else:input_data.append(f"{float(self.sim_input.value()):.2f}")
        flag = self.proxy_mode_rb.isChecked() and self.table.columnCount() > 3
        input_data.append(str(self.match_scheme_spin.value()) if flag else "")
        input_data.append(self.type_combo.currentText() if flag else "")
        input_data.append(str(self.scheme_spin.value()) if flag else "")
        input_data.append(self.part_combo.currentText() if flag else "")
        input_data.append(self.guarantee_priority_combo.currentText() if flag else "")
        return tuple(input_data)
    
    def is_row_unique(self, hex_str, match_str,type_str, scheme_str,part_str,  exclude_row=None, ignore_front=False):
        """
        统一查重函数。
        - 代理染色模式：主键为match_str+type_str+part_str+scheme_str。
        - 查找模式：主键为hex_str。
        - exclude_row: 修改时排除自身。
        - scheme_str: 当前输入的染色方案。
        """
        row_range = range(self.table.rowCount())
        if exclude_row is not None and ignore_front == True:
            row_range = range(exclude_row+1, self.table.rowCount())
        for row in row_range:
            # print(f"Checking row {row} for uniqueness")
            if exclude_row is not None and row == exclude_row:
                continue
            elif (self.proxy_mode_rb.isChecked() and self.table.columnCount() > 3
                  and match_str is not None
                  and type_str is not None
                  and part_str is not None
                  and scheme_str is not None):
                _,_,_,item_match, item_type, item_scheme, item_part, _ = self.get_table_row_data(row)
                # 主键查重：搭配方案+装扮类型+染色部位+染色方案都相同才判重
                if (item_match and item_match == match_str
                and item_type and item_type == type_str 
                and item_part and item_part == part_str 
                and item_scheme and item_scheme == scheme_str):
                    QMessageBox.warning(self, "错误", f"搭配方案{match_str}中{type_str}的染色方案{scheme_str}存在多个染色部位{part_str}的条目！")
                    return False
            else:
                item_color = self.table.item(row, 1)
                if item_color and item_color.text().upper() == hex_str.upper():
                    QMessageBox.warning(self, "错误", f"颜色{hex_str}已存在")
                    return False
        return True
    def is_scheme_unique(self, match_str, type_str, scheme_str, exclude_row=None, ignore_front=False):
        """
        检查染色方案是否唯一。
        - exclude_row: 修改时排除自身。
        """
        row_range = range(self.table.rowCount())
        if exclude_row is not None and ignore_front == True:
            row_range = range(exclude_row+1, self.table.rowCount())
        for row in row_range:
            # print(f"Checking row {row} for uniqueness")
            if exclude_row is not None and row == exclude_row:
                continue
            if self.proxy_mode_rb.isChecked() and self.table.columnCount() > 3 and type_str is not None and scheme_str is not None:
                _,_,_,item_match, item_type, item_scheme, _,_ = self.get_table_row_data(row)
                if (item_match and item_match == match_str
                    and item_type and item_type == type_str
                    and item_scheme and scheme_str is not None and item_scheme != scheme_str
                    ):
                    reply = QMessageBox.question(
                    self, "确认添加", f"存在装扮类型为{type_str}但染色方案不同的条目，是否继续？",
                    QMessageBox.Yes | QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        return False
                    break
        return True

    def add_color(self):
        input_data = self.get_current_row_inputs()
        if input_data == None:
            return
        if hasattr(self, 'prevent_duplicate_cb') and self.prevent_duplicate_cb.isChecked():
            # 如果启用了防止重复查找项，则检查当前输入是否唯一
            if not self.is_row_unique(input_data[1], *input_data[3:7]):
                return
        if hasattr(self, 'confirm_diff_scheme_cb') and self.confirm_diff_scheme_cb.isChecked():
            if not self.is_scheme_unique( *input_data[3:6]):
                return
        row = self.table.rowCount()
        print("添加颜色:",input_data)
        self.insert_or_update_row(row,*input_data)
        self.sort_table()
        #清空选中行
        self.table.clearSelection()


    def modify_color(self):
        if self.editing_row is None:
            return
        input_data = self.get_current_row_inputs()
        current_data = self.get_table_row_data(self.editing_row)
        if input_data == None:
            return
        if current_data and current_data == input_data:
            return
        if hasattr(self, 'prevent_duplicate_cb') and self.prevent_duplicate_cb.isChecked():
            if not self.is_row_unique(input_data[1], *input_data[3:7],exclude_row=self.editing_row):
                return
        if hasattr(self, 'confirm_diff_scheme_cb') and self.confirm_diff_scheme_cb.isChecked():
            if not self.is_scheme_unique( *input_data[3:6], exclude_row=self.editing_row):
                return
        print("修改颜色:",current_data,"→",input_data)
        self.insert_or_update_row(self.editing_row,*input_data)
        self.sort_table()

    def remove_color(self):
        rows = set(idx.row() for idx in self.table.selectedIndexes())
        if not rows:
            return
        if hasattr(self, 'confirm_delete_cb') and self.confirm_delete_cb.isChecked():
            reply = QMessageBox.question(self, "确认删除", "确定要删除选中的颜色吗？", QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        for row in sorted(rows, reverse=True):
            print("删除颜色:",self.get_table_row_data(row))
            self.table.removeRow(row)

    def clear_colors(self):
        if self.table.rowCount() == 0:
            return
        if hasattr(self, 'confirm_delete_cb') and self.confirm_delete_cb.isChecked():
            reply = QMessageBox.question(self, "确认清空", "确定要清空所有颜色吗？", QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        msg = "清空颜色："
        all_data = self.get_all_table_data()
        for row_data in all_data:
            msg += str(row_data)+'\n'
        print(msg)
        self.table.setRowCount(0)

    def sort_table(self):
        """仅在代理染色模式下，对表格内容按装扮类型、染色部位、染色方案排序；非代理模式下只居中对齐."""
        if self.proxy_mode_rb.isChecked() and self.table.columnCount() > 3:
        # 代理染色模式下，收集所有行数据
            rows = []
            editing_row = getattr(self, 'editing_row', None)
            # 1. 记录排序前的信息
            editing_key = None
            if editing_row is not None:
                editing_key =  self.get_table_row_data(editing_row)
            for row in range(self.table.rowCount()):
                row_data = self.get_table_row_data(row)
                if row_data is not None:
                    rows.append(row_data)
            # 排序规则
            match_order = {str(i): i for i in range(1, 4)}
            type_order = {"帽子": 0, "发型": 1, "服装": 2, "挂件": 3}
            part_order = {chr(ord('A')+i): i for i in range(7)}
            scheme_order = {str(i): i for i in range(1, 6)}
            def sort_key(row):
                return (
                    match_order.get(row[3], 99),
                    type_order.get(row[4], 99),
                    scheme_order.get(row[5], 99),
                    part_order.get(row[6], 99)
                )
            rows.sort(key=sort_key)
            self.table.setRowCount(0)
            for row_data in rows:
                row = self.table.rowCount()
                # 复用插入逻辑，保证所有列和格式一致
                self.insert_or_update_row(row,*row_data)
            # 2. 如果有编辑行，重新定位到编辑行
            if editing_key is not None:
                for new_row in range(self.table.rowCount()):
                    rd = self.get_table_row_data(new_row)
                    if rd == editing_key:
                        self.table.setCurrentCell(new_row, 0)
                        self.editing_row = new_row
                        break
        # 居中对齐
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def update_table_columns(self):
        """根据当前工作模式动态调整表格列"""
        headers = ["预览", "颜色值", "相似度"]
        if self.proxy_mode_rb.isChecked():
            # 代理染色模式
            labels = self.dye_form_widget.findChildren(QLabel)
            for lb in labels:
                headers.append(lb.text()[:-1])
        self.table.setColumnCount(len(headers))
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                if not self.table.item(row, col):
                    self.table.setItem(row, col, QTableWidgetItem(""))
        self.table.setHorizontalHeaderLabels(headers)
        # 强制刷新表头和列宽，解决切换模式后表头未拉伸问题
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def check_proxy_data_on_mode_switch(self):
        """切换到查找模式时检查表格是否含代理数据，必要时弹出确认对话框。返回True允许切换，False则不切换。"""
        if not (hasattr(self, 'confirm_delete_proxy_data_cb') and self.confirm_delete_proxy_data_cb.isChecked()):
            return True
        # 仅在代理染色->查找模式时检查
        if not self.proxy_mode_rb.isChecked() and self.search_mode_rb.isChecked() and self.table.columnCount() > 3:
            for row in range(self.table.rowCount()):
                row_data = self.get_table_row_data(row)
                if row_data is not None:
                    _, _, _, match_str, type_str, scheme_str,part_str, guarantee_priority = row_data
                    if match_str or type_str or scheme_str or part_str or guarantee_priority:
                        reply = QMessageBox.question(
                            self, "确认切换模式",
                            "表格中存在代理染色数据（搭配方案/装扮类型/染色部位/染色方案），切换后这些数据将丢失。\n是否继续切换到查找模式？",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        return reply == QMessageBox.Yes
            # 没有代理数据
        return True

    def create_search_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        # 工作模式分区
        self.workmode_box = QGroupBox("工作模式")
        workmode_layout = QVBoxLayout(self.workmode_box)
        # 第一行：单选按钮
        workmode_row1 = QHBoxLayout()
        self.search_mode_rb = QRadioButton("颜色查找")
        self.proxy_mode_rb = QRadioButton("代理染色")
        workmode_row1.addWidget(self.search_mode_rb)
        workmode_row1.addWidget(self.proxy_mode_rb)
        workmode_row1.addStretch(1)
        workmode_layout.addLayout(workmode_row1)
        # 第二行：使用染色剂数+当前保底数（初始隐藏）
        workmode_row2 = QHBoxLayout()
        self.dyes_count_spin = QSpinBox(); self.dyes_count_spin.setRange(0, 999)
        self.current_guarantee_spin = QSpinBox(); self.current_guarantee_spin.setRange(0, 10)
        workmode_row2.addWidget(QLabel("使用染色剂数:"))
        workmode_row2.addWidget(self.dyes_count_spin,1)
        workmode_row2.addWidget(QLabel("当前保底数:"))
        workmode_row2.addWidget(self.current_guarantee_spin,1)
        workmode_row2.setContentsMargins(0, 0, 0, 0)
        self.workmode_row2_widget = QWidget()
        self.workmode_row2_widget.setLayout(workmode_row2)
        self.workmode_row2_widget.setVisible(False)
        workmode_layout.addWidget(self.workmode_row2_widget)
        # --- 输入区 ---
        # 左侧：输入区+匹配模式+匹配参数
        self.input_box = QGroupBox("插入检索条目")
        # ---插入要检索的颜色分区布局重构---
        # 主分区：左右下三分区
        main_vbox = QVBoxLayout(self.input_box)
        main_hbox = QHBoxLayout()
        # 左侧：输入区（16进制、RGB、相似度）
        left_form = QFormLayout()
        # 16进制
        hex_label = QLabel("16进制:")
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("如39C5BB")
        self.hex_input.textChanged.connect(self.on_hex_changed)
        self.hex_input.installEventFilter(self) # 安装事件过滤器以处理快捷键
        left_form.addRow(hex_label, self.hex_input)
        # 新增：点击16进制标签输入随机颜色
        hex_label.mousePressEvent = lambda event: self.on_hex_label_clicked(event)
        # RGB
        rgb_hbox = QHBoxLayout()
        self.r_input = LoopSpinBox(); self.r_input.setRange(0,255)
        self.g_input = LoopSpinBox(); self.g_input.setRange(0,255)
        self.b_input = LoopSpinBox(); self.b_input.setRange(0,255)
        for sb in (self.r_input, self.g_input, self.b_input):
            sb.valueChanged.connect(self.on_rgb_changed)
            sb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        rgb_hbox.addWidget(QLabel("R:")); rgb_hbox.addWidget(self.r_input)
        rgb_hbox.addWidget(QLabel("G:")); rgb_hbox.addWidget(self.g_input)
        rgb_hbox.addWidget(QLabel("B:")); rgb_hbox.addWidget(self.b_input)
        left_form.addRow(QLabel("RGB:"), rgb_hbox)
        # 相似度
        sim_label = QLabel("相似度:")
        self.sim_input = QDoubleSpinBox()
        self.sim_input.setRange(0, 1)
        self.sim_input.setDecimals(2)
        preview_label = QLabel("预览备注:")
        self.preview_input = QLineEdit()
        row = QHBoxLayout();
        row.addWidget(self.sim_input);
        row.addWidget(preview_label); row.addWidget(self.preview_input);
        left_form.addRow(sim_label, row)
        main_hbox.addLayout(left_form)
        # 右侧：颜色预览块
        self.hex_preview = QLabel()
        self.hex_preview.setStyleSheet("background:white;border:1px solid #ccc;")
        main_hbox.addWidget(self.hex_preview)
        main_vbox.addLayout(main_hbox)
        # 装扮选择区（下拉框实现）
        dye_form = QFormLayout()
        dye_form.setContentsMargins(0, 0, 0, 0)
        #搭配方案选择
        self.match_scheme_spin = QSpinBox();
        self.match_scheme_spin.setRange(1, 3)
        dye_form.addRow("搭配方案:", self.match_scheme_spin)
        # 装扮类型下拉框
        self.type_combo = QComboBox()
        self.type_combo.addItems(["帽子", "发型", "服装", "挂件"])
        dye_form.addRow("装扮类型:", self.type_combo)
        # 染色方案选择
        scheme_layout = QHBoxLayout()
        self.scheme_spin = QSpinBox()
        self.scheme_spin.setRange(1, 5)
        scheme_layout.addWidget(self.scheme_spin)
        dye_form.addRow("染色方案:", scheme_layout)
        # 染色部位下拉框
        self.part_combo = QComboBox()
        self.part_combo.addItems([chr(ord('A')+i) for i in range(7)])
        dye_form.addRow("染色部位:", self.part_combo)
        # 保底优先染色多选框（仅代理染色模式下显示）
        self.guarantee_priority_combo = QComboBox()
        self.guarantee_priority_combo.addItems(["否", "是"])
        self.guarantee_priority_combo.setCurrentIndex(0)
        self.guarantee_priority_combo.setToolTip("触发保底前优先查找该项。存在多个保底优先染色项时，优先级按表格顺序。")
        dye_form.addRow("保底优先:", self.guarantee_priority_combo)
        # 将dye_form包装到一个QWidget中以便控制显示/隐藏
        self.dye_form_widget = QWidget()
        self.dye_form_widget.setLayout(dye_form)
        self.dye_form_widget.hide()  # 默认隐藏
        main_vbox.addWidget(self.dye_form_widget)

        # 连接代理染色单选按钮的信号
        def on_proxy_mode_changed(checked):
            # 只在从代理染色切到查找模式时拦截
            if not checked:
                if not self.check_proxy_data_on_mode_switch():
                    # 拦截切换，强制回到代理染色
                    self.proxy_mode_rb.blockSignals(True)
                    self.proxy_mode_rb.setChecked(True)
                    self.proxy_mode_rb.blockSignals(False)
                    return
            self.dye_form_widget.setVisible(checked)
            self.workmode_row2_widget.setVisible(checked)
            if checked: 
                self.apply_font_size()  # 更新字体大小以适应新布局
            self.update_table_columns()
        self.proxy_mode_rb.toggled.connect(on_proxy_mode_changed)


        # 下方：操作按钮
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("添加")
        self.btn_add.clicked.connect(self.add_color)
        self.btn_modify = QPushButton("修改")
        self.btn_modify.setEnabled(False)
        self.btn_modify.clicked.connect(self.modify_color)
        self.btn_del = QPushButton("删除"); self.btn_del.clicked.connect(self.remove_color)
        self.btn_clear = QPushButton("清空"); self.btn_clear.clicked.connect(self.clear_colors)
        for btn in (self.btn_add, self.btn_modify, self.btn_del, self.btn_clear):
            btn.setMinimumWidth(1)
            btn_row.addWidget(btn)
        main_vbox.addLayout(btn_row)
        # 回车快捷键绑定（根据“修改”按钮是否可用动态触发）
        def handle_return_pressed():
            if self.btn_modify.isEnabled():
                self.btn_modify.click()
            else:
                self.btn_add.click()
            self.table.setFocus()
        self.hex_input.returnPressed.connect(handle_return_pressed)
        self.preview_input.returnPressed.connect(handle_return_pressed)
        for sb in (self.r_input, self.g_input, self.b_input, self.sim_input, self.scheme_spin,self.match_scheme_spin):
            sb.lineEdit().returnPressed.connect(handle_return_pressed)
        # 绑定回车事件（事件过滤器方式）
        for combo in (self.type_combo, self.part_combo, self.guarantee_priority_combo):
            combo.installEventFilter(self)
        # 匹配模式（纵向排列）
        self.mode_box = QGroupBox("匹配模式")
        mode_layout = QVBoxLayout(self.mode_box)
        self.fast_match_cb = QCheckBox("快速模糊匹配")
        self.mode_group = QButtonGroup(self)
        self.drag_match_rb = QRadioButton("鼠标拖拽匹配");
        self.scan_match_rb = QRadioButton("逐行遍历匹配")
        self.mode_group.addButton(self.drag_match_rb)
        self.mode_group.addButton(self.scan_match_rb)
        mode_layout.addWidget(self.fast_match_cb)
        mode_layout.addWidget(self.drag_match_rb)
        mode_layout.addWidget(self.scan_match_rb)
        # 匹配参数区（使用网格布局）
        self.param_box = QGroupBox("匹配参数")
        param_layout = QGridLayout(self.param_box)
        # 创建输入框
        self.pool_sim_input = QDoubleSpinBox()
        self.pool_sim_input.setRange(0, 1)
        self.pool_sim_input.setDecimals(2)
        self.radius_input = QLineEdit()
        self.step_input = QLineEdit()
        self.slider_delay_input = QLineEdit()
        # 使用网格布局添加控件
        param_layout.addWidget(QLabel("混色池相似度:"), 0, 0)
        param_layout.addWidget(self.pool_sim_input, 0, 1)
        param_layout.addWidget(QLabel("跳格数:"), 0, 2)
        param_layout.addWidget(self.step_input, 0, 3)

        param_layout.addWidget(QLabel("模糊查找半径:"), 1, 0)
        param_layout.addWidget(self.radius_input, 1, 1)
        param_layout.addWidget(QLabel("拖拽延迟:"), 1, 2)
        param_layout.addWidget(self.slider_delay_input, 1, 3)
        # --- 参数区控件联动 ---
        def update_param_inputs():
            # 快速模糊匹配勾选时启用混色池相似度和模糊查找半径
            fuzzy = self.fast_match_cb.isChecked()
            self.pool_sim_input.setEnabled(fuzzy)
            self.radius_input.setEnabled(fuzzy)
            # 鼠标拖拽匹配选中时启用跳格数和拖拽延迟
            drag = self.drag_match_rb.isChecked()
            self.step_input.setEnabled(drag)
            self.slider_delay_input.setEnabled(drag)
        self.fast_match_cb.stateChanged.connect(update_param_inputs)
        self.drag_match_rb.toggled.connect(update_param_inputs)
        # 初始化一次
        update_param_inputs()
        # --- 滚动区 ---
        self.left_widget = QWidget()
        # 让self.left_widget的最小宽度等于self.scroll_widget内容宽度
        self.scroll_widget = SyncWidthWidget(self.left_widget)
        self.scroll_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        # 设置滚动区垂直布局
        scroll_vbox = QVBoxLayout(self.scroll_widget)
        scroll_vbox.setSpacing(8)
        scroll_vbox.setContentsMargins(8, 8, 8, 8)
        scroll_vbox.addWidget(self.workmode_box)
        scroll_vbox.addWidget(self.input_box)
        scroll_vbox.addWidget(self.mode_box)
        scroll_vbox.addWidget(self.param_box)
        # 添加弹性空间吸收剩余高度
        scroll_vbox.addStretch(1)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁止横向滚动条
        # 左侧主布局
        left_vbox = QVBoxLayout()
        left_vbox.setSpacing(16)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.addWidget(self.scroll_area)
        # 开始匹配按钮
        self.btn_match = QPushButton("开始匹配");
        self.btn_match.clicked.connect(self.start_matching)
        left_vbox.addWidget(self.btn_match)
        # 用QWidget包裹左侧vbox
        
        self.left_widget.setLayout(left_vbox)
        # self.left_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        
        layout.addWidget(self.left_widget, 0)
        # 右侧：颜色表格
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["预览", "颜色值", "相似度"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self.on_table_item_double_clicked)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 右侧可拉伸
        self.table.installEventFilter(self) 

        # --- 新增：导入导出表格按钮 ---
        self.btn_export = QPushButton("导出表格")
        self.btn_import = QPushButton("导入表格")
        self.btn_export.clicked.connect(self.export_table)
        self.btn_import.clicked.connect(self.import_table)
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(self.btn_export)
        btn_hbox.addWidget(self.btn_import)
        
        right_vbox = QVBoxLayout()
        right_vbox.setSpacing(16)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.addWidget(self.table)
        right_vbox.addLayout(btn_hbox)
        self.right_widget = QWidget()
        self.right_widget.setLayout(right_vbox)
        self.right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 右侧可拉伸
        self.editing_row = None
        layout.addWidget(self.right_widget, 1)
        self.tabs.addTab(tab, "主界面")

    def create_settings_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        sub_tabs = QTabWidget()
        # --- 常规设置 ---
        general_widget = QWidget()
        general_layout = QFormLayout(general_widget)
        general_layout.setVerticalSpacing(16)
        general_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        # 字体大小放在第一行
        self.font_size_input = QSpinBox(); self.font_size_input.setRange(8, 32)
        self.font_size_input.valueChanged.connect(self.apply_font_size)
        general_layout.addRow("字体大小:", self.font_size_input)
        # 相似度步进值设置
        self.sim_step_input = QDoubleSpinBox();
        self.sim_step_input.setRange(0.01, 0.2); 
        self.sim_step_input.setDecimals(2); 
        self.sim_step_input.setSingleStep(0.01)
        general_layout.addRow("相似度步进值:", self.sim_step_input)
        # 步进值联动
        self.sim_step_input.valueChanged.connect(lambda v: self.sim_input.setSingleStep(v))
        self.sim_step_input.valueChanged.connect(lambda v: self.pool_sim_input.setSingleStep(v))
        # 各项单独一行
        self.topmost_cb = QCheckBox("启动脚本时游戏窗口置顶"); 
        general_layout.addRow(self.topmost_cb)
        self.maximize_cb = QCheckBox("启动脚本时游戏窗口最大化"); 
        general_layout.addRow(self.maximize_cb)
        self.reset_layout_cb = QCheckBox("每次打开程序时恢复上次窗口位置与大小")
        general_layout.addRow(self.reset_layout_cb)
        self.auto_save_config_cb = QCheckBox("关闭程序时自动保存为默认配置")
        general_layout.addRow(self.auto_save_config_cb)
        # 新增：匹配前检查表格颜色是否可制作
        self.check_color_card_cb = QCheckBox("开始匹配前检查表格中颜色是否可以制作")
        general_layout.addRow(self.check_color_card_cb)
        # 新增：点击16进制标签输入随机颜色功能开关
        self.random_color_cb = QCheckBox("点击16进制标签输入随机颜色")
        self.random_color_k_keyedit = QKeySequenceEdit()
        random_row = QHBoxLayout()
        random_row.addWidget(self.random_color_cb,1)
        random_row.addStretch(1)
        random_row.addWidget(QLabel("快捷键:"))
        random_row.addWidget(self.random_color_k_keyedit,3)
        random_row.addStretch(1)
        general_layout.addRow(random_row)
        def on_random_color_cb_changed(state):
            enabled = state == 2
            self.random_color_k_keyedit.setEnabled(enabled)
        self.random_color_cb.stateChanged.connect(on_random_color_cb_changed)
        # 快捷键绑定
        self.random_color_shortcut = None
        def update_random_color_shortcut():
            seq = self.random_color_k_keyedit.keySequence()
            if self.random_color_shortcut:
                self.random_color_shortcut.setEnabled(False)
                self.random_color_shortcut.deleteLater()
                self.random_color_shortcut = None
            if not seq.isEmpty():
                if self.check_shortcut_conflict():
                    self.random_color_k_keyedit.setKeySequence(QKeySequence())  # 清空冲突的快捷键
                    return
                self.random_color_shortcut = QShortcut(seq, self)
                self.random_color_shortcut.setContext(Qt.ApplicationShortcut)
                self.random_color_shortcut.activated.connect(lambda: self.on_hex_label_clicked())
        self.random_color_k_keyedit.keySequenceChanged.connect(lambda _: update_random_color_shortcut())

        # 合并后的“启动/停止脚本”快捷键
        self.use_script_shortcut_cb = QCheckBox("使用快捷键启动/停止脚本")
        self.script_toggle_keyedit = QKeySequenceEdit()
        self.script_toggle_keyedit.setEnabled(False)
        script_shortcut_row = QHBoxLayout()
        script_shortcut_row.addWidget(self.use_script_shortcut_cb)
        script_shortcut_row.addStretch(1)
        script_shortcut_row.addWidget(QLabel("快捷键:"))
        script_shortcut_row.addWidget(self.script_toggle_keyedit,3)
        script_shortcut_row.addStretch(1)
        general_layout.addRow(script_shortcut_row)
        # 复选框联动快捷键输入框
        def on_use_script_shortcut_cb_changed(state):
            enabled = state == 2
            self.script_toggle_keyedit.setEnabled(enabled)
            if not enabled:
                self.unregister_script_toggle_hotkey()
        self.use_script_shortcut_cb.stateChanged.connect(on_use_script_shortcut_cb_changed)

        # keyboard.hook 方式全局监听
        self._script_toggle_hotkey = None
        self._script_toggle_hotkey_seq = None
        self._script_toggle_hook_handle = None
        def update_script_toggle_hotkey():
            try:
                import keyboard
            except ImportError:
                QMessageBox.warning(self, "依赖缺失", "未安装 keyboard 库，无法使用全局快捷键。请在命令行执行 pip install keyboard 并以管理员权限运行本程序。")
                return
            except Exception as e:
                QMessageBox.warning(self, "依赖异常", f"keyboard 库加载异常：{e}")
                return
            # 注销旧监听
            self.unregister_script_toggle_hotkey()
            seq = self.script_toggle_keyedit.keySequence().toString(QKeySequence.NativeText)
            if self.use_script_shortcut_cb.isChecked() and seq:
                # 检查快捷键冲突
                if self.check_shortcut_conflict():
                    self.script_toggle_keyedit.setKeySequence(QKeySequence())
                    return
                # 记录当前快捷键
                self._script_toggle_hotkey_seq = seq
                # 解析为 keyboard 识别的组合
                key_str = seq.replace("+", "+").replace("空格", "space")
                # 注册 hook
                def on_key_event(e):
                    if e.event_type == 'down':
                        # 检查当前按键组合是否等于设置的快捷键
                        if keyboard.is_pressed(key_str):
                            self.start_matching()
                self._script_toggle_hook_handle = keyboard.hook(on_key_event)
        def unregister_script_toggle_hotkey():
            try:
                import keyboard
            except Exception:
                return
            if self._script_toggle_hook_handle:
                try:
                    keyboard.unhook(self._script_toggle_hook_handle)
                except Exception:
                    pass
                self._script_toggle_hook_handle = None
        self.update_script_toggle_hotkey = update_script_toggle_hotkey
        self.unregister_script_toggle_hotkey = unregister_script_toggle_hotkey
        self.script_toggle_keyedit.keySequenceChanged.connect(lambda _: self.update_script_toggle_hotkey())
        self.use_script_shortcut_cb.stateChanged.connect(lambda _: self.update_script_toggle_hotkey())

        # 检查快捷键冲突
        def check_shortcut_conflict():
            seqs = []
            names = []
            if hasattr(self, 'random_color_cb') and self.random_color_cb.isChecked():
                seqs.append(self.random_color_k_keyedit.keySequence())
                names.append('随机颜色')
            if hasattr(self, 'use_script_shortcut_cb') and self.use_script_shortcut_cb.isChecked():
                seqs.append(self.script_toggle_keyedit.keySequence())
                names.append('启动/停止脚本')
            # 检查非空且有重复
            seq_strs = [seq.toString() for seq in seqs if not seq.isEmpty()]
            for i in range(len(seq_strs)):
                for j in range(i+1, len(seq_strs)):
                    if seq_strs[i] == seq_strs[j]:
                        QMessageBox.warning(self, "快捷键冲突", f"快捷键“{names[i]}”与“{names[j]}”不能相同！")
                        return True
            return False
        self.check_shortcut_conflict = check_shortcut_conflict

      

        # 新增：关闭弹窗开关
        self.close_popup_cb = QCheckBox("导入表格/导出表格/保存配置成功不再弹窗提示")
        general_layout.addRow(self.close_popup_cb)
        #保存日志
        self.save_log_cb = QCheckBox("保存日志")
        general_layout.addRow(self.save_log_cb)
        def on_save_log_cb_changed(state):
            logger_manager.set_file_logging(state == 2)
        # 绑定信号
        self.save_log_cb.stateChanged.connect(on_save_log_cb_changed)
        # --- 防呆设置分区 ---
        self.foolproof_group = QGroupBox("防呆设置")
        foolproof_layout = QVBoxLayout(self.foolproof_group)
        foolproof_layout.setSpacing(16)
        # 新增防止插入重复查找项
        self.prevent_duplicate_cb = QCheckBox("添加/修改表格数据时防止插入重复查找项")
        foolproof_layout.addWidget(self.prevent_duplicate_cb)
        # 新增删除/清空表格数据时二次确认
        self.confirm_delete_cb = QCheckBox("删除/清空表格数据时二次确认")
        foolproof_layout.addWidget(self.confirm_delete_cb)
        # 新增同装扮类型不同染色方案时警告
        self.confirm_diff_scheme_cb = QCheckBox("添加同装扮类型不同染色方案时二次确认")
        foolproof_layout.addWidget(self.confirm_diff_scheme_cb)
        # 新增切换模式警告复选框
        self.confirm_delete_proxy_data_cb = QCheckBox("切换到颜色查找模式时二次确认（防止代理染色数据丢失）")
        foolproof_layout.addWidget(self.confirm_delete_proxy_data_cb)
        # 新增切换模式警告复选框
        self.confirm_config_cb = QCheckBox("保存/恢复默认配置时二次确认")
        foolproof_layout.addWidget(self.confirm_config_cb)
        general_layout.addRow(self.foolproof_group) 
        # 新增批量勾选功能
        self.install_batch_checkbox_toggle(general_widget)
        # 绑定联动逻辑：只在勾选reset_layout_cb时自动勾选auto_save_config_cb
        def on_reset_layout_cb_changed(state):
            if state == 2:
                self.auto_save_config_cb.setChecked(True)
        self.reset_layout_cb.stateChanged.connect(on_reset_layout_cb_changed)
        # 包裹滚动区
        general_scroll = QScrollArea()
        general_scroll.setWidgetResizable(True)
        general_scroll.setWidget(general_widget)
        sub_tabs.addTab(general_scroll, "常规设置")
        # --- 参数设置 ---
        param_widget = QWidget()
        param_main_vbox = QVBoxLayout(param_widget)

        self.group_game = QGroupBox("游戏窗口")
        layout_game = QFormLayout(self.group_game)
        # 帽子装扮
        self.game_x_input = QLineEdit();
        self.game_y_input = QLineEdit(); 
        self.game_height_input = QLineEdit();
        self.game_width_input = QLineEdit();
        row = QHBoxLayout();
        row.addWidget(QLabel("横坐标:")); row.addWidget(self.game_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.game_y_input);
        layout_game.addRow("窗口左上角", row)
        row = QHBoxLayout();
        row.addWidget(QLabel("高度:")); row.addWidget(self.game_height_input); row.addSpacing(10); row.addWidget(QLabel("宽度:")); row.addWidget(self.game_width_input)
        layout_game.addRow("窗口大小", row)
        param_main_vbox.addWidget(self.group_game)
        # 1. 选择服装界面分区
        self.group_cloth = QGroupBox("选择服装界面")
        layout_cloth = QFormLayout(self.group_cloth)
        # 帽子装扮
        self.hat_x_input = QLineEdit();
        self.hat_y_input = QLineEdit(); 
        self.hat_height_input = QLineEdit();
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.hat_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.hat_y_input); row.addSpacing(10); row.addWidget(QLabel("高度:")); row.addWidget(self.hat_height_input)
        layout_cloth.addRow("帽子装扮", row)
        # 染色按钮
        self.dye_sth_x_input = QLineEdit(); 
        self.dye_sth_y_input = QLineEdit();
        self.dye_sth_width_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.dye_sth_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.dye_sth_y_input); row.addSpacing(10); row.addWidget(QLabel("宽度:")); row.addWidget(self.dye_sth_width_input)
        layout_cloth.addRow("染色按钮", row)
        # 搭配方案
        self.match_scheme_x_input = QLineEdit();
        self.match_scheme_y_input = QLineEdit();
        self.match_scheme_width_input = QLineEdit();
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.match_scheme_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.match_scheme_y_input); row.addSpacing(10); row.addWidget(QLabel("宽度:")); row.addWidget(self.match_scheme_width_input)
        layout_cloth.addRow("搭配方案", row)
        param_main_vbox.addWidget(self.group_cloth)
        # 2. 选择染色剂界面分区
        self.group_dye = QGroupBox("选择染色剂界面")
        layout_dye = QFormLayout(self.group_dye)
        # 换染色剂
        self.dye_x_input = QLineEdit(); 
        self.dye_y_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.dye_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.dye_y_input);
        layout_dye.addRow("换染色剂", row)
        # 确认键
        self.ok_x_input = QLineEdit(); 
        self.ok_y_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.ok_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.ok_y_input)
        layout_dye.addRow("确认键", row)
        param_main_vbox.addWidget(self.group_dye)
        # 3. 选色界面分区
        self.group_color = QGroupBox("选色界面")
        layout_color = QFormLayout(self.group_color)
        # 滑块定位
        self.slider_x_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.slider_x_input)
        layout_color.addRow("滑块定位", row)
        # 混色池左上角
        self.pool_left_input = QLineEdit(); 
        self.pool_top_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.pool_left_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.pool_top_input)
        layout_color.addRow("混色池左上角", row)
        # 混色池右下角
        self.pool_right_input = QLineEdit(); 
        self.pool_bottom_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.pool_right_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.pool_bottom_input)
        layout_color.addRow("混色池右下角", row)
        # 第一块预览颜色
        self.preview_x_input = QLineEdit(); 
        self.preview_y_input = QLineEdit(); 
        self.preview_width_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.preview_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.preview_y_input); row.addSpacing(10); row.addWidget(QLabel("宽度:")); row.addWidget(self.preview_width_input)
        layout_color.addRow("第一块预览颜色", row)
        # 向下微调滑块键
        self.down_x_input = QLineEdit(); 
        self.down_y_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.down_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.down_y_input)
        layout_color.addRow("向下微调滑块键", row)
        # 开始染色键
        self.dye_start_x_input = QLineEdit(); 
        self.dye_start_y_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.dye_start_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.dye_start_y_input)
        layout_color.addRow("开始染色键", row)
        # 染色A区
        self.partA_X_input = QLineEdit(); 
        self.partA_Y_input = QLineEdit(); 
        self.part_width_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.partA_X_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.partA_Y_input); row.addSpacing(10); row.addWidget(QLabel("宽度:")); row.addWidget(self.part_width_input)
        layout_color.addRow("染色A区", row)
        # 染色方案
        self.dye_scheme_x_input = QLineEdit(); 
        self.dye_scheme_y_input = QLineEdit(); 
        self.dye_scheme_width_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.dye_scheme_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.dye_scheme_y_input); row.addSpacing(10); row.addWidget(QLabel("宽度:")); row.addWidget(self.dye_scheme_width_input)
        layout_color.addRow("染色方案", row)
        param_main_vbox.addWidget(self.group_color)
        # 4. 确认染色界面分区
        self.group_confirm = QGroupBox("确认染色界面")
        layout_confirm = QFormLayout(self.group_confirm)
        # 染色颜色
        self.dye_color_x_input = QLineEdit(); 
        self.dye_color_y_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.dye_color_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.dye_color_y_input)
        layout_confirm.addRow("染色颜色", row)
        # 保存颜色
        self.save_color_x_input = QLineEdit(); 
        self.save_color_y_input = QLineEdit(); 
        self.save_color_width_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("横坐标:")); row.addWidget(self.save_color_x_input); row.addSpacing(10); row.addWidget(QLabel("纵坐标:")); row.addWidget(self.save_color_y_input); row.addSpacing(10); row.addWidget(QLabel("宽度:")); row.addWidget(self.save_color_width_input)
        layout_confirm.addRow("保存颜色", row)
        param_main_vbox.addWidget(self.group_confirm)
        # 5. 其它参数分区
        self.group_other = QGroupBox("其它参数")
        layout_other = QFormLayout(self.group_other)
        self.delay_input = QLineEdit(); 
        self.skip_similar_input = QLineEdit(); 
        self.slider_between_bottom_input = QLineEdit(); 
        row = QHBoxLayout(); row.addWidget(QLabel("平均延迟:")); row.addWidget(self.delay_input); row.addSpacing(10); 
        row.addWidget(QLabel("跳过相似色数:")); row.addWidget(self.skip_similar_input);row.addSpacing(10);
        self.btn_slider_between_bottom = QPushButton("滑块距底间隔"); self.btn_slider_between_bottom.clicked.connect(self.set_slider_between_bottom)
        row.addWidget(self.btn_slider_between_bottom); row.addWidget(self.slider_between_bottom_input)
        layout_other.addRow(row)
        param_main_vbox.addWidget(self.group_other)
        #压紧
        param_main_vbox.addStretch(1)
        # 包裹滚动区
        param_scroll = QScrollArea()
        param_scroll.setWidgetResizable(True)
        param_scroll.setWidget(param_widget)
        # 滚动区下方的“获取参数”“显示坐标位置”按钮
        btn_get_param = QPushButton("获取参数"); 
        btn_get_param.clicked.connect(self.get_param_action)
        self.btn_show_pos = QPushButton("显示坐标位置"); 
        self.btn_show_pos.clicked.connect(self.toggle_param_positions)
        btn_top_hbox = QHBoxLayout(); btn_top_hbox.addWidget(btn_get_param); btn_top_hbox.addWidget(self.btn_show_pos)
        # 设置按钮不被压缩，防止文字遮挡
        btn_get_param.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_show_pos.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        # 参数设置tab内容区：滚动区+按钮
        param_tab_vbox = QVBoxLayout()
        param_tab_vbox.addWidget(param_scroll)
        param_tab_vbox.addLayout(btn_top_hbox)
        param_tab_widget = QWidget()
        param_tab_widget.setLayout(param_tab_vbox)
        sub_tabs.addTab(param_tab_widget, "参数设置")
        # --- 二级标签页下方的保存等按钮 ---
        btn_save_default = QPushButton("保存为默认配置"); 
        btn_save_default.clicked.connect(self.save_as_default_config)
        btn_reset = QPushButton("恢复默认配置"); btn_reset.clicked.connect(self.reset_default_config)
        btn_hbox = QHBoxLayout(); btn_hbox.addWidget(btn_save_default); btn_hbox.addWidget(btn_reset)
        # --- 主布局 ---
        main_layout.addWidget(sub_tabs)
        main_layout.addLayout(btn_hbox)
        tab.setLayout(main_layout)
        self.tabs.addTab(tab, "设置")

    def toggle_param_positions(self):
        # 分区步进显示/隐藏坐标遮罩
        if not hasattr(self, '_overlay_step'):
            self._overlay_step = 0
        if hasattr(self, '_overlay') and self._overlay is not None and self._overlay.isVisible():
            # 当前有遮罩，切换到下一个分区或关闭
            self._overlay.close()
            self._overlay = None
            self._overlay_step += 1
            if not hasattr(self, '_overlay_total'):
                self._overlay_total = 4
            if self._overlay_step >= self._overlay_total:
                self._overlay_step = 0
                self.btn_show_pos.setText("显示坐标位置")
                return
        else:
            self._overlay_step = 0
        # 收集所有参数
        param_keys = self.get_param_keys()
        params = {k: self.get_config_value(k) for k in param_keys}
        params.update({"font_size": str(self.font_size_input.value())})
        invalids = [(k, v) for k, v in params.items() if not (isinstance(v, str) and v.strip().lstrip('-').isdigit())]
        if invalids:
            msg = "部分坐标参数不是有效数字，无法显示位置！\n" + "\n".join([f"{k}: '{v}'" for k, v in invalids])
            QMessageBox.warning(self, "参数错误", msg)
            # 高亮第一个有问题的输入框
            key = invalids[0][0]
            widget = getattr(self, f"{key}_input", None)
            if widget is not None:
                widget.setStyleSheet("background: #ffcccc;")
                widget.setFocus()
            return
        # 恢复所有输入框背景
        for k in param_keys:
            widget = getattr(self, f"{k}_input", None)
            if widget is not None:
                widget.setStyleSheet("")
        # 显示当前分区遮罩
        self._overlay, self._overlay_total = ui_logic.show_param_overlay(self, params, self.btn_show_pos, self._overlay_step)
        # 按钮文本
        if self._overlay_step < self._overlay_total - 1:
            self.btn_show_pos.setText(f"显示下一区域({self._overlay_step+1}/{self._overlay_total})")
        else:
            self.btn_show_pos.setText(f"隐藏坐标({self._overlay_step+1}/{self._overlay_total})")

    def reset_default_config(self):
        if hasattr(self, 'confirm_config_cb') and self.confirm_config_cb.isChecked():
            reply = QMessageBox.question(self, "确认操作", "确定要恢复为默认配置吗？", QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        self.reset_config()

    def reset_config(self):
        # 恢复为config.ini中的默认值，所有设置参数都恢复
        config_path = os.path.join(os.path.dirname(__file__), '../config/config.ini')
        config_path = os.path.normpath(config_path)
        data = ui_logic.load_config_from_file(config_path, self.get_config_fields())
        
        for k in self.get_config_fields():
            widget = getattr(self, f"{k}_input", None)
            if isinstance(widget, QLineEdit):
                widget.setText(data.get(k, ''))
            elif isinstance(widget, QSpinBox):
                try:
                    widget.setValue(int(data.get(k, 0)))
                except Exception:
                    pass
            elif isinstance(widget, QDoubleSpinBox):
                try:
                    widget.setValue(float(data.get(k, 0.01)))
                except Exception:
                    pass
            else:
                cb = getattr(self, f"{k}_cb", None)
                if isinstance(cb, QCheckBox):
                    cb.setChecked(data.get(k, 'false') == 'true')
                rb = getattr(self, f"{k}_rb", None)
                if isinstance(rb, QRadioButton):
                    rb.setChecked(data.get(k, 'false') == 'true')
                ke = getattr(self, f"{k}_keyedit", None)
                if isinstance(ke, QKeySequenceEdit):
                    ke.setKeySequence(QKeySequence(data.get(k, '')))

        # 恢复窗口位置和大小
        if self.reset_layout_cb.isChecked():
            try:
                x = int(data.get('window_x', -1))
                y = int(data.get('window_y', -1))
                w = int(data.get('window_width', -1))
                h = int(data.get('window_height', -1))
                if w > 0 and h > 0:
                    self.setGeometry(x, y, w, h)
            except Exception:
                pass
        

    def save_config(self):
        # 配置文件路径调整到 config 目录
        config_path = os.path.join(os.path.dirname(__file__), '../config/config.ini')
        config_path = os.path.normpath(config_path)
        data = {k: self.get_config_value(k) for k in self.get_config_fields()}
        geo = self.geometry()
        data['window_x'] = str(geo.x())
        data['window_y'] = str(geo.y())
        data['window_width'] = str(geo.width())
        data['window_height'] = str(geo.height())
        # 不再保存分割线位置
        ui_logic.save_config_to_file(config_path, data, self.get_config_fields())

    def save_as_default_config(self):
        # 保存为默认配置 (config.ini)
        if hasattr(self, 'confirm_config_cb') and self.confirm_config_cb.isChecked():
            reply = QMessageBox.question(self, "确认操作", "确定要将当前参数保存为默认配置吗？", QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        self.save_config()
        if hasattr(self, 'close_popup_cb') and not self.close_popup_cb.isChecked():
            QMessageBox.information(self, "提示", "已保存为默认配置 (config.ini)")

    def closeEvent(self, event):
        if hasattr(self, 'auto_save_config_cb') and self.auto_save_config_cb.isChecked():
            self.save_config()
        self.unregister_script_toggle_hotkey()
        event.accept()
    def set_slider_between_bottom(self):
        pass
    
    def on_table_selection_changed(self):
        selected = self.table.selectedItems()
        # 判断是否有且仅有一行被选中
        rows = set(idx.row() for idx in selected) if selected else set()
        if len(rows) == 1:
            self.btn_modify.setEnabled(True)
            self.editing_row = list(rows)[0]
            row_data = self.get_table_row_data(self.editing_row)
            if row_data is not None:
                # 颜色值、相似度、装扮类型、染色部位、染色方案、保底优先染色
                preview_str, hex_str, sim_str,match_str, type_str, scheme_str, part_str, guarantee_priority = row_data
                self.hex_input.setText(hex_str)
                self.preview_input.setText(preview_str)
                try:
                    self.sim_input.setValue(float(sim_str))
                except Exception:
                    pass
                # 代理染色模式下自动填充下拉框和方案
                if self.proxy_mode_rb.isChecked() and self.table.columnCount() > 3:
                    if match_str:
                        try:
                            self.match_scheme_spin.setValue(int(match_str))
                        except Exception:
                            pass
                    if type_str:
                        idx = self.type_combo.findText(type_str)
                        if idx >= 0:
                            self.type_combo.setCurrentIndex(idx)
                    if part_str:
                        idx = self.part_combo.findText(part_str)
                        if idx >= 0:
                            self.part_combo.setCurrentIndex(idx)
                    if scheme_str:
                        try:
                            self.scheme_spin.setValue(int(scheme_str))
                        except Exception:
                            pass
                    if guarantee_priority:
                        idx = self.guarantee_priority_combo.findText(guarantee_priority)
                        if idx >= 0:
                            self.guarantee_priority_combo.setCurrentIndex(idx)
        else:
            self.btn_modify.setEnabled(False)
            self.editing_row = None
    def on_table_item_double_clicked(self, item):
        col = item.column()
        if col == 0 and hasattr(self, 'preview_input'):  # 预览列
            self.preview_input.setFocus()
        elif col == 1 and hasattr(self, 'hex_input'):  # 颜色值
            self.hex_input.setFocus()
        elif col == 2 and hasattr(self, 'sim_input'):  # 相似度
            self.sim_input.setFocus()
        elif col == 3 and hasattr(self, 'match_scheme_spin'):  # 搭配方案
            self.match_scheme_spin.setFocus()
        elif col == 4 and hasattr(self, 'type_combo'):  # 装扮类型
            self.type_combo.setFocus()
        elif col == 5 and hasattr(self, 'scheme_spin'):  # 染色方案
            self.scheme_spin.setFocus()
        elif col == 6 and hasattr(self, 'part_combo'):  # 染色部位
            self.part_combo.setFocus()
        elif col == 7 and hasattr(self, 'guarantee_priority_combo'):  # 保底优先染色
            self.guarantee_priority_combo.setFocus()

    def get_config_value(self, key):
        """
        获取配置参数的值，返回字符串。
        """
        widget = getattr(self, f"{key}_input", None)
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QSpinBox):
            return str(widget.value())
        elif isinstance(widget, QDoubleSpinBox):
            return str(widget.value())
        else:
            cb = getattr(self, f"{key}_cb", None)
            if isinstance(cb, QCheckBox):
                return 'true' if cb.isChecked() else 'false'
            rb = getattr(self, f"{key}_rb", None)
            if isinstance(rb, QRadioButton):
                return 'true' if rb.isChecked() else 'false'
            ke = getattr(self, f"{key}_keyedit", None)
            if isinstance(ke, QKeySequenceEdit):
                return ke.keySequence().toString(QKeySequence.NativeText)
        return ''
    def start_matching(self):
        if hasattr(self, 'btn_match') and self.btn_match.isEnabled():
            if self.btn_match.text() == "开始匹配":
                if self.table.rowCount() == 0:
                    QMessageBox.warning(self, "警告", "请先添加要匹配的颜色！")
                    return
                #检查重复
                for row in range(self.table.rowCount()):
                    row_data = self.get_table_row_data(row)
                    if row_data is not None:
                        try:
                            self.is_valid_row(*row_data[1:])
                        except ValueError as e:
                            QMessageBox.warning(self, "警告", f"第{row+1}行数据有误：{str(e)}")
                            return
                        if not self.is_row_unique(row_data[1],*row_data[3:7], exclude_row=row, ignore_front=True):
                            return
                        if hasattr(self, 'confirm_diff_scheme_cb') and self.confirm_diff_scheme_cb.isChecked():
                            if not self.is_scheme_unique(*row_data[3:6],  exclude_row=row, ignore_front=True):
                                return
                        #检查色卡
                        if hasattr(self, 'check_color_card_cb') and self.check_color_card_cb.isChecked():
                            # 色卡文件路径调整到 config 目录
                            color_card_path = os.path.join(os.path.dirname(__file__), '../config/color_card.txt')
                            color_card_path = os.path.normpath(color_card_path)
                            if not os.path.exists(color_card_path):
                                QMessageBox.warning(self, "缺少色卡", "未找到色卡文件 color_card.txt！")
                                return
                            color_card = color_card_util.load_color_card(color_card_path)
                            similar_list = color_card_util.find_similar_color_in_card(row_data[1], color_card, row_data[2])
                            if similar_list:
                                card_hex, card_name, sim = similar_list[0]
                                reply = QMessageBox.question(
                                    self, "检测到可制作色卡色", 
                                    f"检测到第{row+1}行颜色 {row_data[1]} 与可制作染色剂 {card_name}({card_hex}) 相似度为 {sim:.2f}，是否继续匹配？",
                                    QMessageBox.Yes | QMessageBox.No
                                )
                                if reply != QMessageBox.Yes:
                                    return
                # 开始匹配
                print("表格内容无误，开始匹配")
                self.btn_match.setText("停止匹配")
                self.script_start()
            else:
                # 停止匹配
                self.script_stop()
                self.btn_match.setText("开始匹配")
    def get_param_action(self):
        """
        一键获取参数。
        获取游戏句柄->窗口坐标->参数计算->自动填充
        """
        try:
            hwnd = ui_logic.get_game_hwnd()
        except ImportError:
            QMessageBox.warning(self, "依赖缺失", "请先安装 pywin32！")
            return
        if not hwnd:
            QMessageBox.warning(self, "未找到窗口", "未检测到‘开放空间’窗口，请先启动游戏！")
            return
        x, y, width, height = ui_logic.get_window_rect(hwnd)
        # 新增：判断坐标或大小为负数时弹窗并退出
        if x < 0 or y < 0 or width < 0 or height < 0:
            QMessageBox.warning(self, "获取参数失败", "获取参数失败，请勿最小化游戏")
            return
        params = ui_logic.calc_params_by_rect(x, y, width, height, self.get_param_keys())
        for k, v in params.items():
            widget = getattr(self, f"{k}_input", None)
            if widget is not None:
                widget.setText(str(v))
        QMessageBox.information(self, "成功", f"已自动获取窗口客户区坐标和参数并填入。")

    def get_table_row_data(self, row):
        """
        获取表格中指定行的全部数据，返回一个元组
        (预览色备注, 颜色值, 相似度, 搭配方案, 装扮类型, 染色部位, 染色方案, 保底优先）
        若行不存在或数据不全，返回None。
        """
        if row < 0 or row >= self.table.rowCount():
            return None
        col_count = self.table.columnCount()
        # 只查找已显示的列
        data = []
        for col in range(col_count):
            item = self.table.item(row, col)
            data.append(item.text().strip() if item else "")
        # 补齐到8列
        while len(data) < 8:
            data.append("")
        return tuple(data)    
    
    def install_batch_checkbox_toggle(self, parent_group):
        """
        给parent_group下所有QCheckBox安装批量勾选/取消功能：
        按住鼠标左键拖动经过的复选框会自动切换勾选状态。
        """
        if not hasattr(self, '_all_batch_checkboxes'):
            self._all_batch_checkboxes = set()
        checkboxes = parent_group.findChildren(QCheckBox)
        for cb in checkboxes:
            cb.installEventFilter(self)
            self._all_batch_checkboxes.add(cb)
        # 给窗口也安装事件过滤器以捕获全局鼠标移动
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        # 支持所有已注册的批量勾选QCheckBox
        if hasattr(self, '_all_batch_checkboxes'):
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if obj in self._all_batch_checkboxes and obj.isEnabled():
                    self._batch_checking = True
                    self._batch_check_value = not obj.isChecked()
                    obj.setChecked(self._batch_check_value)
                    return True
            elif event.type() == QEvent.MouseMove and getattr(self, '_batch_checking', False):
                self.check_checkbox_under_mouse(event.globalPos())
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                if getattr(self, '_batch_checking', False):
                    self._batch_checking = False
                    self._batch_check_value = None
                    return True
        # 保底优先ComboBox回车快捷键
        if isinstance(obj, QComboBox) and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self.btn_modify.isEnabled():
                    self.btn_modify.click()
                else:
                    self.btn_add.click()
                self.table.setFocus()
                return True
        # 表格键盘事件，需先判断self.table已初始化
        if hasattr(self, 'table') and obj == self.table and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
                self.remove_color()
                return True
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.hex_input.setFocus()
        if hasattr(self, 'hex_input') and hasattr(self, 'random_color_k_keyedit') and obj == self.hex_input and event.type() == QEvent.KeyPress:
            seq = self.random_color_k_keyedit.keySequence()
            if not seq.isEmpty():
                key = QKeySequence(int(event.modifiers()) + event.key())
                if key.matches(seq) == QKeySequence.ExactMatch:
                    self.on_hex_label_clicked()
                    return True
        return super().eventFilter(obj, event)

    def check_checkbox_under_mouse(self, pos):
        if not hasattr(self, '_all_batch_checkboxes') or not getattr(self, '_batch_checking', False):
            return
        for cb in self._all_batch_checkboxes:
            if cb.isEnabled() and self.is_pos_in_checkbox(cb, pos):
                if cb.isChecked() != self._batch_check_value:
                    cb.setChecked(self._batch_check_value)
                break

    def is_pos_in_checkbox(self, cb, pos):
        rect = cb.geometry()
        parent_pos = cb.parent().mapFromGlobal(pos)
        return rect.contains(parent_pos)

    def get_all_table_data(self):
        """
        获取表格所有内容，返回列表，每行为元组。
        只获取当前表格显示的列（与导出/导入一致）。
        """
        data = []
        for row in range(self.table.rowCount()):
            row_data = self.get_table_row_data(row)
            if row_data is not None:
                data.append(row_data)
        return data
    
    def export_table(self):
        """导出表格为txt文件"""
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "提示", "表格为空，无需导出！")
            return
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "导出表格", "", "文本文件 (*.txt);;所有文件 (*)", options=options)
        if not file_name:
            return
        try:
            with open(file_name, 'w', encoding='utf-8') as f:
                # 第一行写工作模式
                mode = '代理染色' if self.proxy_mode_rb.isChecked() else '颜色查找'
                f.write(mode + '\n')
                all_data = self.get_all_table_data()
                for row_data in all_data:
                    line = ','.join([str(x) for x in row_data[:self.table.columnCount()]])
                    f.write(line + '\n')

            if hasattr(self, 'close_popup_cb') and not self.close_popup_cb.isChecked():
                QMessageBox.information(self, "导出成功", f"表格已导出到: {file_name}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出失败: {e}")

    def import_table(self):
        """从txt文件导入表格数据（不导入预览列）"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "导入表格", "", "文本文件 (*.txt);;所有文件 (*)", options=options)
        if not file_name:
            return
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) < 2:
                raise ValueError("文件内容不足，无法导入！")
            mode = lines[0].strip()
            if mode not in ("代理染色", "颜色查找"):
                raise ValueError("第一行必须为“代理染色”或“颜色查找”！")
            # 切换工作模式
            if mode == "代理染色":
                self.proxy_mode_rb.setChecked(True)
            else:
                self.search_mode_rb.setChecked(True)
                if self.proxy_mode_rb.isChecked():
                    raise ValueError("请切换为颜色查找模式！")
            # 清空表格
            self.table.setRowCount(0)
            skipped = 0
            error_list = []
            for i, line in enumerate(lines[1:], 2):
                items = [x.strip().replace("'", "").replace('"', '').replace('(', '').replace(')', '').replace('[', '').replace(']', '') for x in line.strip().split(',')]
                while len(items) < 8:
                     items.append("")
                if len(items) > 8:
                    items = items[:8]
                try:
                    self.is_valid_row(*items[1:])
                except ValueError as e:
                    skipped += 1
                    error_list.append(f"\n源文件第{i}行数据有误：\n{str(e)}")
                    continue
                self.insert_or_update_row(self.table.rowCount(), *items)
            self.sort_table()
            if hasattr(self, 'close_popup_cb') and not self.close_popup_cb.isChecked():
                if skipped == len(lines) - 1:
                    raise ValueError("不是哥们，没有一行数据是对的！")
                msg = f"表格已导入: {file_name}"
                if skipped > 0:
                    msg += f"\n有 {skipped} 行因格式错误被跳过。"
                if error_list:
                    msg += "\n错误详情：" + "\n".join(error_list)
                print(msg)
                QMessageBox.information(self, "导入成功", msg)
        except Exception as e:
            print(f"导入失败: {e}")
            QMessageBox.warning(self, "导入失败", f"导入失败: {e}")
    
    def on_hex_label_clicked(self, event=None):
        if hasattr(self, 'random_color_cb') and self.random_color_cb.isChecked():
            import random
            rand_hex = ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
            self.hex_input.setText(rand_hex)
            self.hex_input.setFocus()

    def is_valid_row(self, hex_str, similarity, match_str = None, type_str=None, scheme_str=None, part_str=None, guarantee_priority=None):
        """检查指定行列是否有数据"""
        errors = []
        if not ui_logic.is_valid_hex_color(hex_str):
            errors.append(f"无效的颜色值: {hex_str}")
        if not ui_logic.is_valid_similarity(similarity):
            errors.append(f"无效的相似度: {similarity}")
        if hasattr(self, 'proxy_mode_rb') and self.proxy_mode_rb.isChecked() and self.table.columnCount() > 3:
            # 代理染色模式下，装扮类型、染色部位、染色方案不能为空
            if type_str is None or part_str is None or scheme_str is None or guarantee_priority is None:
                errors.append("代理染色模式下，装扮类型、染色部位、染色方案和保底优先染色不能为空")
            type_list = [self.type_combo.itemText(i) for i in range(self.type_combo.count())]
            part_list = [self.part_combo.itemText(i) for i in range(self.part_combo.count())]
            guarantee_priority_list = [self.guarantee_priority_combo.itemText(i) for i in range(self.guarantee_priority_combo.count())]
            if type_str not in type_list:
                errors.append(f"无效的装扮类型: {type_str}")
            if part_str not in part_list:
                errors.append(f"无效的染色部位: {part_str}")
            if guarantee_priority not in guarantee_priority_list:
                errors.append(f"无效的保底优先染色: {guarantee_priority}")
            try:
                match_val = int(match_str)
            except Exception:
                errors.append(f"无效的染色方案: {match_str}")
                match_val = None
            if match_val is not None and not (self.match_scheme_spin.minimum() <= match_val <= self.match_scheme_spin.maximum()):
                errors.append(f"无效的染色方案: {match_str}")
            try:
                scheme_val = int(scheme_str)
            except Exception:
                errors.append(f"无效的染色方案: {scheme_str}")
                scheme_val = None
            if scheme_val is not None and not (self.scheme_spin.minimum() <= scheme_val <= self.scheme_spin.maximum()):
                errors.append(f"无效的染色方案: {scheme_str}")
        if errors:
            raise ValueError('\n'.join(errors))
        return True

    def show_tray_message(self, title, message, msecs=3000):
        if not hasattr(self, '_tray_icon'):
            self._tray_icon = QSystemTrayIcon(self)
            self._tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            self._tray_icon.setVisible(True)
        self._tray_icon.showMessage(title, message, QSystemTrayIcon.Information, msecs)

    def show_message(self, title, message):
        # 始终置顶弹窗，无论主窗口是否激活
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Information)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        box.setStandardButtons(QMessageBox.Ok)
        box.setWindowModality(Qt.ApplicationModal)
        box.exec_()

    # --- 快捷键互斥校验 ---
    def check_shortcut_conflict(self):
        seqs = []
        names = []
        if hasattr(self, 'random_color_cb') and self.random_color_cb.isChecked():
            seqs.append(self.random_color_k_keyedit.keySequence())
            names.append('随机颜色')
        if hasattr(self, 'use_script_shortcut_cb') and self.use_script_shortcut_cb.isChecked():
            seqs.append(self.script_toggle_keyedit.keySequence())
            names.append('启动/停止脚本')
        # 检查非空且有重复
        seq_strs = [seq.toString() for seq in seqs if not seq.isEmpty()]
        for i in range(len(seq_strs)):
            for j in range(i+1, len(seq_strs)):
                if seq_strs[i] == seq_strs[j]:
                    QMessageBox.warning(self, "快捷键冲突", f"快捷键“{names[i]}”与“{names[j]}”不能相同！")
                    return True
        return False
    
    def script_start(self):
        if self.script_thread and self.script_thread.isRunning():
            self.show_tray_message("脚本消息", "脚本已在运行中！", 3000)
            return
        print("脚本开始运行")
        self.show_tray_message("脚本消息", "脚本开始运行！", 3000)
        self.script_thread = ScriptWorker(
            self,
            {k: self.get_config_value(k) for k in self.get_config_fields()},
            self.get_all_table_data())
        self.script_thread.finished.connect(self.on_script_finished)
        self.script_thread.start()

    def script_stop(self):
        print("正在停止脚本")
        if self.script_thread and self.script_thread.isRunning():
            self.script_thread.stop()
            self.script_thread.wait()
            self.script_thread = None
            print("脚本手动停止")
        else:
            self.showMessageSignal.emit("脚本消息", "脚本未在运行")

    def on_script_finished(self, result):
        self.btn_match.setText("开始匹配")
        if result==0:
            self.showMessageSignal.emit("脚本消息", "脚本已完成")
            print("脚本结束")
        else:
            self.showMessageSignal.emit("脚本消息", "脚本已停止")
        self.script_thread = None
        
    def handle_ask_user(self, title, message, callback):
        """在主线程中显示消息框并返回结果，始终置顶"""
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Question)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setWindowModality(Qt.ApplicationModal)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        result = box.exec_()
        callback(result == QMessageBox.Yes)

    def ask_user(self, title, message):
        """线程安全的用户询问方法"""
        result = {}
        loop = QEventLoop()
        def callback(answer):
            result['answer'] = answer
            loop.quit()
        self.askUserSignal.emit(title, message, callback)
        loop.exec_()
        return result['answer']
    
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
    app = QApplication(sys.argv)
    win = ColorMatcherApp()
    win.show()
    sys.exit(app.exec_())
