import os
from search_util import calc_similarity
from ui_logic import is_valid_hex_color
def load_color_card(filepath=None):
    """
    读取色卡文件，返回[(hex, name), ...]。
    新格式：第一行为表头，第二行起每行“颜色名字,色号,1”，取前两个，name为颜色名，hex为色号。
    """
    color_list = []
    # 支持相对路径 ../config/color_card.txt
    if not os.path.isabs(filepath):
        base_dir = os.path.dirname(__file__)
        filepath = os.path.normpath(os.path.join(base_dir, '../config/color_card.txt'))
    with open(filepath, encoding='utf-8') as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if idx == 0 or not line:
                continue  # 跳过表头或空行
            parts = line.split(',')
            if len(parts) < 2:
                continue
            name, hex_code = parts[0].strip(), parts[1].strip().upper()
            if is_valid_hex_color(hex_code):
                color_list.append((hex_code, name))
    return color_list

def find_similar_color_in_card(hex_str, color_card, threshold=0.95):
    """
    在色卡中查找与hex_str相似度大于等于threshold的色卡，返回[(idx, hex, name, similarity)]，idx为1起始。
    """
    result = []
    hex_str = hex_str.strip().upper()
    if not isinstance(hex_str, str) or len(hex_str) != 6 or not all(c in '0123456789ABCDEF' for c in hex_str):
        raise ValueError("无效的颜色代码，必须为6位16进制字符串")
    threshold = float(threshold)
    if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
        raise ValueError("阈值必须在0到1之间")
    if not isinstance(color_card, list):
        raise TypeError("色卡必须是一个列表")
    if not color_card:
        raise ValueError("色卡列表不能为空")
    color_card = [(c[0].strip().upper(), c[1].strip()) for c in color_card if len(c[0].strip()) == 6]
    for idx, (card_hex, card_name) in enumerate(color_card, 1):
        sim = calc_similarity(hex_str, card_hex)
        if sim >= float(threshold):
            result.append((card_hex, card_name, sim))
    result.sort(key=lambda x: x[2], reverse=True)  # 按相似度降序排序
    return result
