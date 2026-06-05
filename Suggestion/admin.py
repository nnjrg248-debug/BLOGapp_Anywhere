from django.contrib import admin
from .models import Memo  # 作成したモデルをインポート

admin.site.register(Memo)  # 管理画面に登録