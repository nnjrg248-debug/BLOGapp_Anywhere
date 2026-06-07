import os  # 👈 追加：環境変数を扱うために必要
from django.http import JsonResponse
from dotenv import load_dotenv  # 👈 追加：.envファイルを読み込むライブラリ
from google import genai  # 👈 Geminiの公式ライブラリ（環境に合わせて変更してください）

from django.shortcuts import render, redirect, get_object_or_404
from .models import Memo,Post
from django.http import JsonResponse
from openai import OpenAI
from django.conf import settings
from django.db.models.functions import Lower
from .forms import MemoForm#フォーム使ってる場合
from django.contrib.auth.mixins import LoginRequiredMixin#ログインしてないアクセスはsettingsのURLに戻る設定
import unicodedata
from django.views.generic import ListView,CreateView,UpdateView,DeleteView
from django.urls import reverse_lazy#管廊後の移動先指定につかう
from django.contrib.auth.decorators import login_required#関数ベースのログイン制限
import jaconv
from django.core.mail import send_mail
from django.http import HttpResponse
import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth import logout
from django.core.mail import send_mail
from django.contrib import messages 
from django.db.models import Q
from django.urls import reverse
import csv

#上記関数のインポートで波線立ってるので以下のように対処
#ターミナルで pip show django
#Ctrl + Shift + P (Macは Cmd + Shift + P) を押す。
#「Python: Select Interpreter」 と入力して選択。
#「インタープリターパスを入力」　を選択
#リストの中から 「('venv': venv)」 
#とするのは仮想環境が別のフォルダに作ってある場合でこのPCではまだ作ってないので以下のようにする
#python -m venv venv
#Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Proce#s
#venv\Scripts\activate
#「pip install django openai」
#Ctrl + Shift + P (Macは Cmd + Shift + P) を押す。
#「Python: Select Interpreter」 と入力して選択。
#リストの中から 「('venv': venv)」 など、Djangoをインストールした仮想環境のパスが含まれるものを選択



#1.記事一覧（誰でも見れる）
class PostListView(ListView):
    model = Memo
    template_name='edit/post_list.html'

#2記事作成（ログインが必要）
class PostCreateView(LoginRequiredMixin,CreateView):
    model=Post
    fields=['title','']
    template_name='post_form.html'
    success_url=reverse_lazy('post_list')

#3.記事編集(ログインが必要)
class PostUpdateView(LoginRequiredMixin,UpdateView):
    model=Post
    fields=['title','content']
    template_name='post_form.html'
    success_url=reverse_lazy('post_list')

# 💡 全角半角・大文字小文字・ひらがなカタカナを完全統一する関数（関数の外に出しました）
def normalize_text(text):
    if not text:
        return ""
    text_half = unicodedata.normalize("NFKC", str(text))
    text_kana = jaconv.hira2kata(text_half)
    return text_kana.lower()


def memo_list(request):
  # 💡 【重要】チェックボックスの「ON（1）」の状態を取得する
    search_all = request.GET.get("all_blogs") == "1"

    # 1. ログイン状態とチェックボックスに応じてベースとなるメモを取得
    # 💡 ログインしていて、かつ「すべてのブログ」にチェックを入れて【いない】ときだけ自分のメモ
    if request.user.is_authenticated and not search_all:
        memos = Memo.objects.filter(author=request.user)
    else:
        memos = Memo.objects.all()

    # 2. 🔍 検索キーワードを取得（None対策を完全に施す）
    query = (request.GET.get("q") or "").strip()

    # 💡 スペース（全角・半角）でキーワードを複数単語に分解する
    keywords = query.replace("　", " ").split()

    matched_memos = []

    # 全てのメモを1件ずつチェック
    for memo in memos:
        title_norm = normalize_text(memo.title)
        content_norm = normalize_text(memo.content)

        # 投稿者が存在しない（None）場合の対策
        author_name = memo.author.username if memo.author else ""
        author_norm = normalize_text(author_name)

        # 💡 すべてのキーワードが「含まれているか」を判定する（AND検索）
        is_match = True
        for kw in keywords:
            kw_norm = normalize_text(kw)
            # 1つでも含まれていないキーワードがあれば不合格
            if (
                kw_norm not in title_norm
                and kw_norm not in content_norm
                and kw_norm not in author_norm
            ):
                is_match = False
                break  # 次のキーワードのチェックをスキップ

        # 全てのキーワードをクリアした記事だけを合格リストに入れる
        if is_match:
            matched_memos.append(memo)

    # 【重要修正】ループの外で、絞り込んだ結果を上書きする
    memos = matched_memos

    # 3. 最後に日付順に並び替える
    memos = sorted(memos, key=lambda x: x.created_at, reverse=True)

    return render(request, "edit/memo_list.html", {"memos": memos})
def memo_export(request):
    # 🔐 安全対策：ログインしていない人が直リンクでアクセスしてきたら拒否する
    if not request.user.is_authenticated:
        return HttpResponse("認証が必要です。", status=401)

    # 1. ログインしている「あなた」のメモだけをデータベースから集める
    memos = Memo.objects.filter(author=request.user).order_by('-created_at')

    # 2. ブラウザに「これはダウンロード用のCSVファイルだよ」と教える設定
    response = HttpResponse(content_type='text/csv')
    # ダウンロードされるファイル名を設定（例: my_memos.csv）
    response['Content-Disposition'] = 'attachment; filename="my_blogs.csv"'

    # 💡 Excelで開いたときに日本語が文字化けするのを防ぐ魔法のコード（BOM付与）
    response.write('\ufeff')

    # 3. CSVファイルに文字を書き込んでいく
    writer = csv.writer(response)
    
    # 1行目：見出し（タイトル列）
    writer.writerow(['タイトル', '本文', '投稿日時'])

    # 2行目以降：記事データを1件ずつ流し込む
    for memo in memos:
        # 日付を「2026/06/04 15:00」のような見やすい文字に変形
        created_str = memo.created_at.strftime('%Y/%m/%d %H:%M') if memo.created_at else ""
        writer.writerow([memo.title, memo.content, created_str])

    return response
# Create your views here.
@login_required # これ追加で未ログイン時ここに飛ばされない
def memo_create(request):
    if request.method=="POST":
        form=MemoForm(request.POST)
        if form.is_valid():
            memo = form.save(commit=False) # まだDBには保存しない
            memo.author = request.user     # 👈 追加：現在ログイン中のユーザーをセット
            memo.save()
#以前 ↑form.save()だったがmemo.save()違いはデータベースへの保存(memo側)
#に加えて「画面からの入力データの処理（検証や変換）」まで(form側)行うかどうか
            return redirect('memo_list')
    else:
            form=MemoForm() # 空のフォームを用意
    return render(request,'edit/memo_form.html',{'form':form})
#@login_required # これ追加で未ログイン時ここに飛ばされない
def memo_edit(request,pk):
     #pk(ID)に一致するメモを取得、なければ404エラーを出す
     #memo= get_object_or_404(Memo, pk=pk, author=request.user)
    memo= get_object_or_404(Memo, pk=pk)
         # ログインしていない、または投稿者本人ではない場合
    if not request.user.is_authenticated or memo.author != request.user:
        form = MemoForm(instance=memo)
        
        # 【追加】フォーム内のすべてのテキストボックスを読み取り専用（readonly）にする
        for field in form.fields.values():
            field.widget.attrs['readonly'] = True
            # もしセレクトボックスやチェックボックスもある場合は、下の一行に変えてください
            # field.widget.attrs['disabled'] = True

        return render(request, 'edit/memo_form.html', {'form': form, 'read_only': True})
    if request.method=="POST":
        #既存のデータ(instance=memo)をベースに入力内容(request.POST)を反映
        form=MemoForm(request.POST,instance=memo)
    # (定義でなく使用時の)MemoFormのカッコ内に引数2つだが材料の投入ということ  
    #MemoFormクラスの __init__(self, *args, **kwargs): で使われる引数になる
        if form.is_valid():
             form.save()
             return redirect('memo_list')
    else:
        #編集画面を開いたときに、既存の内容をフォームに表示させる
        form=MemoForm(instance=memo)
    return render(request,'edit/memo_form.html',{'form':form})
@login_required # これ追加で未ログイン時ここに飛ばされない
def memo_delete(request,pk):
    memo=  get_object_or_404(Memo, pk=pk, author=request.user)
    if request.method=="POST":
        memo.delete()
        return redirect('memo_list')
#POST（ボタン押下）でないときは、確認画面(html)を出すだけ
    return render(request,'edit/memo_confirm_delete.html',{'memo':memo})

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        
        # 1. 必ず「先に」データを削除し、そのあとにログアウトする
        if user.is_authenticated:
            user.delete()
        logout(request)
        
        # 2. URLに「?status=deleted」という目印をくっつけてログイン画面へ飛ばす
        target_url = reverse('account_login') + '?status=deleted'
        return redirect(target_url)
        
    return render(request, 'account/delete_account.html')


def ai_generate(request):
    try:
        #ユーザが入力した「タイトル」、「冒頭の分を取得」
        api_key_env = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key_env)
        user_input=request.GET.get('text','')


        # 2. 最新のモデル「gemini-2.5-flash」を呼び出す
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=(
                "あなたは優秀な漫才ライターです。ユーザーが入力した文章の続に、"
                f"突っ込みいれてください：\n\n{user_input}"
            )
        )


        #ai_text=response.choices[0].message.content
        ai_text = response.text
        return JsonResponse({'result':ai_text})
    except Exception as e:
            # ターミナルに具体的なエラー内容を表示させる
            print(f"エラーが発生しました: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    



def test_email_view(request):
    send_mail(
        'AI料理アプリ（テスト）',
        '受け取りました。これから解析します！',
        'nnjrg248@gmail.com',
        ['nnjrg248@gmail.com'],
      #  ['nnjrg248@yahoo.co.jp'],
        fail_silently=False,
    )
    return HttpResponse("テストメールを送信しました。")

# 開発・テスト用の入り口（ブラウザから叩く）
def test_form_view(request):
    # ブラウザの画面を表示する（写真と文章を選べるようにする）
    return render(request, 'upload_test.html')




logger = logging.getLogger(__name__) #グローバル変数（外部変数）のようなもの


@csrf_exempt  # SendGridからの外部アクセスを許可
def handle_inbound_email0(request):
    if request.method == 'POST':
        # 1. データの抽出
        sender = request.POST.get('from')    # 送信者のメールアドレス
        subject = request.POST.get('subject') # メールの件名
        body = request.POST.get('text')      # メールの本文
       
        # 添付ファイル（写真）がある場合
        if request.FILES:
            for file_name in request.FILES:
                photo = request.FILES[file_name]
                # ここで写真を保存したり、AI（Gemini等）に渡したりする
                logger.info(f"写真を受信しました: {photo.name}")

        # 2. とりあえずの自動返信（土台作り）
        send_mail(
            f"Re: {subject}",
            "メールを受け取りました！現在AIが料理を考えています...",
            'admin@1q1q.xyz',  # 送信元（自分のドメイン）
            [sender],         # 送ってきた相手へ返信
            fail_silently=False,
        )

        return HttpResponse(status=200) # SendGridに成功を伝える
   
    return HttpResponse(status=405)


#import google.generativeai as genai
import os
from google import genai
# Geminiの設定（本来はsettings.pyや環境変数に書くのが安全です）
#genai.configure(api_key="AIzaSyDiISuhHbd9nFvW153SfGatSOtob8j24zQ")
#model = genai.GenerativeModel('gemini-2.5-flash') # 高速・画像解析可能モデル

@csrf_exempt
def handle_inbound_email(request):
    if request.method == 'POST':
        sender = request.POST.get('from', 'test@example.com')
        body = request.POST.get('text', '')
        
        # 1. AIに送るための準備
        contents = [f"以下の材料や要望からレシピを1つ提案してください：{body}"]
        # ★ここに追加しておくと便利！
        logger.info(f"送信者: {sender}")
        #logger.info(f"件名: {subject}")
        logger.info(f"本文: {body}")

        # 2. 写真がある場合はAIに渡すリストに追加
        if request.FILES:
            for file_name in request.FILES:
                photo = request.FILES[file_name]
                # 画像データを読み込む
                img_data = photo.read()
                contents.append({"mime_type": "image/jpeg", "data": img_data})
                logger.info(f"AIに写真を送信中: {photo.name}")

        # 3. AIにレシピを生成させる
        response = model.generate_content(contents)
        recipe_text = response.text

        # 4. 生成されたレシピをメールで返信
        send_mail(
            "AIおすすめレシピが完成しました！",
            recipe_text,
            'nnjrg248@gmail.com', # 送信元
            [sender],            # 送信先
            fail_silently=False,
        )

        return HttpResponse(f"AIがレシピを作成し、{sender}宛に送信しました。")