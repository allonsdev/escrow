from django.http import JsonResponse
from app.services.blockchain_service import BlockchainService, w3
from .models import *
from app.services.notification_service import NotificationService
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Avg, Count
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from decimal import Decimal

from .models import (
    Order,
    EscrowTransaction,
    Payment,
    Dispute,
    User,
    Product
)
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg
from django.utils.timezone import now
from datetime import timedelta
from .models import (
    Order,
    EscrowTransaction,
    Payment,
    Dispute,
    User
)
from django.shortcuts import render
from .models import Product
from django.shortcuts import redirect
from django.conf import settings
from .models import Order, EscrowTransaction, Product
from .services.blockchain_service import BlockchainService
from .services.blockchain_service import BlockchainService
from .models import *




from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta



from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Order, UserWallet


@login_required
def wallet(request):

    user = request.user

    wallet = UserWallet.objects.filter(user=user).first()

    purchases = Order.objects.filter(buyer=user).select_related(
        "product", "seller"
    ).order_by("-created_at")

    sales = Order.objects.filter(seller=user).select_related(
        "product", "buyer"
    ).order_by("-created_at")

    context = {
        "wallet": wallet,
        "purchases": purchases,
        "sales": sales,
    }

    return render(request, "wallet.html", context)
def analytics_dashboard(request):
    # USERS
    total_users = User.objects.count()
    verified_users = User.objects.filter(is_verified=True).count()
    flagged_users = User.objects.filter(is_flagged=True).count()
    avg_trust = User.objects.aggregate(Avg('trust_score'))['trust_score__avg'] or 0
    avg_fraud_user = User.objects.aggregate(Avg('fraud_risk_score'))['fraud_risk_score__avg'] or 0

    # PRODUCTS
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    avg_conversion = Product.objects.aggregate(Avg('conversion_rate'))['conversion_rate__avg'] or 0
    total_purchases = Product.objects.aggregate(Count('total_purchases'))['total_purchases__count'] or 0

    # ORDERS
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(status="completed").count()
    pending_orders = Order.objects.filter(status="pending").count()

    # ESCROWS
    total_escrows = EscrowTransaction.objects.count()
    funded_escrows = EscrowTransaction.objects.filter(status="funded").count()
    disputed_escrows = EscrowTransaction.objects.filter(status="disputed").count()
    refunded_escrows = EscrowTransaction.objects.filter(status="refunded").count()
    avg_fraud_escrow = EscrowTransaction.objects.aggregate(Avg('fraud_risk_score'))['fraud_risk_score__avg'] or 0

    # DISPUTES
    total_disputes = Dispute.objects.count()
    open_disputes = Dispute.objects.filter(status="open").count()
    resolved_disputes = Dispute.objects.filter(status="resolved").count()

    # PAYMENTS
    total_payments = Payment.objects.count()
    paid_amount = Payment.objects.aggregate(Avg('amount'))['amount__avg'] or 0

    # SITE ACTIVITY
    total_visits = SiteVisit.objects.count()
    unique_visitors = SiteVisit.objects.values('session_id').distinct().count()

    # TREND (last 7 days)
    today = timezone.now().date()
    trend_labels = []
    order_trend = []
    dispute_trend = []

    for i in range(7):
        day = today - timedelta(days=i)
        trend_labels.append(str(day))
        order_trend.append(Order.objects.filter(created_at__date=day).count())
        dispute_trend.append(Dispute.objects.filter(created_at__date=day).count())

    trend_labels.reverse()
    order_trend.reverse()
    dispute_trend.reverse()
# ADD TABLE DATA (LIMIT TO 50 FOR PERFORMANCE)
    recent_escrows = EscrowTransaction.objects.select_related(
        "buyer", "seller"
    ).order_by("-created_at")[:50]

    recent_payments = Payment.objects.select_related(
        "transaction", "payer"
    ).order_by("-created_at")[:50]

    recent_logs = LogTrail.objects.select_related(
        "user", "related_transaction"
    ).order_by("-created_at")[:50]

    recent_visits = SiteVisit.objects.select_related(
        "user"
    ).order_by("-visited_at")[:50]

    # ADD TO CONTEXT

    return render(request, "dashboard.html", {
        # USERS
        "total_users": total_users,
        "verified_users": verified_users,
        "flagged_users": flagged_users,
        "avg_trust": avg_trust,
        "avg_fraud_user": avg_fraud_user,

        # PRODUCTS
        "total_products": total_products,
        "active_products": active_products,
        "avg_conversion": avg_conversion,
        "total_purchases": total_purchases,

        # ORDERS
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,

        # ESCROW
        "total_escrows": total_escrows,
        "funded_escrows": funded_escrows,
        "disputed_escrows": disputed_escrows,
        "refunded_escrows": refunded_escrows,
        "avg_fraud_escrow": avg_fraud_escrow,

        # DISPUTES
        "total_disputes": total_disputes,
        "open_disputes": open_disputes,
        "resolved_disputes": resolved_disputes,

        # PAYMENTS
        "total_payments": total_payments,
        "paid_amount": paid_amount,

        # SITE
        "total_visits": total_visits,
        "unique_visitors": unique_visitors,

        # TREND
        "trend_labels": trend_labels,
        "order_trend": order_trend,
        "dispute_trend": dispute_trend,
        "recent_escrows": recent_escrows,
"recent_payments": recent_payments,
"recent_logs": recent_logs,
"recent_visits": recent_visits,
    })

def raise_dispute(request, escrow_id):
    escrow = EscrowTransaction.objects.get(id=escrow_id)

    if request.method == "POST":
        Dispute.objects.create(
            transaction=escrow,
            raised_by=request.user,
            reason=request.POST.get("reason"),
            status="open"
        )

        escrow.status = "disputed"
        escrow.save()

        messages.warning(request, "Dispute opened successfully.")

        send_mail(
            subject="Dispute Opened",
            message=f"A dispute was opened for Order #{escrow.order.id}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[escrow.buyer.email, escrow.seller.email],
            fail_silently=True,
        )

        return redirect("order_detail", escrow.order.id)

    return render(request, "dispute.html")


from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from decimal import Decimal


# FUND ESCROW
def fund_escrow(request, escrow_id):

    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    if request.method == "POST":

        # Prevent double funding
        if escrow.status == "paid":
            messages.error(request, "Escrow already funded.")
            return redirect("order_detail", escrow.order.id)

        buyer_wallet = escrow.buyer.userwallet

        # Check wallet balance
        if Decimal(buyer_wallet.balance_snapshot) < Decimal(escrow.amount):

            messages.error(
                request,
                "Insufficient wallet balance to fund escrow."
            )

            return redirect("order_detail", escrow.order.id)

        try:

            receipt = BlockchainService.deposit(
                escrow_id=escrow.blockchain_escrow_id,
                from_address=BlockchainService.checksum(
                    request.user.userwallet.wallet_address
                ),
                amount_eth=float(escrow.amount)
            )

        except Exception as e:

            if "insufficient funds" in str(e).lower():
                messages.error(
                    request,
                    "Blockchain wallet has insufficient ETH for gas."
                )
            else:
                messages.error(
                    request,
                    "Blockchain transaction failed."
                )

            return redirect("order_detail", escrow.order.id)

        # Record payment
        Payment.objects.create(
            transaction=escrow,
            payer=request.user,
            amount=escrow.amount,
            currency=escrow.currency,
            payment_method="ganache",
            blockchain_tx_hash=receipt.transactionHash.hex(),
            status="funded"
        )

        buyer_wallet.balance_snapshot -= Decimal(escrow.amount)
        buyer_wallet.save()

        escrow.status = "paid"
        escrow.save()

        messages.success(request, "Escrow funded successfully.")

        send_order_email(request, escrow.order)

        return redirect("order_detail", escrow.order.id)

from django.contrib import messages
from django.shortcuts import redirect


def release_delivery(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    # if request.user != order.seller:
    #     messages.error(request, "Only seller can ship this order.")
    #     return redirect("order_detail", order.id)

    # if order.status != "paid":
    #     messages.error(request, "Order must be paid before shipping.")
    #     return redirect("order_detail", order.id)

    if request.method == "POST":

        order.status = "shipped"
        order.save()

        messages.success(request, "Order marked as shipped.")

    return redirect("order_detail", order.id)


def confirm_delivery(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    if request.user != order.buyer:
        messages.error(request, "Only buyer can confirm delivery.")
        return redirect("order_detail", order.id)

    if order.status != "shipped":
        messages.error(request, "Order must be shipped first.")
        return redirect("order_detail", order.id)

    if request.method == "POST":

        escrow = order.escrowtransaction

        seller_wallet = order.seller.userwallet

        # Credit seller balance
        seller_wallet.balance_snapshot += Decimal(order.total_price)
        seller_wallet.save()

        # Update escrow
        escrow.status = "released"
        escrow.save()

        # Update order
        order.status = "completed"
        order.save()

        messages.success(
            request,
            "Delivery confirmed. Funds released to seller."
        )

        send_order_email(request, order)

    return redirect("order_detail", order.id)


def mark_received(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    # if request.user != order.buyer:
    #     messages.error(request, "Only buyer can mark received.")
    #     return redirect("order_detail", order.id)

    # if order.status != "shipped":
    #     messages.error(request, "Order has not been shipped.")
    #     return redirect("order_detail", order.id)

    if request.method == "POST":

        order.status = "completed"
        order.save()

        messages.success(request, "Order received successfully.")

    return redirect("order_detail", order.id)



# EMAIL FUNCTION
def send_order_email(request, order):
    # Build URLs
    confirm_url = request.build_absolute_uri(
        f"/orders/{order.id}/confirm_delivery/"
    )
    ship_url = request.build_absolute_uri(
        f"/orders/{order.id}/release_delivery/"
    )
    received_url = request.build_absolute_uri(
        f"/orders/{order.id}/received/"
    )

    # HTML Email Content
    html = f"""
    <html>
        <body style="font-family: Segoe UI; background: #f3f4f6; padding: 30px;">
            <div style="
                background: white;
                padding: 25px;
                border-radius: 10px;
                max-width: 500px;
                margin: auto;
                text-align: center;
            ">
                <h2>Order Update</h2>

                <p>Order <b>#{order.id}</b> status updated.</p>

                <p><b>Product:</b> {order.product.name}</p>

                <hr style="margin: 20px 0;">

                <!-- Buttons Container -->
                <div style="
                    display: flex;
                    justify-content: center;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-top: 15px;
                ">

                    <a href="{ship_url}" style="
                        background: #ffa41c;
                        color: white;
                        padding: 12px 18px;
                        text-decoration: none;
                        border-radius: 6px;
                        display: inline-block;
                    ">
                        Ship Order
                    </a>

                    <a href="{confirm_url}" style="
                        background: #0d6efd;
                        color: white;
                        padding: 12px 18px;
                        text-decoration: none;
                        border-radius: 6px;
                        display: inline-block;
                    ">
                        Confirm Delivery
                    </a>

                    <a href="{received_url}" style="
                        background: #198754;
                        color: white;
                        padding: 12px 18px;
                        text-decoration: none;
                        border-radius: 6px;
                        display: inline-block;
                    ">
                        Mark Received
                    </a>

                </div>
            </div>
        </body>
    </html>
    """

    # Create Email
    email = EmailMultiAlternatives(
        subject=f"Order #{order.id} Update",
        body="Order update",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.buyer.email, order.seller.email],
    )

    # Attach HTML version
    email.attach_alternative(html, "text/html")

    # Send Email
    email.send()

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect

def login_view(request):
    if request.user.is_authenticated:
        return redirect('product_list')

    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('product_list')
        else:
            error = "Invalid username or password"

    return render(request, "login.html", {"error": error})

def checkout(request, product_id):
    product = Product.objects.get(id=product_id)

    if request.method == "POST":

        # ✅ Create order
        order = Order.objects.create(
            buyer=request.user,
            seller=product.seller,
            product=product,
            quantity=1,
            total_price=product.price,
            currency=product.currency,
            status="escrow_created"
        )

        # ✅ Create escrow record
        escrow = EscrowTransaction.objects.create(
            order=order,
            buyer=request.user,
            seller=product.seller,
            amount=product.price,
            currency=product.currency,
            status="created",
            blockchain_network="ganache"
        )

        # ✅ Deploy escrow on blockchain
        result = BlockchainService.create_escrow(
            buyer_address=BlockchainService.checksum(
                request.user.userwallet.wallet_address
            ),
            seller_address=BlockchainService.checksum(
                product.seller.userwallet.wallet_address
            )
        )

        escrow.contract_address = settings.MASTER_CONTRACT_ADDRESS
        escrow.blockchain_escrow_id = result["escrow_id"]
        escrow.deployment_tx_hash = result["receipt"].transactionHash.hex()
        escrow.save()

        # ✅ DJANGO ALERT
        messages.success(request, "Order placed! Escrow created successfully.")

        # ✅ EMAIL TO BUYER
        send_mail(
            subject="Order Confirmation",
            message=f"""
Your order #{order.id} was created successfully.

Product: {product.name}
Amount: {product.price} {product.currency}

Next step: Fund the escrow to start the transaction.
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=True,
        )

        # ✅ EMAIL TO SELLER
        send_mail(
            subject="New Order Received",
            message=f"""
You received a new order #{order.id}.

Product: {product.name}
Buyer: {request.user.username}
Amount: {product.price} {product.currency}

Waiting for buyer to fund escrow.
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=True,
        )

        return redirect("order_detail", order.id)

    return render(request, "checkout.html", {
        "product": product
    })



def order_detail(request, order_id):
    order = Order.objects.get(id=order_id)

    return render(request, "order.html", {
        "order": order
    })
    
from django.core.paginator import Paginator
from django.shortcuts import render

def product_list(request):
    query = request.GET.get('q')
    products = Product.objects.filter(is_active=True)

    if query:
        products = products.filter(name__icontains=query)

    from django.core.paginator import Paginator
    paginator = Paginator(products, 8)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "product.html", {
        "page_obj": page_obj
    })
    
def product_detail(request, product_id):
    product = Product.objects.get(id=product_id)

    return render(request, "productdetail.html", {
        "product": product
    })



def chart_view(request):
    # ==============================
    # TIME SERIES (LINE CHART)
    # Orders last 30 days
    # ==============================
    thirty_days_ago = now() - timedelta(days=30)

    orders_time = (
        Order.objects
        .filter(created_at__gte=thirty_days_ago)
        .extra({'day': "date(created_at)"})
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    line_labels = [o['day'].strftime('%Y-%m-%d') for o in orders_time]
    line_data = [o['count'] for o in orders_time]

    # ==============================
    # ESCROW STATUS (BAR CHART)
    # ==============================
    escrow_status = EscrowTransaction.objects.values('status').annotate(
        count=Count('id')
    )

    bar_labels = [e['status'] for e in escrow_status]
    bar_data = [e['count'] for e in escrow_status]

    # ==============================
    # FRAUD & TRUST (PIE CHART)
    # ==============================
    total_users = User.objects.count()
    flagged = User.objects.filter(is_flagged=True).count()
    clean = total_users - flagged

    pie_labels = ["Flagged Users", "Clean Users"]
    pie_data = [flagged, clean]

    avg_fraud = User.objects.aggregate(avg=Avg('fraud_risk_score'))['avg'] or 0
    avg_trust = User.objects.aggregate(avg=Avg('trust_score'))['avg'] or 0

    # ==============================
    # DISPUTE METRICS (BAR)
    # ==============================
    disputes = Dispute.objects.values('status').annotate(count=Count('id'))

    dispute_labels = [d['status'] for d in disputes]
    dispute_data = [d['count'] for d in disputes]

    total_disputes = Dispute.objects.count()
    resolved = Dispute.objects.filter(status="resolved").count()
    open_disputes = Dispute.objects.filter(status="open").count()

    # ==============================
    # REVENUE (LINE/BAR)
    # ==============================
    revenue_time = (
        Payment.objects
        .filter(status="paid")
        .extra({'day': "date(created_at)"})
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )

    revenue_labels = [r['day'].strftime('%Y-%m-%d') for r in revenue_time]
    revenue_data = [float(r['total']) if r['total'] else 0 for r in revenue_time]

    total_revenue = Payment.objects.filter(status="paid").aggregate(
        total=Sum('amount')
    )['total'] or 0

    # ==============================
    # RESPONSE (REAL-TIME FRIENDLY)
    # ==============================
    return JsonResponse({
        "line": {
            "labels": line_labels,
            "data": line_data
        },
        "bar": {
            "labels": bar_labels,
            "data": bar_data
        },
        "pie": {
            "labels": pie_labels,
            "data": pie_data
        },
        "disputes": {
            "labels": dispute_labels,
            "data": dispute_data,
            "total": total_disputes,
            "open": open_disputes,
            "resolved": resolved
        },
        "fraud": {
            "avg_fraud": float(avg_fraud),
            "avg_trust": float(avg_trust),
            "flagged_users": flagged,
            "total_users": total_users
        },
        "revenue": {
            "labels": revenue_labels,
            "data": revenue_data,
            "total": float(total_revenue)
        }
    })
    
    
    

# def analytics_dashboard(request):
#     # ORDERS
#     total_orders = Order.objects.count()
#     completed_orders = Order.objects.filter(status="completed").count()
#     pending_orders = Order.objects.filter(status="pending").count()

#     # ESCROW
#     total_escrows = EscrowTransaction.objects.count()
#     funded = EscrowTransaction.objects.filter(status="funded").count()
#     released = EscrowTransaction.objects.filter(status="released").count()
#     disputed = EscrowTransaction.objects.filter(status="disputed").count()

#     # PAYMENTS
#     total_revenue = Payment.objects.filter(status="paid").aggregate(
#         total=Sum('amount')
#     )['total'] or 0

#     avg_payment = Payment.objects.filter(status="paid").aggregate(
#         avg=Avg('amount')
#     )['avg'] or 0

#     # DISPUTES
#     total_disputes = Dispute.objects.count()
#     open_disputes = Dispute.objects.filter(status="open").count()
#     resolved_disputes = Dispute.objects.filter(status="resolved").count()

#     # USERS
#     total_users = User.objects.count()
#     verified_users = User.objects.filter(is_verified=True).count()
#     flagged_users = User.objects.filter(is_flagged=True).count()

#     # PRODUCTS
#     total_products = Product.objects.count()
#     active_products = Product.objects.filter(is_active=True).count()

#     # TRUST & FRAUD
#     avg_trust = User.objects.aggregate(avg=Avg('trust_score'))['avg'] or 0
#     avg_fraud = User.objects.aggregate(avg=Avg('fraud_risk_score'))['avg'] or 0

#     # CONVERSION (optional)
#     conversion_rate = (completed_orders / total_orders) * 100 if total_orders else 0
#     dispute_rate = (total_disputes / total_orders) * 100 if total_orders else 0

#     context = {
#         "total_orders": total_orders,
#         "completed_orders": completed_orders,
#         "pending_orders": pending_orders,

#         "total_escrows": total_escrows,
#         "funded": funded,
#         "released": released,
#         "disputed": disputed,

#         "total_revenue": total_revenue,
#         "avg_payment": avg_payment,

#         "total_disputes": total_disputes,
#         "open_disputes": open_disputes,
#         "resolved_disputes": resolved_disputes,

#         "total_users": total_users,
#         "verified_users": verified_users,
#         "flagged_users": flagged_users,

#         "total_products": total_products,
#         "active_products": active_products,

#         "avg_trust": avg_trust,
#         "avg_fraud": avg_fraud,

#         "conversion_rate": conversion_rate,
#         "dispute_rate": dispute_rate,
#     }

#     return render(request, "admin/analytics.html", context)

def create_order(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    buyer = request.user
    seller = product.seller

    # Create Order
    order = Order.objects.create(
        buyer=buyer,
        seller=seller,
        product=product,
        quantity=1,
        total_price=product.price,
        currency=product.currency,
        status="pending"
    )

    # Create Escrow DB record
    escrow = EscrowTransaction.objects.create(
        order=order,
        buyer=buyer,
        seller=seller,
        amount=product.price,
        currency=product.currency,
        status="created",
        blockchain_network="ganache"
    )

    # Create blockchain escrow
    result = BlockchainService.create_escrow(
        buyer_address=buyer.userwallet.wallet_address,
        seller_address=seller.userwallet.wallet_address
    )

    escrow.contract_address = str(result["escrow_id"])
    escrow.deployment_tx_hash = result["receipt"].transactionHash.hex()
    escrow.save()

    order.status = "escrow_created"
    order.save()

    NotificationService.order_created(order)

    return JsonResponse({
        "status": "success",
        "order_id": str(order.id),
        "escrow_id": result["escrow_id"]
    })


# def confirm_delivery(request, escrow_id):
#     escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

#     receipt = BlockchainService.confirm_delivery(
#         escrow_id=int(escrow.contract_address),
#         buyer_address=escrow.buyer.userwallet.wallet_address
#     )

#     escrow.status = "released"
#     escrow.save()

#     order = escrow.order
#     order.status = "completed"
#     order.save()

#     NotificationService.delivery_confirmed(order)

#     return JsonResponse({"status": "released"})
    
    
def create_dispute(request, escrow_id):
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    dispute = Dispute.objects.create(
        transaction=escrow,
        raised_by=request.user,
        reason=request.POST.get("reason"),
        status="open"
    )

    escrow.status = "disputed"
    escrow.save()

    NotificationService.dispute_opened(escrow)

    return JsonResponse({"status": "disputed"})




def refund_buyer(request, escrow_id):
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    receipt = BlockchainService.refund_buyer(
        escrow_id=int(escrow.contract_address),
        arbiter_address=request.user.userwallet.wallet_address
    )

    escrow.status = "refunded"
    escrow.save()

    order = escrow.order
    order.status = "cancelled"
    order.save()

    NotificationService.refund_issued(escrow)

    return JsonResponse({"status": "refunded"})


def deposit_to_escrow(request, escrow_id):
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    receipt = BlockchainService.deposit(
        escrow_id=int(escrow.contract_address),
        from_address=escrow.buyer.userwallet.wallet_address,
        amount_eth=float(escrow.amount)
    )

    Payment.objects.create(
        transaction=escrow,
        payer=escrow.buyer,
        amount=escrow.amount,
        currency=escrow.currency,
        payment_method="blockchain",
        blockchain_tx_hash=receipt.transactionHash.hex(),
        status="paid",
        confirmations=0
    )

    escrow.status = "funded"
    escrow.block_number = receipt.blockNumber
    escrow.gas_used = receipt.gasUsed
    escrow.save()

    order = escrow.order
    order.status = "paid"
    order.save()

    NotificationService.escrow_funded(order)

    return JsonResponse({"status": "funded"})


def test_blockchain(request):
    try:
        # Use Ganache accounts
        buyer = w3.eth.accounts[1]
        seller = w3.eth.accounts[2]

        # 1️⃣ Create Escrow
        escrow_result = BlockchainService.create_escrow(buyer, seller)
        escrow_id = escrow_result["escrow_id"]

        if escrow_id is None:
            return JsonResponse({
                "status": "error",
                "message": "Escrow ID not returned from event"
            })

        # 2️⃣ Deposit 1 ETH
        BlockchainService.deposit(
            escrow_id=escrow_id,
            from_address=buyer,
            amount_eth=1
        )

        # 3️⃣ Confirm Delivery
        BlockchainService.confirm_delivery(
            escrow_id=escrow_id,
            buyer_address=buyer
        )

        return JsonResponse({
            "status": "success",
            "escrow_id": escrow_id,
            "buyer": buyer,
            "seller": seller,
            "message": "Escrow created, funded, and confirmed successfully."
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })