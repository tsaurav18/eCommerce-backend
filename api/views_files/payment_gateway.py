import hashlib
import hmac

import razorpay

from api.models import *
import os

from rest_framework import viewsets, mixins

from api.serializers_files.serializers import PrepareOrderSerializer
from api.utility_files.api_call import get_body_data, api_failed, api_success

TEST_KEY_ID = "rzp_test_4DWYbn4PlWlGQF"
TEST_KEY_SECRET = "LUt6VWiy6wrfZy9ubKkkhVII"
client = razorpay.Client(auth=(TEST_KEY_ID, TEST_KEY_SECRET))
client.set_app_details({"title" : "ELeve", "version" : "1.0"})

class CreateOrderView(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    queryset = PrepareOrder.objects.all()
    serializer_class = PrepareOrderSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a Razorpay order.
        """
        user_id = get_body_data(request, "user_id", "").strip()
        amount = get_body_data(request, "amount", "") # Amount in paise (₹1 = 100 paise)
        currency = get_body_data(request, "currency", "INR").strip()
        receipt = f"receipt_{user_id}"  # Generate a unique receipt ID

        # Validate user
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed("User not found", headers={"code": 1004}).secure().rest()

        # Razorpay order data
        order_data = {
            "amount": int(amount)*100,  # Razorpay requires amount in paise
            "currency": currency,
            "receipt": receipt,
            "notes": {
                "user_id": user_id,
                "platform": "ELeve",
            },
        }
        print(order_data)
        try:
            # Create order in Razorpay
            razorpay_order = client.order.create(data=order_data)  # 🔹 FIXED: `order.create()`
            print("razorpay_order", razorpay_order["id"])
            # Save the order in our database
            prepare_order = PrepareOrder.objects.create(
                user=user,
                amount=amount,
                currency=currency,
                receipt=receipt,
                notes=order_data["notes"],
                id=razorpay_order["id"],
                partial_payment=False,  # Default to false
            )

            return api_success(
                "Order created successfully",
                body={"order": razorpay_order},
            ).secure().rest()

        except Exception as e:
            return api_failed(f"Razorpay Error: {str(e)}", headers={"code": 1005}).secure().rest()
        except Exception as e:
            return api_failed(f"Unexpected Error: {str(e)}", headers={"code": 1006}).secure().rest()

class VerifyOrderView(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    queryset = PrepareOrder.objects.all()
    serializer_class = PrepareOrderSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a Razorpay order.
        """
        razorpay_order_id = get_body_data(request, "razorpay_order_id", "").strip()
        razorpay_payment_id = get_body_data(request, "razorpay_payment_id", "").strip() # Amount in paise (₹1 = 100 paise)
        razorpay_signature = get_body_data(request, "razorpay_signature", "").strip()
        print(razorpay_signature, razorpay_order_id, razorpay_payment_id)
        try:
            if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
                return api_failed("Missing required parameters", headers={"success": False}).secure().rest()

            # Fetch Razorpay secret key from settings

            secret = TEST_KEY_SECRET
            if not secret:
                return api_failed("Razorpay secret not found", headers={"success": False}).secure().rest()

            # Generate expected signature
            message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
            generated_signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

            # Compare signatures
            if generated_signature == razorpay_signature:
                return api_success("Payment Successful!", headers={"success": True}).secure().rest()
            else:
                return api_failed("Invalid signature", headers={"success": False}).secure().rest()
        except Exception as e:
            return api_failed("Invalid Razorpay Error", headers={"success": False}).secure().rest()

