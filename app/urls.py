from django.urls import path
from . import views

urlpatterns = [
    path('test-blockchain/', views.test_blockchain, name='test_blockchain'),
    path('products/', views.product_list, name='product_list'),
    path('product/<uuid:product_id>/', views.product_detail, name='product_detail'),

    # CHECKOUT
    path('checkout/<uuid:product_id>/', views.checkout, name='checkout'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
    # ORDERS
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),

    # ESCROW ACTIONS
    path('escrow/fund/<uuid:escrow_id>/', views.fund_escrow, name='fund_escrow'),
    path('escrow/confirm/<uuid:escrow_id>/', views.confirm_delivery, name='confirm_delivery'),

    # DISPUTE
    path('dispute/<uuid:escrow_id>/', views.raise_dispute, name='raise_dispute'),
]