from rest_framework import mixins, viewsets, status
from api.models import *
from api.serializers_files.serializers import ProductSerializer, ReviewSerializer, WishlistSerializer, BrandSerializer, AddressSerializer
from api.utility_files.api_call import get_body_data, api_failed, api_success
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

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

            return api_success("Wishlist fetched successfully", body={"wishlist": serialized_wishlist}).secure().rest()
        except Exception as e:
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