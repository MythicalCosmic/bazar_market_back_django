from django.urls import path
from admins.views.v1.auth_views import login_view


app_name = "admins"



urlpatterns = [
    path('auth-login', login_view, name='login')
]
