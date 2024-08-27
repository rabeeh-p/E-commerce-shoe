from django.shortcuts import render,redirect,get_object_or_404
from admin_app.models import *
from decimal import Decimal
from django.http import HttpResponseBadRequest

from django.contrib import messages

import razorpay
from django.conf import settings

import json
from django.contrib.auth import authenticate, login,logout as logout_fn




from django.http import JsonResponse
# Create your views here.






def cart_page(request):

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    print('cart pageeee')

    if request.user.is_authenticated:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all()  
    else:
        cart_items = []  

    total_price = 0

    for item in cart_items:
        # Access the product variant
        variant = item.variant
        product = variant.product  # Assuming each ProductVariant has a reference to Product

        # Get the active offer for the product
        active_offer = product.get_active_offer()

        if active_offer:
            # Calculate discounted price
            discounted_price = product.price - (product.price * (active_offer.discount_percentage / 100))
            item_total_price = discounted_price * item.quantity
        else:
            discounted_price = product.price
            item_total_price = discounted_price * item.quantity
        
        total_price += item_total_price
        item.discounted_price = discounted_price  # Pass discounted price to template
        item.total_price = item_total_price  # Optional: For display purposes

    print(total_price, 'total price')

    return render(request, 'cart.html', {
        'cart_items': cart_items, 
        'total_price': total_price, 
        'page': 'Cart'
    })



def wishlist(request):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    wishlist_items = Wishlist.objects.filter(user=request.user)
    
    # active_wishlist_items = wishlist_items.filter(product__status=True)
    active_wishlist_items = wishlist_items.filter(
        product__status=True,
        product__brand__status=True,
        product__category__status=True
    )
    # 
    return render(request, 'wishList.html',{'wishlist_items': active_wishlist_items})



def add_to_wishlist(request, id):
    
    product = Product.objects.get(id=id)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    if wishlist_item:
        wishlist_item.delete()
    else:
        Wishlist.objects.create(user=request.user, product=product)
    return redirect('wishList-page')












def add_to_cart(request, variant_id):
        print("Adding to cart...")

        if request.method == "POST":
            print("POST request received")

            variant = get_object_or_404(ProductVariant, id=variant_id)
            print(f"Variant ID: {variant_id}, Variant: {variant}")

            size_id = request.POST.get('size')
            selected_size = get_object_or_404(ShoeSize, id=size_id)
            print(f"Size ID: {size_id}, Selected Size: {selected_size}")

            cart, created = Cart.objects.get_or_create(user=request.user)
            print(f"Cart created: {created}, Cart: {cart}")

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
                size=selected_size,
                defaults={'quantity': 1}
            )
            print(f"Cart item created: {created}, Cart Item: {cart_item}")

            if not created:
                cart_item.quantity += 1
                cart_item.save()
                print(f"Updated cart item quantity: {cart_item.quantity}")

            product = variant.product
            active_offer = product.get_active_offer() 
            if active_offer:
                discounted_price = product.price - (product.price * (active_offer.discount_percentage / 100))
            else:
                discounted_price = product.price
            
            cart_item.discounted_price = discounted_price
            cart_item.save()

            return redirect('cart-page')

        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


    



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












# def update_cart_item_quantity(request, item_id):
    
#     print('Updating is working')
#     if request.method == 'POST':
#         cart_item = get_object_or_404(CartItem, id=item_id)
#         new_quantity = int(request.POST.get('quantity'))

#         product_size = ProductSize.objects.get(variant=cart_item.variant, size=cart_item.size)

#         if new_quantity > product_size.quantity:
#             return JsonResponse({
#                 'success': False,
#                 'message': f"Only {product_size.quantity} items in stock for this size."
#             }, status=400)

#         cart_item.quantity = new_quantity
#         cart_item.save()

#         variant = cart_item.variant
#         product = variant.product

#         active_offer = product.get_active_offer()
#         if active_offer:
#             discounted_price = product.price * (1 - active_offer.discount_percentage / 100)
#         else:
#             discounted_price = product.price

#         item_subtotal = new_quantity * discounted_price

#         cart = cart_item.cart
#         cart_total = 0
#         for item in cart.items.all():
#             variant = item.variant
#             product = variant.product
#             active_offer = product.get_active_offer()
#             if active_offer:
#                 discounted_price = product.price * (1 - active_offer.discount_percentage / 100)
#             else:
#                 discounted_price = product.price
#             cart_total += item.quantity * discounted_price

#         return JsonResponse({
#             'success': True,
#             'itemSubtotal': item_subtotal,
#             'cartTotal': cart_total,
#         })

#     return JsonResponse({'success': False}, status=400)




def update_cart_item_quantity(request, item_id):

    print(item_id,'idddd')
    if request.method == 'POST':
        try:
            # Get the cart item
            cart_item = get_object_or_404(CartItem, id=item_id)
            new_quantity = int(request.POST.get('quantity', 0))

            # print(new_quantity,'new quantity')

            if new_quantity < 1:
                return JsonResponse({
                    'success': False,
                    'message': "Quantity must be at least 1."
                }, status=400)

            product_size = ProductSize.objects.get(variant=cart_item.variant, size=cart_item.size)

            print(product_size.quantity,'quantity')
            print(product_size,'sizse')
            print(new_quantity,'new quantityh')

            if new_quantity > product_size.quantity:
                print('workingg')
                print(new_quantity,'new quantitytyyyyyyyyy')
                print(product_size.quantity,'product sizeseeee')
                return JsonResponse({
                    'success': False,
                    'message': f"Only {product_size.quantity} items in stock for this size."
                }, status=400)
            current_cart_quantity = cart_item.quantity
            if new_quantity > product_size.quantity:
                print('one 2222222222222222222222222222')
                return JsonResponse({
                    'success': False,
                    'message': f"Only {product_size.quantity} items in stock for this size."
                }, status=400)
            cart_item.quantity = new_quantity
            cart_item.save()

            variant = cart_item.variant
            product = variant.product

            active_offer = product.get_active_offer()
            discounted_price = product.price * (1 - active_offer.discount_percentage / 100) if active_offer else product.price

            item_subtotal = new_quantity * discounted_price

            # Calculate total for all items in the cart
            cart_total = 0
            for item in cart_item.cart.items.all():
                variant = item.variant
                product = variant.product
                active_offer = product.get_active_offer()
                discounted_price = product.price * (1 - active_offer.discount_percentage / 100) if active_offer else product.price
                cart_total += item.quantity * discounted_price
            print('one 5555')
            return JsonResponse({
                'success': True,
                'itemSubtotal': item_subtotal,
                'cartTotal': cart_total
            })
        except ProductSize.DoesNotExist:
            print('one 7')

            return JsonResponse({'success': False, 'message': 'Product size not found.'}, status=400)
        except Exception as e:
            print('one 9')

            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)


def get_item_stock_quantity(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id)
        variant = cart_item.variant
        size = cart_item.size

        product_size = ProductSize.objects.get(variant=variant, size=size)
        stock_quantity = product_size.quantity

        return JsonResponse({'stockQuantity': stock_quantity})
    except CartItem.DoesNotExist:
        return JsonResponse({'stockQuantity': 0}, status=404)
    except ProductSize.DoesNotExist:
        return JsonResponse({'stockQuantity': 0}, status=404)


# ADDED DISCOUNT
# def checkoutPage(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     cart_items = cart.items.all()

#     # Calculate subtotal
#     # subtotal = sum(Decimal(item.get_total_price()) for item in cart_items)
#     subtotal = Decimal('0.00')
#     for item in cart_items:
#         variant = item.variant
#         product = variant.product
        
#         # Get the active offer for the product
#         active_offer = product.get_active_offer()
#         if active_offer:
#             discounted_price = product.price - (product.price * (active_offer.discount_percentage / 100))
#         else:
#             discounted_price = product.price
        
#         # Update subtotal with discounted price
#         subtotal += Decimal(discounted_price) * item.quantity
        
#         # Add to cart item for the template
#         item.discounted_price = discounted_price  # Add discounted price
#         item.original_price = product.price  # Add original price
#     coupon_discount = Decimal('0.00')


#     final_price = subtotal

#     if request.method == 'POST':
#         payment_method = request.POST.get('selector')
#         shipping_address_id = request.POST.get('address_id')

#         # Check if the user has applied a coupon
#         if 'applied_coupon' in request.session:
#             coupon_data = request.session.get('applied_coupon')
#             coupon_code = coupon_data.get('code')

#             try:
#                 coupon = Coupon.objects.get(code=coupon_code, active=True)

#                 # Check if the coupon is still valid
#                 if coupon.expiry_date >= timezone.now():
#                     coupon_discount = (Decimal(coupon.discount_percentage) / Decimal('100')) * subtotal
#                     final_price = subtotal - coupon_discount

#             except Coupon.DoesNotExist:
#                 coupon_discount = Decimal('0.00')
#                 final_price = subtotal

#         # Retrieve shipping address or create a new one
#         if shipping_address_id:
#             address = get_object_or_404(Address, id=shipping_address_id)
#         else:
#             address = Address.objects.create(
#                 user=user,
#                 address_line1=request.POST.get('address_line1'),
#                 address_line2=request.POST.get('address_line2'),
#                 city=request.POST.get('city'),
#                 state=request.POST.get('state'),
#                 country=request.POST.get('country'),
#                 postal_code=request.POST.get('postal_code'),
#                 phone_number=request.POST.get('phone_number'),
#                 fullname=request.POST.get('fullname')
#             )

#         if payment_method == 'Razorpay':
#             client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
#             razorpay_order = client.order.create({
#                 'amount': int(final_price * 100),  # Convert to paise
#                 'currency': 'INR',
#                 'payment_capture': '1'
#             })

#             request.session['razorpay_order_id'] = razorpay_order['id']
#             request.session['razorpay_amount'] = int(final_price * 100)
#             request.session['cart_items'] = json.dumps([item.id for item in cart_items])
#             request.session['total_price'] = str(final_price)
#             request.session['address'] = address.id

#             temp_order = Order.objects.create(
#                 user=user,
#                 address=address,
#                 original_price=subtotal,
#                 discounted_price=coupon_discount,
#                 final_price=final_price,
#                 payment_method=payment_method,
#                 total_amount=final_price,
#                 status='CANCELED',
#                 payment_success=False
#             )
#             request.session['order_id'] = temp_order.id

#             for cart_item in cart_items:
#                 product_size = cart_item.variant.sizes.get(size=cart_item.size)

#                 if product_size.quantity >= cart_item.quantity:
#                     product_size.quantity -= cart_item.quantity
#                     if product_size.quantity == 0:
#                         product_size.status = False
#                     product_size.save()

#                     OrderItem.objects.create(
#                         order=temp_order,
#                         product_size=product_size,
#                         quantity=cart_item.quantity
#                     )

#             OrderAddress.objects.create(
#                 order=temp_order,
#                 address_line1=address.address_line1,
#                 address_line2=address.address_line2,
#                 city=address.city,
#                 state=address.state,
#                 country=address.country,
#                 postal_code=address.postal_code,
#                 phone_number=address.phone_number,
#                 fullname=address.fullname
#             )

#             return redirect('razo-payment-method')

#         else:
#             order = Order.objects.create(
#                 user=user,
#                 address=address,
#                 original_price=subtotal,
#                 discounted_price=coupon_discount,
#                 final_price=final_price,
#                 payment_method=payment_method,  # E.g., 'COD' for cash on delivery
#                 total_amount=final_price,
#                 status='Pending'
#             )

#             OrderAddress.objects.create(
#                 order=order,
#                 address_line1=address.address_line1,
#                 address_line2=address.address_line2,
#                 city=address.city,
#                 state=address.state,
#                 country=address.country,
#                 postal_code=address.postal_code,
#                 phone_number=address.phone_number,
#                 fullname=address.fullname
#             )

#             for cart_item in cart_items:
#                 product_size = cart_item.variant.sizes.get(size=cart_item.size)

#                 if product_size.quantity >= cart_item.quantity:
#                     product_size.quantity -= cart_item.quantity
#                     if product_size.quantity == 0:
#                         product_size.status = False
#                     product_size.save()

#                     OrderItem.objects.create(
#                         order=order,
#                         product_size=product_size,
#                         quantity=cart_item.quantity
#                     )

#             Cart.objects.filter(user=user).delete()
#             request.session.pop('applied_coupon', None)

#             return redirect('order_success', order_id=order.id)

#     addresses = Address.objects.filter(user=user)
#     coupons = Coupon.objects.filter(active=True)

#     context = {
#         'cart_items': cart_items,
#         'addresses': addresses,
#         'subtotal': subtotal,
#         'total_price': final_price,
#         'coupon_discount': coupon_discount,
#         'coupons': coupons
#     }

#     return render(request, 'checkout.html', context)



# LATES ONE 
def checkoutPage(request):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')
    user = request.user
    cart = Cart.objects.get(user=user)

    cart_items = cart.items.all()
    items_removed = False

    for item in cart_items:
        variant = item.variant  
        product = variant.product 
        
        if not product.status:
            item.delete()
            items_removed = True
            messages.info(request, f'Product "{product.name}" was removed from your cart because it is inactive.')
            continue  
        
        if not variant.status:
            item.delete()
            items_removed = True
            messages.info(request, f'Product variant "{variant.product.name}" was removed from your cart because it is inactive.')
            continue 
        
        if ProductSize.objects.filter(variant=variant, status=False).exists():
            item.delete()
            items_removed = True
            messages.info(request, f'Product variant "{variant.product.name}" was removed from your cart because it has inactive sizes.')
    
    if items_removed:
        return redirect('checkout-page')
    if not cart.items.exists():
        return redirect('index-page')

    subtotal = Decimal('0.00')
    coupon_discount = Decimal('0.00')
    for item in cart_items:
        variant = item.variant
        product = variant.product
        
        active_offer = product.get_active_offer()
        if active_offer:
            discounted_price = product.price - (product.price * (active_offer.discount_percentage / 100))
        else:
            discounted_price = product.price
        
        subtotal += Decimal(discounted_price) * item.quantity
        
        item.discounted_price = discounted_price 
        item.original_price = product.price  

    final_price = subtotal
    print(final_price,'final price first')

    if request.method == 'POST':
        payment_method = request.POST.get('selector')
        shipping_address_id = request.POST.get('address_id')

        if 'applied_coupon' in request.session:
            coupon_data = request.session.get('applied_coupon')
            coupon_code = coupon_data.get('code')
            print('counpen is workig1')

            try:
                coupon = Coupon.objects.get(code=coupon_code, active=True)

                if coupon.expiry_date >= timezone.now():
                    coupon_discount = (Decimal(coupon.discount_percentage) / Decimal('100')) * subtotal
                    final_price = subtotal - coupon_discount
                    print('coupenn second is working 2')

            except Coupon.DoesNotExist:
                coupon_discount = Decimal('0.00')
                final_price = subtotal

        if shipping_address_id:
            address = get_object_or_404(Address, id=shipping_address_id)
        else:
            address = Address.objects.create(
                user=user,
                address_line1=request.POST.get('add1'),
                address_line2=request.POST.get('add2'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                country=request.POST.get('country'),
                postal_code=request.POST.get('zip'),
                phone_number=request.POST.get('number'),
                fullname=request.POST.get('name')
            )


        if payment_method == 'Razorpay':
            client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
            razorpay_amount = int(final_price * 100)  


            print(razorpay_amount,'razo amounttttttttt')
            print(final_price,'final amounttttttttt')

            razorpay_order = client.order.create({
                'amount': razorpay_amount, 
                'currency': 'INR',
                'payment_capture': '1'
            })

            request.session['razorpay_order_id'] = razorpay_order['id']
            request.session['razorpay_amount'] = razorpay_amount
            request.session['cart_items'] = json.dumps([item.id for item in cart_items])
            request.session['total_price'] = str(final_price)
            request.session['address'] = address.id

            temp_order = Order.objects.create(
                user=user,
                address=address,
                original_price=subtotal,
                discounted_price=coupon_discount,
                final_price=final_price,
                payment_method=payment_method,
                total_amount=final_price,
                status='CANCELED',
                payment_success=False
            )
            request.session['order_id'] = temp_order.id

            for cart_item in cart_items:
                product_size = cart_item.variant.sizes.get(size=cart_item.size)

                if product_size.quantity >= cart_item.quantity:
                    product_size.quantity -= cart_item.quantity
                    if product_size.quantity == 0:
                        product_size.status = False
                    product_size.save()

                    # OrderItem.objects.create(
                    #     order=temp_order,
                    #     product_size=product_size,
                    #     quantity=cart_item.quantity,
                        
                    # )
                    order_item = OrderItem.objects.create(
                        order=temp_order,
                        product_size=product_size,
                        quantity=cart_item.quantity
                    )
                    order_item.final_price = order_item.calculate_final_price()
                    order_item.save()

            OrderAddress.objects.create(
                order=temp_order,
                address_line1=address.address_line1,
                address_line2=address.address_line2,
                city=address.city,
                state=address.state,
                country=address.country,
                postal_code=address.postal_code,
                phone_number=address.phone_number,
                fullname=address.fullname
            )

            return redirect('razo-payment-method')

        else:
            order = Order.objects.create(
                user=user,
                address=address,
                original_price=subtotal,
                discounted_price=coupon_discount,
                final_price=final_price,
                payment_method='Cash on Delivery',  
                total_amount=final_price,
                status='Pending'
            )

            OrderAddress.objects.create(
                order=order,
                address_line1=address.address_line1,
                address_line2=address.address_line2,
                city=address.city,
                state=address.state,
                country=address.country,
                postal_code=address.postal_code,
                phone_number=address.phone_number,
                fullname=address.fullname
            )

            for cart_item in cart_items:
                product_size = cart_item.variant.sizes.get(size=cart_item.size)

                if product_size.quantity >= cart_item.quantity:
                    product_size.quantity -= cart_item.quantity
                    if product_size.quantity == 0:
                        product_size.status = False
                    product_size.save()

                    # OrderItem.objects.create(
                    #     order=order,
                    #     product_size=product_size,
                    #     quantity=cart_item.quantity,
                        
                    # )
                    order_item = OrderItem.objects.create(
                        order=order,
                        product_size=product_size,
                        quantity=cart_item.quantity
                    )
                    order_item.final_price = order_item.calculate_final_price()
                    order_item.save()

            Cart.objects.filter(user=user).delete()
            request.session.pop('applied_coupon', None)

            return redirect('order_success', order_id=order.id)

    addresses = Address.objects.filter(user=user)
    coupons = Coupon.objects.filter(active=True)
    print("coupens are",coupons)
    for i in coupons:
        print(i.code)

    context = {
        'cart_items': cart_items,
        'addresses': addresses,
        'subtotal': subtotal,
        'total_price': final_price,
        'coupon_discount': coupon_discount,
        'coupons': coupons
    }

    return render(request, 'checkout.html', context)



# OLD ONE IS WORKING
# def razorpay_payment(request):
#     print("is working raaa")
#     order_id = request.session.get('order_id')
#     razorpay_order_id = request.session.get('razorpay_order_id')
#     razorpay_amount = request.session.get('razorpay_amount')

#     context = {
#         'razorpay_order_id': razorpay_order_id,
#         'razorpay_merchant_key': settings.RAZORPAY_API_KEY,
#         'razorpay_amount': razorpay_amount,
#         'order_id': order_id,
#     }

#     # return render(request, 'razorpay_payment.html', context)
#     return render(request, 'razo_payment.html', context)



def razorpay_payment(request):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')
    print("Razorpay payment initialization")
    
    order_id = request.session.get('order_id')
    razorpay_order_id = request.session.get('razorpay_order_id')
    razorpay_amount = request.session.get('razorpay_amount')

    if not all([order_id, razorpay_order_id, razorpay_amount]):
        print("Missing session data for Razorpay payment")
        return redirect('checkout-page')



    context = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_merchant_key': settings.RAZORPAY_API_KEY,
        'razorpay_amount': razorpay_amount,
        'order_id': order_id,
    }
    return render(request, 'razo_payment.html', context)





# OLD ONE IS WORKING
# def razorpay_payment_verify(request):
#     print('razo verify is working')
#     if request.method == 'POST':
#         print('rzo post method is working ')
#         data = json.loads(request.body)
#         razorpay_payment_id = data.get('razorpay_payment_id')
#         razorpay_order_id = data.get('razorpay_order_id')
#         razorpay_signature = data.get('razorpay_signature')
#         order_id = data.get('order_id')

#         print(data,'dataaa')
#         print(razorpay_payment_id,'razorpay_payment_id')
#         print(razorpay_order_id,'razorpay_order_id')
#         print(razorpay_signature,'razorpay_signature')
#         print(order_id,'order_id')
        
#         # Initialize Razorpay client
#         razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_KEY_SECRET))

#         # Verify the payment signature
#         try:
#             razorpay_client.utility.verify_payment_signature({
#                 'razorpay_order_id': razorpay_order_id,
#                 'razorpay_payment_id': razorpay_payment_id,
#                 'razorpay_signature': razorpay_signature
#             })
#         except Exception as e:
#             # Handle verification failure
#             return JsonResponse({'status': 'error', 'message': str(e)})

#         # Update order status
#         try:
#             order = Order.objects.get(id=order_id)
#             order.status = 'Completed'
#             order.save()
            
#             # Redirect to the success page
#             return JsonResponse({'status': 'success', 'order_id': order.id})
#         except Order.DoesNotExist:
#             return JsonResponse({'status': 'error', 'message': 'Order does not exist', 'order_id': order_id})
    
#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



def razorpay_payment_verify(request):
    print('Razorpay payment verification')
    
    if request.method == 'POST':
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        order_id = data.get('order_id')

        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            # Update order status if the signature is valid
            order = Order.objects.get(id=order_id)
            order.status = 'Pending'
            order.payment_success = True
            order.save()

            # Remove session data
            request.session.pop('order_id', None)
            request.session.pop('razorpay_order_id', None)
            request.session.pop('razorpay_amount', None)
            

            # Handle cart items
            cart_items = json.loads(request.session.get('cart_items', '[]'))
            print(cart_items, 'cart items')

            cart = Cart.objects.get(user=order.user)

            # for item_id in cart_items:
            #     cart_item = CartItem.objects.get(id=item_id)
            #     product_size = cart_item.variant.sizes.get(size=cart_item.size)

            #     if product_size.quantity >= cart_item.quantity:
            #         product_size.quantity -= cart_item.quantity
            #         if product_size.quantity == 0:
            #             product_size.status = False
            #         product_size.save()

            #         OrderItem.objects.create(
            #             order=order,
            #             product_size=product_size,
            #             quantity=cart_item.quantity
            #         )

            Cart.objects.filter(user=order.user).delete()  # Clear the cart

            request.session.pop('cart_items', None) 

            applied_coupon = request.session.get('applied_coupon')
            if applied_coupon:
                coupon_code = applied_coupon.get('code')
                coupon = get_object_or_404(Coupon, code=coupon_code)
                if coupon.is_valid() and not CouponUsage.objects.filter(user=order.user, coupon=coupon).exists():
                    # Create CouponUsage record
                    CouponUsage.objects.create(user=order.user, coupon=coupon)
                    # Clear coupon from session after usage
                    request.session.pop('applied_coupon', None)

            return JsonResponse({'status': 'success', 'order_id': order.id})

        except Exception as e:
            print(f"Verification failed: {str(e)}")
            # If verification fails, delete the order
            Order.objects.filter(id=order_id).delete()
            return JsonResponse({'status': 'error', 'message': 'Payment verification failed', 'details': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})










# def apply_coupon(request):
#     print('apply coupen')
#     if request.method == 'POST':
#         print('is post method is working')
#         # Extract coupon code and subtotal from POST data
#         coupon_code = request.POST.get('coupon_code')
#         subtotal = float(request.POST.get('subtotal', 0))  # Default to 0 if not provided

#         print(coupon_code,'codeee')
#         print(subtotal,'codeee')

#         # Initialize the response dictionary
#         response = {
#             'valid': False,
#             'message': '',
#             'coupon_discount': 0,
#             'total_price': subtotal
#         }

#         try:
#             # Fetch the coupon from the database
#             coupon = Coupon.objects.get(code=coupon_code, active=True)
            
#             # Check if the coupon is expired
#             if coupon.expiry_date < timezone.now():
#                 response['message'] = 'Coupon has expired.'
#             else:
#                 # Calculate the discount and total price
#                 coupon_discount = (coupon.discount_percentage / 100) * subtotal
#                 total_price = subtotal - coupon_discount


#                 request.session['applied_coupon'] = {
#                     'code': coupon_code,
#                     'discount_percentage': coupon.discount_percentage,
#                     'coupon_discount': float(coupon_discount),  # convert to float for JSON serialization
#                 }

#                 # Update response
#                 response.update({
#                     'valid': True,
#                     'coupon_discount': coupon_discount,
#                     'total_price': total_price
#                 })
#         except Coupon.DoesNotExist:
#             response['message'] = 'Invalid coupon code.'

#         return JsonResponse(response)

#     return JsonResponse({'valid': False, 'message': 'Invalid request method.'})


def apply_coupon(request):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    print('apply coupon')
    
    if request.method == 'POST':
        print('is POST method working')
        
        coupon_code = request.POST.get('coupon_code')
        subtotal = float(request.POST.get('subtotal', 0))  

        print(coupon_code, 'codeee')
        print(subtotal, 'subtotal')

        response = {
            'valid': False,
            'message': '',
            'coupon_discount': 0,
            'total_price': subtotal
        }

        if subtotal < 5000:
            response['message'] = 'Coupon can only be applied for orders above ₹5000.'
            return JsonResponse(response)

        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            
            if coupon.expiry_date < timezone.now():
                response['message'] = 'Coupon has expired.'
            else:
                if CouponUsage.objects.filter(user=request.user, coupon=coupon).exists():
                    response['message'] = 'Coupon has already been used.'
                else:
                    coupon_discount = (coupon.discount_percentage / 100) * subtotal
                    total_price = subtotal - coupon_discount

                    request.session['applied_coupon'] = {
                        'code': coupon_code,
                        'discount_percentage': coupon.discount_percentage,
                        'coupon_discount': float(coupon_discount),  
                    }

                    # Update response
                    response.update({
                        'valid': True,
                        'coupon_discount': coupon_discount,
                        'total_price': total_price
                    })
        except Coupon.DoesNotExist:
            response['message'] = 'Invalid coupon code.'

        return JsonResponse(response)

    return JsonResponse({'valid': False, 'message': 'Invalid request method.'})









def order_success(request, order_id):
    print(order_id,'order idddddd')

    return render(request, 'orders_success.html', {'order_id': order_id})

def conform(request):

    print('haiiii')

    return render(request,'conform.html')