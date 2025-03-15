from django.contrib.auth.hashers import make_password,check_password
from django.forms import model_to_dict
from django.middleware.csrf import get_token
from rest_framework.response import Response
from rest_framework import mixins, viewsets, status
from api.models import User
from api.utility_files.api_call import get_body_data, api_failed, api_success
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from api.utility_files.utils import generate_user_id
from django.contrib.auth import authenticate
from django.utils.timezone import now
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
        user.last_login = now()
        if user:
            user_data = {
                "user_id": user.user_id,
                "name": user.name,
                "email": user.email,
            }
            return api_success("Login success", body={"user_data": user_data}).secure().rest()
        else:
            return api_failed("You entered wrong password", headers={"code": 1006}).secure().rest()