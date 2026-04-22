import json
from decimal import Decimal
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Avg, Count, Sum, Q, F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .models import (
    Category, Dispute, EscrowTransaction, LogTrail, Notification,
    Order, Payment, Product, ProductImage, Review, Shop, SiteVisit,
    StockLog, User, UserWallet,
)
from .services.blockchain_service import BlockchainService, w3
from .services.notification_service import NotificationService


# ─── HELPERS ─────────────────────────────────────────────────────────

def _notify(user, type_, title, message, link=""):
    Notification.objects.create(
        user=user, type=type_, title=title, message=message, link=link
    )


def _log(user, action_type, description, escrow=None, request=None):
    ip = ua = None
    if request:
        ip = request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")
    LogTrail.objects.create(
        user=user, action_type=action_type, description=description,
        related_transaction=escrow, ip_address=ip, user_agent=ua or ""
    )


# ─── EMAIL HELPERS ────────────────────────────────────────────────────

def _email_button(label: str, url: str, color: str) -> str:
    """Render a single CTA button for use inside HTML email."""
    return f"""<a href="{url}" style="
      display: inline-block;
      background-color: {color};
      color: #ffffff;
      text-decoration: none;
      font-size: 14px;
      font-weight: 600;
      padding: 13px 24px;
      border-radius: 8px;
      letter-spacing: 0.3px;
      margin: 4px 2px;
    ">{label}</a>"""


def _detail_row(label: str, value: str, accent_color: str = "#0f172a",
                large: bool = False, last: bool = False) -> str:
    """One labelled row inside the details card."""
    border       = "" if last else "border-bottom:1px solid #e2e8f0;"
    value_size   = "20px" if large else "15px"
    value_weight = "700"  if large else "600"
    return f"""
    <tr>
      <td style="padding:14px 20px; {border}">
        <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;
                     letter-spacing:0.5px;">{label}</span><br>
        <span style="font-size:{value_size}; font-weight:{value_weight};
                     color:{accent_color};">{value}</span>
      </td>
    </tr>"""


def _email_base(title: str, status_label: str, status_color: str,
                detail_rows_html: str, action_buttons: str) -> str:
    """
    Shared HTML shell used by all transactional emails.
    Dark header · white card · status chip · detail table · CTA buttons · footer.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="
  margin:0; padding:0;
  background-color:#f1f5f9;
  font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;
  color:#1e293b;
">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f1f5f9; padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" border="0"
               style="background:#ffffff; border-radius:16px; overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);">

          <!-- Header bar -->
          <tr>
            <td style="background:#0f172a; padding:28px 36px; text-align:left;">
              <span style="font-size:22px; font-weight:700; color:#ffffff;
                           letter-spacing:-0.5px;">MarketPro</span>
              <span style="display:block; font-size:13px; color:#94a3b8;
                           margin-top:4px;">Escrow &amp; Order Management</span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 36px 0 36px;">

              <!-- Status chip -->
              <div style="margin-bottom:24px;">
                <span style="
                  display:inline-block;
                  background:{status_color}1a;
                  color:{status_color};
                  border:1px solid {status_color}40;
                  border-radius:999px;
                  padding:5px 14px;
                  font-size:12px;
                  font-weight:600;
                  text-transform:uppercase;
                  letter-spacing:0.6px;
                ">{status_label}</span>
              </div>

              <!-- Heading -->
              <h1 style="margin:0 0 6px 0; font-size:24px; font-weight:700;
                         color:#0f172a; letter-spacing:-0.5px;">{title}</h1>

              <p style="margin:0 0 28px 0; font-size:15px; color:#64748b;
                        line-height:1.6;">
                Here is the latest status for your order.
                Please take action below if required.
              </p>

              <!-- Details table -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background:#f8fafc; border-radius:10px;
                            border:1px solid #e2e8f0; margin-bottom:28px;">
                {detail_rows_html}
              </table>

              <!-- Action buttons -->
              <div style="text-align:center; margin-bottom:32px;">
                {action_buttons}
              </div>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 36px; background:#f8fafc;
                       border-top:1px solid #e2e8f0; text-align:center;">
              <p style="margin:0; font-size:12px; color:#94a3b8; line-height:1.7;">
                This is an automated notification from MarketPro.<br>
                If you have questions, please contact support.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ─── ORDER EMAIL ──────────────────────────────────────────────────────

def send_order_email(request, order):
    """
    Rich HTML status email sent to both buyer and seller.
    Action buttons are contextual to the current order status.
    """
    confirm_url  = request.build_absolute_uri(f"/orders/{order.id}/confirm_delivery/")
    ship_url     = request.build_absolute_uri(f"/orders/{order.id}/release_delivery/")
    received_url = request.build_absolute_uri(f"/orders/{order.id}/received/")
    order_url    = request.build_absolute_uri(f"/orders/{order.id}/")

    STATUS_LABELS = {
        "escrow_created": ("Escrow Created", "#6366f1"),
        "paid":           ("Funded",         "#0ea5e9"),
        "shipped":        ("Shipped",        "#f59e0b"),
        "completed":      ("Completed",      "#22c55e"),
        "disputed":       ("Disputed",       "#ef4444"),
        "cancelled":      ("Cancelled",      "#6b7280"),
    }
    status_label, status_color = STATUS_LABELS.get(
        order.status,
        (order.status.replace("_", " ").title(), "#6b7280"),
    )

    # Context-sensitive action buttons
    action_buttons = ""
    if order.status == "paid":
        action_buttons = _email_button("Ship Order", ship_url, "#f59e0b")
    elif order.status == "shipped":
        action_buttons = (
            _email_button("Confirm Delivery", confirm_url, "#6366f1")
            + _email_button("Mark Received",   received_url, "#22c55e")
        )
    action_buttons += _email_button("View Order", order_url, "#0ea5e9")

    rows = (
        _detail_row("Product", order.product.name)
        + _detail_row("Buyer",   order.buyer.username)
        + _detail_row("Seller",  order.seller.username)
        + _detail_row(
            "Amount",
            f"{order.total_price} {order.currency}",
            accent_color=status_color,
            large=True,
            last=True,
        )
    )

    html = _email_base(
        title=f"Order #{str(order.id)[:8]} Update",
        status_label=status_label,
        status_color=status_color,
        detail_rows_html=rows,
        action_buttons=action_buttons,
    )

    try:
        email = EmailMultiAlternatives(
            subject=f"Order #{str(order.id)[:8]} — {status_label}",
            body=(
                f"Order #{order.id} status updated to {status_label}. "
                f"Visit {order_url} to take action."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.buyer.email, order.seller.email],
        )
        email.attach_alternative(html, "text/html")
        email.send(fail_silently=True)
    except Exception as e:
        print(f"[EMAIL ERROR] send_order_email failed for order {order.id}: {e}")


# ─── DISPUTE EMAIL ────────────────────────────────────────────────────

def send_dispute_email(request, escrow, reason=""):
    """Sends notification email when a dispute is opened."""
    order_url = request.build_absolute_uri(f"/orders/{escrow.order.id}/")

    rows = (
        _detail_row("Order",   f"#{str(escrow.order.id)[:8]}")
        + _detail_row("Product", escrow.order.product.name)
        + _detail_row("Buyer",   escrow.buyer.username)
        + _detail_row("Seller",  escrow.seller.username)
        + _detail_row(
            "Amount",
            f"{escrow.amount} {escrow.currency}",
            accent_color="#ef4444",
            large=True,
            last=not bool(reason),
        )
    )
    if reason:
        rows += _detail_row("Reason", reason, last=True)

    html = _email_base(
        title="Dispute Opened",
        status_label="Disputed",
        status_color="#ef4444",
        detail_rows_html=rows,
        action_buttons=_email_button("View Dispute", order_url, "#ef4444"),
    )

    try:
        email = EmailMultiAlternatives(
            subject=f"Dispute Opened — Order #{str(escrow.order.id)[:8]}",
            body=f"A dispute was opened for order {escrow.order.id}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[escrow.buyer.email, escrow.seller.email],
        )
        email.attach_alternative(html, "text/html")
        email.send(fail_silently=True)
    except Exception as e:
        print(f"[EMAIL ERROR] send_dispute_email failed: {e}")


# ─── REFUND EMAIL ─────────────────────────────────────────────────────

def send_refund_email(request, escrow):
    """Sends notification email when a refund is issued."""
    order_url = request.build_absolute_uri(f"/orders/{escrow.order.id}/")

    rows = (
        _detail_row("Order",       f"#{str(escrow.order.id)[:8]}")
        + _detail_row("Product",   escrow.order.product.name)
        + _detail_row("Refunded To", escrow.buyer.username)
        + _detail_row(
            "Amount",
            f"{escrow.amount} {escrow.currency}",
            accent_color="#22c55e",
            large=True,
            last=True,
        )
    )

    html = _email_base(
        title="Refund Issued",
        status_label="Refunded",
        status_color="#22c55e",
        detail_rows_html=rows,
        action_buttons=_email_button("View Order", order_url, "#22c55e"),
    )

    try:
        email = EmailMultiAlternatives(
            subject=f"Refund Issued — Order #{str(escrow.order.id)[:8]}",
            body=f"Refund issued for order {escrow.order.id}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[escrow.buyer.email, escrow.seller.email],
        )
        email.attach_alternative(html, "text/html")
        email.send(fail_silently=True)
    except Exception as e:
        print(f"[EMAIL ERROR] send_refund_email failed: {e}")


# ─── AUTH ─────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        if not username or not password:
            error = "Please enter both username and password."
        else:
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                user.total_logins = (user.total_logins or 0) + 1
                user.last_login_ip = request.META.get("REMOTE_ADDR")
                user.last_activity = now()
                user.save(update_fields=["total_logins", "last_login_ip", "last_activity"])
                return redirect(request.GET.get("next") or "home")
            else:
                error = "Invalid username or password."
    return render(request, "login.html", {"error": error})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email    = request.POST.get("email", "").strip()
        password  = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")
        role      = request.POST.get("role", "buyer")
        if not username or not email or not password:
            error = "All fields are required."
        elif password != password2:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "Username already taken."
        elif User.objects.filter(email=email).exists():
            error = "Email already registered."
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password,
                is_buyer=(role in ("buyer", "both")),
                is_seller=(role in ("seller", "both")),
            )
            import random
            wallet_addr = "0x" + "".join(
                [hex(random.randint(0, 15))[2:] for _ in range(40)]
            )
            UserWallet.objects.create(
                user=user, wallet_address=wallet_addr,
                blockchain_network="ganache",
                balance_snapshot=Decimal("100.0"),
            )
            _notify(user, "system", "Welcome to MarketPro!",
                    "Your account is ready.")
            try:
                send_mail(
                    subject="Welcome to MarketPro!",
                    message=f"Hi {username}, your account is ready. Start shopping or selling today!",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
            except Exception:
                pass
            login(request, user)
            messages.success(request, f"Welcome, {username}!")
            return redirect("home")
    return render(request, "register.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


# ─── HOME ─────────────────────────────────────────────────────────────

def home_view(request):
    categories = Category.objects.filter(is_active=True, parent=None)[:6]
    featured   = Product.objects.filter(
        is_active=True, is_featured=True
    ).select_related("seller", "shop", "category")[:8]
    return render(request, "home.html", {
        "categories":      categories,
        "featured":        featured,
        "total_users":     User.objects.count(),
        "total_products":  Product.objects.filter(is_active=True).count(),
        "total_orders":    Order.objects.filter(status="completed").count(),
        "total_shops":     Shop.objects.filter(is_active=True).count(),
    })


# ─── PRODUCTS ─────────────────────────────────────────────────────────

def product_list(request):
    query    = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    price    = request.GET.get("price", "")
    sort     = request.GET.get("sort", "")

    products = Product.objects.filter(is_active=True).select_related(
        "seller", "shop", "category"
    )

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query)
        )
    if category:
        products = products.filter(category__slug=category)
    if price == "low":
        products = products.filter(price__lt=50)
    elif price == "mid":
        products = products.filter(price__gte=50, price__lte=200)
    elif price == "high":
        products = products.filter(price__gt=200)

    sort_map = {
        "price_asc":  "price",
        "price_desc": "-price",
        "newest":     "-created_at",
        "popular":    "-total_purchases",
    }
    products = products.order_by(
        sort_map.get(sort, "-is_featured") if sort else "-is_featured"
    )

    paginator = Paginator(products, 12)
    page_obj  = paginator.get_page(request.GET.get("page"))
    categories = Category.objects.filter(is_active=True, parent=None)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        results = [
            {
                "id": str(p.id), "name": p.name, "price": str(p.price),
                "currency": p.currency,
                "category": p.category.name if p.category else "",
                "seller": p.seller.username,
                "shop": p.shop.name if p.shop else "",
                "is_out_of_stock": p.is_out_of_stock,
                "is_low_stock": p.is_low_stock,
                "is_featured": p.is_featured,
                "total_purchases": p.total_purchases,
                "avg_rating": float(p.avg_rating),
            }
            for p in page_obj
        ]
        return JsonResponse({
            "results": results,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page_obj.number,
        })

    return render(request, "product.html", {
        "page_obj": page_obj, "query": query, "categories": categories,
        "selected_category": category,
        "selected_price": price,
        "selected_sort": sort,
    })


def product_detail(request, product_id):
    product     = get_object_or_404(Product, id=product_id, is_active=True)
    reviews_qs  = product.reviews.select_related("user").order_by("-created_at")
    user_review = (
        reviews_qs.filter(user=request.user).first()
        if request.user.is_authenticated else None
    )
    reviews = reviews_qs[:10]
    related = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]
    Product.objects.filter(id=product.id).update(
        total_views=F("total_views") + 1
    )

    if (
        request.method == "POST"
        and request.user.is_authenticated
        and "submit_review" in request.POST
    ):
        rating = int(request.POST.get("rating", 5))
        title  = request.POST.get("title", "").strip()
        body   = request.POST.get("body", "").strip()
        if body:
            Review.objects.update_or_create(
                product=product, user=request.user,
                defaults={"rating": rating, "title": title, "body": body},
            )
            avg = product.reviews.aggregate(a=Avg("rating"))["a"] or 0
            product.avg_rating = avg
            product.save(update_fields=["avg_rating"])
            messages.success(request, "Review submitted!")
            return redirect("product_detail", product_id=product_id)

    return render(request, "productdetail.html", {
        "product": product, "reviews": reviews,
        "related": related, "user_review": user_review,
    })


# ─── CART (session-based) ─────────────────────────────────────────────

def cart_add(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=401)
    product = get_object_or_404(Product, id=str(product_id), is_active=True)
    if product.seller == request.user:
        return JsonResponse({"error": "Cannot add your own product"}, status=400)
    cart = request.session.get("cart", {})
    key  = str(product_id)
    qty  = int(request.POST.get("quantity", 1))
    if key in cart:
        cart[key]["quantity"] = min(
            cart[key]["quantity"] + qty, product.quantity_available
        )
    else:
        cart[key] = {
            "quantity": qty, "name": product.name,
            "price": str(product.price), "currency": product.currency,
        }
    request.session["cart"]    = cart
    request.session.modified   = True
    total_items = sum(v["quantity"] for v in cart.values())
    return JsonResponse({
        "success": True,
        "cart_count": total_items,
        "message": f"{product.name} added to cart!",
    })


def cart_remove(request, product_id):
    cart = request.session.get("cart", {})
    cart.pop(str(product_id), None)
    request.session["cart"]  = cart
    request.session.modified = True
    return JsonResponse({"success": True})


def cart_update(request, product_id):
    cart = request.session.get("cart", {})
    qty  = int(request.POST.get("quantity", 1))
    key  = str(product_id)
    if key in cart and qty > 0:
        cart[key]["quantity"] = qty
    elif key in cart:
        cart.pop(key)
    request.session["cart"]  = cart
    request.session.modified = True
    return JsonResponse({"success": True})


def cart_data(request):
    cart  = request.session.get("cart", {})
    total = sum(Decimal(v["price"]) * v["quantity"] for v in cart.values())
    return JsonResponse({
        "items": [
            {
                "id": k, **v,
                "subtotal": str(Decimal(v["price"]) * v["quantity"]),
            }
            for k, v in cart.items()
        ],
        "total": str(total),
        "count": sum(v["quantity"] for v in cart.values()),
    })


# ─── CHECKOUT ─────────────────────────────────────────────────────────

@login_required
def checkout(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    if request.user == product.seller:
        messages.error(request, "You cannot purchase your own product.")
        return redirect("product_detail", product_id=product_id)
    if product.is_out_of_stock:
        messages.error(request, "This product is out of stock.")
        return redirect("product_detail", product_id=product_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        if quantity > product.quantity_available:
            messages.error(
                request,
                f"Only {product.quantity_available} units available."
            )
            return redirect("product_detail", product_id=product_id)

        total = product.price * quantity
        order = Order.objects.create(
            buyer=request.user, seller=product.seller, product=product,
            shop=product.shop, quantity=quantity, unit_price=product.price,
            total_price=total, currency=product.currency,
            status="escrow_created",
        )
        escrow = EscrowTransaction.objects.create(
            order=order, buyer=request.user, seller=product.seller,
            amount=total, currency=product.currency,
            status="created", blockchain_network="ganache",
        )

        try:
            result = BlockchainService.create_escrow(
                buyer_address=BlockchainService.checksum(
                    request.user.userwallet.wallet_address
                ),
                seller_address=BlockchainService.checksum(
                    product.seller.userwallet.wallet_address
                ),
                deadline_days=getattr(settings, "ESCROW_DEADLINE_DAYS", 7),
                fee_bps=getattr(settings, "ESCROW_FEE_BPS", 0),
            )
        except Exception as e:
            order.delete()
            escrow.delete()
            messages.error(request, f"Blockchain error: {e}")
            return redirect("product_detail", product_id=product_id)

        escrow.contract_address    = settings.MASTER_CONTRACT_ADDRESS
        escrow.blockchain_escrow_id = result["escrow_id"]
        escrow.deployment_tx_hash  = result["receipt"].transactionHash.hex()
        escrow.save()

        product.quantity_available -= quantity
        product.total_purchases    += quantity
        product.save(update_fields=["quantity_available", "total_purchases"])

        StockLog.objects.create(
            product=product, user=request.user, action="sale",
            quantity_change=-quantity,
            quantity_before=product.quantity_available + quantity,
            quantity_after=product.quantity_available,
            note=f"Order {order.id}",
        )

        _notify(
            request.user, "order",
            f"Order #{str(order.id)[:8]} Created",
            f"Your order for {product.name} was placed. Fund escrow to proceed.",
            f"/orders/{order.id}/",
        )
        _notify(
            product.seller, "order", "New Order Received",
            f"{request.user.username} ordered {product.name}.",
            f"/orders/{order.id}/",
        )
        _log(request.user, "checkout",
             f"Placed order {order.id}", escrow, request)

        send_order_email(request, order)

        cart = request.session.get("cart", {})
        cart.pop(str(product_id), None)
        request.session["cart"]  = cart
        request.session.modified = True

        messages.success(request, "Order placed! Fund escrow to continue.")
        return redirect("order_detail", order_id=order.id)

    return render(request, "checkout.html", {"product": product})


# ─── ORDER DETAIL ─────────────────────────────────────────────────────

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if (
        request.user not in (order.buyer, order.seller)
        and not request.user.is_staff
    ):
        messages.error(request, "Permission denied.")
        return redirect("product_list")
    return render(request, "order.html", {"order": order})


# ─── FUND ESCROW ──────────────────────────────────────────────────────

@login_required
@require_POST
def fund_escrow(request, escrow_id):
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    if escrow.buyer != request.user:
        messages.error(request, "Only the buyer can fund this escrow.")
        return redirect("order_detail", order_id=escrow.order.id)
    if escrow.status == "paid":
        messages.error(request, "Escrow is already funded.")
        return redirect("order_detail", order_id=escrow.order.id)

    buyer_wallet = escrow.buyer.userwallet
    if Decimal(buyer_wallet.balance_snapshot) < Decimal(escrow.amount):
        messages.error(request, "Insufficient wallet balance.")
        return redirect("order_detail", order_id=escrow.order.id)

    try:
        receipt = BlockchainService.deposit(
            escrow_id=escrow.blockchain_escrow_id,
            from_address=BlockchainService.checksum(
                request.user.userwallet.wallet_address
            ),
            amount_eth=float(escrow.amount),
        )
    except Exception as e:
        if "insufficient funds" in str(e).lower():
            messages.error(
                request,
                "Blockchain wallet has insufficient ETH for gas."
            )
        else:
            messages.error(request, f"Blockchain transaction failed: {e}")
        return redirect("order_detail", order_id=escrow.order.id)

    Payment.objects.create(
        transaction=escrow, payer=request.user,
        amount=escrow.amount, currency=escrow.currency,
        payment_method="ganache",
        blockchain_tx_hash=receipt.transactionHash.hex(),
        status="funded",
    )
    buyer_wallet.balance_snapshot -= Decimal(escrow.amount)
    buyer_wallet.save()

    escrow.status = "paid"
    escrow.save()
    escrow.order.status = "paid"
    escrow.order.save()

    _notify(
        escrow.seller, "payment", "Escrow Funded",
        f"Buyer funded escrow for order #{str(escrow.order.id)[:8]}.",
        f"/orders/{escrow.order.id}/",
    )
    _log(request.user, "fund_escrow",
         f"Funded escrow {escrow.id}", escrow, request)

    send_order_email(request, escrow.order)

    messages.success(request, "Escrow funded! Seller has been notified.")
    return redirect("order_detail", order_id=escrow.order.id)


# ─── RELEASE DELIVERY (seller ships) ─────────────────────────────────


def release_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.user != order.seller:
        messages.error(request, "Only the seller can mark order as shipped.")
        return redirect("order_detail", order_id=order.id)
    if order.status != "paid":
        messages.error(request, "Order must be funded before shipping.")
        return redirect("order_detail", order_id=order.id)

    tracking = request.POST.get("tracking_number", "").strip()
    order.tracking_number = tracking
    order.status    = "shipped"
    order.shipped_at = now()
    order.save()

    _notify(
        order.buyer, "order", "Your Order Has Been Shipped!",
        f"Order #{str(order.id)[:8]} shipped. Track: {tracking or 'N/A'}",
        f"/orders/{order.id}/",
    )
    _log(request.user, "ship_order",
         f"Shipped order {order.id}", None, request)

    send_order_email(request, order)

    messages.success(request, "Order marked as shipped.")
    return redirect("order_detail", order_id=order.id)


# ─── CONFIRM DELIVERY (buyer confirms receipt) ────────────────────────

def confirm_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.user != order.buyer:
        messages.error(request, "Only the buyer can confirm delivery.")
        return redirect("order_detail", order_id=order.id)
    if order.status != "shipped":
        messages.error(request, "Order must be shipped before confirming.")
        return redirect("order_detail", order_id=order.id)

    escrow  = order.escrowtransaction
    fee_bps = getattr(settings, "ESCROW_FEE_BPS", 0)

    try:
        BlockchainService.confirm_delivery(
            escrow_id=escrow.blockchain_escrow_id,
            buyer_address=BlockchainService.checksum(
                request.user.userwallet.wallet_address
            ),
        )
        _, seller_payout_eth = BlockchainService.withdraw(
            recipient_address=BlockchainService.checksum(
                order.seller.userwallet.wallet_address
            ),
        )
    except Exception as e:
        messages.error(request, f"Blockchain confirmation failed: {e}")
        return redirect("order_detail", order_id=order.id)

    seller_wallet = order.seller.userwallet
    seller_wallet.balance_snapshot += Decimal(str(seller_payout_eth))
    seller_wallet.save()

    if order.shop:
        order.shop.total_sales   = (order.shop.total_sales or 0) + 1
        order.shop.total_revenue = (
            (order.shop.total_revenue or 0) + Decimal(str(seller_payout_eth))
        )
        order.shop.save(update_fields=["total_sales", "total_revenue"])

    order.seller.successful_transactions = (
        (order.seller.successful_transactions or 0) + 1
    )
    order.seller.save(update_fields=["successful_transactions"])
    order.buyer.successful_transactions = (
        (order.buyer.successful_transactions or 0) + 1
    )
    order.buyer.save(update_fields=["successful_transactions"])

    escrow.status      = "released"
    escrow.released_at = now()
    escrow.save()
    order.status       = "completed"
    order.completed_at = now()
    order.save()

    _notify(
        order.seller, "payment", "Funds Released!",
        f"Payment for order #{str(order.id)[:8]} released to your wallet.",
        f"/orders/{order.id}/",
    )
    _log(request.user, "confirm_delivery",
         f"Confirmed delivery for order {order.id}", escrow, request)

    send_order_email(request, order)

    messages.success(request, "Delivery confirmed. Funds released to seller.")
    return redirect("order_detail", order_id=order.id)


# ─── MARK RECEIVED (alias for confirm, kept for old email links) ──────

@login_required
def mark_received(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        if order.status == "shipped" and request.user == order.buyer:
            return confirm_delivery(request, order_id)
        order.status = "completed"
        order.save()
        messages.success(request, "Order received successfully.")
    return redirect("order_detail", order_id=order.id)


# ─── RAISE DISPUTE ────────────────────────────────────────────────────

@login_required
def raise_dispute(request, escrow_id):
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    if request.user not in (escrow.buyer, escrow.seller):
        messages.error(request, "You are not a party to this escrow.")
        return redirect("product_list")
    if escrow.status in ("released", "refunded"):
        messages.error(request, "This escrow is already closed.")
        return redirect("order_detail", order_id=escrow.order.id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Please provide a reason.")
            return redirect("order_detail", order_id=escrow.order.id)

        Dispute.objects.create(
            transaction=escrow, raised_by=request.user,
            reason=reason, status="open",
        )
        escrow.status = "disputed"
        escrow.save()
        escrow.order.status = "disputed"
        escrow.order.save()

        other = (
            escrow.seller if request.user == escrow.buyer else escrow.buyer
        )
        _notify(
            other, "dispute", "Dispute Opened",
            f"A dispute was raised for order #{str(escrow.order.id)[:8]}.",
            f"/orders/{escrow.order.id}/",
        )
        _log(request.user, "raise_dispute",
             f"Raised dispute on escrow {escrow.id}", escrow, request)

        send_dispute_email(request, escrow, reason=reason)

        messages.warning(
            request, "Dispute opened. Our team will review it shortly."
        )
        return redirect("order_detail", order_id=escrow.order.id)

    return render(request, "dispute.html", {"escrow": escrow})


# ─── CAST DISPUTE VOTE (staff arbiters) ──────────────────────────────

@login_required
@require_POST
def cast_dispute_vote(request, escrow_id):
    if not request.user.is_staff:
        messages.error(request, "Only arbiters can vote on disputes.")
        return redirect("product_list")

    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)
    if escrow.status != "disputed":
        messages.error(request, "This escrow is not in a disputed state.")
        return redirect("order_detail", order_id=escrow.order.id)

    for_buyer_str = request.POST.get("vote", "")
    if for_buyer_str not in ("buyer", "seller"):
        messages.error(
            request, "Invalid vote value. Choose 'buyer' or 'seller'."
        )
        return redirect("order_detail", order_id=escrow.order.id)

    for_buyer      = for_buyer_str == "buyer"
    voter_address  = BlockchainService.checksum(
        request.user.userwallet.wallet_address
    )

    if not BlockchainService.is_arbiter(voter_address):
        messages.error(
            request,
            "Your wallet is not registered as an on-chain arbiter."
        )
        return redirect("order_detail", order_id=escrow.order.id)

    try:
        BlockchainService.cast_dispute_vote(
            escrow_id=escrow.blockchain_escrow_id,
            voter_address=voter_address,
            for_buyer=for_buyer,
        )
    except Exception as e:
        messages.error(request, f"Vote failed: {e}")
        return redirect("order_detail", order_id=escrow.order.id)

    on_chain       = BlockchainService.get_escrow(escrow.blockchain_escrow_id)
    on_chain_state = on_chain["state"]

    if on_chain_state == 3:
        buyer_wallet = escrow.buyer.userwallet
        buyer_wallet.balance_snapshot += Decimal(str(escrow.amount))
        buyer_wallet.save()
        escrow.status = "refunded"
        escrow.save()
        escrow.order.status = "refunded"
        escrow.order.save()
        dispute = escrow.disputes.filter(status="open").first()
        if dispute:
            dispute.status = "resolved"
            dispute.save()
        _notify(
            escrow.buyer, "payment",
            "Dispute Resolved — Refund Issued",
            "Arbiters voted in your favour. Refund credited.",
            f"/orders/{escrow.order.id}/",
        )
        _notify(
            escrow.seller, "dispute", "Dispute Resolved",
            f"Arbiters ruled in the buyer's favour for order "
            f"#{str(escrow.order.id)[:8]}.",
            f"/orders/{escrow.order.id}/",
        )
        send_refund_email(request, escrow)
        messages.success(
            request, "Vote cast. Dispute resolved — buyer refunded."
        )

    elif on_chain_state == 2:
        try:
            _, seller_payout_eth = BlockchainService.withdraw(
                recipient_address=BlockchainService.checksum(
                    escrow.seller.userwallet.wallet_address
                ),
            )
        except Exception as e:
            messages.warning(
                request, f"Vote cast but seller withdrawal failed: {e}"
            )
            return redirect("order_detail", order_id=escrow.order.id)

        seller_wallet = escrow.seller.userwallet
        seller_wallet.balance_snapshot += Decimal(str(seller_payout_eth))
        seller_wallet.save()
        escrow.status      = "released"
        escrow.released_at = now()
        escrow.save()
        escrow.order.status       = "completed"
        escrow.order.completed_at = now()
        escrow.order.save()
        dispute = escrow.disputes.filter(status="open").first()
        if dispute:
            dispute.status = "resolved"
            dispute.save()
        _notify(
            escrow.seller, "payment",
            "Dispute Resolved — Funds Released",
            "Arbiters voted in your favour. Payment released.",
            f"/orders/{escrow.order.id}/",
        )
        _notify(
            escrow.buyer, "dispute", "Dispute Resolved",
            f"Arbiters ruled in the seller's favour for order "
            f"#{str(escrow.order.id)[:8]}.",
            f"/orders/{escrow.order.id}/",
        )
        send_order_email(request, escrow.order)
        messages.success(
            request,
            "Vote cast. Dispute resolved — funds released to seller."
        )

    else:
        messages.info(request, "Vote recorded. Waiting for more arbiter votes.")

    _log(
        request.user, "dispute_vote",
        f"Voted {'for buyer' if for_buyer else 'for seller'} "
        f"on escrow {escrow.id}",
        escrow, request,
    )
    return redirect("order_detail", order_id=escrow.order.id)


# ─── SELLER CANCEL ────────────────────────────────────────────────────

@login_required
@require_POST
def cancel_by_seller(request, escrow_id):
    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    if request.user != escrow.seller:
        messages.error(request, "Only the seller can cancel this escrow.")
        return redirect("order_detail", order_id=escrow.order.id)
    if escrow.status != "created":
        messages.error(
            request, "Escrow can only be cancelled before funding."
        )
        return redirect("order_detail", order_id=escrow.order.id)

    try:
        BlockchainService.cancel_by_seller(
            escrow_id=escrow.blockchain_escrow_id,
            seller_address=BlockchainService.checksum(
                request.user.userwallet.wallet_address
            ),
        )
    except Exception as e:
        messages.error(request, f"Cancellation failed: {e}")
        return redirect("order_detail", order_id=escrow.order.id)

    escrow.status = "cancelled"
    escrow.save()
    escrow.order.status = "cancelled"
    escrow.order.save()

    _notify(
        escrow.buyer, "order", "Order Cancelled",
        f"The seller cancelled order #{str(escrow.order.id)[:8]}.",
        f"/orders/{escrow.order.id}/",
    )
    _log(request.user, "cancel_escrow",
         f"Seller cancelled escrow {escrow.id}", escrow, request)

    send_order_email(request, escrow.order)

    messages.success(request, "Order cancelled.")
    return redirect("order_detail", order_id=escrow.order.id)


# ─── REFUND (staff) ───────────────────────────────────────────────────

@login_required
def refund_buyer_view(request, escrow_id):
    if not request.user.is_staff:
        messages.error(request, "Only staff can issue refunds.")
        return redirect("product_list")

    escrow = get_object_or_404(EscrowTransaction, id=escrow_id)

    try:
        BlockchainService.refund_buyer(escrow_id=escrow.blockchain_escrow_id)
    except Exception as e:
        messages.error(request, f"Refund failed: {e}")
        return redirect("order_detail", order_id=escrow.order.id)

    buyer_wallet = escrow.buyer.userwallet
    buyer_wallet.balance_snapshot += Decimal(str(escrow.amount))
    buyer_wallet.save()

    escrow.status = "refunded"
    escrow.save()
    escrow.order.status = "refunded"
    escrow.order.save()

    dispute = escrow.disputes.filter(status="open").first()
    if dispute:
        dispute.status = "resolved"
        dispute.save()

    _notify(
        escrow.buyer, "payment", "Refund Issued",
        f"Your refund of {escrow.amount} {escrow.currency} has been issued.",
        f"/orders/{escrow.order.id}/",
    )
    _log(request.user, "refund",
         f"Issued refund for escrow {escrow.id}", escrow, request)

    send_refund_email(request, escrow)

    messages.success(request, "Buyer refunded.")
    return redirect("order_detail", order_id=escrow.order.id)


# ─── ARBITER MANAGEMENT ───────────────────────────────────────────────

@login_required
@require_POST
def add_arbiter_view(request):
    if not request.user.is_staff:
        messages.error(request, "Access restricted.")
        return redirect("admin_dashboard")

    address = request.POST.get("wallet_address", "").strip()
    if not address:
        messages.error(request, "Wallet address is required.")
        return redirect("admin_dashboard")

    try:
        BlockchainService.add_arbiter(address)
    except Exception as e:
        messages.error(request, f"Failed to add arbiter: {e}")
        return redirect("admin_dashboard")

    _log(request.user, "add_arbiter",
         f"Added on-chain arbiter {address}", None, request)
    messages.success(request, f"Arbiter {address} added on-chain.")
    return redirect("admin_dashboard")


@login_required
@require_POST
def remove_arbiter_view(request):
    if not request.user.is_staff:
        messages.error(request, "Access restricted.")
        return redirect("admin_dashboard")

    address = request.POST.get("wallet_address", "").strip()
    if not address:
        messages.error(request, "Wallet address is required.")
        return redirect("admin_dashboard")

    try:
        BlockchainService.remove_arbiter(address)
    except Exception as e:
        messages.error(request, f"Failed to remove arbiter: {e}")
        return redirect("admin_dashboard")

    _log(request.user, "remove_arbiter",
         f"Removed on-chain arbiter {address}", None, request)
    messages.success(request, f"Arbiter {address} removed.")
    return redirect("admin_dashboard")


# ─── NOTIFICATIONS ────────────────────────────────────────────────────

@login_required
def notifications_json(request):
    notes = Notification.objects.filter(
        user=request.user, is_read=False
    ).values("id", "type", "title", "message", "link", "created_at")[:10]
    return JsonResponse({
        "notifications": list(notes), "count": notes.count()
    })


@login_required
def notifications_mark_read(request):
    Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({"success": True})


# ─── DASHBOARDS ───────────────────────────────────────────────────────

@login_required
def buyer_dashboard(request):
    user        = request.user
    user_wallet = UserWallet.objects.filter(user=user).first()
    purchases   = Order.objects.filter(buyer=user).select_related(
        "product", "seller", "shop"
    ).order_by("-created_at")
    total_spent = (
        purchases.filter(status="completed")
        .aggregate(s=Sum("total_price"))["s"] or 0
    )
    completed     = purchases.filter(status="completed").count()
    pending       = purchases.filter(
        status__in=["escrow_created", "paid", "shipped"]
    ).count()
    disputed      = purchases.filter(status="disputed").count()
    notifications = Notification.objects.filter(
        user=user
    ).order_by("-created_at")[:20]
    Notification.objects.filter(
        user=user, is_read=False
    ).update(is_read=True)
    return render(request, "buyer_dashboard.html", {
        "wallet": user_wallet, "purchases": purchases,
        "total_spent": total_spent, "completed": completed,
        "pending": pending, "disputed": disputed,
        "notifications": notifications,
    })


@login_required
def wallet(request):
    user        = request.user
    user_wallet = UserWallet.objects.filter(user=user).first()
    purchases   = Order.objects.filter(buyer=user).select_related(
        "product", "seller"
    ).order_by("-created_at")
    sales = Order.objects.filter(seller=user).select_related(
        "product", "buyer"
    ).order_by("-created_at")
    notifications = Notification.objects.filter(
        user=user
    ).order_by("-created_at")[:20]
    Notification.objects.filter(
        user=user, is_read=False
    ).update(is_read=True)
    return render(request, "wallet.html", {
        "wallet": user_wallet, "purchases": purchases,
        "sales": sales, "notifications": notifications,
    })


# ─── SUPPLIER ─────────────────────────────────────────────────────────

@login_required
def supplier_dashboard(request):
    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        shop = None

    if shop:
        products = Product.objects.filter(shop=shop).select_related(
            "category"
        ).order_by("-created_at")
        orders = Order.objects.filter(
            seller=request.user
        ).select_related("product", "buyer").order_by("-created_at")
        low_stock = products.filter(
            quantity_available__lte=F("low_stock_threshold")
        )
        recent_stock_logs = StockLog.objects.filter(
            product__shop=shop
        ).select_related("product").order_by("-created_at")[:20]
        total_revenue = (
            orders.filter(status="completed")
            .aggregate(total=Sum("total_price"))["total"] or 0
        )
        pending_orders  = orders.filter(
            status__in=["paid", "escrow_created"]
        ).count()
        completed_count = orders.filter(status="completed").count()
        dispute_count   = orders.filter(status="disputed").count()
        product_trends  = (
            Order.objects.filter(
                seller=request.user, status="completed"
            ).values("product__name")
            .annotate(sales=Count("id"), revenue=Sum("total_price"))
            .order_by("-sales")[:5]
        )
        paginator = Paginator(products, 15)
        page_obj  = paginator.get_page(request.GET.get("page"))
    else:
        products = page_obj = orders = low_stock = None
        recent_stock_logs = product_trends = None
        total_revenue = pending_orders = completed_count = dispute_count = 0

    categories = Category.objects.filter(is_active=True)
    tabs = [
        {"id": "products", "label": "Products",
         "icon": "bi-box-seam",        "active": True},
        {"id": "orders",   "label": "Orders",
         "icon": "bi-bag-check",       "active": False},
        {"id": "stock",    "label": "Stock Log",
         "icon": "bi-clipboard-data",  "active": False},
        {"id": "trends",   "label": "Trends",
         "icon": "bi-graph-up",        "active": False},
    ]
    return render(request, "supplier.html", {
        "shop": shop, "page_obj": page_obj, "orders": orders,
        "low_stock": low_stock, "recent_stock_logs": recent_stock_logs,
        "total_revenue": total_revenue, "pending_orders": pending_orders,
        "completed_count": completed_count, "dispute_count": dispute_count,
        "categories": categories, "tabs": tabs,
        "product_trends": product_trends,
    })


@login_required
@require_POST
def register_shop(request):
    if hasattr(request.user, "shop"):
        messages.error(request, "You already have a registered shop.")
        return redirect("supplier_dashboard")
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Shop name is required.")
        return redirect("supplier_dashboard")
    slug = slugify(name)
    base = slug; c = 1
    while Shop.objects.filter(slug=slug).exists():
        slug = f"{base}-{c}"; c += 1
    Shop.objects.create(
        seller=request.user, name=name, slug=slug,
        description=request.POST.get("description", ""),
        city=request.POST.get("city", ""),
        country=request.POST.get("country", ""),
        email=request.POST.get("email", ""),
        phone=request.POST.get("phone", ""),
    )
    request.user.is_seller = True
    request.user.save(update_fields=["is_seller"])
    _notify(request.user, "system", "Shop Registered!",
            f"Your shop '{name}' is now live.")
    _log(request.user, "register_shop",
         f"Registered shop '{name}'", None, request)
    messages.success(request, f"Shop '{name}' registered!")
    return redirect("supplier_dashboard")


@login_required
@require_POST
def update_shop(request):
    shop = get_object_or_404(Shop, seller=request.user)
    for field in [
        "name", "description", "city", "country",
        "email", "phone", "website", "address",
    ]:
        val = request.POST.get(field, "").strip()
        if val:
            setattr(shop, field, val)
    shop.save()
    messages.success(request, "Shop updated.")
    return redirect("supplier_dashboard")


@login_required
@require_POST
def add_product(request):
    shop     = get_object_or_404(Shop, seller=request.user)
    category = Category.objects.filter(
        id=request.POST.get("category")
    ).first()
    name  = request.POST.get("name", "").strip()
    price = request.POST.get("price", "0").strip()
    if not name or not price:
        messages.error(request, "Name and price required.")
        return redirect("supplier_dashboard")
    slug = slugify(name); base = slug; c = 1
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base}-{c}"; c += 1
    qty = int(request.POST.get("quantity_available", 1))
    product = Product.objects.create(
        seller=request.user, shop=shop, category=category,
        name=name, slug=slug,
        description=request.POST.get("description", ""),
        price=Decimal(price),
        currency=request.POST.get("currency", "ETH"),
        quantity_available=qty,
        condition=request.POST.get("condition", "new"),
        tags=request.POST.get("tags", ""),
        low_stock_threshold=int(
            request.POST.get("low_stock_threshold", 5)
        ),
        sku=request.POST.get("sku", "") or None,
        is_active=True,
    )
    StockLog.objects.create(
        product=product, user=request.user, action="restock",
        quantity_change=qty, quantity_before=0,
        quantity_after=qty, note="Initial stock",
    )
    _log(request.user, "add_product",
         f"Added product '{name}'", None, request)
    messages.success(request, f"Product '{name}' added.")
    return redirect("supplier_dashboard")


@login_required
@require_POST
def edit_product(request, product_id):
    product  = get_object_or_404(
        Product, id=product_id, seller=request.user
    )
    category = (
        Category.objects.filter(
            id=request.POST.get("category")
        ).first() or product.category
    )
    product.name        = request.POST.get("name", product.name).strip()
    product.description = request.POST.get(
        "description", product.description
    )
    product.price    = Decimal(
        request.POST.get("price", str(product.price))
    )
    product.currency  = request.POST.get("currency", product.currency)
    product.condition = request.POST.get("condition", product.condition)
    product.tags      = request.POST.get("tags", product.tags)
    product.category  = category
    product.low_stock_threshold = int(
        request.POST.get("low_stock_threshold", product.low_stock_threshold)
    )
    product.is_active   = request.POST.get("is_active") == "on"
    product.is_featured = request.POST.get("is_featured") == "on"
    product.save()
    _log(request.user, "edit_product",
         f"Edited product '{product.name}'", None, request)
    messages.success(request, f"Product '{product.name}' updated.")
    return redirect("supplier_dashboard")


@login_required
@require_POST
def restock_product(request, product_id):
    product = get_object_or_404(
        Product, id=product_id, seller=request.user
    )
    qty = int(request.POST.get("quantity", 0))
    if qty <= 0:
        messages.error(request, "Quantity must be positive.")
        return redirect("supplier_dashboard")
    before = product.quantity_available
    product.quantity_available += qty
    product.save(update_fields=["quantity_available"])
    StockLog.objects.create(
        product=product, user=request.user, action="restock",
        quantity_change=qty, quantity_before=before,
        quantity_after=product.quantity_available,
        note=request.POST.get("note", ""),
    )
    _log(request.user, "restock",
         f"Restocked {qty} of '{product.name}'", None, request)
    messages.success(request, f"Restocked {qty} units.")
    return redirect("supplier_dashboard")


@login_required
@require_POST
def delete_product(request, product_id):
    product = get_object_or_404(
        Product, id=product_id, seller=request.user
    )
    name = product.name
    product.is_active = False
    product.save(update_fields=["is_active"])
    _log(request.user, "delete_product",
         f"Deactivated '{name}'", None, request)
    messages.success(request, f"'{name}' deactivated.")
    return redirect("supplier_dashboard")


@login_required
@require_POST
def update_inventory(request, product_id):
    product    = get_object_or_404(
        Product, id=product_id, seller=request.user
    )
    action     = request.POST.get("action", "adjustment")
    qty_change = int(request.POST.get("quantity_change", 0))
    note       = request.POST.get("note", "").strip()
    if action in ("damage",):
        qty_change = -abs(qty_change)
    before = product.quantity_available
    product.quantity_available = max(
        0, product.quantity_available + qty_change
    )
    product.save(update_fields=["quantity_available"])
    StockLog.objects.create(
        product=product, user=request.user, action=action,
        quantity_change=qty_change, quantity_before=before,
        quantity_after=product.quantity_available, note=note,
    )
    _log(
        request.user, "inventory_update",
        f"Inventory {action} {qty_change:+d} for '{product.name}'",
        None, request,
    )
    messages.success(
        request, f"Inventory updated for '{product.name}'."
    )
    return redirect("supplier_dashboard")


# ─── ADMIN DASHBOARD ──────────────────────────────────────────────────

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "Access restricted.")
        return redirect("home")
    today    = now().date()
    week_ago = today - timedelta(days=7)
    stats = {
        "total_users":       User.objects.count(),
        "new_users_week":    User.objects.filter(
            created_at__date__gte=week_ago
        ).count(),
        "verified_users":    User.objects.filter(is_verified=True).count(),
        "flagged_users":     User.objects.filter(is_flagged=True).count(),
        "total_products":    Product.objects.count(),
        "active_products":   Product.objects.filter(is_active=True).count(),
        "out_of_stock":      Product.objects.filter(
            quantity_available=0
        ).count(),
        "total_shops":       Shop.objects.count(),
        "active_shops":      Shop.objects.filter(is_active=True).count(),
        "total_orders":      Order.objects.count(),
        "orders_week":       Order.objects.filter(
            created_at__date__gte=week_ago
        ).count(),
        "completed_orders":  Order.objects.filter(status="completed").count(),
        "pending_orders":    Order.objects.filter(
            status__in=["paid", "escrow_created"]
        ).count(),
        "disputed_orders":   Order.objects.filter(status="disputed").count(),
        "total_escrows":     EscrowTransaction.objects.count(),
        "open_disputes":     Dispute.objects.filter(status="open").count(),
        "resolved_disputes": Dispute.objects.filter(
            status="resolved"
        ).count(),
        "total_revenue":     Payment.objects.filter(
            status="funded"
        ).aggregate(s=Sum("amount"))["s"] or 0,
        "revenue_week":      Payment.objects.filter(
            status="funded", created_at__date__gte=week_ago
        ).aggregate(s=Sum("amount"))["s"] or 0,
        "avg_order_value":   Order.objects.filter(
            status="completed"
        ).aggregate(a=Avg("total_price"))["a"] or 0,
    }
    top_sellers  = (
        Order.objects.filter(status="completed")
        .values("seller__username")
        .annotate(revenue=Sum("total_price"), count=Count("id"))
        .order_by("-revenue")[:10]
    )
    top_products  = Product.objects.filter(
        is_active=True
    ).order_by("-total_purchases")[:10]
    recent_users  = User.objects.order_by("-created_at")[:10]
    recent_orders = Order.objects.select_related(
        "buyer", "seller", "product"
    ).order_by("-created_at")[:20]
    recent_logs   = LogTrail.objects.select_related(
        "user"
    ).order_by("-created_at")[:20]
    open_disputes = Dispute.objects.filter(status="open").select_related(
        "transaction", "raised_by"
    ).order_by("-created_at")[:10]

    trend_labels = []; revenue_trend = []; order_trend = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        trend_labels.append(str(day))
        order_trend.append(
            Order.objects.filter(created_at__date=day).count()
        )
        rev = (
            Payment.objects.filter(
                status="funded", created_at__date=day
            ).aggregate(s=Sum("amount"))["s"] or 0
        )
        revenue_trend.append(float(rev))
    order_status = list(
        Order.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return render(request, "admin_dashboard.html", {
        **stats,
        "top_sellers": top_sellers, "top_products": top_products,
        "recent_users": recent_users, "recent_orders": recent_orders,
        "recent_logs": recent_logs, "open_disputes": open_disputes,
        "trend_labels":   json.dumps(trend_labels),
        "order_trend":    json.dumps(order_trend),
        "revenue_trend":  json.dumps(revenue_trend),
        "order_status":   json.dumps(order_status),
    })


# ─── KPI ──────────────────────────────────────────────────────────────

@login_required
def kpi_view(request):
    if not request.user.is_staff:
        messages.error(request, "Access restricted.")
        return redirect("product_list")
    today    = now().date()
    week_ago = today - timedelta(days=7)
    kpi = {
        "total_users":       User.objects.count(),
        "new_users_week":    User.objects.filter(
            created_at__date__gte=week_ago
        ).count(),
        "verified_users":    User.objects.filter(is_verified=True).count(),
        "flagged_users":     User.objects.filter(is_flagged=True).count(),
        "total_products":    Product.objects.count(),
        "active_products":   Product.objects.filter(is_active=True).count(),
        "out_of_stock":      Product.objects.filter(
            quantity_available=0
        ).count(),
        "total_shops":       Shop.objects.count(),
        "active_shops":      Shop.objects.filter(is_active=True).count(),
        "total_orders":      Order.objects.count(),
        "orders_week":       Order.objects.filter(
            created_at__date__gte=week_ago
        ).count(),
        "completed_orders":  Order.objects.filter(status="completed").count(),
        "pending_orders":    Order.objects.filter(
            status__in=["paid", "escrow_created"]
        ).count(),
        "disputed_orders":   Order.objects.filter(status="disputed").count(),
        "total_escrows":     EscrowTransaction.objects.count(),
        "open_disputes":     Dispute.objects.filter(status="open").count(),
        "resolved_disputes": Dispute.objects.filter(
            status="resolved"
        ).count(),
        "total_revenue":     Payment.objects.filter(
            status="funded"
        ).aggregate(s=Sum("amount"))["s"] or 0,
        "revenue_week":      Payment.objects.filter(
            status="funded", created_at__date__gte=week_ago
        ).aggregate(s=Sum("amount"))["s"] or 0,
        "avg_order_value":   Order.objects.filter(
            status="completed"
        ).aggregate(a=Avg("total_price"))["a"] or 0,
        "avg_trust_score":   User.objects.aggregate(
            a=Avg("trust_score")
        )["a"] or 0,
        "avg_fraud_score":   User.objects.aggregate(
            a=Avg("fraud_risk_score")
        )["a"] or 0,
        "total_visits":      SiteVisit.objects.count(),
        "visits_week":       SiteVisit.objects.filter(
            visited_at__date__gte=week_ago
        ).count(),
    }
    top_sellers  = (
        Order.objects.filter(status="completed")
        .values("seller__username")
        .annotate(revenue=Sum("total_price"), count=Count("id"))
        .order_by("-revenue")[:10]
    )
    top_products = Product.objects.filter(
        is_active=True
    ).order_by("-total_purchases")[:10]
    trend_labels = []; revenue_trend = []; order_trend = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        trend_labels.append(str(day))
        order_trend.append(
            Order.objects.filter(created_at__date=day).count()
        )
        rev = (
            Payment.objects.filter(
                status="funded", created_at__date=day
            ).aggregate(s=Sum("amount"))["s"] or 0
        )
        revenue_trend.append(float(rev))
    order_status = list(
        Order.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return render(request, "kpi.html", {
        **kpi,
        "top_sellers": top_sellers, "top_products": top_products,
        "trend_labels":  json.dumps(trend_labels),
        "order_trend":   json.dumps(order_trend),
        "revenue_trend": json.dumps(revenue_trend),
        "order_status":  json.dumps(order_status),
    })


# ─── ANALYTICS ────────────────────────────────────────────────────────

@login_required
def analytics_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "Access restricted.")
        return redirect("product_list")
    today = now().date()
    trend_labels = []; order_trend = []; dispute_trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        trend_labels.append(str(day))
        order_trend.append(
            Order.objects.filter(created_at__date=day).count()
        )
        dispute_trend.append(
            Dispute.objects.filter(created_at__date=day).count()
        )
    return render(request, "dashboard.html", {
        "total_users":       User.objects.count(),
        "verified_users":    User.objects.filter(is_verified=True).count(),
        "flagged_users":     User.objects.filter(is_flagged=True).count(),
        "avg_trust":         User.objects.aggregate(
            Avg("trust_score")
        )["trust_score__avg"] or 0,
        "avg_fraud_user":    User.objects.aggregate(
            Avg("fraud_risk_score")
        )["fraud_risk_score__avg"] or 0,
        "total_products":    Product.objects.count(),
        "active_products":   Product.objects.filter(is_active=True).count(),
        "total_orders":      Order.objects.count(),
        "completed_orders":  Order.objects.filter(status="completed").count(),
        "pending_orders":    Order.objects.filter(status="pending").count(),
        "total_escrows":     EscrowTransaction.objects.count(),
        "funded_escrows":    EscrowTransaction.objects.filter(
            status="paid"
        ).count(),
        "disputed_escrows":  EscrowTransaction.objects.filter(
            status="disputed"
        ).count(),
        "refunded_escrows":  EscrowTransaction.objects.filter(
            status="refunded"
        ).count(),
        "total_disputes":    Dispute.objects.count(),
        "open_disputes":     Dispute.objects.filter(status="open").count(),
        "resolved_disputes": Dispute.objects.filter(
            status="resolved"
        ).count(),
        "total_payments":    Payment.objects.count(),
        "total_visits":      SiteVisit.objects.count(),
        "unique_visitors":   SiteVisit.objects.values(
            "session_id"
        ).distinct().count(),
        "trend_labels":      trend_labels,
        "order_trend":       order_trend,
        "dispute_trend":     dispute_trend,
        "recent_escrows":    EscrowTransaction.objects.select_related(
            "buyer", "seller"
        ).order_by("-created_at")[:50],
        "recent_payments":   Payment.objects.select_related(
            "transaction", "payer"
        ).order_by("-created_at")[:50],
        "recent_logs":       LogTrail.objects.select_related(
            "user"
        ).order_by("-created_at")[:50],
        "recent_visits":     SiteVisit.objects.select_related(
            "user"
        ).order_by("-visited_at")[:50],
    })


@login_required
def chart_view(request):
    if not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)
    total_users = User.objects.count()
    flagged     = User.objects.filter(is_flagged=True).count()
    disputes    = Dispute.objects.values("status").annotate(count=Count("id"))
    total_revenue = (
        Payment.objects.filter(status="funded")
        .aggregate(total=Sum("amount"))["total"] or 0
    )
    return JsonResponse({
        "pie": {
            "labels": ["Flagged", "Clean"],
            "data":   [flagged, total_users - flagged],
        },
        "disputes": {
            "labels":   [d["status"] for d in disputes],
            "data":     [d["count"] for d in disputes],
            "total":    Dispute.objects.count(),
            "open":     Dispute.objects.filter(status="open").count(),
            "resolved": Dispute.objects.filter(status="resolved").count(),
        },
        "fraud": {
            "avg_fraud":    float(
                User.objects.aggregate(a=Avg("fraud_risk_score"))["a"] or 0
            ),
            "avg_trust":    float(
                User.objects.aggregate(a=Avg("trust_score"))["a"] or 0
            ),
            "flagged_users": flagged,
            "total_users":   total_users,
        },
        "revenue": {"total": float(total_revenue)},
    })


# ─── BLOCKCHAIN TEST ──────────────────────────────────────────────────

@login_required
def test_blockchain(request):
    if not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)
    try:
        buyer  = w3.eth.accounts[1]
        seller = w3.eth.accounts[2]
        result = BlockchainService.create_escrow(buyer, seller)
        eid    = result["escrow_id"]
        BlockchainService.deposit(
            escrow_id=eid, from_address=buyer, amount_eth=1
        )
        BlockchainService.confirm_delivery(
            escrow_id=eid, buyer_address=buyer
        )
        _, payout = BlockchainService.withdraw(
            recipient_address=BlockchainService.checksum(seller)
        )
        return JsonResponse({
            "status": "success",
            "escrow_id": eid,
            "seller_payout_eth": payout,
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})