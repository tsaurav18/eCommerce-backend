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
class ProductSerializer(serializers.ModelSerializer):
    main_image = serializers.SerializerMethodField()
    additional_images = ProductImageSerializer(many=True, read_only=True)
    discount_price = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = '__all__'  # This includes all fields in the Product model

    def get_main_image(self, obj):
        request = self.context.get('request')
        if request and obj.main_image:
            full_url = request.build_absolute_uri(obj.main_image.url)
            print("Generated Image URL:", full_url)  # Debugging print statement
            return full_url
        return None
    def get_price(self, obj):
        return int(obj.price)
    def get_discount_price(self, obj):
        return int(obj.discount_price)
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