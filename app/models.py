import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Roles
    is_buyer = models.BooleanField(default=True)
    is_seller = models.BooleanField(default=False)

    # Identity
    phone_number = models.CharField(max_length=20, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # Verification
    is_verified = models.BooleanField(default=False)
    verification_level = models.CharField(
        max_length=50,
        choices=[("none","None"),("basic","Basic"),("advanced","Advanced")],
        default="none"
    )

    # Trust metrics (research critical)
    trust_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    successful_transactions = models.IntegerField(default=0)
    failed_transactions = models.IntegerField(default=0)
    disputed_transactions = models.IntegerField(default=0)
    dispute_win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Fraud monitoring
    fraud_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_flagged = models.BooleanField(default=False)

    # Activity analytics
    total_logins = models.IntegerField(default=0)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    device_fingerprint = models.CharField(max_length=255, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    # Location
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)





class UserWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    wallet_address = models.CharField(max_length=255)
    private_key_encrypted = models.TextField(blank=True)

    blockchain_network = models.CharField(max_length=100, default="ganache")
    balance_snapshot = models.DecimalField(max_digits=18, decimal_places=8, default=0)

    created_at = models.DateTimeField(auto_now_add=True)


class UserContact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)

    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    is_default_shipping = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    seller = models.ForeignKey(User, on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    description = models.TextField()

    price = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10)

    quantity_available = models.IntegerField(default=1)

    category = models.CharField(max_length=100, blank=True)
    condition = models.CharField(max_length=50, blank=True)

    # Analytics
    total_views = models.IntegerField(default=0)
    total_purchases = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)



class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders_made")
    seller = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders_received")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    quantity = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10)

    shipping_contact = models.ForeignKey(UserContact, on_delete=models.SET_NULL, null=True)

    status = models.CharField(
        max_length=50,
        choices=[
            ("pending","Pending"),
            ("escrow_created","Escrow Created"),
            ("paid","Paid"),
            ("shipped","Shipped"),
            ("completed","Completed"),
            ("cancelled","Cancelled"),
        ]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
    
class EscrowTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blockchain_escrow_id = models.IntegerField(null=True, blank=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE)

    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="escrow_buyer")
    seller = models.ForeignKey(User, on_delete=models.PROTECT, related_name="escrow_seller")

    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10)

    status = models.CharField(
        max_length=50,
        choices=[
            ("created","Created"),
            ("funded","Funded"),
            ("delivered","Delivered"),
            ("released","Released"),
            ("disputed","Disputed"),
            ("refunded","Refunded"),
        ]
    )

    # Smart contract data
    blockchain_network = models.CharField(max_length=100)
    contract_address = models.CharField(max_length=255)
    deployment_tx_hash = models.CharField(max_length=255, blank=True)

    block_number = models.IntegerField(null=True, blank=True)
    gas_used = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)

    fraud_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    transaction = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE)
    payer = models.ForeignKey(User, on_delete=models.PROTECT)

    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10)

    payment_method = models.CharField(max_length=50)
    blockchain_tx_hash = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=50)
    confirmations = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)


class LogTrail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action_type = models.CharField(max_length=100)

    related_transaction = models.ForeignKey(
        EscrowTransaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    description = models.TextField()

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class UserEvent(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    event_type = models.CharField(max_length=100)
    related_object_id = models.UUIDField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)



class SiteVisit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    session_id = models.CharField(max_length=255)
    page_url = models.CharField(max_length=500)

    referrer = models.CharField(max_length=500, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)

    duration_seconds = models.IntegerField(default=0)

    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    is_authenticated = models.BooleanField(default=False)

    visited_at = models.DateTimeField(auto_now_add=True)



class Dispute(models.Model):
    transaction = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE)
    raised_by = models.ForeignKey(User, on_delete=models.PROTECT)

    reason = models.TextField()
    evidence_url = models.URLField(blank=True)

    status = models.CharField(
        max_length=50,
        choices=[
            ("open","Open"),
            ("under_review","Under Review"),
            ("resolved","Resolved"),
            ("rejected","Rejected"),
        ]
    )

    resolution_notes = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)



class DeliveryConfirmation(models.Model):
    transaction = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE)

    confirmed_by_buyer = models.BooleanField(default=False)
    confirmed_by_system = models.BooleanField(default=False)

    tracking_number = models.CharField(max_length=100, blank=True)
    courier_name = models.CharField(max_length=100, blank=True)

    delivery_proof_url = models.URLField(blank=True)

    confirmed_at = models.DateTimeField(auto_now_add=True)


