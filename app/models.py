import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────
#  USER
# ─────────────────────────────────────────────

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    is_buyer  = models.BooleanField(default=True)
    is_seller = models.BooleanField(default=False)

    phone_number  = models.CharField(max_length=20, blank=True)
    national_id   = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar        = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio           = models.TextField(blank=True)

    is_verified        = models.BooleanField(default=False)
    verification_level = models.CharField(
        max_length=50,
        choices=[("none", "None"), ("basic", "Basic"), ("advanced", "Advanced")],
        default="none",
    )

    trust_score             = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    successful_transactions = models.IntegerField(default=0)
    failed_transactions     = models.IntegerField(default=0)
    disputed_transactions   = models.IntegerField(default=0)
    dispute_win_rate        = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    fraud_risk_score   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_flagged         = models.BooleanField(default=False)

    total_logins       = models.IntegerField(default=0)
    last_login_ip      = models.GenericIPAddressField(null=True, blank=True)
    device_fingerprint = models.CharField(max_length=255, blank=True)
    last_activity      = models.DateTimeField(null=True, blank=True)

    country = models.CharField(max_length=100, blank=True)
    city    = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


# ─────────────────────────────────────────────
#  WALLET
# ─────────────────────────────────────────────

class UserWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    wallet_address        = models.CharField(max_length=255)
    private_key_encrypted = models.TextField(blank=True)
    blockchain_network    = models.CharField(max_length=100, default="ganache")
    balance_snapshot      = models.DecimalField(max_digits=18, decimal_places=8, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.balance_snapshot} ETH"


# ─────────────────────────────────────────────
#  SHOP
# ─────────────────────────────────────────────

class Shop(models.Model):
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.OneToOneField(User, on_delete=models.CASCADE, related_name="shop")

    name        = models.CharField(max_length=255)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo        = models.ImageField(upload_to="shop_logos/", null=True, blank=True)
    banner      = models.ImageField(upload_to="shop_banners/", null=True, blank=True)

    email   = models.EmailField(blank=True)
    phone   = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    address     = models.TextField(blank=True)
    city        = models.CharField(max_length=100, blank=True)
    country     = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    is_active   = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    total_sales   = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    rating        = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  CATEGORY
# ─────────────────────────────────────────────

class Category(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon class e.g. bi-laptop")
    parent      = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    is_active   = models.BooleanField(default=True)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  PRODUCT
# ─────────────────────────────────────────────

class Product(models.Model):
    CONDITION_CHOICES = [
        ("new", "New"), ("like_new", "Like New"),
        ("good", "Good"), ("fair", "Fair"), ("poor", "Poor"),
    ]

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller   = models.ForeignKey(User, on_delete=models.CASCADE)
    shop     = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")

    name        = models.CharField(max_length=255)
    slug        = models.SlugField(blank=True)
    description = models.TextField()
    sku         = models.CharField(max_length=100, blank=True, unique=True, null=True)

    price    = models.DecimalField(max_digits=18, decimal_places=4)
    currency = models.CharField(max_length=10, default="ETH")

    quantity_available  = models.IntegerField(default=1)
    low_stock_threshold = models.IntegerField(default=5)

    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES, default="new")
    tags      = models.CharField(max_length=500, blank=True)

    weight     = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=100, blank=True)

    total_views     = models.IntegerField(default=0)
    total_purchases = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_rating      = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    is_active   = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_digital  = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_low_stock(self):
        return 0 < self.quantity_available <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.quantity_available <= 0
    
    @property
    def primary_image(self):
        def safe_url(img):
            try:
                return img.image.url if img and img.image else None
            except ValueError:
                return None

        img = self.images.filter(is_primary=True).first()
        url = safe_url(img)
        if url:
            return url
        first = self.images.first()
        return safe_url(first)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image      = models.ImageField(upload_to="product_images/")
    alt_text   = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


# ─────────────────────────────────────────────
#  STOCK LOG
# ─────────────────────────────────────────────

class StockLog(models.Model):
    ACTION_CHOICES = [
        ("restock", "Restock"), ("sale", "Sale"),
        ("adjustment", "Adjustment"), ("return", "Return"), ("damage", "Damage"),
    ]

    product         = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_logs")
    user            = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action          = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity_change = models.IntegerField()
    quantity_before = models.IntegerField()
    quantity_after  = models.IntegerField()
    note            = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} | {self.action} | {self.quantity_change:+d}"


# ─────────────────────────────────────────────
#  REVIEW
# ─────────────────────────────────────────────

class Review(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    order   = models.ForeignKey("Order", null=True, blank=True, on_delete=models.SET_NULL)

    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title  = models.CharField(max_length=200, blank=True)
    body   = models.TextField()

    is_verified_purchase = models.BooleanField(default=False)
    helpful_count        = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.product.name} — {self.rating}★ by {self.user.username}"


# ─────────────────────────────────────────────
#  ORDER
# ─────────────────────────────────────────────

class UserContact(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name       = models.CharField(max_length=255)
    email           = models.EmailField()
    phone           = models.CharField(max_length=20, blank=True)
    address_line1   = models.CharField(max_length=255, blank=True)
    address_line2   = models.CharField(max_length=255, blank=True)
    city            = models.CharField(max_length=100, blank=True)
    country         = models.CharField(max_length=100, blank=True)
    postal_code     = models.CharField(max_length=20, blank=True)
    is_default_shipping = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending",        "Pending"),
        ("escrow_created", "Escrow Created"),
        ("paid",           "Paid"),
        ("shipped",        "Shipped"),
        ("completed",      "Completed"),
        ("disputed",       "Disputed"),
        ("cancelled",      "Cancelled"),
        ("refunded",       "Refunded"),
    ]

    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer   = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders_made")
    seller  = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders_received")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    shop    = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.SET_NULL)

    quantity    = models.IntegerField(default=1)
    unit_price  = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_price = models.DecimalField(max_digits=18, decimal_places=4)
    currency    = models.CharField(max_length=10)

    shipping_contact = models.ForeignKey(UserContact, on_delete=models.SET_NULL, null=True, blank=True)
    tracking_number  = models.CharField(max_length=100, blank=True)
    shipping_notes   = models.TextField(blank=True)

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")
    notes  = models.TextField(blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    shipped_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order {str(self.id)[:8]} — {self.product.name}"


# ─────────────────────────────────────────────
#  ESCROW
# ─────────────────────────────────────────────

class EscrowTransaction(models.Model):
    STATUS_CHOICES = [
        ("created",   "Created"),
        ("paid",      "Paid"),
        ("funded",    "Funded"),
        ("delivered", "Delivered"),
        ("released",  "Released"),
        ("disputed",  "Disputed"),
        ("refunded",  "Refunded"),
    ]

    id                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blockchain_escrow_id = models.IntegerField(null=True, blank=True)
    order  = models.OneToOneField(Order, on_delete=models.CASCADE)
    buyer  = models.ForeignKey(User, on_delete=models.PROTECT, related_name="escrow_buyer")
    seller = models.ForeignKey(User, on_delete=models.PROTECT, related_name="escrow_seller")

    amount   = models.DecimalField(max_digits=18, decimal_places=4)
    currency = models.CharField(max_length=10)

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="created")

    blockchain_network = models.CharField(max_length=100)
    contract_address   = models.CharField(max_length=255, blank=True)
    deployment_tx_hash = models.CharField(max_length=255, blank=True)
    release_tx_hash    = models.CharField(max_length=255, blank=True)

    block_number = models.IntegerField(null=True, blank=True)
    gas_used     = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)

    fraud_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    created_at  = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Escrow {str(self.id)[:8]} — {self.status}"


# ─────────────────────────────────────────────
#  PAYMENT
# ─────────────────────────────────────────────

class Payment(models.Model):
    transaction        = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE)
    payer              = models.ForeignKey(User, on_delete=models.PROTECT)
    amount             = models.DecimalField(max_digits=18, decimal_places=4)
    currency           = models.CharField(max_length=10)
    payment_method     = models.CharField(max_length=50)
    blockchain_tx_hash = models.CharField(max_length=255, blank=True)
    status             = models.CharField(max_length=50)
    confirmations      = models.IntegerField(default=0)
    created_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.amount} {self.currency} — {self.status}"


# ─────────────────────────────────────────────
#  DISPUTE
# ─────────────────────────────────────────────

class Dispute(models.Model):
    STATUS_CHOICES = [
        ("open",         "Open"),
        ("under_review", "Under Review"),
        ("resolved",     "Resolved"),
        ("rejected",     "Rejected"),
    ]

    transaction      = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE)
    raised_by        = models.ForeignKey(User, on_delete=models.PROTECT)
    reason           = models.TextField()
    evidence_url     = models.URLField(blank=True)
    status           = models.CharField(max_length=50, choices=STATUS_CHOICES, default="open")
    resolution_notes = models.TextField(blank=True)
    refund_amount    = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    resolved_by      = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_disputes")
    created_at       = models.DateTimeField(auto_now_add=True)
    resolved_at      = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Dispute #{self.id} — {self.status}"


# ─────────────────────────────────────────────
#  NOTIFICATION
# ─────────────────────────────────────────────

class Notification(models.Model):
    TYPE_CHOICES = [
        ("order",   "Order"),
        ("payment", "Payment"),
        ("dispute", "Dispute"),
        ("system",  "System"),
        ("stock",   "Stock Alert"),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    title      = models.CharField(max_length=255)
    message    = models.TextField()
    link       = models.CharField(max_length=500, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.type}] {self.title} → {self.user.username}"


# ─────────────────────────────────────────────
#  LOG TRAIL
# ─────────────────────────────────────────────

class LogTrail(models.Model):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user                = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action_type         = models.CharField(max_length=100)
    related_transaction = models.ForeignKey(EscrowTransaction, null=True, blank=True, on_delete=models.SET_NULL)
    description         = models.TextField()
    ip_address          = models.GenericIPAddressField(null=True, blank=True)
    user_agent          = models.TextField(blank=True)
    metadata            = models.JSONField(default=dict, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} by {self.user}"


# ─────────────────────────────────────────────
#  SITE VISIT
# ─────────────────────────────────────────────

class SiteVisit(models.Model):
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    session_id       = models.CharField(max_length=255)
    page_url         = models.CharField(max_length=500)
    referrer         = models.CharField(max_length=500, blank=True)
    ip_address       = models.GenericIPAddressField(null=True, blank=True)
    device_type      = models.CharField(max_length=50, blank=True)
    browser          = models.CharField(max_length=100, blank=True)
    os               = models.CharField(max_length=100, blank=True)
    duration_seconds = models.IntegerField(default=0)
    country          = models.CharField(max_length=100, blank=True)
    city             = models.CharField(max_length=100, blank=True)
    is_authenticated = models.BooleanField(default=False)
    visited_at       = models.DateTimeField(auto_now_add=True)


# ─────────────────────────────────────────────
#  DELIVERY CONFIRMATION
# ─────────────────────────────────────────────

class DeliveryConfirmation(models.Model):
    transaction         = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE)
    confirmed_by_buyer  = models.BooleanField(default=False)
    confirmed_by_system = models.BooleanField(default=False)
    tracking_number     = models.CharField(max_length=100, blank=True)
    courier_name        = models.CharField(max_length=100, blank=True)
    delivery_proof_url  = models.URLField(blank=True)
    confirmed_at        = models.DateTimeField(auto_now_add=True)
