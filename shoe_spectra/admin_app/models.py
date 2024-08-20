from django.db import models
from django.contrib.auth.models import User

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

    def get_total_price(self):
        return self.variant.product.price * self.quantity
    






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

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Link directly to the User model
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Credit Card')

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


    def __str__(self):
        return f'{self.quantity} x {self.product_size.variant.product.name} (Size: {self.product_size.size}) in Order {self.order.id}'







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