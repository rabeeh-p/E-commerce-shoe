from django.shortcuts import render,redirect
from django.contrib.auth. models import User
from django.contrib import messages
from .utilities import generate_otp,send_otp_email
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate, login,logout as logout_fn
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import update_session_auth_hash

from django.http import JsonResponse
from django.template.loader import render_to_string

from admin_app.models import *
from django.db.models import Count, Q, F,Min, Max
import re



from .forms import UserProfileForm

# Create your views here.

# USER HOME PAGE
def indexPage(request):

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            
            
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    cart_item_count = 0

    if request.user.is_authenticated:
        # CART COUNT
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item_count = cart.items.count()
        print(cart_item_count,'counttttt')

        profile_exists = UserProfile.objects.filter(user=request.user).exists()
        if not profile_exists:
            return redirect('profile-form')
        print(f'User: {request.user.username}, Profile Exists: {profile_exists}')

        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
        user_wishlist=[]

    if request.user.is_superuser:
        return redirect('admin-page')
    
    print(request.user)

    products = Product.objects.filter(
        status=True,
        variants__status=True,
        variants__sizes__quantity__gt=0
    ).annotate(
        active_variant_count=Count('variants', filter=Q(variants__status=True)),
        active_size_count=Count('variants__sizes', filter=Q(variants__sizes__status=True, variants__sizes__quantity__gt=0))
    ).filter(
        active_variant_count__gt=0,
        active_size_count__gt=0 
    ).distinct().order_by('-updated_at')



    return render(request,'index.html',{'product': products,'user_wishlist':user_wishlist,'cart_item_count':cart_item_count})



# login page
def loginPage(request):


    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin-page')  
        else:
            return redirect('index-page')
    
    if request.method == 'POST':
        username = request.POST['name']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        
        if user is not None:  
            login(request, user)
            return redirect('profile-form')  # Redirect 
        else:
            
            messages.error(request,'Invalid username or password')
            return render(request, 'login.html',)


    return render(request,'login.html',{'page':'Login'})



# logout function

def logout(request):
    logout_fn(request)
    return redirect('index-page')



# register
def registerPage(request):
    if request.session.get('otp_verified') :
        if request.session.get('otp_verified') == False:
            return redirect('otp-page') 

    if request.method == 'POST':
        print('register page')
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if len(username.strip()) == 0:
            messages.error(request, 'Username is required and cannot be just spaces.')
            return redirect('register-page')
        if len(email.strip()) == 0:
            messages.error(request, 'Email is required.')
            return redirect('register-page')
        if len(password.strip()) == 0:
            messages.error(request, 'Password is required.')
            return redirect('register-page')
        
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            messages.error(request, 'Please enter a valid email address.')
            return redirect('register-page')
        

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('register-page')
        

        
        request.session['user_data'] = {
            'username': username,
            'email': email,
            'password': password
        }

        
        otp = generate_otp()
        request.session['otp'] = otp
        request.session['otp_created_at'] = timezone.now().isoformat()  
        send_otp_email(email, otp)

        request.session['otp_verified'] = False

        return redirect('otp-page')

    return render(request,'register.html',{'page':'Register'})



OTP_EXPIRATION_MINUTES = 5

# OTP PAGE
def otpPage(request):


    if request.method == 'POST':
        otp1 = request.POST.get('otp1')
        otp2 = request.POST.get('otp2')
        otp3 = request.POST.get('otp3')
        otp4 = request.POST.get('otp4')
        otp5 = request.POST.get('otp5')
        otp6 = request.POST.get('otp6')
       
        
        
        otp_input = otp1 + otp2 + otp3 + otp4 + otp5 + otp6

        otp_created_at = timezone.datetime.fromisoformat(request.session.get('otp_created_at'))  

        
        if timezone.now() > otp_created_at + timedelta(minutes=OTP_EXPIRATION_MINUTES):
            messages.error(request, 'OTP has expired. Please register again.')
            return redirect('register-page')

        if otp_input == request.session.get('otp'):
            user_data = request.session.get('user_data')
            if user_data:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                )
                user.set_password(user_data['password'])
                user.is_verified = True
                user.save()
                messages.success(request, 'OTP verified and user registered successfully.')
                request.session['otp_verified'] = True
                return redirect('login-page')
        else:
            # OTP verification failed
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'otp.html', {'page': 'OTP','otp_expiration_time': otp_created_at + timedelta(minutes=OTP_EXPIRATION_MINUTES)}) 
        
    otp_expiration_time = request.session.get('otp_created_at')
    if otp_expiration_time:
        otp_expiration_time = timezone.datetime.fromisoformat(otp_expiration_time) + timedelta(minutes=OTP_EXPIRATION_MINUTES)

    return render(request,'otp.html',{'page':'OTP','otp_expiration_time': otp_expiration_time})




# resend OTP
def resend_otp(request):
    user_data = request.session.get('user_data')
    print('clicked resent otp')
    if user_data:
        otp = generate_otp()
        request.session['otp'] = otp
        request.session['otp_created_at'] = timezone.now().isoformat()  
        send_otp_email(user_data['email'], otp)
        messages.success(request, 'A new OTP has been sent to your email.')
    return redirect('otp-page')






# SINGLE PRODUCT

def SinglePage(request,id):
    print('first')

    obj= Product.objects.get(id=id)

    variant_items = ProductVariant.objects.filter(product=obj)

    first_item = ProductVariant.objects.filter(product=obj).first()

    images_obj= VariantImage.objects.filter(variant= first_item)
    # size_obj= ShoeSize.obj
    size_obj= ProductSize.objects.filter(variant=first_item)
    for i in size_obj:
        print(i.size,'sizeeee')

    all_out_of_stock = all(not s.status for s in size_obj)
    

    if request.user.is_authenticated:

        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
      
        user_wishlist=[]

    # all_out_of_stock = all(size.quantity <= 0 for size in sizes)

    context={
        'obj':obj,
        'variant':variant_items,
        'img':images_obj,
        'page':"Product",
        'size': size_obj,
        'user_wishlist': list(user_wishlist),
        'variant_id':first_item,
        'all_out_of_stock': all_out_of_stock,
        
        
    }


    return render(request,'singleProduct.html',context)


def SingleView(request, variantId):
    print('single viewwwwww')

    selected_variant = get_object_or_404(ProductVariant, id=variantId)
    print(selected_variant.id,'idddddd')

    variant_size_obj= ProductSize.objects.filter(variant=selected_variant)

    all_out_of_stock = all(not s.status for s in variant_size_obj)



   
    if request.user.is_authenticated:

        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
      
        user_wishlist=[]
   
    
    images = VariantImage.objects.filter(variant=selected_variant)
    static_image=images.first()

    print(selected_variant.product.id,'colorrrr')
    color_obj= ProductVariant.objects.filter(product=selected_variant.product.id)
    context = {
        'variant': {
            'name': selected_variant.product,
            'description': selected_variant.product.description,
            # 'quantity': selected_variant.quantity,
            'price': selected_variant.product.price,
            'category': selected_variant.product.category,
            'brand': selected_variant.product.brand,
            'gender': selected_variant.product.gender,
            'color':color_obj,
            'sizes':variant_size_obj,
            'variant_id':selected_variant.id
        },
        'images': images,  
        'static':static_image,
        'page':'Product',
        # 'sizes_by_variant': sizes_by_variant,
        'all_out_of_stock': all_out_of_stock,
        'user_wishlist': list(user_wishlist),
        'obj':selected_variant.product
        
    }

    return render(request, 'singleView.html', context)




# ------------------------------ PROFILE SECTION --------------------

def profile(request):

    user_details = request.user
    print(user_details)  

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            
            
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    
    try:
        address_obj = UserProfile.objects.get(user=user_details)
    except UserProfile.DoesNotExist:
        address_obj = None 

    print(address_obj.state)

    return render(request,'profile/profile.html',{'obj':address_obj,'page':'Profile'})






# FORM DETAILS
def user_profile(request):

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = None  

    
    if user_profile and not user_profile.is_active:
        messages.error(request, 'Your account is blocked. Please contact support.')
        logout(request)  
        return redirect('login-page')  

    
    if user_profile:
        return redirect('index-page')


    if request.method == 'POST':
       

        phone_number = request.POST.get('number').strip()
        fullname = request.POST.get('fullname').strip()
        address_line1_1 = request.POST.get('address').strip()
        city = request.POST.get('city').strip()
        state = request.POST.get('state').strip()
        country = request.POST.get('country').strip()
        postal_code = request.POST.get('pin').strip()
        gender = request.POST.get('gender').strip()



        errors = []

        if not phone_number:
            errors.append("Phone number cannot be empty or contain only spaces.")
        if not fullname:
            errors.append("Full name cannot be empty or contain only spaces.")
        if not address_line1_1:
            errors.append("Address cannot be empty or contain only spaces.")
        if not city:
            errors.append("City cannot be empty or contain only spaces.")
        if not state:
            errors.append("State cannot be empty or contain only spaces.")
        if not country:
            errors.append("Country cannot be empty or contain only spaces.")
        if not postal_code:
            errors.append("Postal code cannot be empty or contain only spaces.")
        if not gender:
            errors.append("Gender cannot be empty or contain only spaces.")

        if errors:
            return render(request, 'userProfile_form.html', {'errors': errors})
        else:
       
            pass

        
        user_profile = UserProfile(
            user=request.user,
            phone_number=phone_number,
            address_line1=address_line1_1,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            gender=gender,
            full_name=fullname
        )
        user_profile.save()

        return redirect('index-page') 
    
    return render(request, 'userProfile_form.html',)



def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('currentPassword').strip()
        new_password = request.POST.get('newPassword').strip()
        confirm_password = request.POST.get('confirmPassword').strip()
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change-password')
        
        if current_password == new_password:
            messages.error(request, "New password cannot be the same as the current password.")
            return redirect('change-password')

        user = authenticate(username=request.user.username, password=current_password)
        
        if user is not None:
            if len(new_password) < 5:
                messages.error(request, 'Password must be at least 5 characters long.')
                return redirect('change-password')

            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('password_change_success')
        else:
            messages.error(request, 'Current password is incorrect.')
    
    return render(request, 'profile/change_password.html')



def password_change_success(request):
    return render(request, 'profile/password_change_success.html')




def update_profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name').strip()
        phone_number = request.POST.get('phone_number').strip()
        address_line1 = request.POST.get('address_line1').strip()
        city = request.POST.get('city').strip()
        state = request.POST.get('state').strip()
        country = request.POST.get('country').strip()
        postal_code = request.POST.get('postal_code').strip()
        gender = request.POST.get('gender')

        # Validation
        if not full_name:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'Full Name cannot be empty'})
        if not phone_number:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'Phone Number cannot be empty'})
        if not address_line1:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'Address Line 1 cannot be empty'})
        if not city:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'City cannot be empty'})
        if not state:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'State cannot be empty'})
        if not country:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'Country cannot be empty'})
        if not postal_code:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'Postal Code cannot be empty'})
        if not gender:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'Gender cannot be empty'})

        # Update user profile
        user_profile.full_name = full_name
        user_profile.phone_number = phone_number
        user_profile.address_line1 = address_line1
        user_profile.city = city
        user_profile.state = state
        user_profile.country = country
        user_profile.postal_code = postal_code
        user_profile.gender = gender
        user_profile.save()

        print('last one finish')
        return redirect('profile')  
    
    context = {'user_profile': user_profile}
    return render(request, 'profile/Edit_profile_user.html', context)


def profile_orderDetails(request):
    user_orders = Order.objects.filter(user=request.user)

    context = {
        'orders': user_orders,
        'page':'Orders'
    }
    
    return render(request,'profile/order.html',context)



def order_detail(request, order_id):
    


    order = get_object_or_404(Order, id=order_id, user=request.user)

    order_items = OrderItem.objects.filter(order=order)

    all_canceled = True  

    for item in order_items:
        print(item.product_size.variant.product, 'producttttt')
        if item.status != 'CANCELED': 
            all_canceled = False  

    if all_canceled and order.status != 'CANCELED':
        order.status = 'CANCELED'
        order.save()

    context = {
        'order': order,
        'order_items': order_items,
        'page':'Order-Detail'
    }
    
    return render(request, 'profile/order_detail.html', context)




def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ['CANCELED', 'DELIVERED']:  
        order.status = 'CANCELED'
        order.save()

        for item in order.order_items.all():
            product_size = item.product_size
            product_size.quantity += item.quantity  
            if product_size.quantity > 0:
                product_size.status = True
            product_size.save()

    return redirect('profile-order')





def cancel_product(request, order_id, item_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)

    if order.status == 'Pending':
        

        product_size = order_item.product_size
        product_size.quantity = F('quantity') + order_item.quantity
        product_size.save()


        order.total_amount -= order_item.quantity * order_item.product_size.variant.product.price
        order.save()

        order_item.delete()

    return redirect('profile-order-details', order_id=order.id)


def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'profile/addressDetails.html', {'addresses': addresses,'page':'address page'})


def single_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    return render(request, 'profile/singleAddress.html', {'address': address})



def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == "POST":
        # Extract data from the request
        fullname = request.POST.get('fullname').strip()
        address_line1 = request.POST.get('address_line1').strip()
        address_line2 = request.POST.get('address_line2').strip()
        phone_number = request.POST.get('phone_number').strip()
        city = request.POST.get('city').strip()
        state = request.POST.get('state').strip()
        postal_code = request.POST.get('postal_code').strip()


        errors = {}
        if not fullname:
            errors['fullname'] = 'Full Name is required.'
        if not address_line1:
            errors['address_line1'] = 'Address Line 1 is required.'
        if not phone_number:
            errors['phone_number'] = 'Phone Number is required.'
        if not city:
            errors['city'] = 'City is required.'
        if not state:
            errors['state'] = 'State is required.'
        if not postal_code:
            errors['postal_code'] = 'ZIP Code is required.'
        
        if errors:
            return render(request, 'profile/editAddress.html', {'address': address, 'errors': errors})
        
        address.fullname = fullname
        address.address_line1 = address_line1
        address.address_line2 = address_line2
        address.phone_number = phone_number
        address.city = city
        address.state = state
        address.postal_code = postal_code
        
        address.save()
        
        return redirect('single-address', address_id=address.id)
    
    return render(request, 'profile/editAddress.html', {'address': address})




def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == "POST":
        address.delete()
        
        messages.success(request, 'Address deleted successfully.')
        
        return redirect('address-list')  
    
    return redirect('address-list')


def add_address(request):
    if request.method == "POST":
        fullname = request.POST.get('fullname').strip()
        address_line1 = request.POST.get('address_line1').strip()
        address_line2 = request.POST.get('address_line2').strip()
        phone_number = request.POST.get('phone_number').strip()
        city = request.POST.get('city').strip()
        state = request.POST.get('state').strip()
        postal_code = request.POST.get('postal_code').strip()
        
        if not fullname or not address_line1 or not phone_number or not city or not state or not postal_code:
            messages.error(request, 'All fields are required ')
            return render(request, 'profile/Add_address.html', {
                'form_data': {
                    'fullname': fullname,
                    'address_line1': address_line1,
                    'address_line2': address_line2,
                    'phone_number': phone_number,
                    'city': city,
                    'state': state,
                    'postal_code': postal_code
                }
            })
        
        
        Address.objects.create(
            user=request.user,  
            fullname=fullname,
            address_line1=address_line1,
            address_line2=address_line2,
            phone_number=phone_number,
            city=city,
            state=state,
            postal_code=postal_code
        )
        
        messages.success(request, 'Address added successfully.')
        
        return redirect('address-list')  
    else:
        return render(request, 'profile/Add_address.html')

# -------------------------------------- END PROFILE SECTION---------------------------


def shopPage(request):

    

    product_obj = Product.objects.filter(
        status=True,
        variants__status=True,
        variants__sizes__quantity__gt=0
    ).annotate(
        active_variant_count=Count('variants', filter=Q(variants__status=True)),
        active_size_count=Count('variants__sizes', filter=Q(variants__sizes__status=True, variants__sizes__quantity__gt=0))
    ).filter(
        active_variant_count__gt=0,
        active_size_count__gt=0 
    ).distinct().order_by('-updated_at')


    category_obj= Category.objects.all()
    brand_obj= Brand.objects.all()
    color_obj= Color.objects.all()


    serach_field = request.GET.get('q')
    if serach_field:
        product_obj = product_obj.filter(name__icontains=serach_field)
    product_obj = product_obj.filter(status=True)

     # =========================== FILTERING SECTION =========================
    brand_id = request.GET.get('brand')
    print(brand_id, 'branddd')
    if brand_id:
        try:
            brand_id = int(brand_id)  
            product_obj = product_obj.filter(brand_id=brand_id)
        except ValueError:
            print(f"Invalid brand_id: {brand_id}")
    
    # Apply color filter
    color_id = request.GET.get('color')
    if color_id:
        try:
            color_id = int(color_id)
            product_obj = product_obj.filter(variants__color_id=color_id).distinct()
        except ValueError:
            pass
    
    # Apply category filter (if needed)
    category_id = request.GET.get('category')
    if category_id:
        try:
            category_id = int(category_id)
            product_obj = product_obj.filter(category_id=category_id)
        except ValueError:
            pass



    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if not min_price and not max_price:
        min_price_filter = product_obj.aggregate(Min('price'))['price__min']
        max_price_filter = product_obj.aggregate(Max('price'))['price__max']
        
        if min_price_filter is not None:
            min_price = min_price_filter
        if max_price_filter is not None:
            max_price = max_price_filter

    if min_price:
        try:
            min_price = float(min_price)
            product_obj = product_obj.filter(price__gte=min_price)
        except ValueError:
            pass
    if max_price:
        try:
            max_price = float(max_price)
            product_obj = product_obj.filter(price__lte=max_price)
        except ValueError:
            pass


    # Check if the filtered products queryset is empty
    if not product_obj.exists():
        no_items_message = "No items found for the selected filters."
    else:
        no_items_message = None

    if request.user.is_authenticated:
        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
        user_wishlist=[]

    context={
        'product':product_obj,
        'category':category_obj,
        'brand': brand_obj,
        'page':'Shopping Page',
        'color':color_obj,
        'user_wishlist': list(user_wishlist),
        'no_items_message': no_items_message, 
        }

    return render(request,'ShopPage.html',context)





def filtering_items(request):

    print('filtering items is working')
    color = request.GET.get('color')
    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Start with all products
    products = Product.objects.all()

    # Apply filters if provided
    if color:
        products = products.filter(color__name=color)
    if category:
        products = products.filter(category__name=category)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Serialize product data
    product_list = list(products.values('id', 'name', 'price', 'image'))

    return JsonResponse({'products': product_list})

















