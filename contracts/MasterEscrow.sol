// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MasterEscrow {

    address public arbiter;
    uint public escrowCount;

    enum State { AWAITING_PAYMENT, AWAITING_DELIVERY, COMPLETE, REFUNDED }

    struct Escrow {
        address buyer;
        address seller;
        uint amount;
        State currentState;
    }

    mapping(uint => Escrow) public escrows;

    // EVENTS
    event EscrowCreated(uint indexed escrowId, address buyer, address seller);
    event PaymentDeposited(uint indexed escrowId, address buyer, uint amount);
    event DeliveryConfirmed(uint indexed escrowId, address seller, uint amount);
    event Refunded(uint indexed escrowId, address buyer, uint amount);

    constructor() {
        arbiter = msg.sender;
    }

    // 1️⃣ CREATE ESCROW
    function createEscrow(address _buyer, address _seller) external returns (uint) {
        require(_buyer != address(0), "Invalid buyer");
        require(_seller != address(0), "Invalid seller");

        escrowCount++;

        escrows[escrowCount] = Escrow({
            buyer: _buyer,
            seller: _seller,
            amount: 0,
            currentState: State.AWAITING_PAYMENT
        });

        emit EscrowCreated(escrowCount, _buyer, _seller);
        return escrowCount;
    }

    // 2️⃣ DEPOSIT FUNDS
    function deposit(uint _escrowId) external payable {
        Escrow storage e = escrows[_escrowId];

        require(msg.sender == e.buyer, "Only buyer can deposit");
        require(e.currentState == State.AWAITING_PAYMENT, "Invalid state");

        e.amount += msg.value;
        e.currentState = State.AWAITING_DELIVERY;

        emit PaymentDeposited(_escrowId, msg.sender, msg.value);
    }

    // 3️⃣ CONFIRM DELIVERY
    function confirmDelivery(uint _escrowId) external {
        Escrow storage e = escrows[_escrowId];

        require(msg.sender == e.buyer, "Only buyer can confirm");
        require(e.currentState == State.AWAITING_DELIVERY, "Invalid state");

        e.currentState = State.COMPLETE;

        (bool success, ) = payable(e.seller).call{value: e.amount}("");
        require(success, "Transfer failed");

        emit DeliveryConfirmed(_escrowId, e.seller, e.amount);
    }

    // 4️⃣ REFUND BUYER (Arbiter)
    function refundBuyer(uint _escrowId) external {
        require(msg.sender == arbiter, "Only arbiter");

        Escrow storage e = escrows[_escrowId];
        require(e.currentState == State.AWAITING_DELIVERY, "Invalid state");

        e.currentState = State.REFUNDED;

        (bool success, ) = payable(e.buyer).call{value: e.amount}("");
        require(success, "Refund failed");

        emit Refunded(_escrowId, e.buyer, e.amount);
    }

    // VIEW FUNCTION
    function getEscrow(uint _escrowId)
        external
        view
        returns (
            address buyer,
            address seller,
            uint amount,
            State currentState
        )
    {
        Escrow memory e = escrows[_escrowId];
        return (e.buyer, e.seller, e.amount, e.currentState);
    }
}
