from django.contrib import admin
from .models import Memo  # 作成したモデルをインポート
from django_summernote.admin import SummernoteModelAdmin
#from .models import Post  # ご自身のブログのモデル名

# 最初にある admin.site.register(Post) は消すかコメントアウトしてください


@admin.register(Memo)
class PostAdmin(SummernoteModelAdmin):
    # ここに画像付きエディタにしたいフィールド（例: content）を指定します
    summernote_fields = ('content',) 
