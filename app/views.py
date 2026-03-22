from django.http import JsonResponse
from app.services.blockchain_service import BlockchainService, w3
from .models import *
from app.services.notification_service import NotificationService
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Avg, Count

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

        return redirect("order_detail", escrow.order.id)

    return render(request, "dispute.html")

def fund_escrow(request, escrow_id):
    escrow = EscrowTransaction.objects.get(id=escrow_id)

    if request.method == "POST":

        receipt = BlockchainService.deposit(
            escrow_id=escrow.id,
            from_address=request.user.userwallet.wallet_address,
            amount_eth=float(escrow.amount)
        )

        Payment.objects.create(
            transaction=escrow,
            payer=request.user,
            amount=escrow.amount,
            currency=escrow.currency,
            payment_method="ganache",
            blockchain_tx_hash=receipt.transactionHash.hex(),
            status="funded"
        )

        escrow.status = "funded"
        escrow.block_number = receipt.blockNumber
        escrow.gas_used = receipt.gasUsed
        escrow.save()

        return redirect("order_detail", escrow.order.id)




def checkout(request, product_id):
    product = Product.objects.get(id=product_id)

    if request.method == "POST":

        # Create order
        order = Order.objects.create(
            buyer=request.user,
            seller=product.seller,
            product=product,
            quantity=1,
            total_price=product.price,
            currency=product.currency,
            status="escrow_created"
        )

        # Create escrow DB record
        escrow = EscrowTransaction.objects.create(
            order=order,
            buyer=request.user,
            seller=product.seller,
            amount=product.price,
            currency=product.currency,
            status="created",
            blockchain_network="ganache"
        )

        # 🚀 Create escrow on blockchain
        result = BlockchainService.create_escrow(
            buyer_address=request.user.userwallet.wallet_address,
            seller_address=product.seller.userwallet.wallet_address
        )

        escrow.contract_address = settings.MASTER_CONTRACT_ADDRESS
        escrow.deployment_tx_hash = result["receipt"].transactionHash.hex()
        escrow.save()

        return redirect("order_detail", order.id)

    return render(request, "checkout.html", {
        "product": product
    })



def order_detail(request, order_id):
    order = Order.objects.get(id=order_id)

    return render(request, "order.html", {
        "order": order
    })
    
    
def product_list(request):
    products = Product.objects.filter(is_active=True)

    return render(request, "product.html", {
        "products": products
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
    
    
    

def analytics_dashboard(request):
    # ORDERS
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(status="completed").count()
    pending_orders = Order.objects.filter(status="pending").count()

    # ESCROW
    total_escrows = EscrowTransaction.objects.count()
    funded = EscrowTransaction.objects.filter(status="funded").count()
    released = EscrowTransaction.objects.filter(status="released").count()
    disputed = EscrowTransaction.objects.filter(status="disputed").count()

    # PAYMENTS
    total_revenue = Payment.objects.filter(status="paid").aggregate(
        total=Sum('amount')
    )['total'] or 0

    avg_payment = Payment.objects.filter(status="paid").aggregate(
        avg=Avg('amount')
    )['avg'] or 0

    # DISPUTES
    total_disputes = Dispute.objects.count()
    open_disputes = Dispute.objects.filter(status="open").count()
    resolved_disputes = Dispute.objects.filter(status="resolved").count()

    # USERS
    total_users = User.objects.count()
    verified_users = User.objects.filter(is_verified=True).count()
    flagged_users = User.objects.filter(is_flagged=True).count()

    # PRODUCTS
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()

    # TRUST & FRAUD
    avg_trust = User.objects.aggregate(avg=Avg('trust_score'))['avg'] or 0
    avg_fraud = User.objects.aggregate(avg=Avg('fraud_risk_score'))['avg'] or 0

    # CONVERSION (optional)
    conversion_rate = (completed_orders / total_orders) * 100 if total_orders else 0
    dispute_rate = (total_disputes / total_orders) * 100 if total_orders else 0

    context = {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,

        "total_escrows": total_escrows,
        "funded": funded,
        "released": released,
        "disputed": disputed,

        "total_revenue": total_revenue,
        "avg_payment": avg_payment,

        "total_disputes": total_disputes,
        "open_disputes": open_disputes,
        "resolved_disputes": resolved_disputes,

        "total_users": total_users,
        "verified_users": verified_users,
        "flagged_users": flagged_users,

        "total_products": total_products,
        "active_products": active_products,

        "avg_trust": avg_trust,
        "avg_fraud": avg_fraud,

        "conversion_rate": conversion_rate,
        "dispute_rate": dispute_rate,
    }

    return render(request, "admin/analytics.html", context)

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


def confirm_delivery(request, escrow_id):
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    receipt = BlockchainService.confirm_delivery(
        escrow_id=int(escrow.contract_address),
        buyer_address=escrow.buyer.userwallet.wallet_address
    )

    escrow.status = "released"
    escrow.save()

    order = escrow.order
    order.status = "completed"
    order.save()

    NotificationService.delivery_confirmed(order)

    return JsonResponse({"status": "released"})
    
    
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