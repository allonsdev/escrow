import random
import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from faker import Faker
from django.utils import timezone

from app.models import (
    User, UserWallet, UserContact, Product, Order,
    EscrowTransaction, Payment, LogTrail,
    UserEvent, SiteVisit, Dispute, DeliveryConfirmation
)

fake = Faker()


class Command(BaseCommand):
    help = "Seed database with marketplace + escrow simulation data"

    def handle(self, *args, **kwargs):
        self.stdout.write("🌱 Seeding database...")

        # -----------------------------
        # USERS
        # -----------------------------
        buyers = []
        sellers = []

        for i in range(2):
            buyers.append(User.objects.create_user(
                username=f"buyer{i}",
                password="password123",
                is_buyer=True,
                is_seller=False,
                email=fake.email(),
                phone_number=fake.phone_number(),
                country="Zimbabwe",
                city=fake.city(),
                is_verified=True,
                verification_level="basic",
                trust_score=random.uniform(60, 95),
            ))

        for i in range(2):
            sellers.append(User.objects.create_user(
                username=f"seller{i}",
                password="password123",
                is_buyer=False,
                is_seller=True,
                email=fake.email(),
                phone_number=fake.phone_number(),
                country="Zimbabwe",
                city=fake.city(),
                is_verified=True,
                verification_level="advanced",
                trust_score=random.uniform(70, 98),
            ))

        users = buyers + sellers

        # -----------------------------
        # WALLETS + CONTACTS
        # -----------------------------
        for user in users:
            UserWallet.objects.create(
                user=user,
                wallet_address=fake.sha1(),
                private_key_encrypted=fake.sha256(),
                balance_snapshot=Decimal(random.uniform(1, 50))
            )

            for _ in range(3):
                UserContact.objects.create(
                    user=user,
                    full_name=fake.name(),
                    email=fake.email(),
                    phone=fake.phone_number(),
                    address_line1=fake.street_address(),
                    city=fake.city(),
                    country="Zimbabwe",
                    postal_code=fake.postcode(),
                    is_default_shipping=random.choice([True, False])
                )

        # -----------------------------
        # PRODUCTS
        # -----------------------------
        products = []
        for _ in range(100):
            products.append(Product.objects.create(
                seller=random.choice(sellers),
                name=fake.word(),
                description=fake.text(),
                price=Decimal(random.uniform(5, 200)),
                currency="USD",
                quantity_available=random.randint(1, 50),
                category=random.choice(["Electronics", "Clothing", "Accessories"]),
                condition=random.choice(["New", "Used"]),
                total_views=random.randint(0, 1000),
                total_purchases=random.randint(0, 100),
                conversion_rate=random.uniform(0, 100)
            ))

        # -----------------------------
        # ORDERS + ESCROW + PAYMENT
        # -----------------------------
        transactions = []

        for _ in range(100):
            buyer = random.choice(buyers)
            product = random.choice(products)
            seller = product.seller

            contact = UserContact.objects.filter(user=buyer).first()

            order = Order.objects.create(
                buyer=buyer,
                seller=seller,
                product=product,
                quantity=random.randint(1, 3),
                total_price=product.price,
                currency="USD",
                shipping_contact=contact,
                status="paid"
            )

            escrow = EscrowTransaction.objects.create(
                order=order,
                buyer=buyer,
                seller=seller,
                amount=order.total_price,
                currency="USD",
                status=random.choice([
                    "funded", "delivered", "released"
                ]),
                blockchain_network="ganache",
                contract_address=fake.sha1(),
                deployment_tx_hash=fake.sha1(),
                block_number=random.randint(1000, 5000),
                gas_used=Decimal(random.uniform(0.001, 0.01)),
                fraud_risk_score=random.uniform(0, 100)
            )

            transactions.append(escrow)

            Payment.objects.create(
                transaction=escrow,
                payer=buyer,
                amount=order.total_price,
                currency="USD",
                payment_method="crypto",
                blockchain_tx_hash=fake.sha1(),
                status="confirmed",
                confirmations=random.randint(1, 12)
            )

            DeliveryConfirmation.objects.create(
                transaction=escrow,
                confirmed_by_buyer=random.choice([True, False]),
                confirmed_by_system=True,
                tracking_number=fake.uuid4(),
                courier_name=random.choice(["DHL", "FedEx", "ZimPost"]),
                delivery_proof_url=fake.url()
            )

        # -----------------------------
        # DISPUTES
        # -----------------------------
        for _ in range(100):
            tx = random.choice(transactions)

            Dispute.objects.create(
                transaction=tx,
                raised_by=random.choice([tx.buyer, tx.seller]),
                reason=fake.sentence(),
                evidence_url=fake.url(),
                status=random.choice([
                    "open", "under_review", "resolved", "rejected"
                ]),
                resolution_notes=fake.text(),
                refund_amount=Decimal(random.uniform(0, float(tx.amount)))
            )

        # -----------------------------
        # LOGS
        # -----------------------------
        for _ in range(100):
            LogTrail.objects.create(
                user=random.choice(users),
                action_type=random.choice([
                    "LOGIN", "ORDER_CREATED", "PAYMENT_SENT",
                    "ESCROW_RELEASED", "DISPUTE_OPENED"
                ]),
                related_transaction=random.choice(transactions),
                description=fake.sentence(),
                ip_address=fake.ipv4(),
                user_agent=fake.user_agent(),
                metadata={"device": fake.word()}
            )

        # -----------------------------
        # USER EVENTS
        # -----------------------------
        for _ in range(100):
            UserEvent.objects.create(
                user=random.choice(users),
                event_type=random.choice([
                    "product_view",
                    "checkout_start",
                    "payment_attempt",
                    "delivery_confirmed"
                ]),
                related_object_id=uuid.uuid4(),
                metadata={"info": fake.word()},
                ip_address=fake.ipv4()
            )

        # -----------------------------
        # SITE VISITS
        # -----------------------------
        for _ in range(100):
            SiteVisit.objects.create(
                user=random.choice(users),
                session_id=fake.uuid4(),
                page_url=f"/product/{fake.uuid4()}",
                referrer=fake.url(),
                ip_address=fake.ipv4(),
                device_type=random.choice(["mobile", "desktop"]),
                browser=random.choice(["Chrome", "Firefox", "Edge"]),
                os=random.choice(["Windows", "Android", "iOS"]),
                duration_seconds=random.randint(5, 300),
                country="Zimbabwe",
                city=fake.city(),
                is_authenticated=random.choice([True, False])
            )

        self.stdout.write(self.style.SUCCESS("✅ Database seeded successfully!"))