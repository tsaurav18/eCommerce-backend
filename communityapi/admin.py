from django.contrib import admin

# Register your models here.
from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import *

admin.site.register(Story)
admin.site.register(LiveStream)
admin.site.register(LiveStreamComment)
admin.site.register(UserFollow)

