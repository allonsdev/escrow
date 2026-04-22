import random
import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils import timezone

from app.models import *


# ─────────────────────────────
# DATA POOLS (ZIMBABWEAN STYLE)
# ─────────────────────────────
FIRST_NAMES = ["Tendai","Nyasha","Tatenda","Kudakwashe","Rumbidzai","Farai","Tafadzwa","Chipo","Simbarashe","Kudzai"]
LAST_NAMES = ["Moyo","Dube","Ndlovu","Sibanda","Gumbo","Khumalo","Chirwa","Zhou","Mlambo","Tshuma"]
CITIES = ["Harare","Bulawayo","Gweru","Mutare","Masvingo"]

PRODUCTS = [
    ("iPhone 14 Pro Max", "smartphone"),
    ("Samsung S23 Ultra", "smartphone"),
    ("Google Pixel 8", "smartphone"),
    ("MacBook Pro M2", "laptop"),
    ("Dell XPS 13", "laptop"),
    ("HP Pavilion Ryzen 7", "laptop"),
    ("Sony Bravia 55-inch", "tv"),
    ("Samsung QLED 65-inch", "tv"),
    ("LG OLED C3", "tv"),
    ("JBL Charge 5", "audio"),
    ("AirPods Pro 2", "audio"),
    ("Anker PowerBank 20k", "accessory"),
]


def rand_user():
    f = random.choice(FIRST_NAMES)
    l = random.choice(LAST_NAMES)
    return {
        "username": f.lower()+str(random.randint(100,999)),
        "email": f"{f}.{l}@zimtech.co.zw",
        "city": random.choice(CITIES),
    }


class Command(BaseCommand):
    help = "Seed ALL models in marketplace"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Seeding ALL models...")

        # ─────────────────────────
        # CATEGORY TREE
        # ─────────────────────────
        electronics, _ = Category.objects.get_or_create(
            name="Electronics",
            defaults={"slug": "electronics"}
        )

        subcats = []
        for name in ["Smartphones","Laptops","TVs","Audio","Accessories"]:
            c, _ = Category.objects.get_or_create(
                name=name,
                defaults={"slug": slugify(name), "parent": electronics}
            )
            subcats.append(c)

        # ─────────────────────────
        # USERS + SHOPS + WALLETS
        # ─────────────────────────
        sellers = []
        buyers = []

        for _ in range(6):
            data = rand_user()

            user = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password="test1234",
                is_buyer=True,
                is_seller=True,
                city=data["city"],
                country="Zimbabwe",
                trust_score=random.randint(60,95),
                total_logins=random.randint(1,50),
                last_login_ip="102.130.1."+str(random.randint(1,200))
            )

            UserWallet.objects.create(
                user=user,
                wallet_address=f"0x{uuid.uuid4().hex[:40]}",
                balance_snapshot=Decimal(random.randint(1,25))
            )

            shop = Shop.objects.create(
                seller=user,
                name=f"{data['username']} Tech Store",
                slug=slugify(data['username']+" store"),
                city=data["city"],
                country="Zimbabwe",
                is_verified=True,
                rating=Decimal(random.uniform(3.5, 5))
            )

            sellers.append((user, shop))

        # Buyers
        for _ in range(3):
            data = rand_user()
            buyer = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password="test1234",
                is_buyer=True,
                city=data["city"],
                country="Zimbabwe"
            )
            buyers.append(buyer)

        # ─────────────────────────
        # PRODUCTS + IMAGES + STOCK
        # ─────────────────────────
        products = []

        for name, _type in PRODUCTS:
            seller, shop = random.choice(sellers)

            p = Product.objects.create(
                seller=seller,
                shop=shop,
                category=random.choice(subcats),
                name=name,
                slug=slugify(name+str(random.randint(1,999))),
                description=f"Original {name} available in Zimbabwe.",
                price=Decimal(random.randint(100,2000)),
                currency="ETH",
                quantity_available=random.randint(5,50),
                condition="new",
                total_views=random.randint(10,500),
                avg_rating=Decimal(random.uniform(3,5))
            )

            # Image placeholder
            ProductImage.objects.create(
                product=p,
                alt_text=name,
                is_primary=True,
                sort_order=1
            )

            StockLog.objects.create(
                product=p,
                user=seller,
                action="restock",
                quantity_change=20,
                quantity_before=0,
                quantity_after=20,
                note="Initial stock load"
            )

            products.append(p)

        # ─────────────────────────
        # ORDERS + ESCROW + PAYMENT
        # ─────────────────────────
        for _ in range(5):
            buyer = random.choice(buyers)
            product = random.choice(products)

            order = Order.objects.create(
                buyer=buyer,
                seller=product.seller,
                product=product,
                shop=product.shop,
                quantity=1,
                unit_price=product.price,
                total_price=product.price,
                currency="ETH",
                status="paid"
            )

            escrow = EscrowTransaction.objects.create(
                order=order,
                buyer=buyer,
                seller=product.seller,
                amount=product.price,
                currency="ETH",
                blockchain_network="ganache",
                status="funded"
            )

            Payment.objects.create(
                transaction=escrow,
                payer=buyer,
                amount=product.price,
                currency="ETH",
                payment_method="crypto_wallet",
                status="confirmed",
                confirmations=12
            )

        # ─────────────────────────
        # REVIEWS
        # ─────────────────────────
        for product in products:
            for buyer in buyers:
                Review.objects.create(
                    product=product,
                    user=buyer,
                    rating=random.randint(4,5),
                    title="Great product",
                    body="Works perfectly in Zimbabwe.",
                    is_verified_purchase=True
                )

        # ─────────────────────────
        # DISPUTES
        # ─────────────────────────
        escrow_list = EscrowTransaction.objects.all()[:2]

        for esc in escrow_list:
            Dispute.objects.create(
                transaction=esc,
                raised_by=esc.buyer,
                reason="Item not as described",
                status="open"
            )

        # ─────────────────────────
        # NOTIFICATIONS
        # ─────────────────────────
        for user in User.objects.all():
            Notification.objects.create(
                user=user,
                type="system",
                title="Welcome to ZimTech Marketplace",
                message="Your account is ready."
            )

        # ─────────────────────────
        # LOG TRAILS
        # ─────────────────────────
        for user in User.objects.all():
            LogTrail.objects.create(
                user=user,
                action_type="LOGIN",
                description="User logged in"
            )

        # ─────────────────────────
        # SITE VISITS
        # ─────────────────────────
        for _ in range(10):
            SiteVisit.objects.create(
                session_id=str(uuid.uuid4()),
                page_url="/products",
                device_type="mobile",
                browser="Chrome",
                os="Android",
                country="Zimbabwe",
                city=random.choice(CITIES),
                is_authenticated=True
            )

        # ─────────────────────────
        # DELIVERY CONFIRMATION
        # ─────────────────────────
        for esc in EscrowTransaction.objects.all():
            DeliveryConfirmation.objects.create(
                transaction=esc,
                confirmed_by_buyer=True,
                confirmed_by_system=True,
                tracking_number=f"TRK{random.randint(10000,99999)}",
                courier_name="ZimPost"
            )

        self.stdout.write(self.style.SUCCESS("✅ ALL MODELS SEEDED SUCCESSFULLY"))