from rest_framework import serializers

from api.utility_files.api_call import get_body_data
from consultantapi.models import *



class CourseSerializer(serializers.ModelSerializer):
    learners = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    category = serializers.CharField(default="", read_only=True)
    featured = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "image",
            "description",
            "price",
            "publisher",
            "level",
            "is_free",
            "created_at",
            "learners",
            "duration",
            "type",
            "category",
            "featured",
        ]

    def get_learners(self, obj):
        # Calculate the number of learners by counting related enrollments
        return obj.enrollments.count()

    def get_duration(self, obj):
        # As duration is not stored, return a default value.
        # You could update this logic if you add a duration field later.
        return "1 hrs"

    def get_type(self, obj):
        # For example, if the course is free, you might label it as "Certificate",
        # otherwise "Diploma". Adjust the logic as needed.
        return "Certificate" if obj.is_free else "Diploma"

class CourseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseUser
        fields = ['user_id', 'email']


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), source='course', write_only=True
    )
    user = CourseUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CourseUser.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = Enrollment
        fields = ['id', 'user', 'user_id', 'course', 'course_id', 'enrolled_at']


class CoursePaymentSerializer(serializers.ModelSerializer):
    enrollment = EnrollmentSerializer(read_only=True)

    class Meta:
        model = CoursePayment
        fields = '__all__'



class CourseVideoSerializer(serializers.ModelSerializer):
    video_source = serializers.SerializerMethodField()

    class Meta:
        model = CourseVideo
        fields = ['id', 'course', 'title', 'video_source', 'description', 'created_at']

    def get_video_source(self, obj):
        # Return the URL of the video file if it exists; otherwise, return the video_url field.
        if obj.video_file:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.video_file.url)
        return obj.video_url

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']



class CourseContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseContact
        fields = ['id', 'name', 'email', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']

class BookPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookPackage
        fields = ["id", "service", "package", "name", "email", "phone", "arrival_date"]

class VisaPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaPackage
        fields = [
            'package_id',
            'name',
            'price',
            'service_include',
        ]

class VisaServiceDetailSerializer(serializers.ModelSerializer):
    packages = VisaPackageSerializer(many=True, read_only=True)

    class Meta:
        model = VisaService
        fields = ["visa_type", "title", "description", "image", "packages"]

class VisaServiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaService
        fields = ("visa_type", "title", "description", "image")