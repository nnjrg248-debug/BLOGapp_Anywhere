
from django.db import models
from django.contrib.auth.models import User
class Memo(models.Model):
    # 👈 追加：このメモを誰が書いたかを記録する（ユーザーが削除されたらメモも消える設定）
    #author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memos') 
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memos')  
    title = models.CharField(max_length=200)  # タイトル（最大200文字）
    content = models.TextField()               # メモ本文
    created_at = models.DateTimeField(auto_now_add=True)  # 作成日時（自動設定）
    updated_at = models.DateTimeField(auto_now=True)      # 更新日時（自動設定）

    class Meta:#自動生成のルール（アプリ名が blog なら blog_memo等）を無視して、データベース上でのテーブル名を強制的に Memo という名前に固定
        db_table='Memo'
        
    def __str__(self):#管理画面などで表示される見出しの文字
        return self.title
    
class Post(models.Model):  # ここが Post ではなく Article などの場合
    title = models.CharField(max_length=200)
    content = models.TextField()