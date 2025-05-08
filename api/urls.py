
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from api import views_files

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
router.register("save_order", views_files.SaveOrdersView, basename="save_order")
router.register("sent_otp", views_files.SendOtpView, basename="sent_otp")
router.register("verify_otp", views_files.VerifyOtpView, basename="verify_otp")
router.register("google_login", views_files.GoogleLoginView, basename="google_login")
router.register("search_products", views_files.SearchProductsView, basename="search_products")
router.register("get_order_history", views_files.GetUserOrderHistoryView, basename="get_order_history")
router.register("register_coupon", views_files.RegisterCouponView, basename='register_coupon')
router.register("get_user_coupons", views_files.GetUserCouponView, basename='get_user_coupons')
router.register("get_cancel_refund_list", views_files.GetCancelRefundListView, basename="get_cancel_refund_list")
router.register("cancel_return_order", views_files.CancelRefundCreateView, basename='cancel_return_order')
router.register('create_paypal_order', views_files.PaypalCreateOrderView, basename='create_paypal_order')
router.register('paypal_capture_order', views_files.PaypalCaptureOrderView, basename='paypal_capture_order')

urlpatterns = [
    # auth api
    path('', include(router.urls)),
    path('community/', include('communityapi.urls')),
    path('consultant/', include('consultantapi.urls')),
]
