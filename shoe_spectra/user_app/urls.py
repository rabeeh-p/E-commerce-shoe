from django.urls import path,include
from . import views


urlpatterns = [

    # ACCOUNTS SECTION
    path('',views.indexPage, name='index-page' ),
    path('login/',views.loginPage, name='login-page' ),
    path('logout/',views.logout, name='logoutUser-page' ),
    path('register/',views.registerPage, name='register-page' ),
    path('otp-page/',views.otpPage, name='otp-page' ),
    path('otp-resend/',views.resend_otp, name='otp-resend' ),


    # PRODUCT SECTION
    path('single-product/<int:id>/',views.SinglePage, name='single-page' ),
    path('shopping-product/',views.shopPage, name='shopping-page' ),

    path('single-view/<int:variantId>/',views.SingleView, name='single-view' ),

   
   
   
    # PROFILE SECTION
    path('profile/',views.profile, name='profile' ),
    path('profile-form/',views.user_profile, name='profile-form' ),
    path('profile-update/',views.update_profile, name='profile-update' ),

    path('profile/addres-list',views.address_list, name='address-list' ),
    path('profile/single-address/<int:address_id>/', views.single_address, name='single-address'),
    path('addresses/<int:address_id>/edit/', views.edit_address, name='edit_address'),
    path('addresses/<int:address_id>/delete/', views.delete_address, name='delete_address'),
    path('addresses/add/', views.add_address, name='add_address'),

    path('change-password/', views.change_password, name='change-password'),
    path('password-change-success/', views.password_change_success, name='password_change_success'),





    # ORDER SECTION
    path('profile-order/',views.profile_orderDetails, name='profile-order' ),
    path('order/<int:order_id>/', views.order_detail, name='profile-order-details'),

    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel-order'),
    path('order/<int:order_id>/cancel-product/<int:item_id>/', views.cancel_product, name='cancel-product'),



    # FILTERING 
    path('filtering-items/',views.filtering_items, name='filtering-items' ),

] 