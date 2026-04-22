from django.urls import path
from . import views

urlpatterns = [
    path("login/",    views.login_view,    name="login"),
    path("logout/",   views.logout_view,   name="logout"),
    path("register/", views.register_view, name="register"),
    path("", views.home_view, name="home"),
    path("shop/",                          views.product_list,   name="product_list"),
    path("product/<uuid:product_id>/",     views.product_detail, name="product_detail"),
    path("cart/add/<uuid:product_id>/",    views.cart_add,    name="cart_add"),
    path("cart/remove/<uuid:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart/update/<uuid:product_id>/", views.cart_update, name="cart_update"),
    path("cart/data/",                     views.cart_data,   name="cart_data"),
    path("checkout/<uuid:product_id>/", views.checkout, name="checkout"),
    path("orders/<uuid:order_id>/",                   views.order_detail,     name="order_detail"),
    path("orders/<uuid:order_id>/release_delivery/",  views.release_delivery, name="release_delivery"),
    path("orders/<uuid:order_id>/confirm_delivery/",  views.confirm_delivery, name="confirm_delivery"),
    path("orders/<uuid:order_id>/mark_received/",     views.confirm_delivery, name="mark_received"),
    path("escrow/fund/<uuid:escrow_id>/",   views.fund_escrow,       name="fund_escrow"),
    path("escrow/refund/<uuid:escrow_id>/", views.refund_buyer_view, name="refund_buyer"),
    path("dispute/<uuid:escrow_id>/",       views.raise_dispute,     name="raise_dispute"),

    # ── NEW: seller cancel before deposit ────────────────────────────
    path("escrow/cancel/<uuid:escrow_id>/", views.cancel_by_seller,  name="cancel_by_seller"),

    # ── NEW: arbiter dispute voting ───────────────────────────────────
    path("escrow/vote/<uuid:escrow_id>/",   views.cast_dispute_vote, name="cast_dispute_vote"),

    path("account/",       views.wallet,           name="wallet"),
    path("buyer/",         views.buyer_dashboard,  name="buyer_dashboard"),
    path("admin-panel/",   views.admin_dashboard,  name="admin_dashboard"),
    path("supplier/",                                  views.supplier_dashboard, name="supplier_dashboard"),
    path("supplier/register-shop/",                    views.register_shop,      name="register_shop"),
    path("supplier/update-shop/",                      views.update_shop,        name="update_shop"),
    path("supplier/add-product/",                      views.add_product,        name="add_product"),
    path("supplier/edit-product/<uuid:product_id>/",   views.edit_product,       name="edit_product"),
    path("supplier/restock/<uuid:product_id>/",        views.restock_product,    name="restock_product"),
    path("supplier/delete-product/<uuid:product_id>/", views.delete_product,     name="delete_product"),
    path("supplier/inventory/<uuid:product_id>/",      views.update_inventory,   name="update_inventory"),
    path("analytics/",        views.analytics_dashboard, name="analytics"),
    path("analytics/charts/", views.chart_view,          name="chart_view"),
    path("kpi/",              views.kpi_view,             name="kpi"),
    path("api/notifications/",           views.notifications_json,      name="notifications_json"),
    path("api/notifications/mark-read/", views.notifications_mark_read, name="notifications_mark_read"),
    path("test-blockchain/", views.test_blockchain, name="test_blockchain"),

    # ── NEW: on-chain arbiter management (staff only) ─────────────────
    path("admin-panel/arbiters/add/",    views.add_arbiter_view,    name="add_arbiter"),
    path("admin-panel/arbiters/remove/", views.remove_arbiter_view, name="remove_arbiter"),
]