"""
WSGI config for editapp project.
"""

import os
from django.core.wsgi import get_wsgi_application

# 1. アプリが起動する前に、環境変数をセットする
# プロジェクトのベースディレクトリを自動取得
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE_PATH = os.path.join(BASE_DIR, "secret_key.txt")

if os.path.exists(KEY_FILE_PATH):
    with open(KEY_FILE_PATH, "r") as f:
        # 環境変数の名前を「GEMINI_API_KEY」にしてセット
        os.environ['GEMINI_API_KEY'] = f.read().strip()

# 2. Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MenuSuggestion.settings')

# 3. アプリケーションの起動（必ず環境変数のセットより下に配置する）
application = get_wsgi_application()
