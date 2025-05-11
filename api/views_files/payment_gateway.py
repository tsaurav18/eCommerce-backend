import hashlib
import hmac
from sqlite3 import IntegrityError

import razorpay
from django.db import transaction
from api.models import *
import os
from requests.auth import HTTPBasicAuth
import requests
from rest_framework import viewsets, mixins
from django.conf import settings
from api.serializers_files.serializers import PrepareOrderSerializer, SaveOrderSerializer, PaypalCreateOrderSerializer, PaypalCaptureOrderSerializer
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

class SaveOrdersView(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    queryset = Orders.objects.all()
    serializer_class = SaveOrderSerializer

    def create(self, request, *args, **kwargs):
        try:
            user_id = get_body_data(request, "user_id", "").strip()
            order_id = get_body_data(request, "order_id", "").strip()
            total_price = get_body_data(request, "total_price", "")
            items = get_body_data(request, "items", [])
            address_id = get_body_data(request, "address_id", "")

            # Validate User
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                return api_failed("User not found", headers={"success": False}).secure().rest()

            # Validate Address
            try:
                address = Address.objects.get(id=address_id, user=user)
            except Address.DoesNotExist:
                return api_failed("Invalid address selected", headers={"success": False}).secure().rest()

            # Validate PrepareOrder
            try:
                prepare_order = PrepareOrder.objects.get(id=order_id)
            except PrepareOrder.DoesNotExist:
                return api_failed("Invalid Razorpay Order ID", headers={"success": False}).secure().rest()

            with transaction.atomic():
                # Create Order
                order = Orders.objects.create(
                    user=user,
                    order_ref=prepare_order,
                    total_price=total_price,
                    status="processing",
                    address=address
                )
                # print("orders", order)
                # Save Order Items
                for item in items:
                    try:
                        product = Product.objects.get(id=item["product_id"])
                        variant_id = item.get("variant_id")
                        if variant_id:
                            try:
                                variant = ProductVariant.objects.get(id=variant_id, product=product)
                            except ProductVariant.DoesNotExist:
                                raise IntegrityError(
                                    f"Variant with ID {variant_id} not found for product {product.name}")

                            if variant.stock < item["quantity"]:
                                raise IntegrityError(f"Insufficient stock for {variant.name}")

                            # Deduct variant stock
                            variant.stock -= item["quantity"]
                            variant.save()

                            price_at_time = variant.price  # Use variant price
                            OrderItem.objects.create(
                                order=order,
                                product=product,
                                variant=variant,
                                quantity=item["quantity"],
                                price=price_at_time,
                            )
                        else:
                            # Fallback to product-level (not ideal anymore)
                            if product.stock < item["quantity"]:
                                raise IntegrityError(f"Insufficient stock for {product.name}")

                            product.stock -= item["quantity"]
                            product.save()

                            OrderItem.objects.create(
                                order=order,
                                product=product,
                                quantity=item["quantity"],
                                price=product.price,
                            )

                    except Product.DoesNotExist:
                        raise IntegrityError(f"Product with ID {item['product_id']} not found")

            return api_success("Order saved successfully!", headers={"success": True}).secure().rest()

        except IntegrityError as e:
            print("Integrity Error:", e)
            return api_failed(f"Transaction failed: {str(e)}", headers={"success": False}).secure().rest()

        except Exception as e:
            print("Error in SaveOrdersView:", e)
            return api_failed("An unexpected error occurred", headers={"success": False}).secure().rest()


class PaypalCreateOrderView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = PaypalCreateOrderSerializer

    def create(self, request, *args, **kwargs):
        # 입력값 검증
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        purchase_units     = data['purchase_units']
        intent             = data.get('intent', 'CAPTURE')
        experience_context = data.get('experience_context', {})
        user_id = data.get('user')
        amount = data.get("amount")
        print("user_id", user_id, "amount", amount, intent, experience_context)
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed("User not found", headers={"code": 1004}).secure().rest()
        # 1) PayPal OAuth 토큰 발급
        token_res = requests.post(
            "https://api-m.sandbox.paypal.com/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_KEY),
        )
        if token_res.status_code != 200:
            return (
                api_failed("Failed to obtain PayPal access token.", headers={"code": 1002})
                .secure()
                .rest()
            )
        access_token = token_res.json().get('access_token')

        # 2) PayPal 주문 생성
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        body = {
            "intent": intent,
            "purchase_units": purchase_units,
            "payment_source": {"paypal": {"experience_context": experience_context}},
        }
        order_res = requests.post(
            "https://api-m.sandbox.paypal.com/v2/checkout/orders",
            json=body,
            headers=headers,
        )

        if order_res.status_code not in (200, 201):
            return (
                api_failed("Failed to capture PayPal order", headers={"code": 1003})
                .secure()
                .rest()
            )
        order_data = order_res.json()

        # 3) DB에 주문 정보 저장
        try:
            with transaction.atomic():  # ✅ wrap entire logic here
                try:
                    # Check if the object exists
                    PaypalOrder.objects.get(order_id=order_data['id'])
                    # If it exists, you can either skip or choose to update it manually
                    # For example:
                    # existing_order = PaypalOrder.objects.get(order_id=order_data['id'])
                    # existing_order.purchase_units = purchase_units
                    # existing_order.save()
                except PaypalOrder.DoesNotExist:
                    # Object doesn't exist, safe to create
                    PaypalOrder.objects.create(
                        order_id=order_data['id'],
                        purchase_units=purchase_units,
                        intent=intent,
                        experience_context=experience_context,
                        status=order_data.get('status'),
                        raw_response=order_data
                    )

                try:
                    # Check if a PrepareOrder with this ID already exists
                    prepare_order = PrepareOrder.objects.get(id=order_data['id'])
                    exists = True
                except PrepareOrder.DoesNotExist:
                    # Create a new PrepareOrder if it doesn't exist
                    prepare_order = PrepareOrder.objects.create(
                        id=order_data['id'],
                        user=user,
                        amount=amount,
                        currency="INR",
                        receipt=intent,
                        notes=order_data,
                        partial_payment=False
                    )
                    exists = False

                # If you need to update even if it exists, add this:
                if exists:
                    prepare_order.user = user
                    prepare_order.amount = amount
                    prepare_order.currency = "INR"
                    prepare_order.receipt = intent
                    prepare_order.notes = order_data
                    prepare_order.partial_payment = False
                    prepare_order.save()
        except Exception as e:
            print("DB Error:", e)
            return api_failed("Failed to save order to DB", headers={"code": 1009}).secure().rest()

        # 4) 응답 반환
        return (
            api_success(api_msg='Success', body=order_data)
            .secure()
            .rest()
        )


class PaypalCaptureOrderView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = PaypalCaptureOrderSerializer

    def create(self, request, *args, **kwargs):
        # 입력값 검증
        order_id = get_body_data(request, 'orderID', '').strip()
        if not order_id:
            return (
                api_failed("orderID is required.", headers={"code": 1004})
                .secure()
                .rest()
            )

        # DB에서 기존 주문 조회
        try:
            paypal_order = PaypalOrder.objects.get(order_id=order_id)
        except PaypalOrder.DoesNotExist:
            return (
                api_failed("Order not found.", headers={"code": 1005})
                .secure()
                .rest()
            )

        # PayPal OAuth 토큰 재발급
        token_res = requests.post(
            "https://api-m.sandbox.paypal.com/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_KEY),
        )
        if token_res.status_code != 200:
            return (
                api_failed("Failed to obtain PayPal access token.", headers={"code": 1006})
                .secure()
                .rest()
            )
        access_token = token_res.json().get('access_token')

        # 주문 캡처 API 호출
        cap_res = requests.post(
            f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
        )
        if cap_res.status_code not in (200, 201):
            return (
                api_failed("Failed to capture PayPal order", headers={"code": 1007})
                .secure()
                .rest()
            )
        cap_data = cap_res.json()

        # DB 업데이트
        paypal_order.status = cap_data.get('status', paypal_order.status)
        paypal_order.raw_response = cap_data
        paypal_order.save()
        captures = cap_data["purchase_units"][0]["payments"]["captures"]
        first_capture = captures[0]
        amount_value = first_capture["amount"]["value"]  # e.g. "1.00"
        amount_currency = first_capture["amount"]["currency_code"]  # e.g. "USD"

        PrepareOrder.objects.update_or_create(
            id=cap_data.get('id'),
            defaults={
                "notes": cap_data,
                "amount": amount_value,  # store as Decimal
                "currency": amount_currency,  # if you have a currency field
            }
        )
        # 응답 반환
        return (
            api_success(body=cap_data)
            .secure()
            .rest()
        )