from django.urls import path

from customer.views.v1.auth_views import (
    register_view,
    login_view,
    verify_phone_view,
    resend_code_view,
    logout_view,
    logout_all_view,
    me_view,
    update_profile_view,
    delete_account_view,
)
from customer.views.v1.catalog_views import (
    list_products_view,
    get_product_view,
    list_categories_view,
    category_tree_view,
    featured_products_view,
    popular_products_view,
    search_products_view,
)
from customer.views.v1.cart_views import (
    get_cart_view,
    add_to_cart_view,
    update_cart_item_view,
    remove_cart_item_view,
    clear_cart_view,
)
from customer.views.v1.address_views import (
    list_addresses_view,
    add_address_view,
    update_address_view,
    delete_address_view,
    set_default_address_view,
)
from customer.views.v1.order_views import (
    place_order_view,
    list_orders_view,
    get_order_view,
    active_orders_view,
    cancel_order_view,
    reorder_view,
)
from customer.views.v1.favorite_views import (
    list_favorites_view,
    toggle_favorite_view,
    check_favorite_view,
)
from customer.views.v1.review_views import (
    submit_review_view,
    list_my_reviews_view,
)
from customer.views.v1.notification_views import (
    list_notifications_view,
    mark_notification_read_view,
    mark_all_read_view,
    unread_count_view,
)
from customer.views.v1.referral_views import (
    my_referral_view,
    my_referrals_list_view,
    apply_referral_view,
)
from customer.views.v1.coupon_views import validate_coupon_view
from customer.views.v1.banner_views import list_banners_view
from customer.views.v1.delivery_zone_views import check_delivery_view, delivery_info_view

app_name = "customer"

urlpatterns = [
    # ── Auth ──
    path("auth/register", register_view, name="register"),
    path("auth/login", login_view, name="login"),
    path("auth/logout", logout_view, name="logout"),
    path("auth/logout-all", logout_all_view, name="logout-all"),
    path("auth/verify", verify_phone_view, name="verify-phone"),
    path("auth/resend-code", resend_code_view, name="resend-code"),
    path("auth/me", me_view, name="me"),
    path("auth/me/update", update_profile_view, name="update-profile"),
    path("auth/me/delete", delete_account_view, name="delete-account"),

    # ── Catalog (public) ──
    path("products", list_products_view, name="products"),
    path("products/featured", featured_products_view, name="products-featured"),
    path("products/popular", popular_products_view, name="products-popular"),
    path("products/search", search_products_view, name="products-search"),
    path("product/<int:product_id>", get_product_view, name="product-detail"),
    path("categories", list_categories_view, name="categories"),
    path("categories/tree", category_tree_view, name="categories-tree"),

    # ── Cart ──
    path("cart", get_cart_view, name="cart"),
    path("cart/add", add_to_cart_view, name="cart-add"),
    path("cart/update", update_cart_item_view, name="cart-update"),
    path("cart/remove", remove_cart_item_view, name="cart-remove"),
    path("cart/clear", clear_cart_view, name="cart-clear"),

    # ── Addresses ──
    path("addresses", list_addresses_view, name="addresses"),
    path("address/add", add_address_view, name="address-add"),
    path("address/<int:address_id>/update", update_address_view, name="address-update"),
    path("address/<int:address_id>/delete", delete_address_view, name="address-delete"),
    path("address/<int:address_id>/default", set_default_address_view, name="address-default"),

    # ── Orders ──
    path("orders", list_orders_view, name="orders"),
    path("orders/active", active_orders_view, name="orders-active"),
    path("orders/place", place_order_view, name="order-place"),
    path("order/<int:order_id>", get_order_view, name="order-detail"),
    path("order/<int:order_id>/cancel", cancel_order_view, name="order-cancel"),
    path("order/<int:order_id>/reorder", reorder_view, name="order-reorder"),

    # ── Favorites ──
    path("favorites", list_favorites_view, name="favorites"),
    path("favorite/<int:product_id>/toggle", toggle_favorite_view, name="favorite-toggle"),
    path("favorite/<int:product_id>/check", check_favorite_view, name="favorite-check"),

    # ── Reviews ──
    path("reviews", list_my_reviews_view, name="reviews"),
    path("review/submit", submit_review_view, name="review-submit"),

    # ── Notifications ──
    path("notifications", list_notifications_view, name="notifications"),
    path("notifications/read-all", mark_all_read_view, name="notifications-read-all"),
    path("notifications/unread-count", unread_count_view, name="notifications-unread-count"),
    path("notification/<int:notification_id>/read", mark_notification_read_view, name="notification-read"),

    # ── Referrals ──
    path("referral", my_referral_view, name="referral"),
    path("referral/list", my_referrals_list_view, name="referral-list"),
    path("referral/apply", apply_referral_view, name="referral-apply"),

    # ── Coupons ──
    path("coupon/validate", validate_coupon_view, name="coupon-validate"),

    # ── Public ──
    path("banners", list_banners_view, name="banners"),
    path("delivery/check", check_delivery_view, name="delivery-check"),
    path("delivery/info", delivery_info_view, name="delivery-info"),
]
