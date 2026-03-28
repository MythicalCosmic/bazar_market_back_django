from django.urls import path
from admins.views.v1.auth_views import login_view, logout_view, logout_all_view, me_view
from admins.views.v1.user_views import list_users_view, get_user_view, create_user_view, update_user_view, delete_user_view, restore_user_view


app_name = "admins"



urlpatterns = [
    path('auth-login', login_view, name='login'),
    path('auth-logout', logout_view, name='logout'),
    path('auth-logout-all', logout_all_view, name='logout-all'),
    path('auth-me', me_view, name="me"),


    path('users', list_users_view, name="users"),
    path('user/<int:pk>', get_user_view, name="user"),
    path('user/create', create_user_view, name="create"),
    path('user/<int:pk>/update', update_user_view, name="update"),
    path('user/<int:pk>/delete', delete_user_view, name="delete"),
    path('user/<int:pk>/restore', restore_user_view, name="restore"),
]
