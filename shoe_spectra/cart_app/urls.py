from django.urls import path
from . import views


urlpatterns = [

    # ACCOUNTS SECTION
    path('',views.cart_page, name='cart-page' ),
    path('add-wishlist-page/<int:id>/',views.add_to_wishlist, name='add-wishList' ),
    path('wishlist-page/',views.wishlist, name='wishList-page' ),
    path('add-to-cart-page/<int:variant_id>/',views.add_to_cart, name='add-to-cart' ),


    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update-item/<int:item_id>/', views.update_cart_item_quantity, name='update_cart_item_quantity'),

    path('get_item_stock_quantity/<int:item_id>/', views.get_item_stock_quantity, name='get_item_stock_quantity'),





    # CHECK OUT PAGE
    path('checkout-page',views.checkoutPage, name='checkout-page' ),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('apply-coupen/', views.apply_coupon, name='apply-coupen'),


    # path('payment_success/', views.payment_success, name='payment_success'),
    path('payment_method/', views.razorpay_payment, name='razo-payment-method'),
    path('razorpay-payment-verify/', views.razorpay_payment_verify, name='razorpay_payment_verify'),

    

    path('success-page',views.conform, name='conform-page' ),
    

] 