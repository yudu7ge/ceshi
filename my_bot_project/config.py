# config.py
import os
from dotenv import load_dotenv

# 加载 .env 文件中的变量
load_dotenv()

# Telegram 机器人 token
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')

# 数据库连接信息
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = os.getenv('DB_PORT')
DB_SSL = os.getenv('DB_SSL')
