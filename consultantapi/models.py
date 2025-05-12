from django.db import models
import random, string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.timezone import now
from django.contrib.auth.backends import BaseBackend

class CourseUserManager(BaseUserManager):
    def generate_random_id(self, length=8):
        characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
        return ''.join(random.choices(characters, k=length))

    def create_user(self, email, name, user_id=None, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
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

class CourseUser(AbstractBaseUser, PermissionsMixin):
    user_id = models.CharField(max_length=100, primary_key=True, default='')
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, default='')
    password = models.CharField(max_length=255, default='')
    register_datetime = models.DateTimeField(default=now)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Override the default groups and user_permissions fields with unique related_names
    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name="course_users",  # Unique related name for CourseUser
        help_text="The groups this user belongs to.",
        verbose_name="groups"
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name="course_users_permissions",  # Unique related name for CourseUser
        help_text="Specific permissions for this user.",
        verbose_name="user permissions"
    )

    objects = CourseUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'course_user'

    def __str__(self):
        return self.name

class CourseUserBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = CourseUser.objects.get(email=email)
            if user.check_password(password):
                return user
        except CourseUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return CourseUser.objects.get(pk=user_id)
        except CourseUser.DoesNotExist:
            return None
class Course(models.Model):
    COURSE_TYPE_CHOICES = (
        ('free', 'Free'),
        ('paid', 'Paid'),
        ('drama', 'Drama'),
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='courses/')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    publisher = models.CharField(max_length=255, default="ezzikroean")
    level = models.CharField(max_length=255, default="beginner")
    is_free = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    course_type = models.CharField(max_length=255, choices=COURSE_TYPE_CHOICES, default="free")
    class Meta:
        db_table = 'course'
    def __str__(self):
        return self.title
class CourseVideo(models.Model):
    course = models.ForeignKey(Course, related_name='videos', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='course_videos/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'course_video'
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Enrollment(models.Model):
    user = models.ForeignKey(CourseUser, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')
        db_table = 'course_enrollment'

    def __str__(self):
        return f"{self.user.user_id} - {self.course.title}"

class CoursePayment(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='course_payment')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=(('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')),
        default='pending'
    )
    paid_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'course_payment'
    def __str__(self):
        return f"Course Payment for {self.enrollment}"
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "contact_message"
    def __str__(self):
        return f"Message from {self.name} ({self.email})"

class CourseContact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "course_contact"
    def __str__(self):
        return f"Message from {self.name} ({self.email})"

class VisaService(models.Model):
    """
    Represents one of the 4 hero-cards (D-2, D-4, E-6, C-4).
    Holds a title, description, hero image, and relates to many VisaPackage entries.
    """
    VISA_CHOICES = [
        ('D2', 'D-2 Student'),
        ('D4', 'D-4 Language Training'),
        ('E6', 'E-6 Entertainment'),
        ('C4', 'C-4 Short-Term Work'),
    ]

    visa_type   = models.CharField(
        max_length=4,                    # must fit "D-2", "D-4" etc.
        choices=VISA_CHOICES,
        unique=True,
        help_text="Which visa this service represents",


    )
    title       = models.CharField(max_length=128)
    description = models.TextField()
    # If you store images locally:
    image       = models.ImageField(upload_to="visa_services/", blank=True, null=True)
    # or if you prefer external URLs:
    # image_url = models.URLField(blank=True, null=True)

    class Meta:
        db_table = "visa_service"
        ordering  = ["visa_type"]

    def __str__(self):
        return f"{self.get_visa_type_display()} Service"

class VisaPackage(models.Model):
    """
    Optional: If you want to manage your packages in the DB,
    you can define this model and FK from BookPackage.
    """
    VISA_CHOICES = [
        ('D2', 'D-2 Student'),
        ('D4', 'D-4 Language Training'),
        ('E6', 'E-6 Entertainment'),
        ('C4', 'C-4 Short-Term Work'),
    ]
    service = models.ForeignKey(
        VisaService,
        on_delete=models.CASCADE,

        related_name = "packages",
        null = True,  # allow NULL on existing rows
        blank = True,
    )

    package_id = models.CharField(max_length=32)  # e.g. "basic", "standard", etc.
    name = models.CharField(max_length=64)
    price = models.PositiveIntegerField(help_text="Price in USD cents or your currency")
    service_include = models.TextField(default='', blank=True)
    class Meta:
        db_table = "visa_package"
        unique_together = [("service", "package_id")]
    def __str__(self):
        return f"{self.service.visa_type} – {self.package_id}"


class BookPackage(models.Model):
    """
    Stores a user’s booking request for a visa package.
    """
    # If you created VisaPackage above, you can instead do:
    # package = models.ForeignKey(VisaPackage, on_delete=models.PROTECT)
    service = models.ForeignKey(VisaService, on_delete=models.CASCADE)
    package = models.ForeignKey(
        VisaPackage,
        on_delete=models.CASCADE,
        null=True,  # <-- allow nulls
        blank=True,  # <-- on the Django form side
    )

    # Contact / booking details
    name = models.CharField("Full Name", max_length=128)
    email = models.EmailField("Email Address")
    phone = models.CharField("Phone Number", max_length=32)
    arrival_date = models.DateField("Planned Arrival Date")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed = models.BooleanField(
        default=False,
        help_text="Set to true once the booking is processed/confirmed"
    )

    class Meta:
        db_table = "book_package"
        ordering = ["-created_at"]
        verbose_name = "Visa Package Booking"
        verbose_name_plural = "Visa Package Bookings"

    def __str__(self):
        return f"{self.name} → {self.service.visa_type}/{self.package.package_id} @ {self.created_at:%Y-%m-%d}"

