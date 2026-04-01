from django.urls import path
from admins.views.v1.auth_views import login_view, logout_view, logout_all_view, me_view
from admins.views.v1.user_views import list_users_view, get_user_view, create_user_view, update_user_view, delete_user_view, restore_user_view
from admins.views.v1.customer_views import list_customers_view, get_customer_view, update_customer_view, deactivate_customer_view, activate_customer_view
from admins.views.v1.stats_views import staff_stats_view, customer_stats_view, overview_view

app_name = "admins"

urlpatterns = [
    path('auth-login', login_view, name='login'),
    path('auth-logout', logout_view, name='logout'),
    path('auth-logout-all', logout_all_view, name='logout-all'),
    path('auth-me', me_view, name="me"),

    path('users', list_users_view, name="users"),
    path('user/<int:user_id>', get_user_view, name="user"),
    path('user/create', create_user_view, name="create"),
    path('user/<int:user_id>/update', update_user_view, name="update"),
    path('user/<int:user_id>/delete', delete_user_view, name="delete"),
    path('user/<int:user_id>/restore', restore_user_view, name="restore"),

    path('customers', list_customers_view, name="customers"),
    path('customer/<int:customer_id>', get_customer_view, name="customer"),
    path('customer/<int:customer_id>/update', update_customer_view, name="customer-update"),
    path('customer/<int:customer_id>/deactivate', deactivate_customer_view, name="customer-deactivate"),
    path('customer/<int:customer_id>/activate', activate_customer_view, name="customer-activate"),

    path('stats/overview', overview_view, name="stats-overview"),
    path('stats/staff', staff_stats_view, name="stats-staff"),
    path('stats/customers', customer_stats_view, name="stats-customers"),
]
