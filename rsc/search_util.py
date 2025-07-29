import pyautogui
import time
from PyQt5.QtCore import QThread, pyqtSignal


def calc_similarity(hex1, hex2):
    """
    计算两个16进制颜色代码的相似度。
    相似度 = 1 - (|r1-r2| + |g1-g2| + |b1-b2|) / 255
    返回值范围[0,1]，越大越相似。
    """
    def hex_to_rgb(s):
        s = s.strip().lstrip('#')
        if len(s) != 6:
            raise ValueError('颜色码长度必须为6位')
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        return r, g, b
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    diff = abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
    similarity = 1 - diff / 255
    return max(0, min(1, similarity))

def is_similarity_enough(hex1, hex2, threshold):
    """
    判断两个颜色的相似度是否大于等于阈值。
    """
    sim = calc_similarity(hex1, hex2)
    return sim >= threshold

class ScriptWorker(QThread):
    finished = pyqtSignal(int)
    def __init__(self, context, params=None,tabel_data=None):
        super().__init__()
        self.running = True
        self.params = params
        self.tabel_data = tabel_data
        self.context = context
    def run(self):
        try:
            result = self.script_entrance()
        except Exception as e:
            print("脚本运行异常：", e)
        self.finished.emit(result)
    def stop(self):
        self.running = False
    def delay(self, ms):
        """分段睡眠，总共ms毫秒，每500ms检查一次self.running"""
        total = 0
        interval = 500
        while total < ms:
            if not self.running:
                return 1
            sleep_time = min(interval, ms - total)
            time.sleep(sleep_time / 1000)
            total += sleep_time
        return 0
    def script_entrance(self):
        result = 0
        while self.running:
            # 按住鼠标左键，从 (x1, y1) 拖到 (x2, y2)
            x = int(self.params['slider_x'])
            y1 = int(self.params['pool_top'])
            y2 = int(self.params['pool_bottom'])
            # 延迟2.5秒
            result += self.delay(2500)
            pyautogui.FAILSAFE = False
            pyautogui.moveTo(x, y1)
            pyautogui.mouseDown()
            while y1 < y2 :
                if not self.running:
                    return 1
                y1 += 100
                pyautogui.moveTo(x, y1)  # duration 可选，控制拖动速度
            pyautogui.mouseUp()
            if self.context is not None:
                answer = self.context.ask_user("确认", "是否继续？")
                if not answer:
                    return 0
            break
        return result
