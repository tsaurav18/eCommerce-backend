from rest_framework import serializers
from api.models import *

class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'image']

    def get_image(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "name",
            "price",
            "discount_price",
            "stock",
            "sold_count",
        ]

class ProductSerializer(serializers.ModelSerializer):
    main_image = serializers.SerializerMethodField()
    additional_images = ProductImageSerializer(many=True, read_only=True)
    discount_price = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    brand_name = serializers.CharField(source="brand.brand_name", read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    description_file = serializers.SerializerMethodField()
    ingredients = serializers.CharField(required=False, allow_blank=True)
    how_to_use = serializers.CharField(required=False, allow_blank=True)
    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description",
            "description_file",  # URL of uploaded PDF, if any
            "ingredients",
            "how_to_use",
            "variants",
            "price", "discount_price",
            "stock", "sold_count",
            "main_image", "additional_images",
            "brand",  # will still be the brand _id_
            "brand_name",  # now also the brand’s human-readable name
            "is_active", "created_at", "updated_at",
        ]

    def get_main_image(self, obj):
        request = self.context.get('request')
        if request and obj.main_image:
            print("obj.main_image.url", obj.main_image.url)
            full_url = request.build_absolute_uri(obj.main_image.url)
            print("Generated Image URL:", full_url)  # Debugging print statement
            return full_url
        return None

    def get_price(self, obj):
        return int(obj.price)
    def get_discount_price(self, obj):
        if obj.discount_price:
            return int(obj.discount_price)
        else:
            return None
    def get_description_file(self, obj):
        """Return absolute URL for the PDF, or None."""
        request = self.context.get('request')
        if request and obj.description_file:
            return request.build_absolute_uri(obj.description_file.url)
        return None
class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['id', 'image']

    def get_image(self, obj):
        """
        Convert image field to an absolute URL.
        """
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None
class ReviewSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True, context={'request': None})
    user_name = serializers.CharField(source="user.name", read_only=True)  # Get user name
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Review
        # fields = '__all__'
        fields = ['id', 'user', 'user_name', 'product', 'rating', 'comment', 'created_at', 'images', 'helpful_count']

    def to_representation(self, instance):
        """
        Pass `request` context to ReviewImageSerializer so that image URLs are absolute.
        """
        representation = super().to_representation(instance)
        request = self.context.get("request")
        if request:
            for image in representation.get("images", []):
                image["image"] = request.build_absolute_uri(image["image"])
        return representation

class WishlistSerializer(serializers.ModelSerializer):
    product_details = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ["id", "product", "product_details", "added_at"]

    def get_product_details(self, obj):
        return ProductSerializer(obj.product, context=self.context).data

class BrandSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    class Meta:
        model = Brand
        fields = ["id", "brand_name", "slug", "main_image", "slogan", "created_at", "products"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'

    def create(self, validated_data):
        """
        Ensure only one default address per user. If is_default=True,
        set all other addresses to is_default=False before saving.
        """
        print('validation in create', validated_data)
        user = validated_data.get("user")
        if validated_data.get("is_default", False):  # If new address is set as default
            Address.objects.filter(user=user, is_default=True).update(is_default=False)

        return super().create(validated_data)

class PrepareOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrepareOrder
        fields = "__all__"  # Include all fields

    def validate_amount(self, value):
        """Ensure the amount is a positive integer"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value

    def validate_currency(self, value):
        """Ensure currency is valid"""
        valid_currencies = ["INR"]
        if value not in valid_currencies:
            raise serializers.ValidationError("Invalid currency type")
        return value

class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = CartItem
        fields = ["product_id", "quantity", "price"]


class OrderItemSerializer(serializers.ModelSerializer):
    # This field will include full product details using the ProductSerializer
    product_details = ProductSerializer(source='product', read_only=True)
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    variant_name = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    def get_price(self, obj):
        return int(obj.price)

    def get_variant_name(self, obj):
        return obj.variant.name if obj.variant else None
    class Meta:
        model = OrderItem
        fields = ["product", "product_details", "variant_id",       # ✅ New input
            "variant_name", "quantity", "price"]

class SaveOrderSerializer(serializers.ModelSerializer):
    order_ref = serializers.PrimaryKeyRelatedField(queryset=PrepareOrder.objects.all())  # ✅ Link to PrepareOrder
    order_items = OrderItemSerializer(many=True)
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())

    class Meta:
        model = Orders
        fields = ["user", "order_ref", "order_items", "total_price", "status", "address"]  # ✅ Replacing order_id with order_ref

    def create(self, validated_data):
        order_items_data = validated_data.pop("order_items")
        order = Orders.objects.create(**validated_data)

        for item_data in order_items_data:
            variant_id = item_data.pop("variant_id", None)
            variant = None

            if variant_id:
                try:
                    variant = ProductVariant.objects.get(id=variant_id)
                except ProductVariant.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Variant with id {variant_id} does not exist."
                    )

            OrderItem.objects.create(
                order=order,
                variant=variant,
                **item_data
            )

        return order


class OrderHistorySerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    order_ref = PrepareOrderSerializer(read_only=True)
    address = AddressSerializer(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    total_price = serializers.SerializerMethodField()
    def get_total_price(self, obj):
        return int(obj.total_price)
    class Meta:
        model = Orders
        fields = [
            "id",
            "order_ref",
            "order_items",
            "total_price",
            "status",
            "address",
            "created_at"
        ]
class CouponSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    discount_value = serializers.SerializerMethodField()
    def get_discount_value(self, obj):
        # Convert the discount value to an int (e.g., 10.00 -> 10)
        return int(obj.discount_value)
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "is_active",
            "usage_count",
            "usage_limit",
            "valid_from",
            "valid_to",
            "created_at",
        ]

class UserCouponSerializer(serializers.ModelSerializer):
    coupon_details = CouponSerializer(source="coupon", read_only=True)
    registered_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    is_used = serializers.SerializerMethodField()

    def get_is_used(self, obj):
        # If your model doesn't store this explicitly, define the logic here.
        # For example, if you add a boolean field 'used' in your UserCoupon model, you can do:
        return getattr(obj, "is_used", False)
    class Meta:
        model = UserCoupon
        fields = ["id", "coupon", "coupon_details", "registered_at", "is_used"]

class CancelRefundSerializer(serializers.ModelSerializer):
    # If you want to nest order details, you can use an Order serializer:
    order_details = OrderHistorySerializer(source="order", read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = CancelRefund
        fields = [
            "id",
            "user",
            "order",
            "status",
            "reason",
            "created_at",
            "order_details",
        ]

class PaypalCreateOrderSerializer(serializers.Serializer):
    purchase_units = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
    user = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    intent = serializers.CharField(default='CAPTURE')
    experience_context = serializers.DictField(required=False)
    def validate_amount(self, value):
        """Ensure the amount is a positive integer"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
class PaypalCaptureOrderSerializer(serializers.Serializer):
    orderID = serializers.CharField()
