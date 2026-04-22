import json
from web3 import Web3
from django.conf import settings

# ─── Connect to Ganache ───────────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider(settings.GANACHE_RPC_URL))

if not w3.is_connected():
    raise Exception("❌ Cannot connect to Ganache RPC")

w3.eth.default_account = w3.eth.accounts[0]

# ─── Load ABI ────────────────────────────────────────────────────────
with open(settings.BLOCKCHAIN_ABI_PATH) as f:
    MASTER_ESCROW_ABI = json.load(f)

CONTRACT_ADDRESS = settings.MASTER_CONTRACT_ADDRESS
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=MASTER_ESCROW_ABI)


class BlockchainService:

    # ─── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def checksum(address: str) -> str:
        if not address:
            raise ValueError("Address is empty")
        if not address.startswith("0x"):
            address = "0x" + address
        return w3.to_checksum_address(address)

    @staticmethod
    def _parse_escrow_id(receipt) -> int:
        """
        Extract escrow ID from EscrowCreated event log.
        Falls back to escrowCount() if event parsing fails.
        """
        try:
            logs = contract.events.EscrowCreated().process_receipt(receipt)
            if logs:
                escrow_id = logs[0]["args"]["escrowId"]
                print(f"🎯 Escrow ID from event: {escrow_id}")
                return escrow_id
        except Exception as e:
            print(f"⚠ Event parse failed, falling back to escrowCount(): {e}")

        escrow_id = contract.functions.escrowCount().call()
        print(f"🎯 Escrow ID from escrowCount(): {escrow_id}")
        return escrow_id

    @staticmethod
    def _get_arbiter_address() -> str:
        """
        Returns the contract-level arbiter address (the deployer).
        This is the address that must sign refundBuyer() calls.
        """
        return contract.functions.arbiter().call()

    # ─── 1. Create escrow ────────────────────────────────────────────

    @staticmethod
    def create_escrow(
        buyer_address: str,
        seller_address: str,
        deadline_days: int = 7,
        fee_bps: int = 0,
    ) -> dict:
        try:
            buyer_address  = w3.to_checksum_address(buyer_address)
            seller_address = w3.to_checksum_address(seller_address)
            print(f"✔ Checksum buyer:  {buyer_address}")
            print(f"✔ Checksum seller: {seller_address}")

            tx_hash = contract.functions.createEscrow(
                buyer_address,
                seller_address,
                deadline_days,
                fee_bps,
            ).transact()

            print(f"⛓ TX hash: {tx_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Block: {receipt.blockNumber}  Gas: {receipt.gasUsed}")

            escrow_id = BlockchainService._parse_escrow_id(receipt)
            return {"receipt": receipt, "escrow_id": escrow_id}

        except Exception as e:
            print(f"❌ create_escrow error: {e}")
            raise

    # ─── 2. Deposit ──────────────────────────────────────────────────

    @staticmethod
    def deposit(escrow_id: int, from_address: str, amount_eth: float):
        try:
            from_address = w3.to_checksum_address(from_address)
            wei_amount   = w3.to_wei(amount_eth, "ether")

            on_chain = contract.functions.getEscrow(escrow_id).call()
            buyer_on_chain = on_chain[0]
            match = buyer_on_chain.lower() == from_address.lower()
            print(f"🔍 On-chain buyer: {buyer_on_chain}  |  Depositor: {from_address}  |  Match: {match}")
            if not match:
                raise ValueError(
                    f"Address mismatch — on-chain buyer is {buyer_on_chain}, "
                    f"got {from_address}"
                )

            print(f"💰 Depositing {amount_eth} ETH ({wei_amount} wei) for escrow {escrow_id}")
            tx_hash = contract.functions.deposit(escrow_id).transact({
                "from": from_address,
                "value": wei_amount,
            })

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Deposit confirmed  Block: {receipt.blockNumber}  Gas: {receipt.gasUsed}")
            return receipt

        except Exception as e:
            print(f"❌ deposit error: {e}")
            raise

    # ─── 3. Confirm delivery ─────────────────────────────────────────

    @staticmethod
    def confirm_delivery(escrow_id: int, buyer_address: str):
        try:
            buyer_address = w3.to_checksum_address(buyer_address)
            print(f"🚚 Confirming delivery for escrow {escrow_id} from {buyer_address}")

            tx_hash = contract.functions.confirmDelivery(escrow_id).transact({
                "from": buyer_address,
            })

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Delivery confirmed  Block: {receipt.blockNumber}  Gas: {receipt.gasUsed}")
            return receipt

        except Exception as e:
            print(f"❌ confirm_delivery error: {e}")
            raise

    # ─── 4. Withdraw (pull-payment) ───────────────────────────────────

    @staticmethod
    def withdraw(recipient_address: str):
        """
        Pull-payment: called after confirm_delivery so seller/fee-recipient
        can claim their on-chain balance.
        Returns (receipt, amount_eth) so callers know the exact payout.
        """
        try:
            recipient_address = w3.to_checksum_address(recipient_address)
            claimable = contract.functions.claimable(recipient_address).call()
            amount_eth = float(w3.from_wei(claimable, "ether"))
            print(f"💵 Claimable for {recipient_address}: {amount_eth} ETH")

            if claimable == 0:
                print("⚠ Nothing to withdraw — skipping")
                return None, 0.0

            tx_hash = contract.functions.withdraw().transact({
                "from": recipient_address,
            })

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Withdrawal confirmed  Block: {receipt.blockNumber}  Gas: {receipt.gasUsed}")
            return receipt, amount_eth

        except Exception as e:
            print(f"❌ withdraw error: {e}")
            raise

    # ─── 5. Refund buyer — MUST use the contract arbiter address ─────

    @staticmethod
    def refund_buyer(escrow_id: int):
        """
        refundBuyer() on-chain requires msg.sender == arbiter (the deployer).
        We read the arbiter address directly from the contract so we never
        rely on a passed-in address that might not match.
        """
        try:
            arbiter_address = BlockchainService._get_arbiter_address()
            print(f"🔄 Refunding escrow {escrow_id} via on-chain arbiter {arbiter_address}")

            tx_hash = contract.functions.refundBuyer(escrow_id).transact({
                "from": arbiter_address,
            })

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Refund confirmed  Block: {receipt.blockNumber}  Gas: {receipt.gasUsed}")
            return receipt

        except Exception as e:
            print(f"❌ refund_buyer error: {e}")
            raise

    # ─── 6. Claim expired refund ──────────────────────────────────────

    @staticmethod
    def claim_expired_refund(escrow_id: int, caller_address: str):
        """
        Anyone can trigger this after the deadline has passed.
        Intended to be called from a Celery beat task.
        """
        try:
            caller_address = w3.to_checksum_address(caller_address)
            print(f"⏰ Claiming expired refund for escrow {escrow_id}")

            tx_hash = contract.functions.claimExpiredRefund(escrow_id).transact({
                "from": caller_address,
            })

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Expired refund claimed  Block: {receipt.blockNumber}")
            return receipt

        except Exception as e:
            print(f"❌ claim_expired_refund error: {e}")
            raise

    # ─── 7. Cancel by seller (before deposit) ────────────────────────

    @staticmethod
    def cancel_by_seller(escrow_id: int, seller_address: str):
        try:
            seller_address = w3.to_checksum_address(seller_address)
            print(f"🚫 Seller cancelling escrow {escrow_id}")

            tx_hash = contract.functions.cancelBySeller(escrow_id).transact({
                "from": seller_address,
            })

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Cancelled  Block: {receipt.blockNumber}")
            return receipt

        except Exception as e:
            print(f"❌ cancel_by_seller error: {e}")
            raise

    # ─── 8. Dispute voting (multi-arbiter, 2-of-3) ───────────────────

    @staticmethod
    def cast_dispute_vote(escrow_id: int, voter_address: str, for_buyer: bool):
        """
        Cast a dispute vote. voter_address must have been added via addArbiter().
        for_buyer=True → refund buyer; for_buyer=False → release to seller.
        """
        try:
            voter_address = w3.to_checksum_address(voter_address)
            print(f"🗳 {voter_address} voting {'for buyer' if for_buyer else 'for seller'} on escrow {escrow_id}")

            tx_hash = contract.functions.castDisputeVote(escrow_id, for_buyer).transact({
                "from": voter_address,
            })

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Vote cast  Block: {receipt.blockNumber}")
            return receipt

        except Exception as e:
            print(f"❌ cast_dispute_vote error: {e}")
            raise

    # ─── 9. Arbiter management ───────────────────────────────────────

    @staticmethod
    def add_arbiter(address: str):
        """Add a dispute-voting arbiter. Must be called from the contract owner account."""
        try:
            address         = w3.to_checksum_address(address)
            owner_address   = BlockchainService._get_arbiter_address()
            tx_hash = contract.functions.addArbiter(address).transact({"from": owner_address})
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Arbiter added: {address}  Block: {receipt.blockNumber}")
            return receipt
        except Exception as e:
            print(f"❌ add_arbiter error: {e}")
            raise

    @staticmethod
    def remove_arbiter(address: str):
        """Remove a dispute-voting arbiter."""
        try:
            address         = w3.to_checksum_address(address)
            owner_address   = BlockchainService._get_arbiter_address()
            tx_hash = contract.functions.removeArbiter(address).transact({"from": owner_address})
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ Arbiter removed: {address}  Block: {receipt.blockNumber}")
            return receipt
        except Exception as e:
            print(f"❌ remove_arbiter error: {e}")
            raise

    @staticmethod
    def is_arbiter(address: str) -> bool:
        address = w3.to_checksum_address(address)
        return contract.functions.isArbiter(address).call()

    # ─── 10. Read helpers ────────────────────────────────────────────

    @staticmethod
    def get_escrow(escrow_id: int) -> dict:
        result = contract.functions.getEscrow(escrow_id).call()
        return {
            "buyer":         result[0],
            "seller":        result[1],
            "amount_wei":    result[2],
            "amount_eth":    float(w3.from_wei(result[2], "ether")),
            "state":         result[3],   # 0=AWAITING_PAYMENT 1=AWAITING_DELIVERY 2=COMPLETE 3=REFUNDED 4=CANCELLED
            "deadline":      result[4],
        }

    @staticmethod
    def get_claimable(address: str) -> float:
        address   = w3.to_checksum_address(address)
        wei_value = contract.functions.claimable(address).call()
        return float(w3.from_wei(wei_value, "ether"))

    @staticmethod
    def compute_payout(amount_eth: float, fee_bps: int) -> tuple[float, float]:
        """
        Returns (seller_payout_eth, fee_eth) matching the contract's arithmetic:
            fee    = amount * feeBps / 10_000
            payout = amount - fee
        Use this whenever you need to credit wallet balances in Django.
        """
        amount_wei = w3.to_wei(amount_eth, "ether")
        fee_wei    = (amount_wei * fee_bps) // 10_000
        payout_wei = amount_wei - fee_wei
        return float(w3.from_wei(payout_wei, "ether")), float(w3.from_wei(fee_wei, "ether"))