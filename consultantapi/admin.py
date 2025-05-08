from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import *


admin.site.register(CourseUser)
admin.site.register(Course)
admin.site.register(CourseVideo)
admin.site.register(Enrollment)
admin.site.register(CoursePayment)
admin.site.register(ContactMessage)
admin.site.register(CourseContact)
admin.site.register(BookPackage)
admin.site.register(VisaPackage)
admin.site.register(VisaService)
