from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from decimal import Decimal

# Create your models here.


class Gender(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50)
    status = models.BooleanField(default=True) 

    def __str__(self):
        return self.name
    


class Brand(models.Model):
    name = models.CharField(max_length=50)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    


class Offer(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='offers')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.discount_percentage}% off on {self.brand.name} (From {self.start_date} to {self.end_date})"

    def is_active(self):
        today = date.today()
        return self.start_date <= today <= self.end_date


class Color(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name
    

class ShoeSize(models.Model):
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
    ]

    size = models.CharField(max_length=3, choices=SIZE_CHOICES)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.get_size_display()


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    def __str__(self):
        return self.name
    

  


    def get_active_offer(self):
        product_offer = getattr(self, 'product_offer', None)
        if product_offer and product_offer.is_active():
            return product_offer
        
        brand_offers = self.brand.offers.filter(
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        return brand_offers.first()

    def get_discounted_price(self):
        offer = self.get_active_offer()
        if offer:
            discount = offer.discount_percentage / 100
            discounted_price = self.price * (1 - discount)
            return discounted_price
        return None


class ProductOffer(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='product_offer')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)  
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    offer_description = models.TextField(blank=True, null=True)

    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date
    
    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}% off"
    



class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')  
    color = models.ForeignKey(Color, on_delete=models.CASCADE)  
    image = models.ImageField(upload_to='variant_images/', blank=True, null=True)  

    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.color.name}  "



class VariantImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='additional_images')  
    image = models.ImageField(upload_to='variant_images/', blank=True, null=True)  
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"Image for {self.variant.product.name} - Variant {self.variant.id}"

# variant size
class ProductSize(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='sizes')
    size = models.ForeignKey(ShoeSize, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    status = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.variant.product.name} - {self.variant.color.name} - {self.size.size}"







class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    address_line1 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    full_name = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    referral_code = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'
    









# WISHLIST 
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s wishlist"
    
    
    



# CART 
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username} created on {self.created_at}"
    



class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    size = models.ForeignKey(ShoeSize, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.name}  in cart of {self.cart.user.username}"

    # def get_total_price(self):
    #     return self.variant.product.price * self.quantity

    def get_total_price(self):
        product = self.variant.product
        active_offer = product.get_active_offer()
        if active_offer:
            discounted_price = product.price - (product.price * (active_offer.discount_percentage / 100))
            return discounted_price * self.quantity
        return product.price * self.quantity
    






# ADDRESS

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    fullname = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)


    def __str__(self):
        return f'{self.user.username} - {self.address_line1}, {self.city}'




class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Credit Card', 'Credit Card'),
        ('PayPal', 'PayPal'),
        ('Cash on Delivery', 'Cash on Delivery'),
        ('Bank Transfer', 'Bank Transfer'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Credit Card')
    payment_success = models.BooleanField(default=False)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    coupon_code = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'Order {self.id} by {self.user.username}'
    



class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CANCELED', 'Canceled'),
        ('DELIVERED', 'Delivered'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product_size = models.ForeignKey(ProductSize, on_delete=models.CASCADE)  # Link to ProductSize
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


    def __str__(self):
        return f'{self.quantity} x {self.product_size.variant.product.name} (Size: {self.product_size.size}) in Order {self.order.id}'
    
   


    def calculate_final_price(self):
        product = self.product_size.variant.product
        
        active_offer = product.get_active_offer()

        if active_offer:
            discount = (product.price * active_offer.discount_percentage) / 100
            final_price = product.price - Decimal(discount)
        else:
            final_price = product.price
        
        return final_price * self.quantity







class OrderAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='address_order')
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20, blank=True)
    fullname = models.CharField(max_length=100)



    def __str__(self):
        return f"Address for Order {self.order.id} - {self.address_line1}, {self.city}, {self.state}, {self.postal_code}, {self.country}"
    






class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.FloatField()
    active = models.BooleanField(default=True)
    expiry_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)  # Add this line
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.code

    def is_valid(self):
        return self.active and self.expiry_date > timezone.now()
    



class CouponUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'coupon')

    def __str__(self):
        return f"{self.user.username} used {self.coupon.code}"
    




class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet"
    
    def add_balance(self, amount):
        """Add credit to the wallet balance."""
        self.balance += amount
        self.save()
    


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )

    TRANSACTION_PURPOSES = (
        ('purchase', 'Purchase'),
        ('refund', 'Refund'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    purpose = models.CharField(max_length=10, choices=TRANSACTION_PURPOSES)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} for {self.purpose.capitalize()} on {self.created_at}"