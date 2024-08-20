from django.shortcuts import render,redirect,get_object_or_404
from admin_app.models import *

from django.http import JsonResponse
# Create your views here.




def cart_page(request):
    print('cart pageeee')

    if request.user.is_authenticated:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all()  
    else:
        cart_items = []  

    print(cart_items)

    total_price = sum(item.get_total_price() for item in cart_items)  
    print(total_price,'tottel parice')

    return render(request,'cart.html',{'cart_items': cart_items, 'total_price': total_price,'page':'Cart'})



def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    for item in wishlist_items:
        print(item.product.name) 
        print(item.product.id) 
        
    # 
    return render(request, 'wishList.html',{'wishlist_items': wishlist_items})



def add_to_wishlist(request, id):
    
    product = Product.objects.get(id=id)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    if wishlist_item:
        wishlist_item.delete()
    else:
        Wishlist.objects.create(user=request.user, product=product)
    return redirect('wishList-page')









# CART ADDING
def add_to_cart(request, variant_id):
    print("working1")
    if request.method == "POST":
        print("post methodd isssss1")
        # Retrieve the product variant
        variant = get_object_or_404(ProductVariant, id=variant_id)

        size_id = request.POST.get('size')
        selected_size = get_object_or_404(ShoeSize, id=size_id)
        print(size_id,'size idddddddd')
        print(selected_size,'size idddddddd')

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,                
            variant=variant,
            size= selected_size,
            defaults={'quantity': 1}
        )

        if not created:
            cart_item.quantity += 1  
            cart_item.save()
        
        return redirect('cart-page')
    



def remove_from_cart(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id)
        cart = cart_item.cart
        cart_item.delete()

        cart_total = float(sum(item.quantity * item.variant.product.price for item in cart.items.all()))

        return JsonResponse({
            'success': True,
            'cartTotal': cart_total,
            'cartItemCount': cart.items.count()
        })
    return redirect('cart-page') 








def update_cart_item_quantity(request, item_id):
    
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id)
        print(cart_item,'cart itemmmmmmmmmmm')
        new_quantity = int(request.POST.get('quantity'))

        product_size = ProductSize.objects.get(variant=cart_item.variant,size=cart_item.size)
        print(product_size,'sizeeeee')

        if new_quantity > product_size.quantity:
            return JsonResponse({
                'success': False,
                'message': f"Only {product_size.quantity} items in stock for this size."
            }, status=400)

        # Update the cart item quantity
        cart_item.quantity = new_quantity
        cart_item.save()

        item_subtotal = cart_item.quantity * cart_item.variant.product.price

        cart = cart_item.cart
        cart_total = float(sum(item.quantity * item.variant.product.price for item in cart.items.all()))
        print(cart_total,'cart totte')
        return JsonResponse({
            'success': True,
            'itemSubtotal': item_subtotal,
            'cartTotal': cart_total,
        })

    return JsonResponse({'success': False}, status=400)








# CHECKOUT PAGE

def checkoutPage(request):

    user = request.user
    cart = Cart.objects.get(user=user) 
    cart_items = cart.items.all() 

    print(cart_items,'cartttttttt isss')
    for i in cart_items:
        print(i.cart)
    subtotal = sum(item.get_total_price() for item in cart_items)
    total_price = subtotal

    if request.method == 'POST':
        print('is workinggggggg')
        payment_method = request.POST.get('selector')
        print(payment_method,'methodddd')
        shipping_address_id = request.POST.get('address_id')  

        



        
        if shipping_address_id:
            address = get_object_or_404(Address, id=shipping_address_id)
        else:


            address_line1 = request.POST.get('add1').strip()
            address_line2 = request.POST.get('add2').strip()
            city = request.POST.get('city').strip()
            state = request.POST.get('state').strip()
            country = request.POST.get('country').strip()
            postal_code = request.POST.get('zip').strip()
            fullname = request.POST.get('name').strip()
            phone_number = request.POST.get('number').strip()


            errors = []

            # Validate postal code
            if not postal_code.isdigit() or len(postal_code) != 5:  # Adjust length as needed
                errors.append("Please enter a valid postal code (no spaces, only digits).")
            elif " " in postal_code:
                errors.append("Postal code should not contain spaces.")

            # Validate phone number
            if not phone_number.isdigit() or len(phone_number) != 10:  # Adjust length as needed
                errors.append("Please enter a valid phone number (no spaces, only digits).")
            elif " " in phone_number:
                errors.append("Phone number should not contain spaces.")

            # Validate fullname
            if "  " in fullname:
                errors.append("Full name should not contain consecutive spaces.")
            elif len(fullname) < 2:
                errors.append("Full name is too short.")

            # Validate other fields
            if len(address_line1) == 0:
                errors.append("Address line 1 cannot be empty.")
            if len(city) == 0:
                errors.append("City cannot be empty.")
            if len(state) == 0:
                errors.append("State cannot be empty.")
            if len(country) == 0:
                errors.append("Country cannot be empty.")

            if errors:
                # Return the form with errors to the user
                return render(request, 'checkout.html', {'errors': errors})
            
            address = Address.objects.create(
                user=user,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                state=state,
                country= country,
                postal_code=postal_code,
                fullname=fullname,
                phone_number=phone_number,
            )

        # Create the order
        order = Order.objects.create(
            user=user,
            address=address,  
            payment_method=payment_method,
            total_amount=sum(item.get_total_price() for item in cart_items)  
        )

       

        for cart_item in cart_items:
            product_size = cart_item.variant.sizes.get(size=cart_item.size)  
            
            # Check stock availability
            if product_size.quantity >= cart_item.quantity:
                # Update the stock
                product_size.quantity -= cart_item.quantity
                if product_size.quantity == 0:
                    product_size.status = False
                product_size.save()
                
                # Create OrderItem
                OrderItem.objects.create(
                    order=order,
                    product_size=product_size,
                    quantity=cart_item.quantity
                )
            else:
                print(f"Not enough stock for in size eorrrrrr")






        OrderAddress.objects.create(
            order=order,
            address_line1=address.address_line1,
            address_line2=address.address_line2,
            city=address.city,
            state=address.state,
            country=address.country,
            postal_code=address.postal_code,
            phone_number=address.phone_number,
            fullname= address.fullname
            
        )

        cart.items.all().delete()  

        return redirect('order_success',order_id=order.id)

    addresses = Address.objects.filter(user=user)  
    context= {
        'cart_items': cart_items,
        'addresses': addresses,
        'subtotal': subtotal,
        'total_price': total_price
    }
    
    
    return render(request, 'checkout.html',context)


def order_success(request, order_id):
    print(order_id,'order idddddd')

    return render(request, 'orders_success.html', {'order_id': order_id})

def conform(request):

    print('haiiii')

    return render(request,'conform.html')