from django.core.mail import send_mail
from django.conf import settings


class NotificationService:

    @staticmethod
    def send_email(to_email, subject, message):
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )

    @staticmethod
    def order_created(order):
        NotificationService.send_email(
            order.buyer.email,
            "Order Created",
            f"Your order for {order.product.name} was created."
        )

    @staticmethod
    def escrow_funded(order):
        NotificationService.send_email(
            order.seller.email,
            "Escrow Funded",
            f"Escrow for order {order.id} is funded."
        )

    @staticmethod
    def delivery_confirmed(order):
        NotificationService.send_email(
            order.seller.email,
            "Delivery Confirmed",
            f"Delivery confirmed for order {order.id}."
        )