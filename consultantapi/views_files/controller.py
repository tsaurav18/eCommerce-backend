import traceback
from django.db import IntegrityError
from django.db.models import Count
from rest_framework import viewsets, mixins, status,permissions
from rest_framework.response import Response
from django.middleware.csrf import get_token
from django.core.exceptions import ObjectDoesNotExist
from api.models import EmailOTP
from api.utility_files.api_call import api_success, api_failed
from api.utility_files.utils import generate_user_id
from ..models import *
from django.core.mail import send_mail
import requests
from django.conf import settings
from django.contrib.auth import authenticate
from ..serializers_files.serializers import *
from django.shortcuts import get_object_or_404
MAX_GENERATE_ATTEMPT = 10
class GetCsrfView(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = []

    def list(self, request, *args, **kwargs):
        token = get_token(request)
        return Response({'token': token}, status=status.HTTP_200_OK)


class CourseRegisterView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Register a new courses user.
    """
    queryset = CourseUser.objects.all()
    serializer_class = CourseUserSerializer
    # permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        name = get_body_data(request, "name", "").strip()
        email = get_body_data(request, "email", "").strip()
        password = get_body_data(request, "password", "").strip()
        if not name or not email or not password:
            return api_failed("Fill up all the fields", headers={"code": 1004}).secure().rest()
        # Check if courses user already exists
        if CourseUser.objects.filter(email=email).exists():
            return api_failed("User already exists", headers={"code": 1000}).secure().rest()
        try:
            user_id = generate_user_id(name, email, max_iter=MAX_GENERATE_ATTEMPT)
        except Exception as e:
            return api_failed("Error occurred while creating user id", headers={"code": 1002}).secure().rest()
        try:
            user = CourseUser.objects.create_user(email=email, name=name, user_id=user_id, password=password)
            user.last_login = now()
            user.save()
            print("user is saved", user)
            user_data = {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
            }
            return api_success("Register success", body={"user_data": user_data}).secure().rest()
        except Exception as e:
            traceback.print_exc()
            return api_failed("Error occurred while creating user", headers={"code": 1003}).secure().rest()


class CourseLoginView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Login a courses user.
    """
    queryset = CourseUser.objects.all()
    # permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        email = get_body_data(request, "email", "").strip()
        password = get_body_data(request, "password", "").strip()

        if not email or not password:
            return api_failed("Fill up all fields.", headers={"code": 1004}).secure().rest()
        try:
            user = CourseUser.objects.get(email=email)

        except ObjectDoesNotExist:
            return api_failed("User not found", headers={"code": 1005}).secure().rest()
        # Use Django's authentication mechanism


        user = authenticate(request, email=email, password=password)

        if user is not None:
            user.last_login = now()
            user.save()
            user_data = {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
            }
            return api_success("Login success", body={"user_data": user_data}).secure().rest()

        else:
            return api_failed("Incorrect password", headers={"code": 1006}).secure().rest()


class CourseSendOtpView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Send an OTP to the courses user's email for verification.
    """
    queryset = EmailOTP.objects.all()

    def create(self, request, *args, **kwargs):
        email = get_body_data(request, "email", "").strip()
        if not email:
            return api_failed("Email is required", headers={"code": 1010}).secure().rest()
        # Generate a 6-digit OTP
        otp = str(random.randint(100000, 999999))
        # Create an OTP entry (make sure your EmailOTP model has fields: email, otp, verified, created_at, etc.)
        otp_entry = EmailOTP.objects.create(email=email, otp=otp)
        subject = "Your Course OTP Verification Code"
        message = (
            f"Hello,\n\n"
            f"Thank you for signing up with our Course Platform.\n\n"
            f"Your One Time Password (OTP) is: {otp}\n\n"
            f"This code is valid for 10 minutes.\n\n"
            f"Best regards,\n"
            f"The Course Team"
        )
        from_email = "your_email@example.com"  # Replace with your sender email
        recipient_list = [email]
        try:
            send_mail(subject, message, from_email, recipient_list)
        except Exception as e:
            print("Error sending email:", e)
            return api_failed("Error sending email", headers={"code": 1011}).secure().rest()
        return api_success("OTP sent successfully", body={"otp_sent": True}).secure().rest()


class CourseVerifyOtpView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Verify the OTP for the courses user.
    """
    queryset = EmailOTP.objects.all()
    # permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        email = get_body_data(request, "email", "").strip()
        otp = get_body_data(request, "otp", "").strip()
        if not email or not otp:
            return api_failed("Email and OTP are required", headers={"code": 1012}).secure().rest()
        try:
            otp_entry = EmailOTP.objects.filter(email=email, otp=otp, verified=False).latest('created_at')
        except EmailOTP.DoesNotExist:
            return api_failed("Invalid OTP", headers={"code": 1013}).secure().rest()
        # Assuming your EmailOTP model has an is_expired() method
        if otp_entry.is_expired():
            return api_failed("OTP expired", headers={"code": 1014}).secure().rest()
        otp_entry.verified = True
        otp_entry.save()
        return api_success("OTP verified successfully", body={"otp_verified": True}).secure().rest()


class CourseGoogleLoginView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Login or register a courses user using Google authentication.
    """
    queryset = CourseUser.objects.all()
    # permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        name = get_body_data(request, "name", "").strip()
        email = get_body_data(request, "email", "").strip()
        google_token = get_body_data(request, "google_token", "").strip()
        if not email or not name:
            return api_failed("Name and email are required", headers={"code": 1020}).secure().rest()
        try:
            user = CourseUser.objects.filter(email=email).first()
            if not user:
                try:
                    user_id = generate_user_id(name, email, max_iter= MAX_GENERATE_ATTEMPT)
                except Exception as e:
                    return api_failed("Error occurred while creating user id", headers={"code": 1002}).secure().rest()
                # Since Google manages authentication, you may set a dummy password.
                user = CourseUser.objects.create_user(email=email, name=name, user_id=user_id, password="")
            user.last_login = now()
            user.save()
            user_data = {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
            }
            return api_success("Google login success", body={"user_data": user_data}).secure().rest()
        except Exception as e:
            traceback.print_exc()
            return api_failed("Error occurred during Google login", headers={"code": 1021}).secure().rest()




class CourseListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = CourseSerializer
    # permission_classes = [permissions.AllowAny]  # adjust as needed

    def create(self, request, *args, **kwargs):
        try:
            course_type = get_body_data(request, "course_type", '').strip()
            queryset = Course.objects.all().filter(course_type=course_type).order_by('-created_at')
            serializer = self.get_serializer(queryset, many=True)
            return api_success("Courses retrieved successfully", body={"data": serializer.data}).secure().rest()
        except Exception as e:
            return api_failed("Error retrieving courses", headers={"code": 1002}).secure().rest()


class CourseDetailView(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    # permission_classes = [permissions.AllowAny]  # adjust as needed

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return api_success("Course details retrieved successfully", body={"data": serializer.data}).secure().rest()
        except Exception as e:
            return api_failed("Error retrieving course details", headers={"code": 1002}).secure().rest()


class CheckEnrollCourseView(viewsets.GenericViewSet, mixins.CreateModelMixin):

    serializer_class = EnrollmentSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user_id = get_body_data(request, "user_id", "").strip()
        course_id = get_body_data(request, "course_id", "")

        try:

            queryset = Enrollment.objects.filter(user_id=user_id, course_id=course_id)

            if len(queryset)>0:
                return api_success("User is already enrolled in this course").secure().rest()
            else:
                return api_failed("User is not enrolled in this course", headers={"code": 1001}).secure().rest()
        except Exception as e:
            print("error enrolling course details", e)
            return api_failed("Error enrolling in course", headers={"code": 1002}).secure().rest()

class EnrollCourseView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):

        try:
            serializer = self.get_serializer(data=request.data)


            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return api_success("Enrolled successfully", body={"data": serializer.data}).secure().rest()
        except IntegrityError as e:
            # Likely due to the unique_together constraint (user already enrolled)
            return api_failed("User is already enrolled in this course", headers={"code": 1007}).secure().rest()
        except Exception as e:
            print("error enrolling course details", e)
            return api_failed("Error enrolling in course", headers={"code": 1002}).secure().rest()

class CoursePaymentView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = CoursePayment.objects.all()
    serializer_class = CoursePaymentSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return api_success("Payment processed successfully", body={"data": serializer.data}).secure().rest()
        except Exception as e:
            return api_failed("Error processing payment", headers={"code": 1002}).secure().rest()




class UserDetailView(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    serializer_class = CourseUserSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            serializer = self.get_serializer(user)
            return api_success("User details retrieved", body={"data": serializer.data}).secure().rest()
        except Exception as e:
            return api_failed("Error retrieving user details", headers={"code": 1002}).secure().rest()


class CourseVideoListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = CourseVideoSerializer
    # permission_classes = [permissions.IsAuthenticated]  # adjust if needed

    def get_queryset(self, request, *args, **kwargs):

        course_id = get_body_data(request, "course_id", "")
        return CourseVideo.objects.filter(course_id=course_id).order_by('created_at')

    def create(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset(request, *args, **kwargs)

            serializer = self.get_serializer(queryset, many=True, context={'request': request})
            return api_success("Course videos retrieved successfully", body={"data": serializer.data}).secure().rest()
        except Exception as e:
            return api_failed("Error retrieving course videos", headers={"code": 1002}).secure().rest()




class CreateContactMessageView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Submit a contact message.
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

    def create(self, request, *args, **kwargs):
        """
        Handles contact form submission and optionally triggers external API (e.g., notify or log).
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            # Optional: You could add external API integration here if needed
            # self.notify_external_service(serializer.data)
            return api_success("successfully submitted",
                               body={"data": serializer.data}).secure().rest()

        except Exception as e:
            return api_failed("Error occured", headers={"code": 1002}).secure().rest()
    def notify_external_service(self, data):
        try:
            url = "https://example.com/webhook"
            headers = {
                "Authorization": f"Bearer {settings.MY_API_TOKEN}",
                "Content-Type": "application/json",
            }
            payload = {
                "name": data["name"],
                "email": data["email"],
                "message": data["message"]
            }
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except Exception as e:
            print("Error notifying external service:", e)


class CreateCoursesContactView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Submit a contact message.
    """
    queryset = CourseContact.objects.all()
    serializer_class = CourseContactSerializer

    def create(self, request, *args, **kwargs):
        """
        Handles contact form submission and optionally triggers external API (e.g., notify or log).
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            # Optional: You could add external API integration here if needed
            # self.notify_external_service(serializer.data)
            return api_success("successfully submitted",
                               body={"data": serializer.data}).secure().rest()

        except Exception as e:
            return api_failed("Error occured", headers={"code": 1002}).secure().rest()


class TotalLearnersView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    API endpoint to compute total number of learners across all courses,
    including a breakdown by course_type (free, paid, drama).
    """
    # No queryset or serializer needed because we compute data dynamically.
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            total_learners = Enrollment.objects.count()
            # Compute breakdown per course_type:
            # Assumes Course has a field 'course_type' with choices: free, paid, drama
            breakdown = Course.objects.values('course_type').annotate(
                learners=Count('enrollments')
            )
            # Transform breakdown into a dictionary for easy consumption:
            breakdown_dict = {entry["course_type"]: entry["learners"] for entry in breakdown}
            return api_success(
                "Total learners computed",
                body={
                    "total_learners": total_learners,
                    "breakdown": breakdown_dict
                }
            ).secure().rest()
        except Exception as e:
            print("Error computing total learners:", e)
            return api_failed("Error computing total learners", headers={"code": 1008}).secure().rest()


class BookVisaPackageView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = BookPackage.objects.all()
    serializer_class = BookPackageSerializer

    def create(self, request, *args, **kwargs):
        # Extract all necessary fields from the encrypted request body
        visa_type   = get_body_data(request, "visaType", "").strip()
        package_id  = get_body_data(request, "packageId", "").strip()
        name        = get_body_data(request, "name", "").strip()
        email       = get_body_data(request, "email", "").strip()
        phone       = get_body_data(request, "phone", "").strip()
        arrival_date= get_body_data(request, "arrivalDate", "").strip()

        print("visa_type",visa_type, "package_id",package_id, name, email,phone,arrival_date)
        # 2) look up the service
        service = get_object_or_404(VisaService, visa_type=visa_type)

        # 3) look up the package under that service
        pkg = get_object_or_404(VisaPackage,
                                service=service,
                                package_id=package_id)
        # Build payload for serializer
        booking_data = {
            "service": service.pk,
            "package": pkg.pk,
            "name": name,
            "email": email,
            "phone": phone,
            "arrival_date": arrival_date,
        }

        # Deserialize, validate, and save
        serializer = self.get_serializer(data=booking_data)
        print("booking_data", booking_data)
        if serializer.is_valid():
            booking = serializer.save()

            # Return the newly created booking back to the frontend
            return api_success(
                "Booking created successfully",
                body={"booking": BookPackageSerializer(booking).data}
            ).secure().rest()
        else:
            errors = serializer.errors  # e.g. {'email': ['Enter a valid email address.'], 'phone': ['This field may not be blank.']}
            messages = []
            for field, err_list in errors.items():
                for err in err_list:
                    messages.append(f"{field}: {err}")
            error_message = " ".join(messages)
            print("error", serializer.errors)
            # Validation errors
            return api_failed(error_message, headers={"code": 1005}).secure().rest()


class GetVisaServiceListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = VisaService.objects.all()
    serializer_class = VisaServiceListSerializer

    def create(self, request, *args, **kwargs):
        # Extract all necessary fields from the encrypted request body

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            return self.get_paginated_response(data)

        serializer = self.get_serializer(queryset, many=True)
        return api_success(
            "Success",
            body={"results": serializer.data}
        ).secure().rest()

class GetVisaPackageDetailsView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = VisaPackage.objects.all()
    serializer_class = VisaServiceDetailSerializer

    def create(self, request, *args, **kwargs):
        visa_type = get_body_data(request, "visa_type", "").strip()

        try:
            service = get_object_or_404(VisaService, visa_type=visa_type)
            serializer = self.get_serializer(service)

            return api_success(
                "Fetched service and packages successfully",
                body={"service": serializer.data}
            ).secure().rest()

        except Exception as e:
            print("exception", e)
            return api_failed(str(e), headers={"code": 1005}).secure().rest()
