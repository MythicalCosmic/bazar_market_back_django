from django.urls import path
from customer.views.category_views import get_category_view, list_categories_view, category_tree_view

app_name = 'customers'

url_patterns = [
    path('categories', list_categories_view, name="list-categories"),
    path('categories/tree', category_tree_view, name="categories-tree"),
    path('categories/<int:id>', get_category_view, name="get-category")
]