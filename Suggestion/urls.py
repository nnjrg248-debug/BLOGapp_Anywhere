
from django.urls import path,include
from .import views
from .views import PostListView,PostCreateView,PostUpdateView#作ったViweをインポート
from django.contrib.auth import views as auth_views

'''

from django.urls import path,include from .import viewsのちがいで
from django.urls import path,includeはfromファイル名importメソッド名 
from .import viewsはfrom.（ディレクトリ名)fromファイル名だが

「どこから」「何を」インポートするかという点で決定的な違いあり
from django.urls import path, include: Djangoの外部ライブラリから、機能（関数）を取り込む。
from . import views: 現在と同じフォルダ内にある views.py を、モジュール全体として取り込む

'''
urlpatterns=[
    
  #  path('memo/<int:pk>/', views.post_detail, name='memo_detail'),
    
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    
    path('',PostListView.as_view(),name='post_list'),                #これはひつよう←←←←←←←←どうして path('', views.memo_list, name='post_list'), が一番か？

#↑name='login' にしてはいけないDjangoが用意したログイン専用のViewにすでに割り当照られているので、
# name='login' と付けてしまうと、名前が重複となる
#    path('post/new/',PostCreateView.as_view(),name='post_create'),# クラスベース 
    #クラスベースはviewの中でのif request.method == "POST"の処理分岐がいらずmodel = Postという記載で処理してくれる
    
    path('post/<int:pk>/edit/',PostUpdateView.as_view(),name='post_edit'),
 
    #path('',views.memo_list,name='memo_list'),#上の「path('',PostListView.～」第一引数同じなのでその場合下の行は無視される
    path('list',views.memo_list,name='memo_list'),# name='memo_list'は href="{% url 'memo_list' %}"で呼ばれるが第一引数を変えることで第一引数がかぶらなくなったので問題なし
    path('memo/export/', views.memo_export, name='memo_export'), 
    #path('new/',views.memo_create,name='memo_create'),#関数ベース htmlから第3引数のボタン押されたら第1引数のURLで第2引数もメソッドが実行される　第一引数は単なるURLで表示される場所と覚える
   # path('new/', views.create_blog_post, name='memo_create'),
   path('new/', views.memo_create, name='memo_create'),

    path('detail/<int:pk>/', views.memo_detail, name='memo_detail'),  # ← 閲覧専用 

    path('edit/<int:pk>',views.memo_edit,name='memo_edit'),
 


    #↑第一引数のpkがviewsのmemo_editのurlでの表示のみで第2引数が指定される
    #またmemo_form.htmlでmemo_editの第2引数として指定されている
    path('delete/<int:pk>',views.memo_delete,name='memo_delete'),
  # path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('ai-generate/',views.ai_generate,name='ai_generate'),
    path('accounts/delete/', views.delete_account, name='account_delete'),

    #path('test-send/', views.test_email_view),
    #path('test/', views.test_email_view),
    path('inbound/', views.handle_inbound_email),
    
    path('handle_inbound_email/', views.handle_inbound_email, name='handle_inbound_email'),
]