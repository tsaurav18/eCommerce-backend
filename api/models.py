from django.db import models
from django.utils.timezone import now
from django.utils.text import slugify
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# Create your models here.

class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, user_id, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name)
        user.user_id = str(user_id)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None):
        user = self.create_user(email=email, name=name, password=password)
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
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
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

class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='media/reviews/')

    class Meta:
        db_table = 'review_image'

    def __str__(self):
        return f"Image for review {self.review.id} - {self.review.product.name}"

