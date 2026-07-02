from django.shortcuts import render
from inventory.models import Product, Brand, Category
from accounts.models import User

def home_view(request):
    medicines_count = Product.objects.count()
    dealers_count = User.objects.filter(role='dealer', profile__approval_status='approved').count()
    brands_count = Brand.objects.count()
    categories = Category.objects.all()
    
    return render(request, 'index.html', {
        'medicines_count': medicines_count,
        'dealers_count': dealers_count,
        'brands_count': brands_count,
        'categories': categories,
    })
