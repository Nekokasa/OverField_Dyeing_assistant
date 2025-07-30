from pyautogui import click, moveTo, mouseUp, mouseDown,moveRel,press
import time
from PyQt5.QtCore import QThread, pyqtSignal
from ui_logic_mini import *
import win32con
import win32api

def fast_move_rel(dx, dy):
    """使用win32api快速移动鼠标（相对移动）"""
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy, 0, 0)

class ScriptWorker(QThread):
    finished = pyqtSignal(int,str)
    def __init__(self, context, params=None,tabel_data=None):
        super().__init__()
        self.running = True
        self.params = params
        self.tabel_data = tabel_data
        self.context = context
        self.pool_middle_x = (self.value('pool_left') + self.value('pool_right')) // 2
        self.pool_middle_y = (self.value('pool_top') + self.value('pool_bottom')) // 2
        self.exit_reason = None
        self.error_msg = "" # 存储错误信息
        self.success_color = ""# 存储成功匹配的颜色及其索引
        self.skip_flag=[0,0,0,0,0]
        self.current_exit_level = 0  # 当前退出原因的等级

    def set_exit_reason(self, level):
        """
        设置退出原因，只能设置更高等级的退出原因
        :param level: 退出原因等级
        :return: 是否设置成功
        """
        if not isinstance(level, int):
            return False
        
        # 只有新的等级更高时才更新退出原因
        if level > self.current_exit_level:
            self.current_exit_level = level
            return True
            
        return False
    def run(self):
        self.set_exit_reason(0)  # 初始化为正常结束
        try:
            self.script_entrance()
        except Exception as e:
            self.error_msg = str(e)  # 获取异常信息
            self.set_exit_reason(2)  # 设置异常退出和错误信息
            print("脚本运行异常：", self.error_msg)
        finally:
            # 根据退出级别生成最终的退出原因
            if self.current_exit_level == 0:
                self.exit_reason = str(self.success_color)
            elif self.current_exit_level == 2:
                self.exit_reason = self.error_msg
            else:
                self.exit_reason = ""
            mouseUp()
            self.finished.emit(self.current_exit_level, self.exit_reason)
    def stop(self):
        self.running = False
        self.set_exit_reason(1)
    def delay(self, ms):
        """分段睡眠，总共ms毫秒，每500ms检查一次self.running"""
        total = 0
        interval = 500
        while total < ms and self.running:
            sleep_time = min(interval, ms - total)
            time.sleep(sleep_time / 1000)
            total += sleep_time
        return
 

    def value(self,key):
        return int(self.params[key])
    def set_window(self):
        hwnd = self.params['hwnd']
        #置顶放大
        if self.params['topmost'] == 'true':
            set_window_topmost(hwnd)
        if self.params['maximize'] == 'true':
            maximize_window(hwnd)
        self.delay(self.value('delay'))
    def script_entrance(self):
        #置顶放大
        self.set_window()
        #模式选择
        print("匹配模式：")
        if self.params['fast_match'] == 'true':
            msg="快速模糊匹配"
            if self.params['drag_match'] == 'true':
                msg+="+鼠标拖拽匹配"
            else:
                msg+="+逐行遍历匹配"
            print(msg)
            print("混色池相似度：", self.params['pool_sim']," 模糊查找半径：",self.params['radius'])
            if self.params['drag_match'] == 'true':
                print("跳格数：", self.params['step'])
            self.fast_match()
        elif self.params['drag_match'] == 'true':
            print("鼠标拖拽匹配")
            print("跳格数：", self.params['step'])
            self.drag_match()
        else:
            print("逐行遍历匹配")
            self.scan_match()
        return
    def fast_match(self):
        while self.running:
            result = self.find_color_ranges(self.tabel_data)
            if result is not None:
                # print("找到染色范围：", result)
                for start_y, end_y, color_indices in result:
                    if self.params['drag_match'] == 'true' and self.running:
                        self.drag(start_y, end_y, color_indices)
                    elif self.params['scan_match'] == 'true' and self.running:
                        self.scan(start_y, end_y, color_indices)
            if self.running:
                self.set_window()
                self.change_dye_pool()
            # self.match_preview_colors(tuple(range(len(self.tabel_data))))
        return
    def drag_match(self):
        while self.running:
            self.drag(self.value('pool_top'), self.value('pool_bottom'),range(len(self.tabel_data)))
            if self.running:
                self.set_window()
                self.change_dye_pool()
        return
    def scan_match(self):
        while self.running:
            self.scan(self.value('pool_top'), self.value('pool_bottom'),range(len(self.tabel_data)))
            if self.running:
                self.set_window()
                self.change_dye_pool()
        return
    def drag(self, start_y, end_y, color_indices):
        """
        按下滑块并拖动到指定位置
        """
        start_y = max(start_y, self.value('pool_top'))
        end_y = min(end_y, self.value('pool_bottom'))
        if start_y >= end_y:
            self.stop()
            self.set_exit_reason(2)
            print("drag：参数异常，滑块起始位置大于或等于滑块终止位置。")
            return
        self.move_slider_to(start_y)
        mouseDown()
        step = self.value('step')
        while self.running and self.find_slider() < end_y - self.value('slider_between_bottom'):
            self.match_preview_colors(color_indices)
            fast_move_rel(0, step)  # 使用快速移动方法

    def scan(self, start_y, end_y, color_indices):
        """
        按下移键
        """
        start_y = max(start_y, self.value('pool_top'))
        end_y = min(end_y, self.value('pool_bottom'))
        if start_y >= end_y:
            self.stop()
            self.set_exit_reason(2)
            print("scan：参数异常，滑块起始位置大于或等于滑块终止位置。")
            return
        self.move_slider_to(start_y)
        moveTo(self.pool_middle_x,self.value('down_y'))
        while self.running and self.find_slider() < end_y - self.value('slider_between_bottom'):
            self.match_preview_colors(color_indices)
            click()     
            

    def find_slider(self):
        '''
        返回滑块的y坐标
        '''
        coordinate = find_similar_color(self.value('slider_x'), int(0.95*self.value('pool_top')), self.value('slider_x'), self.value('pool_bottom'), 'FFFFFF',1)
        if coordinate is None:
            self.stop()
            self.set_exit_reason(3)
            print("find_slider：找不到滑块,貌似不在染色界面。")
            return None
        return coordinate[1]
    def move_to_slider(self):
        '''
        将鼠标移动到滑块上
        '''
        slider_y = self.find_slider()
        if slider_y is None:
            self.set_exit_reason(3)
            self.stop()
            return
        mouseUp()
        moveTo(self.value('slider_x'), slider_y)
        return
    def move_slider_to(self, y):
        '''
        将滑块移动到指定的y坐标
        '''
        slider_y = self.find_slider()
        if slider_y is None:
            self.set_exit_reason(3)  # 设置为"找不到滑块"错误
            self.stop()
            return
            
        self.move_to_slider()
        mouseDown()
        moveRel(0, y - slider_y)  # 使用已经获取的 slider_y
        mouseUp()

    def change_dye_pool(self):
        '''
        一次自动更换染色池操作
        '''
        mouseUp()
        moveTo(self.pool_middle_x,self.value('change_pool_y'))
        self.delay(self.value('delay'))
        click()
        self.delay(3*self.value('delay'))
        press('F')
        press('F')
        press('F')
        self.delay(3*self.value('delay'))
    def match_preview_colors(self,target_color_indices):
        '''
        预览染色效果
        '''
        px = self.value('preview_x')
        py = self.value('preview_y')
        pw = self.value('preview_width')
        
        # 一次性截取包含所有预览色块的区域
        preview_width = pw * 5  # 5个色块的总宽度
        pixels = fast_grab_pixels(px, py, preview_width, 1)
        
        for i in target_color_indices:
            color = self.tabel_data[i][1]
            sim = float(self.tabel_data[i][2])
            for x in range(5):
                if self.skip_flag[x] >= 0:
                    # 直接从像素数组中获取颜色
                    r, g, b = pixels[0, x * pw]
                    result = '%02X%02X%02X' % (r, g, b)
                    if is_similarity_enough(result,color,sim):
                        #music
                        if self.params['play_music'] == 'true':
                            music_path = os.path.join(get_base_dir(), 'config', 'mission_completed.wav')
                            if not os.path.exists(music_path):
                                print("未找到音频文件 mission_completed.wav！")
                            else:
                                try:
                                    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
                                    from PyQt5.QtCore import QUrl
                                    if not hasattr(self, '_music_player'):
                                        self._music_player = QMediaPlayer()
                                    self._music_player.setMedia(QMediaContent(QUrl.fromLocalFile(music_path)))
                                    self._music_player.setVolume(self.value('music_volume'))
                                    self._music_player.play()
                                except Exception as e:
                                    print(self, "播放失败", f"播放音频失败: {e}")
                        print(f"在第{x+1}个色块上找到第{i+1}个颜色{color}的近似值{result},相似度为{calc_similarity(result,color):.2f}")
                        mouseUp()
                        if self.context is not None:
                            answer = self.context.ask_user("确认", f"在第{x+1}个色块上找到第{i+1}个颜色{color}的近似值{result},相似度为{calc_similarity(result,color):.2f}，是否继续寻找其他可能的匹配？\n点击\"确定\"接受当前结果并结束脚本\n点击\"取消\"继续寻找")
                            if answer:
                                self.success_color = (i, result)
                                self.running = False
                                self.success_color = i
                                print("用户接受当前结果并结束脚本")
                                return
                            else:
                                print("用户不接受当前结果，选择继续寻找")
                                self.skip_flag[x] = -self.value('skip_similar')
                                self.set_window()
                                if self.params['drag_match'] == 'true':
                                    self.move_to_slider()
                                    mouseDown()
                                else:
                                    moveTo(self.pool_middle_x,self.value('down_y'))  # 标记该步已完成，跳过该步
                else:
                    self.skip_flag[x] += 1
    def find_color_ranges(self, target_colors):
        """
        寻找所有目标颜色的范围并合并
        target_colors: [(color_hex, similarity), ...]
        返回: [(start_y, end_y, [color_indices]), ...]  # color_indices表示该范围内可能存在的颜色索引
        """
        # 1. 为每个颜色建立独立的范围集合
        color_ranges = {}
        self.move_slider_to(self.value('pool_bottom'))
        for i, (_,color, _) in enumerate(target_colors):
            ranges = self.find_single_color_ranges(color,self.value('pool_top'),self.pool_middle_y, [])
            if not self.running:
                return None
            color_ranges[i] = ranges
        self.move_slider_to(self.value('pool_top'))
        for i, (_,color, _) in enumerate(target_colors):
            existing_ranges = color_ranges.get(i, [])  # 获取已存在的范围，如果不存在则返回空列表
            ranges = self.find_single_color_ranges(color,self.pool_middle_y,self.value('pool_bottom'), existing_ranges)
            if not self.running:
                return None
            color_ranges[i] = ranges

        # 2. 合并所有范围
        merged = self.merge_all_ranges(color_ranges)
        return merged

    def find_single_color_ranges(self, color, top_y, bottom_y, ranges):
        """
        找到单个颜色的所有可能范围
        Args:
            color: 目标颜色的十六进制值
            top_y: 搜索的上边界
            bottom_y: 搜索的下边界
            ranges: 已存在的范围列表，用于合并
        返回: [(start_y, end_y), ...]
        """
        x1 = self.value('pool_left')
        x2 = self.value('pool_right')
        similarity = float(self.params['pool_sim'])
        # 确保 ranges 是列表类型
        ranges = list(ranges) if ranges else []
        current_y = ranges[-1][1] if ranges else top_y
        top_y = current_y

        pixels = fast_grab_pixels(x1, current_y, x2-x1+1, bottom_y-current_y+1)
        height, width = pixels.shape[:2]  # numpy数组的shape是(height, width, channels)

        while current_y <= bottom_y and self.running:
            found_y = None
            for y in range(current_y-top_y,height):
                for x in range(width):
                    r, g, b = pixels[y, x]  # 直接从numpy数组获取RGB值
                    pixel_hex = '%02X%02X%02X' % (r, g, b)
                    sim = calc_similarity(pixel_hex, color)
                    if sim >= similarity:
                        found_y = current_y + y
                        break
                if found_y is not None:
                    break
            if found_y is None:
                break
            start_y = max(self.value('pool_top'), found_y - self.value('radius'))
            end_y = min(self.value('pool_bottom'), found_y + self.value('radius'))
            # 合并重叠范围
            if ranges and ranges[-1][1] >= start_y - 1:
                ranges[-1] = (ranges[-1][0], end_y)
            else:
                ranges.append((start_y, end_y))
            current_y = end_y + 1
        return ranges

    def merge_all_ranges(self, color_ranges):
        """
        合并所有颜色的范围
        使用线段树或者区间合并算法优化
        
        Args:
            color_ranges: 字典，键为颜色索引，值为该颜色的范围列表 [(start_y, end_y), ...]
        Returns:
            合并后的范围列表 [(start_y, end_y, [color_indices]), ...]
        """
        # 1. 收集所有边界点
        points = []
        for color_idx, ranges in color_ranges.items():
            for start, end in ranges:
                if not self.running:
                    return None
                points.append((start, 1, color_idx))  # 1表示开始
                points.append((end , -1, color_idx))  # -1表示结束
        # 2. 按坐标排序
        points.sort()
        
        # 3. 扫描线算法合并范围
        merged = []
        active_colors = set()
        last_y = None
        
        for y, type_, color_idx in points:
            if not self.running:
                return None
            # 如果有活动颜色且位置变化，记录一个范围
            if active_colors and last_y is not None and last_y < y:
                merged.append((last_y, y, list(active_colors)))
            
            # 更新活动颜色集合
            if type_ == 1:
                active_colors.add(color_idx)
            else:
                active_colors.discard(color_idx)
                
            last_y = y
            
        return merged
    
