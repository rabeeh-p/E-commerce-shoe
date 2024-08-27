from django.contrib import admin
from . models import *
# Register your models here.



admin.site.register(Gender)
admin.site.register(Category)
admin.site.register(Color)
admin.site.register(Brand)
admin.site.register(Product)
admin.site.register(ShoeSize)
admin.site.register(UserProfile)
admin.site.register(ProductVariant)
admin.site.register(VariantImage)
admin.site.register(ProductSize)
admin.site.register(Wishlist)
admin.site.register(Cart)
admin.site.register(CartItem)








admin.site.register(Address)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderAddress)





# coupen

admin.site.register(Coupon)
admin.site.register(CouponUsage)


# WALLET    
admin.site.register(Wallet)
admin.site.register(Transaction)


# BRAND OFFER
admin.site.register(Offer)

