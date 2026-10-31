import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
NOTION_TOKEN = os.getenv('NOTION_TOKEN', '').strip()
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '').strip().replace('-', '')

# 代理配置（可选）
PROXY = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY') or os.getenv('ALL_PROXY') or None
if PROXY:
    PROXY = PROXY.strip()

# 白名单用户 ID
allowed_ids_raw = os.getenv('ALLOWED_USER_IDS', '').strip()
ALLOWED_USER_IDS = set()
if allowed_ids_raw:
    for item in allowed_ids_raw.split(','):
        item = item.strip()
        if item.isdigit():
            ALLOWED_USER_IDS.add(int(item))

def validate_config():
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append('TELEGRAM_BOT_TOKEN')
    if not NOTION_TOKEN:
        missing.append('NOTION_TOKEN')
    if not NOTION_DATABASE_ID:
        missing.append('NOTION_DATABASE_ID')
    
    if missing:
        print(f'[ERROR] 缺少必要的环境变量: {missing}', file=sys.stderr)
        print('请检查并在 .env 文件中补全配置。', file=sys.stderr)
        return False
    return True
