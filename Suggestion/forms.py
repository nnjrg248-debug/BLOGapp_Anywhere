#「データのチェックや加工はFormの役割」というルールがある
from django import forms
from .models import Memo
from django_summernote.widgets import SummernoteWidget

class MemoForm(forms.ModelForm):#クラスのカッコ内のforms.ModelFormは引数でなく親クラスを表す
    class Meta:
        
        model=Memo
#このフォームは、Memoというデータベースのテーブル（モデル）と合体して動くものですよ、と指定
       
        fields=['title','content']
        widgets = {
            'content': SummernoteWidget(),
        }
        #このフォームを使用することで、ビューでのデータ保存がform.save()だけで完結し、バリデーションも自動化
#画面に表示して入力してもらうのは (テーブル列の)titleと contentの2つだけという指定
    def __init__(self, *args, **kwargs):
#フォームが画面に表示されるために「初期化（生成）」関数 __init__を定義
        super().__init__(*args, **kwargs)# Djangoの元の親クラスが持っている「フォームを作るための標準的な準備処理」（これがないとフォームが壊れる）
        # HTMLの画面上で「必須（required）」という属性を強制的に外します
        self.fields['title'].required = False#必須入力なしという設定
        self.fields['content'].required = False

    def clean(self):
        cleaned_data = super().clean()
        #「親クラス（super）に元から備わっている、データチェック処理(数値チェック、空チェックとか)実行という意味
        title = cleaned_data.get('title', '')
        content = cleaned_data.get('content', '')

        # タイトルも本文も両方とも空（空白文字だけ含む）の場合にエラーにする
        if not title.strip() and not content.strip():
            #raise forms.ValidationError('タイトルまたは本文のどちらか一方は必ず入力してください。')
            self.add_error('title', 'タイトルまたは本文のどちらか一方は必ず入力してください。')
            return cleaned_data
        
        if not title.strip() and content.strip():
            cleaned_data['title'] ="無題";


        return cleaned_data