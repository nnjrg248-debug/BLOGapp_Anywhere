from django.contrib import admin
from django.urls import path,include
from allauth.account import views as allauth_views  
from django.conf import settings
from django.conf.urls.static import static

urlpatterns=[
    
    path('admin/',admin.site.urls),
    #path('accounts/', include('django.contrib.auth.urls')), 
    #path('',include('edit.urls')),
    path('',include('Suggestion.urls')),

    path('accounts/login/', allauth_views.login, name='login'),  
    # 新しく allauth の URL をガッチャンコする
    path('accounts/', include('allauth.urls')), 
    path('summernote/', include('django_summernote.urls')),  # これを追加


]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)