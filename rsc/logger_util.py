import logging
import os
import sys
import datetime
import faulthandler
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class LoggerManager:
    def __init__(self, log_dir='log'):
        self.log_dir = os.path.join(BASE_DIR, log_dir)
        self.log_name = f"log_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
        self.logger = None
        self.file_handler = None
        self.console_handler = None

    def setup_logger(self, enable_file=True):
        if self.logger:
            # 避免重复添加handler
            return self.logger
        self.logger = logging.getLogger("DyeingAssistant")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

        # 控制台输出
        self.console_handler = logging.StreamHandler(sys.__stdout__)
        self.console_handler.setFormatter(formatter)
        self.logger.addHandler(self.console_handler)

        # 文件输出
        if enable_file:
            os.makedirs(self.log_dir, exist_ok=True)
            log_path = os.path.join(self.log_dir, self.log_name)
            self.file_handler = logging.FileHandler(log_path, encoding='utf-8')
            self.file_handler.setFormatter(formatter)
            self.logger.addHandler(self.file_handler)
            # faulthandler也写入同一个文件
            try:
                faulthandler.enable(self.file_handler.stream)
            except Exception:
                pass

        # 捕获print和异常
        sys.stdout = StreamToLogger(self.logger, logging.INFO)
        sys.stderr = StreamToLogger(self.logger, logging.ERROR)
        return self.logger

    def set_file_logging(self, enable_file):
        if self.logger is None:
            self.setup_logger(enable_file=enable_file)
            return
        if enable_file and not self.file_handler:
            # 新增文件handler
            os.makedirs(self.log_dir, exist_ok=True)
            log_path = os.path.join(self.log_dir, self.log_name)
            self.file_handler = logging.FileHandler(log_path, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
            self.file_handler.setFormatter(formatter)
            self.logger.addHandler(self.file_handler)
        elif not enable_file and self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None

class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.buffer = ''

    def write(self, message):
        if message != '\n':
            self.buffer += message
        if '\n' in message:
            self.logger.log(self.level, self.buffer.strip())
            self.buffer = ''

    def flush(self):
        if self.buffer:
            self.logger.log(self.level, self.buffer.strip())
            self.buffer = ''

# 单例
logger_manager = LoggerManager()