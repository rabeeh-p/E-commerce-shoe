from django.urls import path
from . import views

from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [

    # ACCOUNT RELEATED

    path('index/',views.adminPage, name='admin-page' ),
    path('profile-page/',views.profilePage, name='adminProfile-page' ),
    path('',views.adminLogin, name='adminLogin-page' ),
    path('logout/',views.logoutAdmin, name='logout-page' ),


    # USERS RELATED
    path('users-page/',views.usersPage, name='users-page' ),
    path('users-status/',views.users_status, name='users-status' ),
    path('user-details/<int:id>/',views.userDetailsPage, name='user-details' ),
    path('user-status/<int:id>/',views.userStatus, name='single-userstatus' ),

    # PRODUCT RELATED
    path('product/',views.productList, name='product-page' ),
    path('product-category/',views.productCategory, name='product-category' ),
    path('product-single/<int:id>/', views.productSingle_status, name='mainStatus'),

    path('product/edit/<int:product_id>/', views.edit_product_form, name='edit_product'),

    path('add-product/',views.productAdd, name='add2-page' ),
    path('edit-product1/<int:id>/',views.productSingleView, name='product-edit' ),

    # STATUS
    path('brand_status/', views.brand_status, name='brand-status'),
    path('category_status/', views.category_status, name='category-status'),



    # ADD VARIANTSS
    path('add-variants/<int:id>/',views.variantsAdd, name='variants-add' ),
    path('edit-variant/<int:id>/',views.singleVariant_status, name='single-variant-status' ),


    # EDIT VARIANTS and VARIAT DETAILS
    path('edit-variants/<int:id>/',views.editVariants, name='variants-edit' ),
    path('variant-image-edit/<int:id>/',views.editVariant_image, name='variants-image-edit' ),
    path('variant-size-edit/<int:id>/',views.variant_size_edit, name='variants-size-edit' ),



    # EDIT VARIANT IMAGES
    path('variant-images-edit/<int:id>/',views.edit_variant_images, name='variants-images-edit' ),


    # SIZE ADD VARIANT
    path('add-size/<int:id>/',views.sizeAdd, name='add-size' ),
    path('size-status/<int:id>/',views.sizeStatus, name='size-status' ),




    # ADD CATEGORIES

    path('Add-category/',views.addCategory, name='add-categories' ),
    path('category-edit/<int:id>/',views.editCategories, name='editcategory-page' ),
    path('category-delete/<int:id>/',views.deleteCategory, name='deleteCategory-page' ),


    # BRAND 
    path('Add-brand/',views.brandAdd, name='add-brand' ),
    path('edit-brand/<int:id>/',views.brandEdit, name='edit-brand' ),
    path('delete-brand/<int:id>/',views.brandDelete, name='delete-brand' ),


    # COLORS
    path('edit-color/<int:id>/',views.colorEdit, name='edit-color' ),
    path('delete-color/<int:id>/',views.colorDelete, name='delete-color' ),
    path('add-color/',views.colorAdd, name='add-color' ),


    # GENDER
    path('add-gender/',views.genderAdd, name='add-gender' ),
    path('edit-gender/<int:id>/',views.genderEdit, name='edit-gender' ),
    path('delete-gender/<int:id>/',views.genderDelete, name='delete-gender' ),







    # ORDERS DETAILS
    path('orders-table/',views.orders_table, name='admin-orders-table' ),
    path('orders/<int:order_id>/', views.order_details, name='admin-order-details'),


    # COUPEN SECTION
    path('coupen-table/',views.coupen_section, name='coupen-list' ),
    path('coupen-add/',views.add_coupon, name='coupen-add' ),
    path('coupon-edit/<int:id>/', views.edit_coupon, name='coupon-edit'),
    path('coupon-delete/<int:id>/', views.delete_coupon, name='coupon-delete'),



    # OFFER SECTION 
    path('offer-table/',views.offer_list, name='offer-list' ),
    path('offer-add/',views.add_offer, name='offer-add' ),
    path('offer-table/<int:offer_id>/edit/',views.edit_offer, name='offer-edit' ),
    path('offer-table/<int:offer_id>/delete/',views.delete_offer, name='offer-delete' ),




    # PRODUCT OFFER
    path('product-offer-add/',views.add_product_offer, name='product-offer-add' ),
    path('product-offer-delete/<int:offer_id>/',views.delete_product_offer, name='product-offer-delete' ),
    path('product-offer-edit/<int:offer_id>/',views.edit_product_offer, name='product-offer-edit' ),



    path('sales-report/',views.sales_report, name='sales-report' ),


]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)