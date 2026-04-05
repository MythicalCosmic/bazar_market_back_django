from django.urls import path
from admins.views.v1.auth_views import login_view, logout_view, logout_all_view, me_view
from admins.views.v1.user_views import list_users_view, get_user_view, create_user_view, update_user_view, delete_user_view, restore_user_view
from admins.views.v1.customer_views import list_customers_view, get_customer_view, update_customer_view, deactivate_customer_view, activate_customer_view
from admins.views.v1.stats_views import staff_stats_view, customer_stats_view, overview_view
from admins.views.v1.category_views import (
    list_categories_view, get_category_view, category_tree_view,
    create_category_view, update_category_view, delete_category_view, restore_category_view,
    reorder_categories_view, activate_category_view, deactivate_category_view,
    category_stats_view,
)
from admins.views.v1.product_views import (
    list_products_view, get_product_view, create_product_view, update_product_view,
    delete_product_view, restore_product_view, reorder_products_view,
    activate_product_view, deactivate_product_view,
    feature_product_view, unfeature_product_view, update_stock_view,
    add_images_view, remove_image_view, reorder_images_view, set_primary_image_view,
    assign_discounts_view, remove_discounts_view,
    product_stats_view,
)
from admins.views.v1.address_views import list_addresses_view, user_addresses_view, get_address_view
from admins.views.v1.order_views import (
    list_orders_view, get_order_view, update_order_status_view,
    assign_courier_view, unassign_courier_view,
    update_payment_status_view, add_admin_note_view, cancel_order_view,
    bulk_update_status_view, get_min_order_view, set_min_order_view,
    order_stats_view,
)
from admins.views.v1.banner_views import (
    list_banners_view, get_banner_view, create_banner_view, update_banner_view,
    delete_banner_view, reorder_banners_view, activate_banner_view, deactivate_banner_view,
    banner_stats_view,
)
from admins.views.v1.coupon_views import (
    list_coupons_view, get_coupon_view, create_coupon_view, update_coupon_view,
    delete_coupon_view, activate_coupon_view, deactivate_coupon_view,
    coupon_stats_view,
)
from admins.views.v1.discount_views import (
    list_discounts_view, get_discount_view, create_discount_view, update_discount_view,
    delete_discount_view, restore_discount_view, activate_discount_view, deactivate_discount_view,
    set_discount_products_view, add_discount_products_view, remove_discount_products_view,
    set_discount_categories_view, add_discount_categories_view, remove_discount_categories_view,
    discount_stats_view,
)
from admins.views.v1.delivery_zone_views import (
    list_zones_view, get_zone_view, create_zone_view, update_zone_view,
    delete_zone_view, reorder_zones_view, activate_zone_view, deactivate_zone_view,
    zone_stats_view,
)
from admins.views.v1.review_views import (
    list_reviews_view, get_review_view, approve_review_view, reject_review_view,
    reply_review_view, delete_review_view, bulk_approve_reviews_view,
    bulk_reject_reviews_view, review_stats_view,
)
from admins.views.v1.payment_views import (
    list_payments_view, get_payment_view, order_payments_view,
    update_payment_status_view as update_payment_view,
    refund_payment_view, payment_stats_view,
)
from admins.views.v1.notification_views import (
    list_notifications_view, get_notification_view,
    send_notification_view, send_bulk_notification_view,
    delete_notification_view, delete_user_notifications_view,
    notification_stats_view,
)
from admins.views.v1.role_views import (
    list_permissions_view, list_permission_groups_view,
    get_role_permissions_view, set_role_permissions_view, reset_role_permissions_view,
    get_user_permissions_view, grant_user_permission_view, deny_user_permission_view,
    remove_user_permission_view, clear_user_permissions_view,
    sync_permissions_view,
)
from admins.views.v1.setting_views import (
    list_settings_view, get_setting_view, set_setting_view, delete_setting_view,
)
from admins.views.v1.favorite_views import (
    list_favorites_view, most_favorited_view, favorite_stats_view,
)

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

    path('addresses', list_addresses_view, name="addresses"),
    path('addresses/user/<int:user_id>', user_addresses_view, name="user-addresses"),
    path('address/<int:address_id>', get_address_view, name="address"),

    path('categories', list_categories_view, name="categories"),
    path('categories/tree', category_tree_view, name="categories-tree"),
    path('categories/reorder', reorder_categories_view, name="categories-reorder"),
    path('category/<int:category_id>', get_category_view, name="category"),
    path('category/create', create_category_view, name="category-create"),
    path('category/<int:category_id>/update', update_category_view, name="category-update"),
    path('category/<int:category_id>/delete', delete_category_view, name="category-delete"),
    path('category/<int:category_id>/restore', restore_category_view, name="category-restore"),
    path('category/<int:category_id>/activate', activate_category_view, name="category-activate"),
    path('category/<int:category_id>/deactivate', deactivate_category_view, name="category-deactivate"),

    path('products', list_products_view, name="products"),
    path('products/reorder', reorder_products_view, name="products-reorder"),
    path('product/<int:product_id>', get_product_view, name="product"),
    path('product/create', create_product_view, name="product-create"),
    path('product/<int:product_id>/update', update_product_view, name="product-update"),
    path('product/<int:product_id>/delete', delete_product_view, name="product-delete"),
    path('product/<int:product_id>/restore', restore_product_view, name="product-restore"),
    path('product/<int:product_id>/activate', activate_product_view, name="product-activate"),
    path('product/<int:product_id>/deactivate', deactivate_product_view, name="product-deactivate"),
    path('product/<int:product_id>/feature', feature_product_view, name="product-feature"),
    path('product/<int:product_id>/unfeature', unfeature_product_view, name="product-unfeature"),
    path('product/<int:product_id>/stock', update_stock_view, name="product-stock"),
    path('product/<int:product_id>/images', add_images_view, name="product-images-add"),
    path('product/<int:product_id>/images/reorder', reorder_images_view, name="product-images-reorder"),
    path('product/<int:product_id>/image/<int:image_id>', remove_image_view, name="product-image-remove"),
    path('product/<int:product_id>/image/<int:image_id>/primary', set_primary_image_view, name="product-image-primary"),
    path('product/<int:product_id>/discounts/assign', assign_discounts_view, name="product-discounts-assign"),
    path('product/<int:product_id>/discounts/remove', remove_discounts_view, name="product-discounts-remove"),

    path('orders', list_orders_view, name="orders"),
    path('orders/bulk-status', bulk_update_status_view, name="orders-bulk-status"),
    path('orders/min-order', get_min_order_view, name="orders-min-order-get"),
    path('orders/min-order/set', set_min_order_view, name="orders-min-order-set"),
    path('order/<int:order_id>', get_order_view, name="order"),
    path('order/<int:order_id>/status', update_order_status_view, name="order-status"),
    path('order/<int:order_id>/assign-courier', assign_courier_view, name="order-assign-courier"),
    path('order/<int:order_id>/unassign-courier', unassign_courier_view, name="order-unassign-courier"),
    path('order/<int:order_id>/payment-status', update_payment_status_view, name="order-payment-status"),
    path('order/<int:order_id>/note', add_admin_note_view, name="order-note"),
    path('order/<int:order_id>/cancel', cancel_order_view, name="order-cancel"),

    path('banners', list_banners_view, name="banners"),
    path('banners/reorder', reorder_banners_view, name="banners-reorder"),
    path('banner/<int:banner_id>', get_banner_view, name="banner"),
    path('banner/create', create_banner_view, name="banner-create"),
    path('banner/<int:banner_id>/update', update_banner_view, name="banner-update"),
    path('banner/<int:banner_id>/delete', delete_banner_view, name="banner-delete"),
    path('banner/<int:banner_id>/activate', activate_banner_view, name="banner-activate"),
    path('banner/<int:banner_id>/deactivate', deactivate_banner_view, name="banner-deactivate"),

    path('coupons', list_coupons_view, name="coupons"),
    path('coupon/<int:coupon_id>', get_coupon_view, name="coupon"),
    path('coupon/create', create_coupon_view, name="coupon-create"),
    path('coupon/<int:coupon_id>/update', update_coupon_view, name="coupon-update"),
    path('coupon/<int:coupon_id>/delete', delete_coupon_view, name="coupon-delete"),
    path('coupon/<int:coupon_id>/activate', activate_coupon_view, name="coupon-activate"),
    path('coupon/<int:coupon_id>/deactivate', deactivate_coupon_view, name="coupon-deactivate"),

    path('discounts', list_discounts_view, name="discounts"),
    path('discount/<int:discount_id>', get_discount_view, name="discount"),
    path('discount/create', create_discount_view, name="discount-create"),
    path('discount/<int:discount_id>/update', update_discount_view, name="discount-update"),
    path('discount/<int:discount_id>/delete', delete_discount_view, name="discount-delete"),
    path('discount/<int:discount_id>/restore', restore_discount_view, name="discount-restore"),
    path('discount/<int:discount_id>/activate', activate_discount_view, name="discount-activate"),
    path('discount/<int:discount_id>/deactivate', deactivate_discount_view, name="discount-deactivate"),
    path('discount/<int:discount_id>/products/set', set_discount_products_view, name="discount-products-set"),
    path('discount/<int:discount_id>/products/add', add_discount_products_view, name="discount-products-add"),
    path('discount/<int:discount_id>/products/remove', remove_discount_products_view, name="discount-products-remove"),
    path('discount/<int:discount_id>/categories/set', set_discount_categories_view, name="discount-categories-set"),
    path('discount/<int:discount_id>/categories/add', add_discount_categories_view, name="discount-categories-add"),
    path('discount/<int:discount_id>/categories/remove', remove_discount_categories_view, name="discount-categories-remove"),

    path('zones', list_zones_view, name="zones"),
    path('zones/reorder', reorder_zones_view, name="zones-reorder"),
    path('zone/<int:zone_id>', get_zone_view, name="zone"),
    path('zone/create', create_zone_view, name="zone-create"),
    path('zone/<int:zone_id>/update', update_zone_view, name="zone-update"),
    path('zone/<int:zone_id>/delete', delete_zone_view, name="zone-delete"),
    path('zone/<int:zone_id>/activate', activate_zone_view, name="zone-activate"),
    path('zone/<int:zone_id>/deactivate', deactivate_zone_view, name="zone-deactivate"),

    # Reviews
    path('reviews', list_reviews_view, name="reviews"),
    path('reviews/bulk-approve', bulk_approve_reviews_view, name="reviews-bulk-approve"),
    path('reviews/bulk-reject', bulk_reject_reviews_view, name="reviews-bulk-reject"),
    path('review/<int:review_id>', get_review_view, name="review"),
    path('review/<int:review_id>/approve', approve_review_view, name="review-approve"),
    path('review/<int:review_id>/reject', reject_review_view, name="review-reject"),
    path('review/<int:review_id>/reply', reply_review_view, name="review-reply"),
    path('review/<int:review_id>/delete', delete_review_view, name="review-delete"),

    # Payments
    path('payments', list_payments_view, name="payments"),
    path('payment/<int:payment_id>', get_payment_view, name="payment"),
    path('payment/<int:payment_id>/status', update_payment_view, name="payment-status"),
    path('payment/<int:payment_id>/refund', refund_payment_view, name="payment-refund"),
    path('payments/order/<int:order_id>', order_payments_view, name="payments-by-order"),

    # Notifications
    path('notifications', list_notifications_view, name="notifications"),
    path('notifications/send', send_bulk_notification_view, name="notifications-send-bulk"),
    path('notification/<int:notification_id>', get_notification_view, name="notification"),
    path('notification/<int:notification_id>/delete', delete_notification_view, name="notification-delete"),
    path('notification/user/<int:user_id>/send', send_notification_view, name="notification-send"),
    path('notification/user/<int:user_id>/delete', delete_user_notifications_view, name="notification-user-delete"),

    # Roles & Permissions
    path('permissions', list_permissions_view, name="permissions"),
    path('permissions/groups', list_permission_groups_view, name="permission-groups"),
    path('permissions/sync', sync_permissions_view, name="permissions-sync"),
    path('role/<str:role>/permissions', get_role_permissions_view, name="role-permissions"),
    path('role/<str:role>/permissions/set', set_role_permissions_view, name="role-permissions-set"),
    path('role/<str:role>/permissions/reset', reset_role_permissions_view, name="role-permissions-reset"),
    path('user/<int:user_id>/permissions', get_user_permissions_view, name="user-permissions"),
    path('user/<int:user_id>/permissions/grant', grant_user_permission_view, name="user-permission-grant"),
    path('user/<int:user_id>/permissions/deny', deny_user_permission_view, name="user-permission-deny"),
    path('user/<int:user_id>/permissions/remove', remove_user_permission_view, name="user-permission-remove"),
    path('user/<int:user_id>/permissions/clear', clear_user_permissions_view, name="user-permissions-clear"),

    # Settings
    path('settings', list_settings_view, name="settings"),
    path('settings/set', set_setting_view, name="settings-set"),
    path('setting/<str:key>', get_setting_view, name="setting"),
    path('setting/<str:key>/delete', delete_setting_view, name="setting-delete"),

    # Favorites
    path('favorites', list_favorites_view, name="favorites"),
    path('favorites/most', most_favorited_view, name="favorites-most"),

    # Stats
    path('stats/overview', overview_view, name="stats-overview"),
    path('stats/staff', staff_stats_view, name="stats-staff"),
    path('stats/customers', customer_stats_view, name="stats-customers"),
    path('stats/categories', category_stats_view, name="stats-categories"),
    path('stats/products', product_stats_view, name="stats-products"),
    path('stats/orders', order_stats_view, name="stats-orders"),
    path('stats/banners', banner_stats_view, name="stats-banners"),
    path('stats/coupons', coupon_stats_view, name="stats-coupons"),
    path('stats/discounts', discount_stats_view, name="stats-discounts"),
    path('stats/zones', zone_stats_view, name="stats-zones"),
    path('stats/reviews', review_stats_view, name="stats-reviews"),
    path('stats/payments', payment_stats_view, name="stats-payments"),
    path('stats/notifications', notification_stats_view, name="stats-notifications"),
    path('stats/favorites', favorite_stats_view, name="stats-favorites"),
]
