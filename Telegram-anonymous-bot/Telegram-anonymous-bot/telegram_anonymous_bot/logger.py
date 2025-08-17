import logging
import logging.handlers
import os

from .config import PATH_STORAGE

# اطمینان از وجود مسیر ذخیره‌سازی
os.makedirs(PATH_STORAGE, exist_ok=True)

# فرمت زمان و پیام
FORMAT = '%(asctime)s ==> %(message)s'
DATEFMT = '%Y-%m-%d %H:%M:%S'

# تعریف سطح لاگ پیش‌فرض برای تلگرام
TELEGRAM_LOG_LEVEL = logging.INFO

# ------------------------------
# 🟥 ERROR LOGGER CONFIGURATION
# ------------------------------
error_log_file = PATH_STORAGE.joinpath('error_logs.txt')
error_handler = logging.handlers.RotatingFileHandler(
    error_log_file, maxBytes=20 * 1024 * 1024, backupCount=1, encoding='utf-8'
)
error_handler.setFormatter(logging.Formatter(FORMAT, datefmt=DATEFMT))

error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)
error_logger.addHandler(error_handler)
error_logger.propagate = False  # جلوگیری از تکرار لاگ در کنسول

# ------------------------------
# 🟦 INFO LOGGER CONFIGURATION
# ------------------------------
info_log_file = PATH_STORAGE.joinpath('info_logs.txt')
info_handler = logging.handlers.RotatingFileHandler(
    info_log_file, maxBytes=20 * 1024 * 1024, backupCount=1, encoding='utf-8'
)
info_handler.setFormatter(logging.Formatter(FORMAT, datefmt=DATEFMT))

info_log = logging.getLogger("info_logger")
info_log.setLevel(TELEGRAM_LOG_LEVEL)
info_log.addHandler(info_handler)
info_log.propagate = False

# ------------------------------
# برای استفاده در بقیه فایل‌ها:
# ------------------------------
# error_logger.error("متنی برای خطای مهم")
# info_log.info("اطلاعات عادی")
