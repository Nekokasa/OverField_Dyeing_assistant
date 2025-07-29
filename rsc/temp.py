import math
from colorsys import rgb_to_hsv

import win32gui
import win32ui
import win32con
import numpy as np
from PIL import Image

def calc_similarity(hex1, hex2):
    """
    基于HSV空间计算十六进制颜色的相似度
    :param hex1: 十六进制颜色字符串（如 "#FF0000"）
    :param hex2: 十六进制颜色字符串
    :return: 相似度（0~1，1表示完全相同）
    """
    def hex_to_hsv(hex_color):
        """
        将十六进制颜色字符串转换为HSV
        :param hex_color: 格式为 "#FF0000" 或 "FF0000"
        :return: (h, s, v) 值域 h:0-360, s:0-1, v:0-1
        """
        # 去除可能的 # 号
        hex_color = hex_color.lstrip('#')
        hex_color = hex_color.strip().lstrip('#')
        if len(hex_color) != 6:
            raise ValueError('颜色码长度必须为6位')
        # 转换为RGB整数（0-255）
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # 将RGB转换到0-1范围并转为HSV
        h, s, v = rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        # 调整色相到0-360度
        h *= 360
        return h, s, v
    hsv1 = hex_to_hsv(hex1)
    hsv2 = hex_to_hsv(hex2)
    
    # 计算色相差异（考虑圆形色相空间）
    hue_diff = min(abs(hsv1[0] - hsv2[0]), 360 - abs(hsv1[0] - hsv2[0])) / 180.0
    
    # 计算饱和度与明度差异
    sv_diff = math.sqrt((hsv1[1] - hsv2[1])**2 + (hsv1[2] - hsv2[2])**2) / math.sqrt(2.0)
    
    # 加权组合（色相权重70%）
    similarity = 1 - (0.7 * hue_diff + 0.3 * sv_diff)
    return similarity

def ColourDistance(hex_color_1, hex_color_2):
    def hex_to_rgb(hex_color):
        hex_color = hex_color.strip().lstrip('#')
        if len(hex_color) != 6:
            raise ValueError('颜色码必须为6位十六进制')
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )
    
    R1, G1, B1 = hex_to_rgb(hex_color_1)
    R2, G2, B2 = hex_to_rgb(hex_color_2)
    
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

def fast_get_pixel_color(x, y):
    """快速获取单个像素的颜色"""
    pixels = fast_grab_pixels(x, y, 1, 1)
    r, g, b = pixels[0, 0]
    return '%02X%02X%02X' % (r, g, b)

hwnd = win32gui.FindWindow("UnityWndClass", "开放空间")
# 获取200x200的区域图像
pixels = fast_grab_pixels(1, 1, 200, 200)

# 将numpy数组转换为PIL图像
img = Image.fromarray(pixels)  # 自动转换为RGB模式
img.show()  # 显示图像

# 同时打印单个像素的颜色值
print(fast_get_pixel_color(100, 100))