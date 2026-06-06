from django.contrib import admin
from django.urls import path,include
from allauth.account import views as allauth_views  

urlpatterns=[
    
    path('admin/',admin.site.urls),
    #path('accounts/', include('django.contrib.auth.urls')), 
    #path('',include('edit.urls')),
    path('',include('Suggestion.urls')),

    path('accounts/login/', allauth_views.login, name='login'),  
    # 新しく allauth の URL をガッチャンコする
    path('accounts/', include('allauth.urls')), 


]