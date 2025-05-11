from django.db import models
from django.utils.timezone import now
from django.utils.text import slugify
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import random
import string
from datetime import timedelta

# Create your models here.

class CustomUserManager(BaseUserManager):
    def generate_random_id(self, length=8):
        characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
        return ''.join(random.choices(characters, k=length))

    def create_user(self, email, name, user_id=None, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        print("user_id in create user", user_id, email, name)
        if not user_id:
            user_id = self.generate_random_id()
        user = self.model(email=email, name=name, user_id=user_id)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, user_id=None):
        user = self.create_user(email=email, name=name, password=password, user_id=user_id)
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.CharField(default='', max_length=100, primary_key=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, default='')
    password = models.CharField(default='', max_length=255)  # Automatically handled by AbstractBaseUser
    register_datetime = models.DateTimeField(default=now)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Required for Django Admin
    is_superuser = models.BooleanField(default=False)  # Required for Django Admin

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'  # This is used for authentication
    REQUIRED_FIELDS = ['name']  # Required when creating a superuser

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name="subcategories")
    class Meta:
        db_table = 'category'
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parent.name} > {self.name}" if self.parent else self.name


class Brand(models.Model):
    brand_name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    main_image = models.ImageField(upload_to="media/brands/", blank=True, null=True)
    slogan = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brand"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.brand_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.brand_name
class Product(models.Model):
    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    description = models.TextField(blank=True)
    description_file = models.FileField(
        upload_to='media/products/descriptions/',
        null=True,
        blank=True,
        help_text="Upload a PDF to use as the description if `description` is empty."
    )
    ingredients = models.TextField(
        blank=True,
        help_text="List of ingredients, one per line or however you prefer."
    )
    how_to_use = models.TextField(
        blank=True,
        help_text="Instructions on how to use this product."
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    stock = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)
    main_image = models.ImageField(upload_to='media/products/')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'product'
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    # e.g. “100 ml”, “200 ml”, “Red / Large”, etc.
    name = models.CharField(max_length=100)

    # override prices, stock, sold_count per variant
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    stock = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'product_variant'
        unique_together = [["product", "name"]]
        ordering = ["product", "name"]

    def __str__(self):
        return f"{self.product.name} — {self.name}"
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="additional_images")
    image = models.ImageField(upload_to='media/products/')
    class Meta:
        db_table = 'product_image'
    def __str__(self):
        return f"Image of {self.product.name}"



class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    helpful_count = models.PositiveIntegerField(default=0)
    class Meta:
        db_table = 'review'
    def __str__(self):
        return f"Review by {self.user.name} - {self.product.name}"

class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='media/reviews/')

    class Meta:
        db_table = 'review_image'

    def __str__(self):
        return f"Image for review {self.review.id} - {self.review.product.name}"

class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'cart_item'
    def __str__(self):
        return f"{self.user.name} - {self.product.name} ({self.quantity})"



class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    pincode = models.CharField(max_length=10)
    house = models.CharField(max_length=255)  # House/Flat/Office No.
    road = models.CharField(max_length=255)  # Road Name/Area/Colony
    name = models.CharField(max_length=255)  # Recipient's Name
    phone = models.CharField(max_length=15)  # Contact Number
    email = models.EmailField(blank=True, null=True)  # Optional Email
    is_default = models.BooleanField(default=False)  # Default Address Toggle
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "address"

    def save(self, *args, **kwargs):
        """
        Ensure only one default address per user.
        If this is set as default, remove default from other addresses.
        """
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.name} - {self.house}, {self.road} ({'Default' if self.is_default else 'Secondary'})"

class PrepareOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    id = models.CharField(max_length=255, unique=True, primary_key=True)  # Unique identifier for the order
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Amount in INR
    currency = models.CharField(max_length=10, default="INR")  # Currency, default to INR
    receipt = models.CharField(max_length=255, blank=True, null=True)  # Receipt number
    partial_payment = models.BooleanField(default=False)  # Boolean for partial payment

    # Notes (storing key-value pairs as JSON)
    notes = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for order creation
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for last update
    class Meta:
        db_table = 'prepare_order'
    def __str__(self):
        return f"Order {self.id} - {self.amount} {self.currency}"


class Orders(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),  # 주문 처리 중
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('returned', 'Returned')
    ]
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_ref = models.OneToOneField(PrepareOrder, on_delete=models.CASCADE,
                                     unique=True)  # ✅ Keep it unique but not primary key

    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'
    def __str__(self):
        return f"Orders {self.id} - {self.user.name} ({self.status})"

class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name="order_items")  # ✅ References `Orders`
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ NEW
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at the time of order

    class Meta:
        db_table = "order_item"

    def __str__(self):
        return f"Order {self.order.id} - {self.product.name} ({self.quantity})"
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="wishlist_items")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Prevent duplicate wishlist items
        db_table = 'wishlist'

    def __str__(self):
        return f"{self.user.name} - {self.product.name}"



class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'email_otp'
    def is_expired(self):
        # Define the OTP validity period (e.g., 10 minutes)
        return now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"{self.email} - {self.otp} - Verified: {self.verified}"

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("fixed", "Fixed"),       # e.g. $10 off
        ("percent", "Percent"),   # e.g. 10% off
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default="fixed")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    usage_limit = models.PositiveIntegerField(default=1)  # How many times it can be used in total
    usage_count = models.PositiveIntegerField(default=0)  # How many times it has been used
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    def is_valid(self) -> bool:
        """Check if the coupon is currently valid for use."""
        now_ = now()
        return (
            self.is_active and
            self.usage_count <= self.usage_limit and
            self.valid_from <= now_ <= self.valid_to
        )

class UserCoupon(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_coupons")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="user_coupons")
    registered_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    class Meta:
        unique_together = ("user", "coupon")  # Each coupon can only be registered once per user

    def __str__(self):
        return f"{self.user.name} - {self.coupon.code}"

class CancelRefund(models.Model):
    STATUS_CHOICES = [
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cancel_refunds")
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name="cancel_refunds")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    reason = models.TextField(blank=True, null=True)  # Reason for cancel/return
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - Order #{self.order.id} - {self.status}"

class PaypalOrder(models.Model):
    order_id = models.CharField(max_length=64, unique=True)
    purchase_units = models.JSONField()
    intent = models.CharField(max_length=16, default="CAPTURE")
    experience_context = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=32)
    raw_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'paypal_order'
    def __str__(self):
        return self.order_id