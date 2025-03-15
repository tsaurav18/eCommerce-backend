from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import *

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Review)
admin.site.register(CartItem)
admin.site.register(Orders)
admin.site.register(Wishlist)
admin.site.register(User)
admin.site.register(ReviewImage)
admin.site.register(Brand)
