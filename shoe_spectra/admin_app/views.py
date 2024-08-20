from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login,logout as logout_fn
from django.contrib import messages
from django.contrib.auth.models import User

from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import *
from django.core.paginator import Paginator,EmptyPage, PageNotAnInteger

import base64
from django.core.files.base import ContentFile

from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
# Create your views here.


# ADMIN DASHBOARD
@never_cache
@login_required(login_url='adminLogin-page')
def adminPage(request):
    name=request.user.username
    print(name,'username issssss')
    if not request.user.is_superuser:
        return redirect('index-page')
    return render(request,'dashboard.html',{'name':name})



# ADMIN LOGIN PAGE
@never_cache
def adminLogin(request):
    if request.session.session_key:
        if request.user.is_staff:
            return redirect('admin-page')
        else:
            return redirect('adminLogin-page')


    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('admin-page')  
            else:
                messages.error(request, "your not admin ")
                return redirect('adminLogin-page')  
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, 'adminlogin.html')
        
    return render(request,'adminLogin.html')

# LOGOUT FUNCTION
def logoutAdmin(request):
    logout_fn(request)  
    return redirect('adminLogin-page')


# ADMIN PROFILE PAGE
@never_cache
@login_required(login_url='adminLogin-page')
def profilePage(request):
    print('profile')
    if not request.user.is_superuser:
        return redirect('index-page')
    return render(request,'adminProfile.html')

# users-page
@never_cache
@login_required(login_url='adminLogin-page')
def usersPage(request):
    if not request.user.is_superuser:
        return redirect('index-page')


    users_count = UserProfile.objects.aggregate(total_users=Count('id'))            
    print(users_count['total_users'])

    users_obj= UserProfile.objects.all()


    context= {
        'users':users_obj,
        'count':users_count
        }
    return render(request,'users_list.html',context)



# USER STATUS
@never_cache
@login_required(login_url='adminLogin-page')
def users_status(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_profile = get_object_or_404(UserProfile, id=user_id)
        
        
        if user_profile.is_active:
            user_profile.is_active = False
        else:
            user_profile.is_active = True
        
        user_profile.save()
    return redirect('users-page')



# PRODUCT LIST
@never_cache
@login_required(login_url='adminLogin-page')
def productList(request):

    if not request.user.is_superuser:
        return redirect('index-page')



    categories_count = Category.objects.aggregate(count=Count('id'))
    print(categories_count['count'], 'the count isss')
    brands_count= Brand.objects.aggregate(count=Count('id'))
    colors_count= Color.objects.aggregate(count=Count('id'))
    shoe_count= ShoeSize.objects.aggregate(count=Count('id'))
    product_count= Product.objects.aggregate(count=Count('id'))




    product_obj = Product.objects.select_related('category', 'brand', 'gender').order_by('-created_at')
    paginator = Paginator(product_obj, 5)



    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    
    start_index = (page_obj.number - 1) * paginator.per_page + 1
    end_index = min(start_index + paginator.per_page - 1, paginator.count)

   

    context={
        'c_count':categories_count['count'],
        'b_count':brands_count['count'],
        'color_count':colors_count['count'],
        'shoe_count':shoe_count['count'],
        'p_count':product_count['count'],
        'page_obj': page_obj,
        'start_index': start_index,
        'end_index': end_index,
        'total_items': paginator.count,
        }
    
    return render(request,'productList.html',context)


# PRODUCT STATUS
@never_cache
@login_required(login_url='adminLogin-page')
def productSingle_status(request,id):
    print('statuss is wowrkinggg')
    product_obj=Product.objects.get(id=id)
    if product_obj:
       product_obj.status = not product_obj.status  
       product_obj.save()
    return redirect('product-page')


# PRODUCT ADD 
@never_cache
@login_required(login_url='adminLogin-page')
def productAdd(request):

    if not request.user.is_superuser:
        return redirect('index-page')


    category_obj = Category.objects.all()
    brand_obj = Brand.objects.all()
    color_obj = Color.objects.all()
    size_obj = ShoeSize.objects.all()
    gender_obj = Gender.objects.all()

    context = {
        'category': category_obj,
        'brand': brand_obj,
        'color': color_obj,
        'size': size_obj,
        'gender': gender_obj
    }

    print('is working')
    if request.method == 'POST':
        print('Trigger')
        cropped_image = request.POST.get('cropped_image_1')
        if cropped_image:
            format, imgstr = cropped_image.split(';base64,')
            ext = format.split('/')[-1]  # Extract the file extension
            data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')

            product_name = request.POST.get('productTitle').strip()
            price = request.POST.get('price').strip()
            description = request.POST.get('description').strip()
            brand_id = request.POST.get('brand1') 
            print(brand_id)
            gender_id = request.POST.get('gender') 
            category_id = request.POST.get('category1') 
            
            category_instance = Category.objects.get(id=category_id)
            brand_instance = Brand.objects.get(id=brand_id)
            gender_instance = Gender.objects.get(id=gender_id)

            errors = {}
            if not product_name:
                errors['productTitle'] = "Product name cannot be empty."
            if not price or not price.replace('.', '', 1).isdigit():  
                errors['price'] = "Price must be a valid number."
            
            if not description:
                errors['description'] = "Description cannot be empty."

            if errors:
                return render(request, 'AddProduct2.html', {'errors': errors})

            product = Product(
                name=product_name,
                price=price,
                description=description,
                category=category_instance,
                brand=brand_instance,
                gender=gender_instance,
                image=data
            )
            product.save()
            print("Image saved successfully")
            return redirect('product-edit', product.id )
        else:
            print("No cropped image received")
    return render(request, 'AddProduct2.html',context)









def edit_product_form(request, product_id):
    product = get_object_or_404(Product, id=product_id)


    if request.method == 'POST':
        # Update product with form data
        product.name = request.POST.get('productTitle')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.gender_id = request.POST.get('gender')
        product.category_id = request.POST.get('category1')
        product.brand_id = request.POST.get('brand1')

        # Handle file uploads
        cropped_image = request.POST.get('cropped_image_1')
        if cropped_image:
            format, imgstr = cropped_image.split(';base64,')
            ext = format.split('/')[-1]  # Extract the file extension
            data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')
        product.image=data
        
        # Save changes
        product.save()
        return redirect('product_list')  # Redirect to a list of products or another view

    else:
        context = {
            'product': product,
            'gender': Gender.objects.all(),  # Adjust to your actual model
            'category': Category.objects.all(),  # Adjust to your actual model
            'brand': Brand.objects.all()  # Adjust to your actual model
        }

    return render(request, 'SingleEdit.html', context)

# ----------------------------------------------- variants section ------------------------------------------------

#  ADD VARIANTS
@never_cache
@login_required(login_url='adminLogin-page')
def variantsAdd(request,id):
    if not request.user.is_superuser:
        return redirect('index-page')
    
    print(id)
    size_obj=ShoeSize.objects.all()
    color_obj=Color.objects.all()

    product_obj=Product.objects.get(id=id)
    print(product_obj)

    if request.method == 'POST':
        color_id = request.POST.get('color') 
        size_id = request.POST.get('size') 
        quantity = request.POST.get('quantitiy') 
        print('psot triger')

        color_obj= Color.objects.get(id=color_id)
        size_obj= ShoeSize.objects.get(id=size_id)

        variant_obj= ProductVariant.objects.all()

        check = ProductVariant.objects.filter(product= product_obj,color=color_obj)
        if check :
            messages.error(request,'already exisiting data')
            return redirect('variants-add',product_obj.id)
        
       

        cropped_image = request.POST.get('cropped_image_1')
        format, imgstr = cropped_image.split(';base64,')
        ext = format.split('/')[-1]  # Extract the file extension
        data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')

        try:
            quantity = int(quantity)
            if quantity <= 0:
                messages.error(request, "Quantity must be a positive number.")
                return redirect('variants-add',product_obj.id)  # Redirect to an appropriate view
        except ValueError:
            messages.error(request, "Invalid quantity.")
            return redirect('variants-add',product_obj.id)

        New_variant= ProductVariant(
            product= product_obj,
            # quantity=quantity,
            color=color_obj,
            # size=size_obj,
            image=data

        )
        New_variant.save()

        shoesize_Values= ProductSize(
            variant= New_variant,
            size= size_obj,
            quantity= quantity
        )
        shoesize_Values.save()
        


        for i in range(2, 5):
            cropped_image_data = request.POST.get(f'cropped_image_{i}')
            print('Processing cropped_image_', i)  # Debugging log
            if cropped_image_data:
                try:
                    # Decode the base64 image data for the additional images
                    format, imgstr = cropped_image_data.split(';base64,')
                    ext = format.split('/')[-1]  # Extract the file extension
                    data = ContentFile(base64.b64decode(imgstr), name=f'product_additional_pic_{i}.{ext}')

                    # Save the additional image to the ProductImage model
                    VariantImage.objects.create(variant=New_variant, image=data)
                except Exception as e:
                    print(f"Error processing cropped image {i}: {e}")
        return redirect( 'product-edit', product_obj.id)
        


    context={
        'size':size_obj,
        'color':color_obj
    }
    return render(request,'forms/Addvariant.html',context)





# VARIANT DETAILS
@never_cache
@login_required(login_url='adminLogin-page')
def editVariants(request,id):
    if not request.user.is_superuser:
        return redirect('index-page')
    
    productVariant_obj= ProductVariant.objects.get(id=id)
    mainProduct_id= productVariant_obj.product
    print(mainProduct_id,'idddddd')
    productImages_obj= VariantImage.objects.filter(variant=productVariant_obj)
    print(productImages_obj)

    new_size= ProductSize.objects.filter(variant= productVariant_obj)


    color_obj= Color.objects.all()
    size_obj= ShoeSize.objects.all()

    print(productVariant_obj,'this variants')

    if request.method == 'POST':

        cropped_image = request.POST.get('cropped_image_1')
        format, imgstr = cropped_image.split(';base64,')
        ext = format.split('/')[-1]  # Extract the file extension
        data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')

        
        
        productVariant_obj.color= color_obj
        productVariant_obj.size= size_obj
        productVariant_obj.image= data
        productVariant_obj.product= mainProduct_id
        productVariant_obj.image= data
        productVariant_obj.save()

        for i in range(2, 5):
            cropped_image_data = request.POST.get(f'cropped_image_{i}')
            if cropped_image_data:
                try:
                    variant_image = VariantImage.objects.get(id=id)  
                    variant_image.delete()
                except VariantImage.DoesNotExist:
                    continue 
        
        for i in range(2, 5):
            cropped_image_data = request.POST.get(f'cropped_image_{i}')
            print('Processing cropped_image_', i)  # Debugging log
            if cropped_image_data:
                try:
                    # Decode the base64 image data for the additional images
                    format, imgstr = cropped_image_data.split(';base64,')
                    ext = format.split('/')[-1]  # Extract the file extension
                    data = ContentFile(base64.b64decode(imgstr), name=f'product_additional_pic_{i}.{ext}')

                    # Save the additional image to the ProductImage model
                    VariantImage.objects.create(variant=productVariant_obj, image=data)
                except Exception as e:
                    print(f"Error processing cropped image {i}: {e}")


        print("successsssss")

        return redirect('product-edit',mainProduct_id.id)

    context= {
        'product':productVariant_obj,
        # 'colors':color_obj,
        # 'sizes':size_obj,
        'images':productImages_obj,
        'newsize':new_size
        }
    
    return render(request,'variants/VariantDetails.html',context)


@never_cache
@login_required(login_url='adminLogin-page')
def editVariant_image(request,id):
    product_variant_obj= ProductVariant.objects.get(id=id)
    print(product_variant_obj)

    if request.method == 'POST':
        print('Trigger')
        cropped_image = request.POST.get('cropped_image_1')
        if cropped_image:
            format, imgstr = cropped_image.split(';base64,')
            ext = format.split('/')[-1]  # Extract the file extension
            data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')

            product_variant_obj.image= data

            product_variant_obj.save()
            return redirect('variants-edit',product_variant_obj.id)

    return render(request,'variants/EditVariantImage.html')






# SIZE ADD 
@never_cache
@login_required(login_url='adminLogin-page')
def sizeAdd(request,id):

    variant_obj= ProductVariant.objects.get(id=id)
    print(variant_obj,'variant')
    size_obj= ShoeSize.objects.all()


    if request.method == 'POST':
        size_id = request.POST.get('size') 
        quantity = request.POST.get('quantity') 
        
        sizes_instance= ShoeSize.objects.get(id = size_id)
        shoe_obj= ProductSize.objects.filter(variant=variant_obj,size=sizes_instance)
        if shoe_obj:
            messages.error(request,'already existing ')
            return redirect('add-size',variant_obj.id )

        ProductSize.objects.create(variant= variant_obj,size=sizes_instance,quantity= quantity)
        return redirect('variants-edit',variant_obj.id)
    
    context= {
        'size':size_obj
    }
    return render(request,'variants/sizeAdd.html',context)



# SIZE STATUS 
@never_cache
@login_required(login_url='adminLogin-page')
def sizeStatus(request,id):

    product_obj =ProductSize.objects.get(id=id)
    product_obj.status = not product_obj.status
    product_obj.save()
    return redirect('variants-edit',product_obj.variant.id)



# PRODUCT EDIT 
@never_cache
@login_required(login_url='adminLogin-page')
def productSingleView(request,id):
    print(id)
    
    product_obj= Product.objects.get(id= id)
    print(product_obj.gender)

    varient_obj= ProductVariant.objects.filter(product=product_obj)
    print(varient_obj,'varrr')

    context={
        'product':product_obj,
        'variant':varient_obj,
        }
    return render(request,'SingleProductDetails.html',context)



# SINGLE VARAINT STATUS EDIT
@never_cache
@login_required(login_url='adminLogin-page')
def singleVariant_status(request,id):

    variant_obj=ProductVariant.objects.get(id=id)
    variant_obj.status = not variant_obj.status
    variant_obj.save()
    return redirect('product-edit',variant_obj.product.id )



# USER DETAILS PAGE
@never_cache
@login_required(login_url='adminLogin-page')
def userDetailsPage(request,id):

    single_userDetails= UserProfile.objects.get(id=id)
    context={'user':single_userDetails}
    return render(request,'users/DetailsPage.html',context)

@never_cache
@login_required(login_url='adminLogin-page')
def userStatus(request, id):

    print('working')
    user_obj = get_object_or_404(UserProfile, id=id)
    
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    return redirect('user-details', user_obj.id)






# ------------------------------------- PRODUCT CATEGORY ---------------------
@never_cache
@login_required(login_url='adminLogin-page')
def productCategory(request):
    brand_obj= Brand.objects.all()
    category_obj= Category.objects.all()
    color_obj= Color.objects.all()
    shoe_obj= ShoeSize.objects.all()
    gender_obj= Gender.objects.all()

    context={
        'brand':brand_obj,
        'categories':category_obj,
        'color':color_obj,
        'shoe':shoe_obj,
        'gender':gender_obj
        
        }
    return render(request,'Category.html',context)



# BRAND ITEMS STATUS
@never_cache
@login_required(login_url='adminLogin-page')
def brand_status(request):
   print("status is working")

   if request.method == 'POST':
        item_id = request.POST.get('item_id')  
        print(item_id)
        item = get_object_or_404(Brand, id=item_id)
        print(item)

        # Toggle status
        item.status = not item.status
        item.save()
        # return redirect('product-category')
   return redirect('product-category') 

# CATEGORY STATUS
@never_cache
@login_required(login_url='adminLogin-page')
def category_status(request):
   print("status is working")

   if request.method == 'POST':
        item_id = request.POST.get('item_id')  
        print(item_id)
        item = get_object_or_404(Category, id=item_id)
        print(item)

        # Toggle status
        item.status = not item.status
        item.save()
        # return redirect('product-category')
   return redirect('product-category') 






# ------------------------------------- ORDERS DETAILS ------------------------------
@never_cache
@login_required(login_url='adminLogin-page')
def orders_table(request):
    if not request.user.is_superuser:
        return redirect('index-page')

    # Query all orders from the database
    orders = Order.objects.all()

    # Pass the orders to the template
    context = {
        'orders': orders,
    }

    return render(request,'orders/orders_table.html',context)


@never_cache
@login_required(login_url='adminLogin-page')
def order_details(request, order_id):

    if not request.user.is_superuser:
        return redirect('index-page')
    
     
    order = get_object_or_404(Order, id=order_id)

    print(order.id)
    print(order.payment_method)
    order_items = OrderItem.objects.filter(order=order)
    order_address = OrderAddress.objects.get(order=order)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            if new_status == 'CANCELED' and order.status != 'CANCELED':
                for item in order_items:
                    product_size = item.product_size
                    product_size.quantity += item.quantity  
                    product_size.save()

            order.status = new_status
            order.save()
            return redirect('admin-order-details', order_id=order.id)

    context = {
        'order': order,
        'order_items': order_items,
        'order_address': order_address,
    }
    return render(request, 'orders/singleDetail.html', context)





















# ADD CATEGORIES
@never_cache
@login_required(login_url='adminLogin-page')
def addCategory(request):
    if request.method == 'POST':
        item_name = request.POST.get('category').strip()  
        if len(item_name) == 0:  
            messages.error(request, 'Category name cannot be empty.')  
        else:
            Category.objects.create(name=item_name)
            messages.success(request, 'Category added successfully!')  
            return redirect('product-category')
    return render(request,'forms/AddCategories.html')

# EDIT CATEGORIES
@never_cache
@login_required(login_url='adminLogin-page')
def editCategories(request,id):
    category_obj= Category.objects.get(id=id)

    if request.method == 'POST':
        # Get the updated category name from the form
        updated_name = request.POST.get('category').strip()  # Remove leading/trailing whitespace

        if len(updated_name) == 0:  # Check if the updated name is empty
            messages.error(request, 'Category name cannot be empty.')  # Error message
        else:
            # Update the category name
            category_obj.name = updated_name
            category_obj.save()  # Save the changes to the database
            messages.success(request, 'Category updated successfully!')  # Success message
            return redirect('product-category') 


    return render(request,'forms/EditCategory.html',{'category':category_obj})

# DELETE CATEGORY
@never_cache
@login_required(login_url='adminLogin-page')
def deleteCategory(request,id):
    print('delete triger')
    Category.objects.get(id=id).delete()
    return redirect('product-category')
    

# ADD BRAND
@never_cache
@login_required(login_url='adminLogin-page')
def brandAdd(request):
    if request.method == 'POST':
        item_name = request.POST.get('brand').strip()  
        if len(item_name) == 0:  
            messages.error(request, 'brand name cannot be empty.')  
        else:
            Brand.objects.create(name=item_name)
            messages.success(request, 'Brand added successfully!')  
            return redirect('product-category')
    return render(request,'forms/BrandAdd.html')



#  BRAND EDIT
@never_cache
@login_required(login_url='adminLogin-page')
def brandEdit(request,id):
    brand_obj= Brand.objects.get(id=id)

    if request.method == 'POST':
        # Get the updated category name from the form
        updated_name = request.POST.get('brand').strip()  # Remove leading/trailing whitespace

        if len(updated_name) == 0:  # Check if the updated name is empty
            messages.error(request, 'Category name cannot be empty.')  # Error message
        else:
            # Update the category name
            brand_obj.name = updated_name
            brand_obj.save()  # Save the changes to the database
            messages.success(request, 'Brand updated successfully!')  # Success message
            return redirect('product-category') 


    return render(request,'forms/BrandEdit.html',{'brand':brand_obj})




#  BRAND DELETE
@never_cache
@login_required(login_url='adminLogin-page')
def brandDelete(request,id):
    print('delete triger')
    Brand.objects.get(id=id).delete()
    return redirect('product-category')





# COLORS EDIT
@never_cache
@login_required(login_url='adminLogin-page')
def colorEdit(request,id):
    color_obj= Color.objects.get(id=id)
    if request.method == 'POST':
        # Get the updated category name from the form
        updated_name = request.POST.get('color').strip()  # Remove leading/trailing whitespace

        if len(updated_name) == 0:  # Check if the updated name is empty
            messages.error(request, 'Color name cannot be empty.')  # Error message
        else:
            # Update the category name
            color_obj.name = updated_name
            color_obj.save()  # Save the changes to the database
            messages.success(request, 'color updated successfully!')  # Success message
            return redirect('product-category') 


    return render(request,'forms/ColorsEdit.html',{'color':color_obj})



# COLOR DELETE
@never_cache
@login_required(login_url='adminLogin-page')
def colorDelete(request,id):
    print('delete triger')
    Color.objects.get(id=id).delete()
    return redirect('product-category')



# COLOR ADD
@never_cache
@login_required(login_url='adminLogin-page')
def colorAdd(request):
    if request.method == 'POST':
        item_name = request.POST.get('color').strip()  
        if len(item_name) == 0:  
            messages.error(request, 'color name cannot be empty.')  
        else:
            Color.objects.create(name=item_name)
            messages.success(request, 'Color added successfully!')  
            return redirect('product-category')
    return render(request,'forms/ColorAdd.html')





# GENDER ADD
@never_cache
@login_required(login_url='adminLogin-page')
def genderAdd(request):
    if request.method == 'POST':
        item_name = request.POST.get('gender').strip()  
        if len(item_name) == 0:  
            messages.error(request, 'gender field cannot be empty.')  
        else:
            Gender.objects.create(name=item_name)
            messages.success(request, 'gender added successfully!')  
            return redirect('product-category')
    return render(request,'forms/GenderAdd.html')




# GENDER EDIT
@never_cache
@login_required(login_url='adminLogin-page')
def genderEdit(request,id):
    gender_obj= Gender.objects.get(id=id)
    if request.method == 'POST':
        # Get the updated category name from the form
        updated_name = request.POST.get('gender').strip()  # Remove leading/trailing whitespace

        if len(updated_name) == 0:  # Check if the updated name is empty
            messages.error(request, 'gender name cannot be empty.')  # Error message
        else:
            # Update the category name
            gender_obj.name = updated_name
            gender_obj.save()  # Save the changes to the database
            messages.success(request, 'gender updated successfully!')  # Success message
            return redirect('product-category')
    return render(request,'forms/GenderEdit.html',{'gender':gender_obj})


# GENDER DELETE
@never_cache
@login_required(login_url='adminLogin-page')
def genderDelete(request,id):

    print('delete triger')
    Gender.objects.get(id=id).delete()
    return redirect('product-category')









