from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login,logout as logout_fn
from django.contrib import messages
from django.contrib.auth.models import User

from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import *
from django.core.paginator import Paginator,EmptyPage, PageNotAnInteger
from django.db.models import Sum
import base64
from django.core.files.base import ContentFile

from django.db.models import F, Sum
from datetime import datetime, timedelta
from django.utils.dateparse import parse_date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.http import HttpResponse

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
from io import BytesIO
from openpyxl import Workbook
# from openpyxl.writer.excel import save_virtual_workbook
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
import json
# Create your views here.





def get_sales_report(start_date, end_date):
    completed_orders = Order.objects.filter(order_date__range=[start_date, end_date])
   
    total_sales = completed_orders.aggregate(total_sales=Sum('final_price'))['total_sales'] or 0
   
    return total_sales, completed_orders


# ADMIN DASHBOARD
@never_cache
@login_required(login_url='adminLogin-page')
def adminPage(request):
    name = request.user.username
    if not request.user.is_superuser:
        return redirect('index-page')

    today = timezone.now()

    # Filter orders by day, week, and month
    day_orders = Order.objects.filter(order_date__date=today.date())
    week_orders = Order.objects.filter(order_date__gte=today - timedelta(days=7))
    month_orders = Order.objects.filter(order_date__gte=today - timedelta(days=30))
    year_orders = Order.objects.filter(order_date__gte=today - timedelta(days=365))

    def get_chart_data(orders):
        return {
            'labels': [order.order_date.strftime('%Y-%m-%d') for order in orders],
            'data': [float(order.final_price) for order in orders]  
        }
    
    top_products = (
        OrderItem.objects
        .values('product_size__variant__product')
        .annotate(total_sold=Count('product_size'))
        .order_by('-total_sold')[:10]
    )

    top_products_list = [
        {
            'name': Product.objects.get(id=item['product_size__variant__product']).name,
            'total_sold': item['total_sold'],
            'image': Product.objects.get(id=item['product_size__variant__product']).image.url
        }
        for item in top_products
    ]


    top_categories = (
        OrderItem.objects
        .values('product_size__variant__product__category')
        .annotate(total_sold=Count('product_size'))
        .order_by('-total_sold')[:10]
    )

    top_categories_list = [
        {
            'name': Category.objects.get(id=item['product_size__variant__product__category']).name,
            'total_sold': item['total_sold'],
        }
        for item in top_categories
    ]


    top_brands = (
        OrderItem.objects
        .values('product_size__variant__product__brand')
        .annotate(total_sold=Count('product_size'))
        .order_by('-total_sold')[:10]
    )

    top_brands_list = [
        {
            'name': Brand.objects.get(id=item['product_size__variant__product__brand']).name,
            'total_sold': item['total_sold'],
        }
        for item in top_brands
    ]
 
    context = {
        'name': request.user,
        'day_data': json.dumps(get_chart_data(day_orders)), 
        'week_data': json.dumps(get_chart_data(week_orders)), 
        'month_data': json.dumps(get_chart_data(month_orders)),  
        'year_data': json.dumps(get_chart_data(year_orders)),
        'top_products_list': top_products_list,
        'top_categories_list': top_categories_list ,
        'top_brands_list': top_brands_list
        
    }
  
    return render(request, 'dashboard.html', context)




def sales_report(request):

    name = request.user.username
    if not request.user.is_superuser:
        return redirect('index-page')

    today = datetime.now().date()
    default_start_date = today - timedelta(days=30)
    default_end_date = today

    filter_type = request.GET.get('filter_type', 'custom')

    if filter_type == '1_day':
        start_date = today - timedelta(days=1)
        end_date = today
    elif filter_type == '1_week':
        start_date = today - timedelta(weeks=1)
        end_date = today
    elif filter_type == '1_month':
        start_date = today - timedelta(weeks=4)
        end_date = today
    elif filter_type == 'custom':
        start_date_str = request.GET.get('start_date', default_start_date.strftime('%Y-%m-%d'))
        end_date_str = request.GET.get('end_date', default_end_date.strftime('%Y-%m-%d'))
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if end_date < start_date:
                raise ValueError("End date cannot be before start date.")
        except ValueError as e:
            return render(request, 'dashboard.html', {
                'error_message': str(e),
                'start_date': default_start_date,
                'end_date': default_end_date,
                'filter_type': filter_type
            })
    else:
        start_date = default_start_date
        end_date = default_end_date

    total_sales, completed_orders = get_sales_report(start_date, end_date)

    overall_sales_count = completed_orders.count()
    overall_order_amount = sum(order.final_price for order in completed_orders)
    overall_discount = sum(order.original_price - order.discounted_price for order in completed_orders)

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    no_orders_message = "No orders found for the selected date range." if not completed_orders else None

    if request.GET.get('pdf'):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=sales_report.pdf'
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle('Header', parent=styles['Title'], fontSize=18, alignment=1, spaceAfter=12)
        title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=16, alignment=1, spaceAfter=12)
        normal_style = styles['Normal']
        
        project_name = "ShoeSpectra Sales Report"
        header = Paragraph(f'<b>{project_name}</b>', header_style)
        elements.append(header)

        if filter_type == 'custom':
            report_date_description = f'From {start_date} to {end_date}'
        else:
            filter_description = {
                '1_day': 'Last 1 Day',
                '1_week': 'Last 1 Week',
                '1_month': 'Last 1 Month'
            }
            report_date_description = filter_description.get(filter_type, 'Custom Range')
        
        report_date = Paragraph(f'Report Period: {report_date_description}', normal_style)
        elements.append(report_date)

        total_sales_paragraph = Paragraph(f'<b>Total Sales:</b> ${total_sales:.2f}', title_style)
        elements.append(total_sales_paragraph)

        overall_sales_count_paragraph = Paragraph(f'<b>Overall Sales Count:</b> {overall_sales_count}', normal_style)
        overall_order_amount_paragraph = Paragraph(f'<b>Overall Order Amount:</b> ${overall_order_amount:.2f}', normal_style)
        overall_discount_paragraph = Paragraph(f'<b>Overall Discount:</b> ${overall_discount:.2f}', normal_style)
        elements.append(overall_sales_count_paragraph)
        elements.append(overall_order_amount_paragraph)
        elements.append(overall_discount_paragraph)

        if no_orders_message:
            no_orders_paragraph = Paragraph(no_orders_message, normal_style)
            elements.append(no_orders_paragraph)
        else:
            # Order Details Table
            data = [['Order ID', 'User', 'Final Price', 'Payment Method', 'Order Date', 'Status']]
            for order in completed_orders:
                data.append([
                    order.id,
                    order.user.username,
                    f'${order.final_price:.2f}',
                    order.payment_method,
                    order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
                    order.status
                ])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            elements.append(table)

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
    
    context = {
        'total_sales': total_sales,
        'completed_orders': completed_orders,
        'start_date': start_date,
        'end_date': end_date,
        'name': name,
        'no_orders_message': no_orders_message,
        'filter_type': filter_type,
        'overall_sales_count': overall_sales_count,
        'overall_order_amount': overall_order_amount,
        'overall_discount': overall_discount,
        'start_date': start_date_str, 
        'end_date': end_date_str, 
    }

    return render(request,'sales_report.html',context)



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

    if request.method == 'POST':
        cropped_image = request.POST.get('cropped_image_1')
        if cropped_image:
            format, imgstr = cropped_image.split(';base64,')
            ext = format.split('/')[-1]  # Extract the file extension
            data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')

            product_name = request.POST.get('productTitle').strip()
            price = request.POST.get('price').strip()
            description = request.POST.get('description').strip()
            brand_id = request.POST.get('brand1') 
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
            return redirect('product-edit', product.id )
        else:
            print("No cropped image received")
    return render(request, 'AddProduct2.html',context)







def edit_product_form(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    image= product.image


    if request.method == 'POST':
       

        product_title = request.POST.get('productTitle', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('amount', '').strip()
        gender_id = request.POST.get('gender', '').strip()
        category_id = request.POST.get('category1', '').strip()
        brand_id = request.POST.get('brand1', '').strip()



        errors = {}
        
        if not product_title:
            errors['productTitle'] = 'Product title is required and cannot be empty or just spaces.'
        if not description:
            errors['description'] = 'Description is required and cannot be empty or just spaces.'
        if price:
            price = float(price) 
            if price <= 0:
                errors['price'] = 'Price must be a positive number.'
        else:
            price=product.price
        if not gender_id:
            errors['gender'] = 'Gender is required and cannot be empty or just spaces.'
        if not category_id:
            errors['category1'] = 'Category is required and cannot be empty or just spaces.'
        if not brand_id:
            errors['brand1'] = 'Brand is required and cannot be empty or just spaces.'

        if errors:
            return render(request, 'SingleEdit.html', {'errors': errors})
        

        product = Product(
            name=product_title,
            description=description,
            price=price,
            gender_id=gender_id,
            category_id=category_id,
            brand_id=brand_id
        )

        # Handle file uploads
        cropped_image = request.POST.get('cropped_image_1')
        if cropped_image:
            format, imgstr = cropped_image.split(';base64,')
            ext = format.split('/')[-1]  # Extract the file extension
            data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')
        else:
            data= image
        product.image=data
        
        # Save changes
        product.save()
        return redirect('product-edit',product.id)  

    else:
        context = {
            'product': product,
            'gender': Gender.objects.all(),  
            'category': Category.objects.all(),  
            'brand': Brand.objects.all() 
        }

    return render(request, 'SingleEdit.html', context)

# ----------------------------------------------- variants section ------------------------------------------------

#  ADD VARIANTS
@never_cache
@login_required(login_url='adminLogin-page')
def variantsAdd(request,id):
    if not request.user.is_superuser:
        return redirect('index-page')
    
    size_obj=ShoeSize.objects.all()
    color_obj=Color.objects.all()

    product_obj=Product.objects.get(id=id)

    if request.method == 'POST':
        color_id = request.POST.get('color') 
        size_id = request.POST.get('size') 
        quantity = request.POST.get('quantitiy') 

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
                return redirect('variants-add',product_obj.id) 
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
    productImages_obj= VariantImage.objects.filter(variant=productVariant_obj)

    new_size= ProductSize.objects.filter(variant= productVariant_obj)


    color_obj= Color.objects.all()
    size_obj= ShoeSize.objects.all()


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

    if request.method == 'POST':
        cropped_image = request.POST.get('cropped_image_1')
        if cropped_image:
            format, imgstr = cropped_image.split(';base64,')
            ext = format.split('/')[-1]  # Extract the file extension
            data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')

            product_variant_obj.image= data

            product_variant_obj.save()
            return redirect('variants-edit',product_variant_obj.id)

    return render(request,'variants/EditVariantImage.html')



@never_cache
@login_required(login_url='adminLogin-page')
def variant_size_edit(request, id):
    size_obj = get_object_or_404(ProductSize, id=id)
    if not request.user.is_superuser:
        return redirect('index-page')
    
    sizes = ShoeSize.objects.all()

    if request.method == 'POST':
        selected_size_id = request.POST.get('size', '').strip()
        quantity = request.POST.get('quantity', '').strip()

        errors = []
        
        if not selected_size_id:
            errors.append("Size must be selected.")
        else:
            try:
                size_instance = ShoeSize.objects.get(id=selected_size_id)
            except ShoeSize.DoesNotExist:
                errors.append("Selected size does not exist.")
        
        if not quantity:
            errors.append("Quantity cannot be empty or spaces.")
        elif not quantity.isdigit() or int(quantity) <= 0:
            errors.append("Quantity must be a positive integer.")
        
        if errors:
            context = {
                'size_obj': size_obj,
                'sizes': sizes,
                'errors': errors
            }
            return render(request, 'variants/SizeEdit.html', context)
        

        variant_obj = size_obj.variant  
        if ProductSize.objects.exclude(id=size_obj.id).filter(variant=variant_obj, size=size_instance).exists():
            messages.error(request, 'The selected size already exists for this variant.')
            return redirect('variants-size-edit',size_obj.id)
        
       
        
        size_obj.size = size_instance
        size_obj.quantity = int(quantity)
        size_obj.save()

        return redirect('variants-edit', id=size_obj.variant.id)

    context = {
        'size_obj': size_obj,
        'sizes': sizes,
    }
    return render(request, 'variants/SizeEdit.html', context)


@never_cache
@login_required(login_url='adminLogin-page')
def edit_variant_images(request,id):
    image_obj= VariantImage.objects.get(id=id)
    if not request.user.is_superuser:
        return redirect('index-page')

   

    if request.method == 'POST':
        cropped_image = request.POST.get('cropped_image_1')
        if cropped_image:
            format, imgstr = cropped_image.split(';base64,')
            ext = format.split('/')[-1]  # Extract the file extension
            data = ContentFile(base64.b64decode(imgstr), name=f'profile_pic.{ext}')

            image_obj.image= data

            image_obj.save()
            return redirect('variants-edit',image_obj.variant.id)

    return render(request,'variants/Images_edit.html',{'photo':image_obj})
  





# SIZE ADD 
@never_cache
@login_required(login_url='adminLogin-page')
def sizeAdd(request,id):
    if not request.user.is_superuser:
        return redirect('index-page')

    variant_obj= ProductVariant.objects.get(id=id)
    size_obj= ShoeSize.objects.all()


    if request.method == 'POST':
       
        size_id = request.POST.get('size', '').strip()
        quantity = request.POST.get('quantity', '').strip()
        errors = []


        if not size_id:
            errors.append("Size must be selected.")
        else:
            try:
                size_instance = ShoeSize.objects.get(id=size_id)
            except ShoeSize.DoesNotExist:
                errors.append("Selected size does not exist.")

        if not quantity:
            errors.append("Quantity cannot be empty or spaces.")
        elif not quantity.isdigit() or int(quantity) <= 0:
            errors.append("Quantity must be a positive integer.")

        if errors:
            context = {
                'size':size_obj,
                'errors': errors
            }
        
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

    if not request.user.is_superuser:
        return redirect('index-page')
    
    product_obj= Product.objects.get(id= id)

    varient_obj= ProductVariant.objects.filter(product=product_obj)

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

    if not request.user.is_superuser:
        return redirect('index-page')


    single_userDetails= UserProfile.objects.get(id=id)
    context={'user':single_userDetails}
    return render(request,'users/DetailsPage.html',context)

@never_cache
@login_required(login_url='adminLogin-page')
def userStatus(request, id):

    user_obj = get_object_or_404(UserProfile, id=id)
    
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    return redirect('user-details', user_obj.id)






# ------------------------------------- PRODUCT CATEGORY ---------------------
@never_cache
@login_required(login_url='adminLogin-page')
def productCategory(request):

    if not request.user.is_superuser:
        return redirect('index-page')
    
    



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

   if request.method == 'POST':
        item_id = request.POST.get('item_id')  
        item = get_object_or_404(Brand, id=item_id)

        item.status = not item.status
        item.save()
   return redirect('product-category') 

# CATEGORY STATUS
@never_cache
@login_required(login_url='adminLogin-page')
def category_status(request):

   if request.method == 'POST':
        item_id = request.POST.get('item_id')  
        item = get_object_or_404(Category, id=item_id)

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

    orders = Order.objects.all().order_by('-order_date')

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

    order_items = OrderItem.objects.filter(order=order)
    order_address = OrderAddress.objects.get(order=order)

    form_disabled = (order.status in ['DELIVERED', 'CANCELED']) or \
                    (order.payment_method == 'Razorpay' and not order.payment_success)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            if new_status == 'CANCELED' and order.status != 'CANCELED':
                user = order.user
                
                if order.payment_success:  
                    refund_amount = order.total_amount  
                    
                    wallet, created = Wallet.objects.get_or_create(user=user)
                    
                    wallet.balance += refund_amount
                    wallet.save()  
                    order.total_amount=0

                    
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=refund_amount,
                        transaction_type='credit',
                        purpose='refund',
                        description=f"Refund for canceled order {order.id}"
                    )
                
                for item in order_items:
                    product_size = item.product_size
                    product_size.quantity += item.quantity
                    product_size.save()
                

                order.status = new_status
                order.save()
                return redirect('admin-order-details', order_id=order.id)
            
            elif new_status == 'DELIVERED' and order.status != 'DELIVERED':
                
                order.status = new_status
                order.payment_success= True
                order.save()
                messages.success(request, 'Order has been marked as delivered.')
                return redirect('admin-order-details', order_id=order.id)

    context = {
        'order': order,
        'order_items': order_items,
        'order_address': order_address,
        'form_disabled': form_disabled,
    }
    return render(request, 'orders/singleDetail.html', context)





# ---------------------------------     COUPENS SECTION -----------------------------
@never_cache
@login_required(login_url='adminLogin-page')
def coupen_section(request):
    if not request.user.is_superuser:
        return redirect('index-page')
    coupons = Coupon.objects.all()
    total_coupons = coupons.count() 
    return render(request,'coupen/coupen_list.html',{'coupon':coupons ,'total_coupons': total_coupons})




@never_cache
@login_required(login_url='adminLogin-page')
def add_coupon(request):
    if not request.user.is_superuser:
        return redirect('index-page')
    
    errors = []
    
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        discount_percentage = request.POST.get('discount_percentage')
        expiry_date = request.POST.get('expiry_date')
        min_amount = request.POST.get('min_amount')  # Get min_amount from POST data
        active = request.POST.get('active') == 'on'

        # Validate coupon_code
        if not coupon_code or len(coupon_code.strip()) == 0:
            errors.append("Coupon code is required and cannot be empty.")
        else:
            coupon_code = coupon_code.strip()
            if ' ' in coupon_code:
                errors.append("Coupon code should not contain spaces.")
            elif len(coupon_code) < 3:
                errors.append("Coupon code must be at least 3 characters long.")
            elif Coupon.objects.filter(code=coupon_code).exists():
                errors.append("Coupon code already exists.")
        
        # Validate discount_percentage
        try:
            discount_percentage = float(discount_percentage)
            if discount_percentage <= 0 or discount_percentage > 100:
                errors.append("Discount percentage must be between 1 and 100.")
        except ValueError:
            errors.append("Discount percentage must be a valid number.")
        
        # Validate expiry_date
        try:
            expiry_date = timezone.make_aware(timezone.datetime.fromisoformat(expiry_date))
            if expiry_date <= timezone.now():
                errors.append("Expiry date must be in the future.")
        except ValueError:
            errors.append("Expiry date must be a valid date and time.")
        
        # Validate min_amount
        try:
            min_amount = float(min_amount)
            if min_amount < 0:
                errors.append("Minimum amount must be a non-negative number.")
        except ValueError:
            errors.append("Minimum amount must be a valid number.")

        # If no errors, create the coupon
        if not errors:
            Coupon.objects.create(
                code=coupon_code,
                discount_percentage=discount_percentage,
                expiry_date=expiry_date,
                min_amount=min_amount,  # Include min_amount when creating the coupon
                active=active
            )
            return redirect('coupen-list')

    return render(request, 'coupen/add.html', {'errors': errors})

@never_cache
@login_required(login_url='adminLogin-page')
def edit_coupon(request, id):
    if not request.user.is_superuser:
        return redirect('index-page')
    
    coupon = get_object_or_404(Coupon, id=id)
    errors = []

    if request.method == 'POST':
        coupon_code = request.POST.get('code').strip()
        discount_percentage = request.POST.get('discount_percentage')
        expiry_date_str = request.POST.get('expiry_date')
        min_amount_str = request.POST.get('min_amount')  # Get min_amount from POST data
        active = request.POST.get('active') == 'on'

        # Validate coupon code
        if not coupon_code:
            errors.append("Coupon code is required.")
        elif ' ' in coupon_code:
            errors.append("Coupon code should not contain spaces.")
        elif Coupon.objects.filter(code=coupon_code).exclude(id=coupon.id).exists():
            errors.append("Coupon code already exists.")

        # Validate discount percentage
        try:
            discount_percentage = float(discount_percentage)
            if discount_percentage <= 0 or discount_percentage > 100:
                errors.append("Discount percentage must be between 1 and 100.")
        except ValueError:
            errors.append("Discount percentage must be a valid number.")

        # Validate expiry date
        try:
            expiry_date = timezone.make_aware(timezone.datetime.fromisoformat(expiry_date_str))
            if expiry_date <= timezone.now():
                errors.append("Expiry date must be in the future.")
        except ValueError:
            errors.append("Expiry date must be a valid date and time.")

        # Validate min_amount
        try:
            min_amount = float(min_amount_str)
            if min_amount < 0:
                errors.append("Minimum amount must be a non-negative number.")
        except ValueError:
            errors.append("Minimum amount must be a valid number.")

        # If there are errors, render the form with error messages
        if errors:
            return render(request, 'coupen/edit.html', {'coupon': coupon, 'errors': errors})

        # Update the coupon
        coupon.code = coupon_code
        coupon.discount_percentage = discount_percentage
        coupon.expiry_date = expiry_date
        coupon.min_amount = min_amount  # Include min_amount in the update
        coupon.active = active
        coupon.save()

        return redirect('coupen-list')
    
    return render(request, 'coupen/edit.html', {'coupon': coupon})





def delete_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id)
    if request.method == 'POST':
        coupon.delete()
        return redirect('coupen-list')
    return redirect('coupen-list')






# ------------------------------------------------------------------ END COUPEN SECTION -----------------------------------
@never_cache
@login_required(login_url='adminLogin-page')
def offer_list(request):
    if not request.user.is_superuser:
        return redirect('index-page')
    
    
    offers = Offer.objects.all()
    product_offer = ProductOffer.objects.all()

    total_brand_offer = offers.count()
    total_product_offer = offers.count()
    return render(request, 'offer/offer_list.html', {'offers': offers,'count':total_brand_offer,'product_offer':product_offer,'total_product_offer':total_product_offer})


@never_cache
@login_required(login_url='adminLogin-page')
def edit_offer(request, offer_id):
    if not request.user.is_superuser:
        return redirect('index-page')
    
    offer = get_object_or_404(Offer, id=offer_id)
    brands = Brand.objects.all()

    if request.method == 'POST':
        brand_id = request.POST.get('brand')
        discount_percentage = request.POST.get('discount_percentage')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        if not brand_id or not discount_percentage or not start_date or not end_date:
            return render(request, 'offer/edit_offer.html', {
                'offer': offer,
                'brands': brands,
                'error': 'All fields are required.'
            })

        try:
            discount_percentage = float(discount_percentage)
            if discount_percentage <= 0 or discount_percentage > 100:
                return render(request, 'offer/Edit.html', {
                    'offer': offer,
                    'brands': brands,
                    'error': 'Discount percentage must be between 1 and 100.'
                })
        except ValueError:
            return render(request, 'offer/Edit.html', {
                'offer': offer,
                'brands': brands,
                'error': 'Invalid discount percentage.'
            })

        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            if start_date > end_date:
                return render(request, 'offer/Edit.html', {
                    'offer': offer,
                    'brands': brands,
                    'error': 'Start date cannot be after end date.'
                })
        except ValueError:
            return render(request, 'offer/Edit.html', {
                'offer': offer,
                'brands': brands,
                'error': 'Invalid date format. Use YYYY-MM-DD.'
            })

        offer.brand_id = brand_id
        offer.discount_percentage = discount_percentage
        offer.start_date = start_date
        offer.end_date = end_date
        offer.save()

        return redirect('offer-list')

   

    return render(request, 'offer/Edit.html',{'offer':offer,'brands':brands})






@never_cache
@login_required(login_url='adminLogin-page')
def add_offer(request):
    if not request.user.is_superuser:
        return redirect('index-page')
    brands = Brand.objects.all() 

    if request.method == 'POST':
        brand_id = request.POST.get('brand')
        discount_percentage = request.POST.get('discount_percentage')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        if not brand_id or not discount_percentage or not start_date or not end_date:
            return render(request, 'offer/add_offer.html', {
                'brands': brands,
                'error': 'All fields are required.'
            })

        try:
            discount_percentage = float(discount_percentage)
            if discount_percentage <= 0 or discount_percentage > 100:
                return render(request, 'offer/add_offer.html', {
                    'brands': brands,
                    'error': 'Discount percentage must be between 1 and 100.'
                })
        except ValueError:
            return render(request, 'offer/add_offer.html', {
                'brands': brands,
                'error': 'Invalid discount percentage.'
            })

        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            if start_date > end_date:
                return render(request, 'offer/add_offer.html', {
                    'brands': brands,
                    'error': 'Start date cannot be after end date.'
                })
        except ValueError:
            return render(request, 'offer/add_offer.html', {
                'brands': brands,
                'error': 'Invalid date format. Use YYYY-MM-DD.'
            })
        
        existing_offer = Offer.objects.filter(
        brand_id=brand_id,
        start_date__lte=end_date,
        end_date__gte=start_date).exists()

        if existing_offer:
            return render(request, 'offer/add_offer.html', {
                'brands': brands,
                'error': 'An active offer already exists for this brand within the specified date range.'
            })

        Offer.objects.create(
            brand_id=brand_id,
            discount_percentage=discount_percentage,
            start_date=start_date,
            end_date=end_date
        )

        return redirect('offer-list')

    return render(request, 'offer/add_offer.html', {'brands': brands})

def delete_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    offer.delete()
    
    return redirect('offer-list')










# PRODUCT OFFER

def add_product_offer(request):

    errors = {}  

    if request.method == 'POST':
        product_id = request.POST.get('product', '').strip() 
        offer_percentage = request.POST.get('offer_percentage', '').strip() 
        start_date = request.POST.get('start_date', '').strip() 
        end_date = request.POST.get('end_date', '').strip() 

        if not product_id or len(product_id) < 1:
            errors['product'] = 'Product selection is required.'
        
        if not offer_percentage:
            errors['offer_percentage'] = 'Offer percentage is required.'
        else:
            try:
                offer_percentage_value = int(offer_percentage)
                if offer_percentage_value < 1 or offer_percentage_value > 100:
                    errors['offer_percentage'] = 'Offer percentage must be between 1 and 100.'
            except ValueError:
                errors['offer_percentage'] = 'Offer percentage must be a valid number.'

        if not start_date or len(start_date) < 1:
            errors['start_date'] = 'Start date is required.'
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                errors['start_date'] = 'Invalid start date format.'

        if not end_date or len(end_date) < 1:
            errors['end_date'] = 'Expiry date is required.'
        else:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                if end_date <= datetime.today().date():
                    errors['end_date'] = 'Expiry date must be in the future.'
                elif start_date >= end_date:
                    errors['end_date'] = 'Expiry date must be after the start date.'
            except ValueError:
                errors['end_date'] = 'Invalid expiry date format.'

        if not errors:
            try:
                product = Product.objects.get(id=product_id)

                existing_offer = ProductOffer.objects.filter(
                    product=product,
                    end_date__gte=timezone.now()  
                ).first()

                if existing_offer:
                    errors['existing_offer'] = 'This product already has an active offer.'
                else:
                    ProductOffer.objects.create(
                        product=product,
                        discount_percentage=offer_percentage_value,
                        start_date=start_date,
                        end_date=end_date
                    )
                    return redirect('offer-list')  

            except Product.DoesNotExist:
                errors['product'] = 'Invalid product selected.'


    product_obj = Product.objects.all()  

    product_obj= Product.objects.all()
    
    return render(request,'offer/add_product_offer.html',{'products':product_obj,'errors': errors})


def delete_product_offer(request, offer_id):


    offer = get_object_or_404(ProductOffer, id=offer_id)
    if request.method == 'POST':
        offer.delete()
        return redirect('offer-list')  
    
    return render(request, 'offer/confirm_delete.html', {'offer': offer})


def edit_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    products = Product.objects.all()  

    if request.method == 'POST':
        product_id = request.POST.get('product', '').strip()
        discount_percentage = request.POST.get('discount_percentage', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        
        errors = {}

        if not product_id:
            errors['product'] = 'Product is required.'
        elif not Product.objects.filter(id=product_id).exists():
            errors['product'] = 'Selected product does not exist.'

        if not discount_percentage:
            errors['discount_percentage'] = 'Discount percentage is required.'
        else:
            try:
                discount_percentage = int(discount_percentage)
                if discount_percentage < 1 or discount_percentage > 100:
                    errors['discount_percentage'] = 'Discount percentage must be between 1 and 100.'
            except ValueError:
                errors['discount_percentage'] = 'Invalid discount percentage value.'

        if not start_date:
            errors['start_date'] = 'Start date is required.'
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                errors['start_date'] = 'Invalid start date format.'

        if not end_date:
            errors['end_date'] = 'Expiry date is required.'
        else:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                if end_date <= datetime.today().date():
                    errors['end_date'] = 'Expiry date must be in the future.'
            except ValueError:
                errors['end_date'] = 'Invalid expiry date format.'

        if errors:
            return render(request, 'offer/edit_product_offer.html', {
                'offer': offer,
                'products': products,
                'errors': errors,
                'product_id': product_id,
                'discount_percentage': discount_percentage,
                'start_date': start_date,
                'end_date': end_date
            })
        else:
            offer.product_id = product_id
            offer.discount_percentage = discount_percentage
            offer.start_date = start_date
            offer.end_date = end_date
            offer.save()
            
            return redirect('offer-list')  

    else:
        return render(request, 'offer/edit_product_offer.html', {
            'offer': offer,
            'products': products,
            'product_id': offer.product_id,
            'discount_percentage': offer.discount_percentage,
            'start_date': offer.start_date.strftime('%Y-%m-%d') if offer.start_date else '',
            'end_date': offer.end_date.strftime('%Y-%m-%d') if offer.end_date else ''
        })

# ------------------------------------------------------ OFFER END------------------------

# ADD CATEGORIES
@never_cache
@login_required(login_url='adminLogin-page')
def addCategory(request):
    if not request.user.is_superuser:
        return redirect('index-page')
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
    if not request.user.is_superuser:
        return redirect('index-page')
    
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
    Category.objects.get(id=id).delete()
    return redirect('product-category')
    

# ADD BRAND
@never_cache
@login_required(login_url='adminLogin-page')
def brandAdd(request):
    if not request.user.is_superuser:
        return redirect('index-page')
    
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
    if not request.user.is_superuser:
        return redirect('index-page')
    
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
    Brand.objects.get(id=id).delete()
    return redirect('product-category')





# COLORS EDIT
@never_cache
@login_required(login_url='adminLogin-page')
def colorEdit(request,id):
    if not request.user.is_superuser:
        return redirect('index-page')
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
    Color.objects.get(id=id).delete()
    return redirect('product-category')



# COLOR ADD
@never_cache
@login_required(login_url='adminLogin-page')
def colorAdd(request):
    if not request.user.is_superuser:
        return redirect('index-page')
    
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
    if not request.user.is_superuser:
        return redirect('index-page')
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
    if not request.user.is_superuser:
        return redirect('index-page')
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

    Gender.objects.get(id=id).delete()
    return redirect('product-category')









