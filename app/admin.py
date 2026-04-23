from django.contrib import admin
from django.utils.html import format_html
from .models import *


# ─────────────────────────────────────────────
#  GLOBAL COLOR HELPER
# ─────────────────────────────────────────────

def colored_badge(value, color_map):
    color = color_map.get(value, "secondary")
    return format_html(
        '<span style="padding:4px 8px; border-radius:6px; background:{}; color:white;">{}</span>',
        color,
        value.upper()
    )


STATUS_COLORS = {
    "pending": "orange",
    "paid": "blue",
    "shipped": "purple",
    "completed": "green",
    "cancelled": "red",
    "disputed": "darkred",
}


# ─────────────────────────────────────────────
#  USER ADMIN
# ─────────────────────────────────────────────

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username", "email", "is_seller",
        "is_verified", "verification_level",
        "trust_score", "is_flagged", "is_staff"
    )

    list_filter = (
        "is_seller",
        "is_verified",
        "verification_level",
        "is_flagged",
        "is_staff",
        "country",
    )

    search_fields = ("username", "email", "phone_number")

    fieldsets = (
        ("Basic Info", {
            "fields": ("username", "email", "password")
        }),
        ("Roles", {
            "fields": ("is_buyer", "is_seller")
        }),
        ("Permissions", {
            "fields": ("is_staff", "is_superuser", "is_active")
        }),
        ("Verification", {
            "fields": ("is_verified", "verification_level")
        }),
        ("Trust & Risk", {
            "fields": ("trust_score", "fraud_risk_score", "is_flagged")
        }),
        ("Activity", {
            "fields": ("last_login_ip", "last_activity")
        }),
    )


# ─────────────────────────────────────────────
#  PRODUCT ADMIN
# ─────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "seller", "price",
        "quantity_available", "stock_status_display",
        "is_active", "is_featured"
    )

    list_filter = (
        "is_active",
        "is_featured",
        "condition",
        "category",
    )

    search_fields = ("name", "description", "sku")

    def stock_status_display(self, obj):
        if obj.quantity_available <= 0:
            return colored_badge("out", {"out": "red"})
        elif obj.quantity_available <= obj.low_stock_threshold:
            return colored_badge("low", {"low": "orange"})
        return colored_badge("ok", {"ok": "green"})

    stock_status_display.short_description = "Stock"


# ─────────────────────────────────────────────
#  ORDER ADMIN
# ─────────────────────────────────────────────

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id_short",
        "buyer",
        "product",
        "total_price",
        "status_badge",
        "created_at"
    )

    list_filter = ("status", "created_at")

    search_fields = ("id", "buyer__username", "product__name")

    def id_short(self, obj):
        return str(obj.id)[:8]

    def status_badge(self, obj):
        return colored_badge(obj.status, STATUS_COLORS)

    status_badge.short_description = "Status"


# ─────────────────────────────────────────────
#  ESCROW ADMIN
# ─────────────────────────────────────────────

@admin.register(EscrowTransaction)
class EscrowAdmin(admin.ModelAdmin):
    list_display = (
        "id_short",
        "order",
        "amount",
        "status_badge",
        "created_at"
    )

    list_filter = ("status", "created_at")

    def id_short(self, obj):
        return str(obj.id)[:8]

    def status_badge(self, obj):
        return colored_badge(obj.status, STATUS_COLORS)


# ─────────────────────────────────────────────
#  PAYMENT ADMIN
# ─────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payer",
        "amount",
        "currency",
        "status",
        "confirmations",
        "created_at"
    )

    list_filter = ("status", "currency")

    search_fields = ("payer__username", "blockchain_tx_hash")


# ─────────────────────────────────────────────
#  DISPUTE ADMIN
# ─────────────────────────────────────────────

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transaction",
        "raised_by",
        "status",
        "created_at"
    )

    list_filter = ("status",)

    search_fields = ("raised_by__username", "reason")


# ─────────────────────────────────────────────
#  CATEGORY ADMIN
# ─────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name",)


# ─────────────────────────────────────────────
#  SHOP ADMIN
# ─────────────────────────────────────────────

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        "name", "seller",
        "is_active", "is_verified",
        "total_sales", "rating"
    )

    list_filter = ("is_active", "is_verified")

    search_fields = ("name", "seller__username")


# ─────────────────────────────────────────────
#  NOTIFICATIONS
# ─────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "title", "is_read", "created_at")
    list_filter = ("type", "is_read")


# ─────────────────────────────────────────────
#  LOG TRAIL
# ─────────────────────────────────────────────

@admin.register(LogTrail)
class LogTrailAdmin(admin.ModelAdmin):
    list_display = ("action_type", "user", "created_at")
    list_filter = ("action_type",)
    search_fields = ("description",)


# ─────────────────────────────────────────────
#  SITE VISITS
# ─────────────────────────────────────────────

@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = ("user", "page_url", "country", "visited_at")
    list_filter = ("country", "device_type")


# ─────────────────────────────────────────────
#  DELIVERY CONFIRMATION
# ─────────────────────────────────────────────

@admin.register(DeliveryConfirmation)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "transaction",
        "confirmed_by_buyer",
        "confirmed_by_system",
        "confirmed_at"
    )


# ─────────────────────────────────────────────
#  USER WALLET ADMIN
# ─────────────────────────────────────────────

@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet_address", "blockchain_network", "balance_snapshot", "created_at")
    search_fields = ("user__username", "wallet_address")
    list_filter = ("blockchain_network",)


# ─────────────────────────────────────────────
#  PRODUCT IMAGE ADMIN
# ─────────────────────────────────────────────

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_primary", "sort_order", "created_at")
    list_filter = ("is_primary",)
    search_fields = ("product__name",)


# ─────────────────────────────────────────────
#  STOCK LOG ADMIN
# ─────────────────────────────────────────────

@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "action", "quantity_change", "quantity_before", "quantity_after", "note", "created_at")
    list_filter = ("action",)
    search_fields = ("product__name", "note")


# ─────────────────────────────────────────────
#  REVIEW ADMIN
# ─────────────────────────────────────────────

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_verified_purchase", "created_at")
    list_filter = ("rating", "is_verified_purchase")
    search_fields = ("product__name", "user__username", "title")


# ─────────────────────────────────────────────
#  USER CONTACT ADMIN
# ─────────────────────────────────────────────

@admin.register(UserContact)
class UserContactAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "email", "city", "country", "is_default_shipping")
    list_filter = ("country", "is_default_shipping")
    search_fields = ("user__username", "email", "full_name")