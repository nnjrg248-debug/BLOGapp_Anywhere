import os  # 👈 追加：環境変数を扱うために必要
from django.http import JsonResponse
from dotenv import load_dotenv  # 👈 追加：.envファイルを読み込むライブラリ
from google import genai  # 👈 Geminiの公式ライブラリ（環境に合わせて変更してください）

from django.shortcuts import render, redirect, get_object_or_404
from .models import Memo
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
    model=Memo
    fields=['title','']
    template_name='post_form.html'
    success_url=reverse_lazy('post_list')

#3.記事編集(ログインが必要)
class PostUpdateView(LoginRequiredMixin,UpdateView):
    model=Memo
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
    
# 💡 【修正箇所】HTML側で現在の検索状態を維持するために context を追加・整理します
    context = {
        "memos": memos,
        "query": query,         # 検索窓の文字を維持するため
        "search_all": search_all, # チェックボックスの状態を維持するため
    }
    return render(request, "edit/memo_list.html", context)    


   # return render(request, "edit/memo_list.html", {"memos": memos})


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
#@login_required # これ追加で未ログイン時ここに飛ばされない
#def memo_create(request):
#    if request.method=="POST":
#        form=MemoForm(request.POST)
#        if form.is_valid():
#            memo = form.save(commit=False) # まだDBには保存しない
#            memo.author = request.user     # 👈 追加：現在ログイン中のユーザーをセット
#            memo.save()
#以前 ↑form.save()だったがmemo.save()違いはデータベースへの保存(memo側)
#に加えて「画面からの入力データの処理（検証や変換）」まで(form側)行うかどうか
#            return redirect('memo_list')
#    else:
#            form=MemoForm() # 空のフォームを用意
#    return render(request,'edit/memo_form.html',{'form':form})
#def memo_edit(request, pk):
#    memo = get_object_or_404(Memo, pk=pk)

    # 投稿者以外は編集不可
#    if memo.author != request.user:
#        return redirect('memo_detail', pk=pk)

#    if request.method == "POST":
#        form = MemoForm(request.POST, instance=memo)
#        if form.is_valid():
#            form.save()
#            return redirect('memo_detail', pk=pk)
#    else:
#        form = MemoForm(instance=memo)

#    return render(request, 'edit/memo_form.html', {
#        'form': form,
#        'memo': memo,
#    })

def memo_detail(request, pk):
    memo = get_object_or_404(Memo, pk=pk)#SQLエラーが出たときの対処

    # いいね状態（セッション）
    session_like_key = f'user_liked_{pk}'
    liked_by_session = request.session.get(session_like_key, False)

    # 閲覧数カウント（非ログイン時のみ）
    if not request.user.is_authenticated:
        session_view_key = f'viewed_memo_{pk}'
        if not request.session.get(session_view_key, False):
            memo.views_count = (memo.views_count or 0) + 1
            memo.save()
            request.session[session_view_key] = True

    return render(request, 'edit/memo_detail.html', {
        'memo': memo,
        'liked_by_session': liked_by_session,
    })

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

#@login_required
def ai_generate(request):
    try:
        #ユーザが入力した「タイトル」、「冒頭の分を取得」
        api_key_env = os.getenv("GEMINI_API_KEY")
         
        client = genai.Client(api_key=api_key_env)
        user_input=request.GET.get('text','')

    
    #    # 2. 最新のモデル「gemini-2.5-flash」を呼び出す
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=(
                "あなたは優秀な漫才ライターです。ユーザーが入力した文章の続に、"
                f"突っ込みいれてください：\n\n{user_input}"
            )
        )


        try:
            
            ai_text = response.text
    #        ai_text = 'TEST'#response.text
            return JsonResponse({'result': ai_text})

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    except Exception as e:
            # ターミナルに具体的なエラー内容を表示させる
            print(f"エラーが発生しました: {e}")
            return JsonResponse({'error': str(e)}, status=500)


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Memo
def like_post(request, post_id):
    if request.method == 'POST':
        memo = get_object_or_404(Memo, id=post_id)

        # 自分の記事にはいいね不可
        if request.user == memo.author:
            return JsonResponse({'error': '自分の記事にはいいねできません'})

        session_key = f'user_liked_{post_id}'
        already_liked = request.session.get(session_key, False)

        # いいね取り消し
        if already_liked:
            request.session[session_key] = False
            liked = False

            memo.total_likes_count = max(0, memo.total_likes_count - 1)

            if request.user.is_authenticated:
                memo.likes.remove(request.user)

        # 新規いいね
        else:
            request.session[session_key] = True
            liked = True

            memo.total_likes_count += 1

            if request.user.is_authenticated:
                memo.likes.add(request.user)

        memo.save()

        return JsonResponse({
            'liked': liked,
            'total_likes': memo.total_likes_count
        })



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
    


# --- 以下、実際の投稿受付ビューのイメージ ---
#def upload_blog_image(request):
#    if request.method == "POST":
#        # フロント（JavaScript）等から送られてきたBase64文字列を取得
#        base64_data = request.POST.get("image_base64") 
        
#        if not base64_data:
#            return JsonResponse({"error": "画像データがありません"}, status=400)

#        # Base64のヘッダー（data:image/png;base64, 等）を切り離してデコード
#        format, imgstr = base64_data.split(';base64,') 
#        ext = format.split('/')[-1]  # 拡張子 (png, jpgなど)
#        image_bytes = base64.b64decode(imgstr)
#        
#        upload_file_size = len(image_bytes)

#        try:
            # 💡 ここで容量制限チェックを実行！
#            check_r2_limits(upload_file_size)
            
            # チェックが通ったらR2へ直接アップロード
#            s3_client = boto3.client(
#                's3',
#                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
#                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#            )
            
#            file_name = f"blog_images/img_{upload_file_size}.{ext}" # 重複しないファイル名
            
#            s3_client.put_object(
#                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
#                Key=file_name,
#                Body=image_bytes,
#                ContentType=f"image/{ext}"
#            )
            
            # 画像のアクセスURLを生成
#            image_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{file_name}"
            
            # 💡 ああとはこの image_url を記事モデル（DB）のテキストフィールド等に保存するだけ！
            # Example: post.image_url = image_url; post.save()
            
#            return JsonResponse({"success": True, "url": image_url})

#        except ValueError as e:
            # 容量オーバーのエラーを画面に返す
#            return JsonResponse({"error": str(e)}, status=400)
            
#    return render(request, "upload_form.html")
import base64
import re
import uuid
import boto3
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Memo  # モデル名に合わせて適宜調整してください
from .forms import MemoForm  # フォーム名に合わせて適宜調整してください

# Base64画像を抽出するための正規表現パターン
BASE64_IMAGE_PATTERN = r'data:image/([a-zA-Z]*);base64,([^"]*)'


def check_r2_limits(upload_file_size):
    """
    R2の容量制限をチェックする関数
    """
    # 対策1: 1枚のサイズチェック
    if upload_file_size > settings.MAX_FILE_SIZE:
        raise ValueError("ファイルサイズが2MBを超える画像が含まれています。")

    # R2クライアント作成
    s3_client = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    # 対策2: R2バケット内の合計容量を計算
    total_size = 0
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=settings.AWS_STORAGE_BUCKET_NAME)

    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                total_size += obj['Size']

    # 合計が9.5GBを超えたらエラー
    if (total_size + upload_file_size) > settings.MAX_TOTAL_SIZE:
        raise ValueError("ストレージの容量制限に達したため、投稿（アップロード）できません。")


@login_required
def memo_create(request):
    """
    記事の新規投稿を行うビュー（画像はR2に自動保存）
    """
    if request.method == "POST":
        form = MemoForm(request.POST)
        if form.is_valid():
            new_memo = form.save(commit=False)
            new_memo.author = request.user  # ログイン中のユーザーを投稿者に設定
            content = new_memo.content

            s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )

            matches = re.findall(BASE64_IMAGE_PATTERN, content)
            
            try:
                for ext, base64_str in matches:
                    image_bytes = base64.b64decode(base64_str)
                    upload_file_size = len(image_bytes)

                    check_r2_limits(upload_file_size)

                    file_name = f"blog_images/{uuid.uuid4()}.{ext}"
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=file_name,
                        Body=image_bytes,
                        ContentType=f"image/{ext}"
                    )

                    r2_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{file_name}"
                    old_src = f'data:image/{ext};base64,{base64_str}'
                    content = content.replace(old_src, r2_url)

                new_memo.content = content
                new_memo.save()
                return redirect('memo_list')

            except ValueError as e:
                return render(request, "edit/memo_form.html", {
                    "form": form,
                    "error": str(e),
                })
    else:
        form = MemoForm()

    return render(request, "edit/memo_form.html", {"form": form})


@login_required
def memo_edit(request, pk):
    """
    記事の編集を行うビュー（途中で追加された画像もR2に自動保存）
    """
    memo = get_object_or_404(Memo, pk=pk)

    # 投稿者以外は編集不可
    if memo.author != request.user:
        return redirect('memo_detail', pk=pk)

    if request.method == "POST":
        form = MemoForm(request.POST, instance=memo)
        if form.is_valid():
            updated_memo = form.save(commit=False)
            content = updated_memo.content

            s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )

            matches = re.findall(BASE64_IMAGE_PATTERN, content)
            
            try:
                for ext, base64_str in matches:
                    image_bytes = base64.b64decode(base64_str)
                    upload_file_size = len(image_bytes)

                    check_r2_limits(upload_file_size)

                    file_name = f"blog_images/{uuid.uuid4()}.{ext}"
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=file_name,
                        Body=image_bytes,
                        ContentType=f"image/{ext}"
                    )

                    r2_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{file_name}"
                    old_src = f'data:image/{ext};base64,{base64_str}'
                    content = content.replace(old_src, r2_url)

                updated_memo.content = content
                updated_memo.save()
                return redirect('memo_detail', pk=pk)

            except ValueError as e:
                return render(request, 'edit/memo_form.html', {
                    'form': form,
                    'memo': memo,
                    'error': str(e)
                })
    else:
        form = MemoForm(instance=memo)

    return render(request, 'edit/memo_form.html', {
        'form': form,
        'memo': memo,
    })
