"""
tasks.py — Celery periodic tasks for escrow lifecycle management.

Add to your settings.py / celery beat schedule:

    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        "sweep-expired-escrows": {
            "task": "app.tasks.sweep_expired_escrows",
            "schedule": crontab(minute="*/30"),   # every 30 minutes
        },
    }
"""

from celery import shared_task
from django.utils.timezone import now
from decimal import Decimal

from .models import EscrowTransaction, Order
from .services.blockchain_service import BlockchainService, w3


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sweep_expired_escrows(self):
    """
    Finds all funded escrows whose on-chain deadline has passed and
    triggers claimExpiredRefund() for each one.

    Safe to run repeatedly — the contract will revert if the deadline
    hasn't expired yet or the escrow is already resolved.
    """
    # Only escrows that are funded (paid) and not yet resolved
    candidates = EscrowTransaction.objects.filter(
        status="paid",
        order__status__in=["paid", "shipped"],
    ).select_related("buyer", "seller", "order")

    caller = w3.eth.accounts[0]   # Ganache deployer — has gas; any funded address works
    processed = 0
    failed = 0

    for escrow in candidates:
        try:
            on_chain = BlockchainService.get_escrow(escrow.blockchain_escrow_id)

            # State 1 = AWAITING_DELIVERY (funded but not confirmed)
            # Only attempt if on-chain state is AWAITING_DELIVERY AND deadline has passed
            deadline_passed = now().timestamp() > on_chain["deadline"]
            if on_chain["state"] != 1 or not deadline_passed:
                continue

            print(f"⏰ Sweeping expired escrow #{escrow.blockchain_escrow_id} (DB id: {escrow.id})")

            BlockchainService.claim_expired_refund(
                escrow_id=escrow.blockchain_escrow_id,
                caller_address=caller,
            )

            # Credit buyer's DB wallet with the refund amount
            buyer_wallet = escrow.buyer.userwallet
            buyer_wallet.balance_snapshot += Decimal(str(escrow.amount))
            buyer_wallet.save()

            escrow.status = "refunded"
            escrow.save()
            escrow.order.status = "refunded"
            escrow.order.save()

            from .models import Notification, LogTrail
            Notification.objects.create(
                user=escrow.buyer,
                type="payment",
                title="Escrow Expired — Refund Issued",
                message=(
                    f"Order #{str(escrow.order.id)[:8]} was not completed before the deadline. "
                    f"Your {escrow.amount} {escrow.currency} has been refunded."
                ),
                link=f"/orders/{escrow.order.id}/",
            )
            Notification.objects.create(
                user=escrow.seller,
                type="order",
                title="Escrow Expired",
                message=f"Order #{str(escrow.order.id)[:8]} expired and was refunded to the buyer.",
                link=f"/orders/{escrow.order.id}/",
            )
            LogTrail.objects.create(
                user=None,
                action_type="auto_refund",
                description=f"Auto-refund for expired escrow {escrow.id} (blockchain id {escrow.blockchain_escrow_id})",
                related_transaction=escrow,
            )

            processed += 1

        except Exception as exc:
            failed += 1
            print(f"❌ sweep_expired_escrows failed for escrow {escrow.id}: {exc}")
            # Don't retry the whole task for one bad escrow — log and continue
            continue

    print(f"✅ sweep_expired_escrows complete: {processed} refunded, {failed} failed")
    return {"processed": processed, "failed": failed}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_single_expired_escrow(self, escrow_db_id: int):
    """
    Refund a single specific escrow by its Django DB primary key.
    Can be triggered manually from admin or after a dispute timeout.
    """
    from .models import EscrowTransaction

    try:
        escrow = EscrowTransaction.objects.select_related(
            "buyer", "seller", "order"
        ).get(id=escrow_db_id)
    except EscrowTransaction.DoesNotExist:
        print(f"❌ Escrow {escrow_db_id} not found")
        return

    caller = w3.eth.accounts[0]

    try:
        BlockchainService.claim_expired_refund(
            escrow_id=escrow.blockchain_escrow_id,
            caller_address=caller,
        )
        buyer_wallet = escrow.buyer.userwallet
        buyer_wallet.balance_snapshot += Decimal(str(escrow.amount))
        buyer_wallet.save()

        escrow.status = "refunded"
        escrow.save()
        escrow.order.status = "refunded"
        escrow.order.save()

        print(f"✅ Manual expired refund complete for escrow {escrow_db_id}")

    except Exception as exc:
        raise self.retry(exc=exc)