
import os
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from api import views_files
from django.conf import settings
from django.conf.urls.static import static
from ecombackend.settings import BASE_DIR, ROOT_DIR, DEBUG
router = SimpleRouter()
router.register('get_csrf', views_files.GetCsrfView, basename='get_csrf')
router.register('register', views_files.RegisterView, basename='register')
router.register('login', views_files.LoginView, basename='login')
router.register('get_products', views_files.GetProductListView, basename='get_products')
router.register('get_product_detail', views_files.GetProductDetailView, basename='get_product_detail')
router.register('add_remove_wishlist', views_files.AddRemoveWishlistView, basename='add_remove_wishlist')
router.register('get_wishlist', views_files.GetWishListView, basename='get_wishlist')
router.register('get_brands_list', views_files.GetBrandListView, basename="get_brands_list")
router.register('get_brand_products', views_files.GetBrandProductsView, basename='get_brand_products')
router.register('add_new_address', views_files.AddNewAddressView, basename="add_new_address")
router.register('get_address_list', views_files.GetAddressListView, basename='get_address_list')
router.register('delete_user_address', views_files.DeleteAddressView, basename='delete_user_address')
router.register('update_user_address', views_files.UpdateAddressView, basename='update_user_address')
router.register('prepare_order', views_files.CreateOrderView, basename='prepare_order')
router.register('verify_order', views_files.VerifyOrderView, basename='verify_order')
urlpatterns = [
    # auth api
    path('', include(router.urls))
]
