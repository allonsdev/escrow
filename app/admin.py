from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
from import_export.admin import ExportMixin
from django.contrib import admin
from .models import *

class BusinessAdminSite(admin.AdminSite):
    site_header = "Business Intelligence Admin"
    site_title = "BI Admin"
    index_title = "Management Dashboard"

admin_site = BusinessAdminSite(name="business_admin")


# ==============================
# Custom User Admin
# ==============================
@admin.register(User)
class CustomUserAdmin( ExportMixin,UserAdmin):
    model = User

    list_display = (
        "username",
        "email",
        "is_buyer",
        "is_seller",
        "is_verified",
        "verification_level",
        "trust_score",
        "fraud_risk_score",
        "is_flagged",
        "country",
        "created_at",
    )

    list_filter = (
        "is_buyer",
        "is_seller",
        "is_verified",
        "verification_level",
        "is_flagged",
        "country",
    )

    search_fields = ("username", "email", "phone_number", "national_id")
    ordering = ("-created_at",)

    fieldsets = UserAdmin.fieldsets + (
        ("Role Information", {
            "fields": ("is_buyer", "is_seller")
        }),
        ("Identity", {
            "fields": ("phone_number", "national_id", "date_of_birth")
        }),
        ("Verification", {
            "fields": ("is_verified", "verification_level")
        }),
        ("Trust & Risk", {
            "fields": (
                "trust_score",
                "successful_transactions",
                "failed_transactions",
                "disputed_transactions",
                "dispute_win_rate",
                "fraud_risk_score",
                "is_flagged",
            )
        }),
        ("Activity Analytics", {
            "fields": (
                "total_logins",
                "last_login_ip",
                "device_fingerprint",
                "last_activity",
            )
        }),
        ("Location", {
            "fields": ("country", "city")
        }),
    )


# ==============================
# Simple Registrations
# ==============================

@admin.register(UserWallet)
class UserWalletAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("user", "wallet_address", "blockchain_network", "balance_snapshot", "created_at")
    search_fields = ("user__username", "wallet_address")
    list_filter = ("blockchain_network",)


@admin.register(UserContact)
class UserContactAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("user", "full_name", "email", "city", "country", "is_default_shipping")
    search_fields = ("user__username", "email", "full_name")
    list_filter = ("country", "is_default_shipping")


@admin.register(Product)
class ProductAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("name", "seller", "price", "currency", "quantity_available", "is_active", "total_views", "total_purchases")
    search_fields = ("name", "seller__username")
    list_filter = ("is_active", "category", "condition")
    ordering = ("-created_at",)


@admin.register(Order)
class OrderAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("id", "buyer", "seller", "product", "quantity", "total_price", "status", "created_at")
    search_fields = ("buyer__username", "seller__username", "product__name")
    list_filter = ("status", "currency")
    ordering = ("-created_at",)


@admin.register(EscrowTransaction)
class EscrowTransactionAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("id", "order", "buyer", "seller", "amount", "status", "blockchain_network", "fraud_risk_score")
    search_fields = ("contract_address", "order__id")
    list_filter = ("status", "blockchain_network")
    ordering = ("-created_at",)


@admin.register(Payment)
class PaymentAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("transaction", "payer", "amount", "currency", "payment_method", "status", "confirmations")
    search_fields = ("transaction__id", "blockchain_tx_hash")
    list_filter = ("status", "payment_method")
    ordering = ("-created_at",)


@admin.register(LogTrail)
class LogTrailAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("id", "user", "action_type", "related_transaction", "ip_address", "created_at")
    search_fields = ("action_type", "user__username")
    list_filter = ("action_type",)
    ordering = ("-created_at",)


@admin.register(UserEvent)
class UserEventAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("user", "event_type", "ip_address", "created_at")
    search_fields = ("event_type", "user__username")
    ordering = ("-created_at",)


@admin.register(SiteVisit)
class SiteVisitAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("user", "page_url", "country", "city", "device_type", "browser", "duration_seconds", "visited_at")
    search_fields = ("page_url", "user__username", "session_id")
    list_filter = ("country", "device_type", "is_authenticated")
    ordering = ("-visited_at",)


@admin.register(Dispute)
class DisputeAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("transaction", "raised_by", "status", "refund_amount", "created_at")
    search_fields = ("transaction__id", "raised_by__username")
    list_filter = ("status",)
    ordering = ("-created_at",)


@admin.register(DeliveryConfirmation)
class DeliveryConfirmationAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("transaction", "confirmed_by_buyer", "confirmed_by_system", "courier_name", "tracking_number")
    search_fields = ("tracking_number", "courier_name")
