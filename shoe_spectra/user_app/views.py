from django.shortcuts import render,redirect
from django.contrib.auth. models import User
from django.contrib import messages
from .utilities import generate_otp,send_otp_email
from django.utils import timezone
from datetime import timedelta,datetime
from django.contrib.auth import authenticate, login,logout as logout_fn
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import update_session_auth_hash


from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache



from django.http import JsonResponse
from django.template.loader import render_to_string
from decimal import Decimal

from admin_app.models import *
from django.db.models import Count, Q, F,Min, Max
import re
import razorpay
from .utilities import generate_unique_code
from django.utils.timezone import make_aware
from django.conf import settings
import json

from .forms import UserProfileForm
from razorpay.errors import BadRequestError
# Create your views here.



# USER HOME PAGE
@never_cache
def indexPage(request):
    

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

  

    cart_item_count = 0

    if request.user.is_authenticated:
        # CART COUNT
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item_count = cart.items.count()

        profile_exists = UserProfile.objects.filter(user=request.user).exists()
        if not profile_exists:
            return redirect('profile-form')

        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
        user_wishlist=[]

    if request.user.is_superuser:
        return redirect('admin-page')
    

    products = Product.objects.filter(
        status=True,
        category__status=True,   
        brand__status=True,  
        variants__status=True,
        variants__sizes__quantity__gt=0
    ).annotate(
        active_variant_count=Count('variants', filter=Q(variants__status=True)),
        active_size_count=Count('variants__sizes', filter=Q(variants__sizes__status=True, variants__sizes__quantity__gt=0))
    ).filter(
        active_variant_count__gt=0,
        active_size_count__gt=0 
    ).distinct().order_by('-updated_at')

    now = timezone.now().date()

    for product in products:
        active_offer = product.brand.offers.filter(start_date__lte=now, end_date__gte=now).first()
        if active_offer:
            discount = active_offer.discount_percentage
            product.discounted_price = product.price * (1 - discount / 100)
        else:
            product.discounted_price = None
    
    deals = Product.objects.filter(
        product_offer__isnull=False,
        product_offer__start_date__lte=now,
        product_offer__end_date__gte=now,
        product_offer__discount_percentage__gt=0, 
        status=True, 
        brand__status=True  
    ).distinct().order_by('-product_offer__discount_percentage')[:10]


    brand_offer_products = Product.objects.filter(
        brand__offers__isnull=False,
        brand__offers__start_date__lte=now,
        brand__offers__end_date__gte=now,
        brand__offers__discount_percentage__gt=0,  
        status=True,  
        brand__status=True,  
        product_offer__isnull=True  
    ).distinct().order_by('-brand__offers__discount_percentage')[:10]   




    return render(request,'index.html',{'product': products,'user_wishlist':user_wishlist,'cart_item_count':cart_item_count,'deals': deals,'brand_offer_products': brand_offer_products})



# login page
@never_cache
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
            if user.is_superuser:
                messages.error(request, "Superadmins can't log in this way.")
                return redirect('login-page')  

            login(request, user)
            return redirect('profile-form') 

        else:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'login.html')


    return render(request,'login.html',{'page':'Login'})



# logout function

def logout(request):
    logout_fn(request)
    return redirect('index-page')



# register
def registerPage(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin-page') 
        else:
            return redirect('index-page') 



    if request.session.get('otp_verified') :
        if request.session.get('otp_verified') == False:
            return redirect('otp-page') 

    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        referral_code = request.POST.get('referral_code', '')


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
            'password': password,
            'referral_code': referral_code
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

                referral_code = user_data.get('referral_code')
                if referral_code:
                    wallet, created = Wallet.objects.get_or_create(user=user)
                    wallet.add_balance(200)  
                    
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=200,
                        transaction_type='credit',
                        purpose='welcome',
                        description='Welcome credit for signing up with referral'
                    )
                    
                    try:
                        referrer_profile = UserProfile.objects.get(referral_code=referral_code)
                        referrer_wallet, created = Wallet.objects.get_or_create(user=referrer_profile.user)
                        
                        referrer_wallet.add_balance(500)
                        Transaction.objects.create(
                            wallet=referrer_wallet,
                            amount=500,
                            transaction_type='credit',
                            purpose='referral',
                            description=f'Credit for referral code {referral_code}'
                        )
                    except UserProfile.DoesNotExist:
                        pass  

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
    if user_data:
        otp = generate_otp()
        request.session['otp'] = otp
        request.session['otp_created_at'] = timezone.now().isoformat()  
        send_otp_email(user_data['email'], otp)
        messages.success(request, 'A new OTP has been sent to your email.')
    return redirect('otp-page')






def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, 'forgot.html', {'error': 'This email is not registered.'})
        
        otp = generate_otp()
        otp_created_at = timezone.now()  
        otp_expiry_duration = timedelta(minutes=5) 
        otp_expiry_time = otp_created_at + otp_expiry_duration

        # Store OTP, email, and times in the session
        request.session['otp'] = otp
        request.session['email'] = email
        request.session['otp_created_at'] = otp_created_at.isoformat()
        request.session['otp_expiry_time'] = otp_expiry_time.isoformat()
        
        # Send OTP email
        send_otp_email(email, otp)
        return redirect('forgot-otp')
    
    return render(request, 'forgot/forgot.html')



def forgot_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        sent_otp = request.session.get('otp')
        otp_created_at_str = request.session.get('otp_created_at')
        otp_expiry_time_str = request.session.get('otp_expiry_time')

        if sent_otp is None or otp_created_at_str is None or otp_expiry_time_str is None:
            return render(request, 'forgot/forgot_otp.html', {'error': 'Session expired. Please request a new OTP.'})

        # Convert ISO 8601 strings back to datetime objects
        otp_created_at = timezone.datetime.fromisoformat(otp_created_at_str)
        otp_expiry_time = timezone.datetime.fromisoformat(otp_expiry_time_str)
        current_time = timezone.now()

        if current_time > otp_expiry_time:
            return render(request, 'forgot/forgot_otp.html', {'error': 'OTP has expired. Please request a new one.'})

        if int(entered_otp) == int(sent_otp):
            return redirect('forgot-set-newpassword')
        else:
            return render(request, 'forgot/forgot_otp.html', {'error': 'Invalid OTP'})
        
    otp_expiry_time = request.session.get('otp_expiry_time', None)
    return render(request, 'forgot/forgot_otp.html', {'otp_expiry_time': otp_expiry_time})




def set_new_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password').strip()
        confirm_password = request.POST.get('confirm_password').strip()
        email = request.session.get('email') 

        if not new_password or not confirm_password:
            messages.error(request, 'Both fields are required.')
            return render(request, 'forgot/set_new_password.html')

        if not email:
            return redirect('forgot_password')  # Redirect if no email in session
        
        if ' ' in new_password or ' ' in confirm_password:
            messages.error(request, 'Passwords should not contain spaces.')
            return render(request, 'forgot/set_new_password.html')
        

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'forgot/set_new_password.html')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'forgot/set_new_password.html')
        
        if not email:
            return redirect('forgot_password') 

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user) 
            return redirect('forgot-success')  
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return render(request, 'forgot/set_new_password.html')

    return render(request, 'forgot/set_new_password.html')


def success_forgot(request):
    return render(request,'forgot/success.html',{'page':"success"})




# SINGLE PRODUCT

def SinglePage(request,id):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')


    obj= Product.objects.get(id=id)
    # variant_items = ProductVariant.objects.filter(product=obj)
    variant_items = ProductVariant.objects.filter(product=obj, status=True)
    # first_item = ProductVariant.objects.filter(product=obj).first()
    first_item = variant_items.first()
    images_obj= VariantImage.objects.filter(variant= first_item)
    size_obj= ProductSize.objects.filter(variant=first_item)

   
    all_out_of_stock = all(not s.status for s in size_obj)


    if request.user.is_authenticated:
        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
        user_wishlist=[]

    active_offer = obj.get_active_offer()
    if active_offer:
        discounted_price = obj.price - (obj.price * (active_offer.discount_percentage / 100))
    else:
        discounted_price = obj.price


    context={
        'obj':obj,
        'variant':variant_items,
        'img':images_obj,
        'page':"Product",
        'size': size_obj,
        'user_wishlist': list(user_wishlist),
        'variant_id':first_item,
        'all_out_of_stock': all_out_of_stock,
        'active_offer': active_offer,
        'discounted_price': discounted_price,
        
        
    }


    return render(request,'singleProduct.html',context)


def SingleView(request, variantId):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)        
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')
    

    selected_variant = get_object_or_404(ProductVariant, id=variantId)

    variant_size_obj= ProductSize.objects.filter(variant=selected_variant)

    all_out_of_stock = all(not s.status for s in variant_size_obj)



   
    if request.user.is_authenticated:

        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
      
        user_wishlist=[]

    
    product = selected_variant.product

    # Active offer logic
    active_offer = product.get_active_offer()  
    if active_offer:
        discounted_price = product.price - (product.price * (active_offer.discount_percentage / 100))
    else:
        discounted_price = product.price
   
    
    images = VariantImage.objects.filter(variant=selected_variant)
    static_image=images.first()

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
        'obj':selected_variant.product,
        'discounted_price': discounted_price,
        'active_offer': active_offer,
        'variant_id':selected_variant.product.id
        
    }

    return render(request, 'singleView.html', context)




# ------------------------------ PROFILE SECTION --------------------
@never_cache
@login_required(login_url='login-page')
def profile(request):

    user_details = request.user
    if user_details.is_superuser:
        # Redirect to the admin page
        return redirect('admin-page')

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)            
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    
    try:
        address_obj = UserProfile.objects.get(user=user_details)
    except UserProfile.DoesNotExist:
        address_obj = None 


    return render(request,'profile/profile.html',{'obj':address_obj,'page':'Profile'})






# FORM DETAILS
def user_profile(request):

    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin-page')

    

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = None  

    
    

    
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

        if not phone_number or not phone_number.strip().isdigit() or len(phone_number.strip()) != 10:
            errors.append("Phone number must be exactly 10 digits long and cannot be empty or contain only spaces.")

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

        referral_code = generate_unique_code()

        
        user_profile = UserProfile(
            user=request.user,
            phone_number=phone_number,
            address_line1=address_line1_1,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            gender=gender,
            full_name=fullname,
            referral_code=referral_code
        )
        user_profile.save()

        return redirect('index-page') 
    
    return render(request, 'userProfile_form.html',)


@never_cache
@login_required(login_url='login-page')
def change_password(request):

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')






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



@never_cache
@login_required(login_url='login-page')
def update_profile(request):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')



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
        if not phone_number.isdigit() or len(phone_number) != 10:
            return render(request, 'profile/Edit_profile_user.html', {'user_profile': user_profile, 'error': 'Phone Number must be 10 digits and numeric'})
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

        return redirect('profile')  
    
    context = {'user_profile': user_profile}
    return render(request, 'profile/Edit_profile_user.html', context)


@never_cache
@login_required(login_url='login-page')
def profile_orderDetails(request):
    if request.user.is_superuser:
        return redirect('admin-page')
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    # user_orders = Order.objects.filter(user=request.user)
    user_orders = Order.objects.filter(user=request.user).order_by('-order_date')

    context = {
        'orders': user_orders,
        'page':'Orders'
    }
    
    return render(request,'profile/order.html',context)


@never_cache
@login_required(login_url='login-page')
def order_detail(request, order_id):

    if request.user.is_superuser:
        return redirect('admin-page')

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')
    

    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    all_canceled = True  

    for item in order_items:
        if item.status != 'CANCELED': 
            all_canceled = False  

    if all_canceled and order.status != 'CANCELED':
        order.status = 'CANCELED'
        order.save()

    payment_failed = order.payment_method == 'Razorpay' and not order.payment_success

    razorpay_order_id = None
    if order.status != 'CANCELED':
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
            amount_in_paise = int(order.total_amount * 100)
            razorpay_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'payment_capture': '1'
            })
            razorpay_order_id = razorpay_order['id']
        # except razorpay.errors.RazorpayError as e:
        #     print(f"Razorpay Error: {e}")  
        except razorpay.errors.BadRequestError as e:
            print(f"Razorpay BadRequestError: {e}")
        except razorpay.errors.UnauthorizedError as e:
            print(f"Razorpay UnauthorizedError: {e}")
        except razorpay.errors.ServerError as e:
            print(f"Razorpay ServerError: {e}")
        except razorpay.errors.ConnectionError as e:
            print(f"Razorpay ConnectionError: {e}")
        except Exception as e:
            print(f"Razorpay Unexpected Error: {e}")


    context = {
        'order': order,
        'order_items': order_items,
        'page':'Order-Detail',
        'payment_failed': payment_failed,
        'razorpay_order_id': razorpay_order_id ,
    }
    
    return render(request, 'profile/order_detail.html', context)




def razorpay_payment_verify_retry(request):
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

            order = get_object_or_404(Order, id=order_id)
            order.status = 'Pending'
            order.payment_success = True
            order.save()

            request.session.pop('order_id', None)
            request.session.pop('razorpay_order_id', None)
            request.session.pop('razorpay_amount', None)

            cart_items = json.loads(request.session.get('cart_items', '[]'))
            cart = Cart.objects.get(user=order.user)

            order_items = OrderItem.objects.filter(order=order)

            for order_item in order_items:
                product_size = order_item.product_size  # Using the reserved product size

                if product_size.quantity >= order_item.quantity:
                    product_size.quantity -= order_item.quantity
                    if product_size.quantity == 0:
                        product_size.status = False
                    product_size.save()
            
           
            

            # Cart.objects.filter(user=order.user).delete()  
            request.session.pop('cart_items', None)

            


            return JsonResponse({'status': 'success', 'order_id': order.id})

        except Exception as e:
            Order.objects.filter(id=order_id).delete()
            return JsonResponse({'status': 'error', 'message': 'Payment verification failed', 'details': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})




def cancel_order(request, order_id):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status not in ['CANCELED', 'DELIVERED']:

        order.status = 'CANCELED'
        
        for item in order.order_items.all():
            product_size = item.product_size
            product_size.quantity += item.quantity
            if product_size.quantity > 0:
                product_size.status = True  
            product_size.save()

        if order.payment_method == 'Razorpay':
            shipping_charge = Decimal('50.00')
            
            refund_amount = order.total_amount - shipping_charge
            refund_amount = refund_amount.quantize(Decimal('0.01'))

            wallet = request.user.wallet
            wallet.balance = F('balance') + refund_amount
            wallet.save()

            Transaction.objects.create(
                wallet=wallet,
                amount=refund_amount,
                transaction_type='credit',
                purpose='refund',
                description=f'Refund for canceled order {order.id} (excluding shipping charge)'
            )
            messages.success(request, f'₹{refund_amount} has been credited to your wallet (excluding shipping charge).')

        # order.total_amount = Decimal('50.00')
        order.save()

    else:
        messages.error(request, 'Order cannot be canceled as it is already canceled or delivered.')

    return redirect('profile-order')




def cancel_product(request, order_id, item_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)

    if order.status == 'Pending':
        product_size = order_item.product_size
        product_size.quantity = F('quantity') + order_item.quantity
        product_size.save()

        product = order_item.product_size.variant.product
        discounted_price = product.get_discounted_price()  # Ensure this is handled correctly
        product_price = discounted_price if discounted_price is not None else product.price
        item_total_price = order_item.quantity * product_price

        order_item.delete()

        subtotal = sum((item.product_size.variant.product.get_discounted_price() or item.product_size.variant.product.price) * item.quantity for item in order.order_items.all())
        shipping_charge = Decimal('50.00')
        total_amount_before_coupon = subtotal + shipping_charge

        if order.discounted_price < order.original_price and order.discounted_price > 0:
            discount_percentage = (order.original_price - order.discounted_price) / order.original_price
            item_discount = item_total_price * discount_percentage
            item_refund_amount = item_total_price - item_discount

            new_discounted_price = subtotal * (1 - discount_percentage)
        else:
            item_refund_amount = item_total_price
            new_discounted_price = subtotal  

        new_original_price = subtotal
        total_amount = new_discounted_price + shipping_charge if subtotal > 0 else shipping_charge

        order.original_price = new_original_price
        # order.discounted_price = new_discounted_price
        # order.total_amount = total_amount
        order.save()


        if order.payment_method == 'Razorpay':
            wallet = request.user.wallet
            wallet.balance = F('balance') + item_refund_amount 
            wallet.save()

            Transaction.objects.create(
                wallet=wallet,
                amount=item_refund_amount,
                transaction_type='credit',
                purpose='refund',
                description=f'Refund for canceled order item {item_id}'
            )

            messages.success(request, f'₹{item_refund_amount} has been credited to your wallet.')

        return redirect('profile-order-details', order_id=order.id)

    return redirect('profile-order-details', order_id=order.id)







@never_cache
@login_required(login_url='login-page')
def user_wallet(request):

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().order_by('-created_at') 
    
    context = {
        'balance': wallet.balance,
        'transactions': transactions,
        'page':'wallet'
    }
    return render(request,'profile/wallet.html',context)

@never_cache
@login_required(login_url='login-page')
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'profile/addressDetails.html', {'addresses': addresses,'page':'address page'})

@never_cache
@login_required(login_url='login-page')
def single_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    return render(request, 'profile/singleAddress.html', {'address': address})


@never_cache
@login_required(login_url='login-page')
def edit_address(request, address_id):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')


    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == "POST":
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
        elif not phone_number.isdigit() or len(phone_number) != 10:
            errors['phone_number'] = 'Phone Number must be exactly 10 digits.'
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

@never_cache
@login_required(login_url='login-page')
def add_address(request):
    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

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



@never_cache
@login_required(login_url='login-page')
def user_coupon_and_refferal(request):
    if request.user.is_superuser:
        return redirect('admin-page')
    user = request.user
    
    available_coupons = Coupon.objects.filter(
        active=True, 
        expiry_date__gt=timezone.now()
    ).exclude(
        id__in=CouponUsage.objects.filter(user=user).values_list('coupon_id', flat=True)
    )

    user_profile = UserProfile.objects.filter(user=user).first()

    


    return render(request, 'profile/referal.html', {'available_coupons': available_coupons,
                                                    'user_profile': user_profile,

                                                    })





def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status == 'DELIVERED':
        order.status = 'RETURNED'
        
        shipping_charge = Decimal('50.00')  
        refund_amount = order.total_amount - shipping_charge

        user_wallet, created = Wallet.objects.get_or_create(user=request.user)
        user_wallet.add_balance(refund_amount)

        Transaction.objects.create(
            wallet=user_wallet,
            amount=refund_amount,
            transaction_type='credit',
            purpose='refund',
            description=f"Refund for returned order {order.id}"
        )

        # Restock products
        for item in OrderItem.objects.filter(order=order):
            product_size = item.product_size
            product_size.quantity += item.quantity
            product_size.save()

        # Save updated order
        # order.total_amount = shipping_charge  
        order.save()

        # Redirect with a success message
        messages.success(request, "Order returned successfully and refund issued.")
        return redirect('profile-order-details', order_id=order_id)
    else:
        messages.error(request, "This order cannot be returned.")
        return redirect('profile-order-details', order_id=order_id)




    



def return_product(request, order_id, order_item_id):

    order = get_object_or_404(Order, id=order_id)

    if order.status == 'DELIVERED':
        try:
            order_item = OrderItem.objects.get(order=order, id=order_item_id)
        except OrderItem.DoesNotExist:
            messages.error(request, "This product is not part of the order or the order item ID is incorrect.")
            return redirect('profile-order-details', order_id=order_id)

        refund_amount = order_item.final_price * order_item.quantity

        user_wallet, created = Wallet.objects.get_or_create(user=request.user)

        user_wallet.add_balance(refund_amount)

        Transaction.objects.create(
            wallet=user_wallet,
            amount=refund_amount,
            transaction_type='credit',
            purpose='refund',
            description=f"Refund for product in order {order.id}"
        )

        # Adjust the product size quantity
        product_size = order_item.product_size
        product_size.quantity += order_item.quantity
        product_size.save()

        # Remove the order item
        order_item.delete()

        

        # Update order status if no items remain
        remaining_items = OrderItem.objects.filter(order=order).exists()
        if not remaining_items:
            order.status = 'RETURNED'
            order.save()

        # Show a success message
        messages.success(request, "Product returned successfully and refund issued.")
        return redirect('profile-order-details', order_id=order_id)
    else:
        messages.error(request, "This order cannot be returned.")
        return redirect('profile-order-details', order_id=order_id)
    



@never_cache
@login_required(login_url='login-page')
def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.filter(status='PENDING')  
    shipping_charge = Decimal('50.00')
    
    discount_amount = order.original_price - order.discounted_price
    
    return render(request, 'profile/invoice_bill.html', {
        'order': order,
        'order_items': order_items,
        'shipping_charge': shipping_charge,
        'discount_amount': discount_amount,
        'page':'invoice'
    })














def generate_pdf(order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.filter(status='PENDING')  # Include only non-canceled items
    shipping_charge = Decimal('50.00')  # Fixed shipping charge
    
    # Use the values from the Order model directly
    total_amount = order.total_amount
    discount_amount = order.original_price - order.discounted_price
    final_price = order.final_price
    
    # Create a PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Styles for the PDF
    styles = getSampleStyleSheet()

    # Header
    header_style = ParagraphStyle(
        'Header',
        fontSize=18,
        alignment=1,  # Centered
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    header_info_style = ParagraphStyle(
        'HeaderInfo',
        fontSize=12,
        spaceAfter=10,
        fontName='Helvetica'
    )
    
    header = (
        f"<strong>Invoice ID:</strong> {order.id}<br/>"
        f"<strong>Date:</strong> {order.order_date.strftime('%d M Y')}<br/>"
        f"<strong>Customer:</strong> {order.user.username}<br/>"
        f"<strong>Address:</strong> {order.address}"
    )
    elements.append(Paragraph("Invoice", header_style))
    elements.append(Paragraph(header, header_info_style))
    
    elements.append(Spacer(1, 12))

    # Order Details Table
    data = [['Product', 'Size', 'Quantity', 'Price', 'Total']]
    for item in order_items:
        product_price = item.product_size.variant.product.price
        total_price = product_price * item.quantity
        
        data.append([
            item.product_size.variant.product.name,
            item.product_size.size,
            item.quantity,
            f"Rs {product_price:.2f}",
            f"Rs {total_price:.2f}"
        ])
    
    table = Table(data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch, 2*inch], rowHeights=[24]*len(data))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 1), (-1, -1), 8),
        ('RIGHTPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    
    elements.append(Spacer(1, 24))
    
    # Totals
    total_style = ParagraphStyle(
        'Total',
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
        alignment=2,  # Align right
        fontName='Helvetica'
    )
    
    if order.original_price > 0:
        elements.append(Paragraph(f"Original Price: Rs {order.original_price:.2f}", total_style))
    
    if discount_amount > 0:
        elements.append(Paragraph(f"Discount: -Rs {discount_amount:.2f}", total_style))
    
    elements.append(Paragraph(f"Final Price: Rs {final_price:.2f}", total_style))
    elements.append(Paragraph(f"Shipping Charge: Rs {shipping_charge:.2f}", total_style))
    elements.append(Paragraph(f"<b>Total Amount: Rs {total_amount:.2f}</b>", total_style))
    
    elements.append(Spacer(1, 36))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        fontSize=10,
        leading=12,
        alignment=1,
        textColor=colors.grey,
        fontName='Helvetica'
    )
    footer_text = """
    Thank you for your purchase!<br/>
    For inquiries, contact us at: support@shoespectra.com<br/>
    Address: 123 Fashion Street, Malappuram, Kerala - 676505
    """
    elements.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    return buffer




def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    pdf_buffer = generate_pdf(order_id)

    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
    return response
# -------------------------------------- END PROFILE SECTION---------------------------


def shopPage(request):

    if request.user.is_authenticated:
        try:
            profile_obj = UserProfile.objects.get(user=request.user)
            if not profile_obj.is_active:
                messages.error(request, 'Your account is blocked.')
                logout_fn(request) 
                return redirect('login-page')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Profile not found.')

    

    product_obj = Product.objects.filter(
        status=True,
        category__status=True,   
        brand__status=True,  
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


    sort_order = request.GET.get('sort', 'default') 
    if sort_order == 'name_asc':
        product_obj = product_obj.order_by('name') 
    elif sort_order == 'name_desc':
        product_obj = product_obj.order_by('-name') 
    else:
        product_obj = product_obj.order_by('-updated_at') 
        

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


    
    today = date.today()
    for product in product_obj:
        offer = Offer.objects.filter(
            brand=product.brand,
            start_date__lte=today,
            end_date__gte=today
        ).first()

        if offer:
            discount_amount = (product.price * offer.discount_percentage) / 100
            product.discounted_price = round(product.price - discount_amount, 2)
        else:
            product.discounted_price = None

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

    color = request.GET.get('color')
    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    products = Product.objects.all()

    if color:
        products = products.filter(color__name=color)
    if category:
        products = products.filter(category__name=category)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    product_list = list(products.values('id', 'name', 'price', 'image'))

    return JsonResponse({'products': product_list})


