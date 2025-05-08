from django.contrib.auth.hashers import make_password,check_password
from django.forms import model_to_dict
from django.middleware.csrf import get_token
from rest_framework.response import Response
from rest_framework import mixins, viewsets, status
from api.models import *
from api.utility_files.api_call import get_body_data, api_failed, api_success
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from api.utility_files.utils import generate_user_id
from django.contrib.auth import authenticate
from django.utils.timezone import now
from django.core.mail import send_mail
MAX_GENERATE_ATTEMPT = 10
class GetCsrfView(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = []

    def list(self, request, *args, **kwargs):
        token = get_token(request)
        return Response({'token': token}, status=status.HTTP_200_OK)

class RegisterView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = User.objects.all()

    def model_to_dict_with_date_conversion(self, instance):
        data_dict = model_to_dict(instance)
        for field, value in data_dict.items():
            if isinstance(value, datetime):
                data_dict[field] = value.date().isoformat()
        return data_dict

    def create(self, request, *args, **kwargs):
        name = get_body_data(request, "name", "").strip()
        email = get_body_data(request, "email", "").strip()
        password = get_body_data(request, "password", "").strip()
        print(name, email, password)
        if not name or not email or not password:
            return api_failed("Fill up all the fields", headers={"code": 1004}).secure().rest()

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return api_failed("User is already existed", headers={"code": 1000}).secure().rest()

        try:
            user_id = generate_user_id(name, email, max_iter=MAX_GENERATE_ATTEMPT)
        except Exception as e:
            return api_failed("Error occured while creating user", headers={"code": 1002}).secure().rest()
        try:
            # Create the user using the manager
            user = User.objects.create_user(email=email, name=name, user_id=user_id, password=password)
            user.last_login = now()
            user.save()

            user_data = self.model_to_dict_with_date_conversion(user)
            return api_success("Register success", body={"user_data": user_data}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occured while creating user", headers={"code": 1003}).secure().rest()



class LoginView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        email = get_body_data(request, "email", "").strip()
        password = get_body_data(request, "password", "").strip()

        if not email or not password:
            return api_failed("Fill up all the fields.", headers={"code": 1004}).secure().rest()

        try:
            user = User.objects.get(email=email)
        except ObjectDoesNotExist:
            return api_failed("User not found", headers={"code": 1005}).secure().rest()

        # Authenticate using Django's built-in method
        user = authenticate(request, email=email, password=password)
        if user is not None:
            user.last_login = now()
            user.save()  # Don't forget to save the updated last_login!
            user_data = {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
            }
            return api_success("Login success", body={"user_data": user_data}).secure().rest()
        else:
            # Authentication failed, so user is None
            return api_failed("You entered wrong password", headers={"code": 1006}).secure().rest()
class SendOtpView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = EmailOTP.objects.all()

    def create(self, request, *args, **kwargs):
        email = get_body_data(request, "email", "").strip()
        if not email:
            return api_failed("Email is required", headers={"code": 1010}).secure().rest()
        print("email", email)
        # Generate a 6-digit OTP
        otp = str(random.randint(100000, 999999))
        print("otp", otp)
        # Save the OTP record (you could also delete/expire previous OTPs for the same email)
        otp_entry = EmailOTP.objects.create(email=email, otp=otp)

        # Prepare email content
        subject = "Your Eleve OTP Verification Code"
        message = (
            f"Hello,\n\n"
            f"Thank you for signing up with Eleve.\n\n"
            f"Your One Time Password (OTP) is: {otp}\n\n"
            f"Please enter this code on our website to verify your email address. "
            f"This code is valid for 10 minutes.\n\n"
            f"If you did not request this code, please ignore this email or contact our support.\n\n"
            f"Best regards,\n"
            f"The Eleve Team"
        )
        from_email = "tsaurav1711@gmail.com"  # Change to your sender email
        recipient_list = [email]

        try:
            send_mail(subject, message, from_email, recipient_list)

        except Exception as e:
            # Log the error as needed
            print("exception", e)
            return api_failed("Error sending email", headers={"code": 1011}).secure().rest()

        return api_success("OTP sent successfully", body={"otp_sent": True}).secure().rest()

class VerifyOtpView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = EmailOTP.objects.all()

    def create(self, request, *args, **kwargs):
        email = get_body_data(request, "email", "").strip()
        otp = get_body_data(request, "otp", "").strip()
        if not email or not otp:
            return api_failed("Email and OTP are required", headers={"code": 1012}).secure().rest()

        # Try to retrieve the latest OTP entry that matches and is not yet verified
        try:
            otp_entry = EmailOTP.objects.filter(email=email, otp=otp, verified=False).latest('created_at')
        except EmailOTP.DoesNotExist:
            return api_failed("Invalid OTP", headers={"code": 1013}).secure().rest()

        # Check if the OTP is expired
        if otp_entry.is_expired():
            return api_failed("OTP expired", headers={"code": 1014}).secure().rest()

        # Mark the OTP as verified
        otp_entry.verified = True
        otp_entry.save()

        return api_success("OTP verified successfully", body={"otp_verified": True}).secure().rest()


class GoogleLoginView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        # Extract fields from request body (assumes name and email are sent from frontend)
        name = get_body_data(request, "name", "").strip()
        email = get_body_data(request, "email", "").strip()
        # Optionally, you can extract google_token and verify it:
        google_token = get_body_data(request, "google_token", "").strip()

        if not email or not name:
            return api_failed("Name and email are required", headers={"code": 1020}).secure().rest()

        try:
            # Try to get the user by email
            user = User.objects.filter(email=email).first()
            if not user:
                # User doesn't exist: generate a user_id and create a new user.
                try:
                    user_id = generate_user_id(name, email, max_iter=MAX_GENERATE_ATTEMPT)
                except Exception as e:
                    return api_failed("Error occurred while creating user id", headers={"code": 1002}).secure().rest()

                # Create the user.
                # Since Google manages authentication, you might set a dummy password or leave it empty
                user = User.objects.create_user(email=email, name=name, user_id=user_id, password="")

            # Update the last_login time
            user.last_login = now()
            user.save()

            # Prepare the response user data.
            user_data = {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
            }
            return api_success("Google login success", body={"user_data": user_data}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred during Google login", headers={"code": 1021}).secure().rest()