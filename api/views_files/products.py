from rest_framework import mixins, viewsets, status
from api.models import *
from api.serializers_files.serializers import ProductSerializer, ReviewSerializer, WishlistSerializer, BrandSerializer, \
    AddressSerializer, OrderHistorySerializer, CouponSerializer, UserCouponSerializer, CancelRefundSerializer
from api.utility_files.api_call import get_body_data, api_failed, api_success
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from dateutil.relativedelta import relativedelta
from django.db.models import Prefetch
#Product list
class GetProductListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Product.objects.all()

    def create(self, request, *args, **kwargs):
        category_name = get_body_data(request, "category", "").strip()
        subcategory_name = get_body_data(request, "subcategory", "").strip()
        print("category:", category_name, "| subcategory:", subcategory_name)

        try:
            # Find the parent category
            parent_category = Category.objects.filter(name=category_name, parent=None).first()
            if not parent_category:
                return api_failed("Invalid category", headers={"code": 1001}).secure().rest()

            # Get all subcategories under the parent
            subcategories = Category.objects.filter(parent=parent_category)

            # If subcategory is empty or "all", return products from all subcategories
            if not subcategory_name or subcategory_name.lower() == "all":
                products = Product.objects.prefetch_related("reviews__user").filter(category__in=[parent_category, *subcategories])
            else:
                # Find the exact subcategory
                subcategory = subcategories.filter(name=subcategory_name).first()
                if not subcategory:
                    return api_failed("Invalid subcategory", headers={"code": 1002}).secure().rest()
                products = Product.objects.prefetch_related("reviews__user").filter(category=subcategory)

            # Fetch reviews for these products
            reviews = Review.objects.filter(product__in=products)

            # Serialize products and reviews
            serialized_products = ProductSerializer(products, many=True, context={"request": request}).data
            serialized_reviews = ReviewSerializer(reviews, many=True, context={"request": request}).data

            return api_success("Products fetched successfully", body={"products": serialized_products, "reviews": serialized_reviews}).secure().rest()

        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while fetching products", headers={"code": 1003}).secure().rest()

#Product detail view
class GetProductDetailView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Product.objects.all()

    def create(self, request, *args, **kwargs):
        product_id = get_body_data(request, "product_id", "").strip()
        print("Fetching product:", product_id)

        try:
            # Fetch the product using the given ID
            product = Product.objects.prefetch_related("reviews__images", "reviews__user", "additional_images").get(id=product_id)

            # Fetch all reviews and prefetch related images
            reviews = product.reviews.all()

            print("product:", product)
            print("reviews:", reviews)

            # Serialize the product
            serialized_product = ProductSerializer(product, context={"request": request}).data
            serialized_reviews = ReviewSerializer(reviews, many=True, context={"request": request}).data

            return api_success(
                "Product fetched successfully",
                body={
                    "product_details": serialized_product,
                    "product_reviews": serialized_reviews
                }
            ).secure().rest()

        except ObjectDoesNotExist:
            return api_failed("Product not found", headers={"code": 1004}).secure().rest()

        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while fetching product details").secure().rest()

# Add product in user's wishlist
class AddRemoveWishlistView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Wishlist.objects.all()

    def create(self, request, *args, **kwargs):
        """Add or remove a product from the wishlist."""
        user = request.user
        product_id = request.data.get("product_id", "")
        user_id = request.data.get("user_id", "")

        if not product_id:
            return api_failed("Product ID is required", headers={"code": 1001}).secure().rest()

        try:
            product = get_object_or_404(Product, id=product_id)
            user = User.objects.get(user_id=user_id)

            # Check if the product is already in the user's wishlist
            wishlist_item = Wishlist.objects.filter(user=user, product=product).first()
            print("wishlist_item",wishlist_item)
            if wishlist_item:
                # Remove from wishlist
                wishlist_item.delete()
                return api_success("Product removed from wishlist", body={"product_id": product_id, "is_wishlisted": False}).secure().rest()
            else:
                # Add to wishlist
                Wishlist.objects.create(user=user, product=product)
                return api_success("Product added to wishlist", body={"product_id": product_id, "is_wishlisted": True}).secure().rest()

        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while updating wishlist").secure().rest()

class GetWishListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Wishlist.objects.all()
    serializer_class = WishlistSerializer

    def create(self, request, *args, **kwargs):
        """Fetch all wishlist items of the authenticated user."""
        user_id = request.data.get("user_id", "")
        try:
            user = User.objects.get(user_id=user_id)
            wishlist_items = Wishlist.objects.filter(user=user).select_related("product")
            serialized_wishlist = WishlistSerializer(wishlist_items, many=True, context={"request": request}).data
            if len(serialized_wishlist)>0:
                return api_success("Wishlist fetched successfully", body={"wishlist": serialized_wishlist}).secure().rest()
            else:
                return api_success("Wishlist fetched successfully", body={"wishlist": serialized_wishlist}).secure().rest()

        except Exception as e:
            print("e in GetWishListView", e)
            return api_failed("Error occurred while fetching wishlist").secure().rest()

class GetBrandListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer

    def create(self, request, *args, **kwargs):
        """Fetch all brands"""
        try:
            brands = Brand.objects.annotate(product_count=Count("products")).order_by("brand_name")
            print("brands", brands)
            serialized_brands = BrandSerializer(brands, many=True, context={"request": request}).data

            return api_success("Brand list fetched successfully", body={"brands": serialized_brands}).secure().rest()
        except Exception as e:
            print(e)
            return api_failed("Error occurred while fetching brands").secure().rest()

class GetBrandProductsView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Product.objects.all()

    def create(self, request, *args, **kwargs):
        """Fetch products by brand and subcategory."""
        brand_name = get_body_data(request, "brand", "").strip()
        subcategory_name = get_body_data(request, "subcategory", "").strip()
        print("Brand:", brand_name, "| Subcategory:", subcategory_name)

        try:
            # Find the brand
            brand = get_object_or_404(Brand, brand_name__iexact=brand_name)  # Case insensitive match
            print("brand", brand)
            # Base query: Get products of this brand
            products_query = Product.objects.filter(brand=brand).prefetch_related("reviews__images", "reviews__user", "additional_images")
            print("products_query", products_query)
            # Filter by subcategory if it's not "all"
            if subcategory_name.lower() != "all":
                parent_category = Category.objects.filter(name=subcategory_name).first()
                print("parent_category>>>>>>", parent_category)
                if not parent_category:
                    return api_failed("Sub category not found", headers={"code": 1002}).secure().rest()
                if parent_category:
                    child_subcategories = Category.objects.filter(parent=parent_category)
                    print("parent_category", parent_category)
                    if not child_subcategories:
                        return api_failed("Invalid subcategory", headers={"code": 1004}).secure().rest()
                    products_query = Product.objects.filter(Q(brand=brand) &
                                                            (Q(category=parent_category) | Q(category__in=child_subcategories))
                    ).prefetch_related("reviews__images", "reviews__user", "additional_images")

                print("products_query in if", products_query)
            # Fetch reviews for these products
            reviews = Review.objects.filter(product__in=products_query)

            # Serialize products and reviews
            serialized_products = ProductSerializer(products_query, many=True, context={"request": request}).data
            serialized_reviews = ReviewSerializer(reviews, many=True, context={"request": request}).data

            return api_success(
                "Products fetched successfully",
                body={
                    "brand": brand.brand_name,
                    "subcategory": subcategory_name,
                    "products": serialized_products,
                    "reviews": serialized_reviews
                },
            ).secure().rest()

        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while fetching products", headers={"code": 1003}).secure().rest()


class AddNewAddressView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

    def create(self, request, *args, **kwargs):
        """
        Save a new address and return updated address list.
        """
        user_id = get_body_data(request, "user_id", "").strip()
        pincode = get_body_data(request, "pincode", "").strip()
        house = get_body_data(request, "house", "").strip()
        road = get_body_data(request, "road", "").strip()
        name = get_body_data(request, "name", "").strip()
        phone = get_body_data(request, "phone", "").strip()
        email = get_body_data(request, "email", "").strip()
        is_default = get_body_data(request, "isDefault", False)
        print(user_id, pincode, house, road, name, phone, email, is_default)
        # Validate user existence
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed( "User not found", headers={"code":1004}).secure().rest()

        # Prepare address data
        address_data = {
            "user": user.user_id,
            "pincode": pincode,
            "house": house,
            "road": road,
            "name": name,
            "phone": phone,
            "email": email,
            "is_default": is_default,
        }

        # Serialize and save the address
        serializer = AddressSerializer(data=address_data)
        if serializer.is_valid():
            serializer.save()

            return api_success(
               "Address saved successfully", body={}
            ).secure().rest()
        return api_failed(serializer.errors, headers={"code":1004}).secure().rest()


class UpdateAddressView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

    def create(self, request, *args, **kwargs):
        """
        Save a new address and return updated address list.
        """
        user_id = get_body_data(request, "user_id", "").strip()
        address_id = get_body_data(request, "address_id", "")
        pincode = get_body_data(request, "pincode", "").strip()
        house = get_body_data(request, "house", "").strip()
        road = get_body_data(request, "road", "").strip()
        name = get_body_data(request, "name", "").strip()
        phone = get_body_data(request, "phone", "").strip()
        email = get_body_data(request, "email", "").strip()
        is_default = get_body_data(request, "isDefault", False)
        print(user_id, pincode, house, road, name, phone, email, is_default, address_id)
        # Validate user existence
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed("User not found", headers={"code": 1004}).secure().rest()

            # Validate address existence
        address = get_object_or_404(Address, id=address_id, user=user)
        if is_default:
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        address.pincode = pincode or address.pincode
        address.house = house or address.house
        address.road = road or address.road
        address.name = name or address.name
        address.phone = phone or address.phone
        address.email = email or address.email
        address.is_default = is_default

        # Save updated address
        address.save()

        return api_success(
           "Address updated successfully", body={}
        ).secure().rest()


class GetAddressListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

    def create(self, request, *args, **kwargs):
        """
        Save a new address and return updated address list.
        """
        user_id = get_body_data(request, "user_id", "").strip()
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed("User not found", headers={"code": 1004}).secure().rest()

            # Fetch and serialize addresses
        addresses = Address.objects.filter(user=user).order_by("-is_default", "-created_at")
        serialized_addresses = AddressSerializer(addresses, many=True).data

        return api_success("Addresses fetched successfully", body={"addressList": serialized_addresses}).secure().rest()

class DeleteAddressView(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

    def create(self, request, *args, **kwargs):
        """
        Delete an address using user_id and address_id.
        """
        user_id = get_body_data(request, "user_id", "").strip()
        address_id = get_body_data(request, "address_id", "")

        # Validate user
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed("User not found", headers={"code": 1004}).secure().rest()

        # Validate and delete address
        address = get_object_or_404(Address, id=address_id, user=user)
        address.delete()

        # Return updated address list
        updated_addresses = Address.objects.filter(user=user).order_by("-is_default", "-created_at")
        serialized_addresses = AddressSerializer(updated_addresses, many=True).data

        return api_success("Address deleted successfully", body={"addressList": serialized_addresses}).secure().rest()

from django.db.models import Q
from rest_framework import mixins, viewsets

class SearchProductsView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Product.objects.all()

    def create(self, request, *args, **kwargs):
        query = get_body_data(request, "query", "").strip()
        if not query:
            # If no query, return empty results
            return api_success("No search term provided", body={"products": [], "reviews": []}).secure().rest()

        try:
            # Filter products by name, description, or brand name (case-insensitive)
            products = Product.objects.prefetch_related("reviews__user").filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(brand__brand_name__icontains=query)
            )

            # Fetch all reviews for the filtered products
            reviews = Review.objects.filter(product__in=products)

            # Serialize products and reviews
            serialized_products = ProductSerializer(products, many=True, context={"request": request}).data
            serialized_reviews = ReviewSerializer(reviews, many=True, context={"request": request}).data

            return api_success("Search results", body={
                "products": serialized_products,
                "reviews": serialized_reviews
            }).secure().rest()

        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while searching products", headers={"code": 1003}).secure().rest()

class GetUserOrderHistoryView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Orders.objects.all()
    serializer_class = OrderHistorySerializer

    def create(self, request, *args, **kwargs):
        # 1. Extract user_id and range from the request body
        user_id = get_body_data(request, "user_id", "").strip()
        range_value = get_body_data(request, "range", "").strip().lower()  # e.g., "3m", "6m", "1y", "3y"

        if not user_id:
            return api_failed("User ID is required", headers={"code": 1001}).secure().rest()

        # 2. Validate the user
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed("User not found", headers={"code": 1004}).secure().rest()

        # 3. Determine the date cutoff based on the range
        filter_date = None
        if range_value == "3m":
            filter_date = now() - relativedelta(months=3)
        elif range_value == "6m":
            filter_date = now() - relativedelta(months=6)
        elif range_value == "1y":
            filter_date = now() - relativedelta(years=1)
        elif range_value == "3y":
            filter_date = now() - relativedelta(years=3)
        # If range_value is empty or invalid, we fetch all orders.

        try:
            # 4. Build the base queryset for the user's orders
            orders_qs = Orders.objects.filter(user=user)
            if filter_date:
                orders_qs = orders_qs.filter(created_at__gte=filter_date)

            # 5. Prefetch order_items and the related product (for product details)
            orders_qs = orders_qs.prefetch_related("order_items__product").order_by("-created_at")

            # 6. Serialize and return the order history
            serialized_orders = self.get_serializer(orders_qs, many=True, context={"request": request}).data
            return api_success("Order history fetched successfully", body={"orders": serialized_orders}).secure().rest()

        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while fetching order history", headers={"code": 1003}).secure().rest()

class RegisterCouponView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

    def create(self, request, *args, **kwargs):
        # 1. Extract data
        user_id = get_body_data(request, "user_id", "").strip()
        coupon_code = get_body_data(request, "coupon_code", "").strip()

        if not user_id or not coupon_code:
            return api_failed("user_id and coupon_code are required", headers={"code": 1001}).secure().rest()

        # 2. Validate user
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed("User not found", headers={"code": 1004}).secure().rest()

        # 3. Lookup coupon by code (case-insensitive)
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code)
        except Coupon.DoesNotExist:
            print("error coupon is not existed")
            return api_failed("Invalid coupon code", headers={"code": 1002}).secure().rest()
        print("coupon", coupon.code)
        # 4. Check if coupon is valid
        if not coupon.is_valid():
            return api_failed("Coupon is invalid or expired", headers={"code": 1003}).secure().rest()

        # 5. Check if user already registered this coupon
        if UserCoupon.objects.filter(user=user, coupon=coupon).exists():
            return api_failed("Coupon already registered by this user", headers={"code": 1005}).secure().rest()

        # 6. Mark usage and create user coupon record
        coupon.usage_count += 1
        coupon.save()

        user_coupon = UserCoupon.objects.create(user=user, coupon=coupon)

        # 7. Return success with coupon discount details and user coupon info
        return api_success(
            "Coupon applied successfully",
            body={
                "coupon_code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": str(coupon.discount_value),
                "user_coupon": UserCouponSerializer(user_coupon, context={"request": request}).data,
            }
        ).secure().rest()


class GetUserCouponView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = UserCouponSerializer

    def create(self, request, *args, **kwargs):
        # 1. Extract data
        user_id = get_body_data(request, "user_id", "").strip()
        try:
            if user_id:
                user = get_object_or_404(User, user_id=user_id)
                uc = UserCoupon.objects.filter(user=user).order_by("-registered_at")
                return api_success(
                    "Coupon fetched successfully",
                    body={
                        "user_coupon": UserCouponSerializer(uc, many=True, context={"request": request}).data,
                    }
                ).secure().rest()
            else:
                api_failed("No user id provided", headers={"code":1004}).secure().rest()
        except UserCoupon.DoesNotExist:
            print("No coupon provided")
            return api_failed("Registered Coupon is not found", headers={"code": 1005}).secure().rest()


class GetCancelRefundListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = CancelRefundSerializer

    def create(self, request, *args, **kwargs):
        user_id = get_body_data(request, "user_id").strip()
        status = get_body_data(request, "status", "").strip()
        range_value = get_body_data(request, "range", "").strip()

        if not user_id:
            return api_failed("User ID required", headers={"code": 1001}).secure().rest()

        user = User.objects.filter(user_id=user_id).first()
        if not user:
            return api_failed("User not found.", headers={"code": 1004}).secure().rest()

        cancel_refund_qs = CancelRefund.objects.filter(user=user)

        if status in ['cancelled', 'returned']:
            cancel_refund_qs = cancel_refund_qs.filter(status=status)

        from django.utils.timezone import now
        from dateutil.relativedelta import relativedelta

        filter_date = None
        if range_value == "3m":
            filter_date = now() - relativedelta(months=3)
        elif range_value == "6m":
            filter_date = now() - relativedelta(months=6)
        elif range_value == "1y":
            filter_date = now() - relativedelta(years=1)
        elif range_value == "3y":
            filter_date = now() - relativedelta(years=3)

        if filter_date:
            cancel_refund_qs = cancel_refund_qs.filter(created_at__gte=filter_date)

        cancel_refund_qs = cancel_refund_qs.select_related(
            "order",
            "order__address",
            "order__order_ref"
        ).prefetch_related(
            "order__order_items__product",
            "order__order_items__product__additional_images",
            "order__order_items__product__brand",
            "order__order_items__product__category"
        ).order_by("-created_at")

        # In your GetCancelRefundListView
        serialized_data = self.serializer_class(cancel_refund_qs, many=True, context={"request": request}).data
        return api_success("Cancel/Refund list fetched successfully.", body={"cancel_refund": serialized_data}).secure().rest()
class CancelRefundCreateView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = CancelRefundSerializer

    def create(self, request, *args, **kwargs):
        user_id = get_body_data(request, "user_id", "").strip()
        order_id = get_body_data(request, "order_id", "")
        status = get_body_data(request, "status", "").strip()
        reason = get_body_data(request, "reason", "").strip()

        if not user_id or not order_id or not status:
            return api_failed("All fields are required.", headers={"code": 1001}).secure().rest()

        user = User.objects.filter(user_id=user_id).first()
        order = Orders.objects.filter(id=order_id, user=user).first()

        if not user or not order:
            return api_failed("User or Order not found.", headers={"code": 1002}).secure().rest()

        # Check if already cancelled/returned
        if CancelRefund.objects.filter(user=user, order=order, status=status).exists():
            return api_failed("Already applied for this status.", headers={"code": 1003}).secure().rest()

            # Create CancelRefund entry
        cancel_refund = CancelRefund.objects.create(user=user, order=order, status=status, reason=reason)

        # Update the order's status based on the action
        order.status = status  # Update order status to 'cancelled' or 'returned'
        order.save()

        return api_success(f"Order {status} successfully applied.").secure().rest()

