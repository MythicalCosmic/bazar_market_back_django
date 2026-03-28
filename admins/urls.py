from django.urls import path
from admins.views.v1.auth_views import login_view, logout_view, logout_all_view


app_name = "admins"



urlpatterns = [
    path('auth-login', login_view, name='login'),
    path('auth-logout', logout_view, name='logout'),
    path('auth-logout-all', logout_all_view, name='logout-all')
]
