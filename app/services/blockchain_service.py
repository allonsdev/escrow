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
    def checksum(address):
        if not address:
            raise ValueError("Address is empty")

        if not address.startswith("0x"):
            address = "0x" + address

        return w3.to_checksum_address(address)
    
    @staticmethod
    def create_escrow(buyer_address: str, seller_address: str):
        try:
            print(f"🧠 Raw buyer address: {buyer_address}")
            print(f"🧠 Raw seller address: {seller_address}")

            # Convert to checksum
            buyer_address = w3.to_checksum_address(buyer_address)
            seller_address = w3.to_checksum_address(seller_address)

            print(f"✔ Checksum buyer: {buyer_address}")
            print(f"✔ Checksum seller: {seller_address}")

            # Call contract
            tx_hash = contract.functions.createEscrow(
                buyer_address,
                seller_address
            ).transact()

            print(f"⛓ Transaction hash: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            print(f"✅ Receipt block: {receipt.blockNumber}")
            print(f"✅ Gas used: {receipt.gasUsed}")

            # DO NOT USE EVENTS (good)
            escrow_id = contract.functions.escrowCount().call() - 1
            print(f"🎯 Escrow ID: {escrow_id}")

            return {
                "receipt": receipt,
                "escrow_id": escrow_id
            }

        except Exception as e:
            print(f"❌ Error creating escrow: {e}")
            raise
    
    
    @staticmethod
    def deposit(escrow_id: int, from_address: str, amount_eth: float):
        
        escrow_on_chain = contract.functions.getEscrow(escrow_id).call()

        buyer_on_chain = escrow_on_chain[0]   # adjust index if needed
        print("BUYER ON CHAIN:", buyer_on_chain)
        print("ADDRESS YOU SEND:", from_address)
        print("MATCH:", buyer_on_chain.lower() == from_address.lower())
        try:
            print(f"🧠 Deposit request for escrow: {escrow_id}")
            print(f"🧠 Raw from_address: {from_address}")
            print(f"🧠 Amount ETH: {amount_eth}")

            # checksum address
            from_address = w3.to_checksum_address(from_address)
            print(f"✔ Checksum from_address: {from_address}")

            wei_amount = w3.to_wei(amount_eth, "ether")
            print(f"💰 Wei amount: {wei_amount}")

            tx_hash = contract.functions.deposit(escrow_id).transact({
                "from": from_address,
                "value": wei_amount
            })

            print(f"⛓ Transaction hash: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            print(f"✅ Deposit confirmed in block: {receipt.blockNumber}")
            print(f"✅ Gas used: {receipt.gasUsed}")

            return receipt

        except Exception as e:
            print(f"❌ Deposit error: {e}")
            raise
        
    @staticmethod
    def confirm_delivery(escrow_id: int, buyer_address: str):
        try:
            print(f"🧠 Confirm delivery for escrow: {escrow_id}")
            print(f"🧠 Raw buyer address: {buyer_address}")

            buyer_address = w3.to_checksum_address(buyer_address)
            print(f"✔ Checksum buyer: {buyer_address}")

            tx_hash = contract.functions.confirmDelivery(escrow_id).transact({
                "from": buyer_address
            })

            print(f"⛓ Transaction hash: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            print(f"✅ Delivery confirmed block: {receipt.blockNumber}")

            return receipt

        except Exception as e:
            print(f"❌ Confirm delivery error: {e}")
            raise
        
    @staticmethod
    def refund_buyer(escrow_id: int, arbiter_address: str):
        try:
            print(f"🧠 Refund request for escrow: {escrow_id}")
            print(f"🧠 Raw arbiter: {arbiter_address}")

            arbiter_address = w3.to_checksum_address(arbiter_address)
            print(f"✔ Checksum arbiter: {arbiter_address}")

            tx_hash = contract.functions.refundBuyer(escrow_id).transact({
                "from": arbiter_address
            })

            print(f"⛓ Transaction hash: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            print(f"✅ Refund confirmed block: {receipt.blockNumber}")

            return receipt

        except Exception as e:
            print(f"❌ Refund error: {e}")
            raise