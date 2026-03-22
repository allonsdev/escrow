import json
from web3 import Web3
from django.conf import settings

# -----------------------
# Connect to Ganache RPC
# -----------------------
w3 = Web3(Web3.HTTPProvider(settings.GANACHE_RPC_URL))
if not w3.is_connected():
    raise Exception("❌ Cannot connect to Ganache RPC")

# Set default account (first Ganache account)
w3.eth.default_account = w3.eth.accounts[0]

# -----------------------
# Load Contract ABI
# -----------------------
with open(settings.BLOCKCHAIN_ABI_PATH) as f:
    MASTER_ESCROW_ABI = json.load(f)

CONTRACT_ADDRESS = settings.MASTER_CONTRACT_ADDRESS
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=MASTER_ESCROW_ABI)

# -----------------------
# Blockchain Service
# -----------------------
class BlockchainService:

    @staticmethod
    def create_escrow(buyer_address: str, seller_address: str):

        tx_hash = contract.functions.createEscrow(
            buyer_address,
            seller_address
        ).transact()

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        # ✅ DO NOT USE EVENTS
        escrow_id = contract.functions.escrowCount().call() - 1

        return {
            "receipt": receipt,
            "escrow_id": escrow_id
        }

    @staticmethod
    def deposit(escrow_id: int, from_address: str, amount_eth: float):
        """
        Buyer deposits ETH into escrow
        """
        wei_amount = w3.to_wei(amount_eth, "ether")
        tx_hash = contract.functions.deposit(escrow_id).transact({
            "from": from_address,
            "value": wei_amount
        })
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @staticmethod
    def confirm_delivery(escrow_id: int, buyer_address: str):
        """
        Buyer confirms delivery, releasing funds to seller
        """
        tx_hash = contract.functions.confirmDelivery(escrow_id).transact({
            "from": buyer_address
        })
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @staticmethod
    def refund_buyer(escrow_id: int, arbiter_address: str):
        """
        Arbiter refunds buyer in case of dispute
        """
        tx_hash = contract.functions.refundBuyer(escrow_id).transact({
            "from": arbiter_address
        })
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt