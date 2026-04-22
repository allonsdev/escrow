// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// ─── Custom errors (cheaper than require strings ~50% gas saving) ───
error NotBuyer();
error NotSeller();
error NotArbiter();
error InvalidAddress();
error InvalidState();
error InvalidAmount();
error DeadlineExpired();
error DeadlineNotExpired();
error TransferFailed();
error Paused();
error AlreadyVoted();
error InsufficientVotes();

contract MasterEscrow {

    // ─── Types ───────────────────────────────────────────────────────
    enum State { AWAITING_PAYMENT, AWAITING_DELIVERY, COMPLETE, REFUNDED, CANCELLED }

    struct Escrow {
        address buyer;
        address seller;
        uint128 amount;           // packed: max ~3.4×10^38 wei, plenty
        uint64  deadline;         // unix timestamp, packed with amount
        uint16  feeBps;           // platform fee in basis points e.g. 250 = 2.5%
        State   currentState;
    }

    // ─── State ───────────────────────────────────────────────────────
    address public arbiter;
    address public feeRecipient;
    uint256 public escrowCount;
    bool    public paused;

    mapping(uint256 => Escrow)  public escrows;
    mapping(uint256 => uint256) public pendingWithdrawals; // escrowId → amount owed
    mapping(address => uint256) public claimable;          // pull-payment balances

    // Dispute voting: escrowId => voter => voted
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(uint256 => uint8)  public votesForBuyer;
    mapping(uint256 => uint8)  public votesForSeller;
    uint8 public constant VOTES_REQUIRED = 2;

    // ─── Events ──────────────────────────────────────────────────────
    event EscrowCreated(uint256 indexed escrowId, address buyer, address seller, uint256 deadline);
    event PaymentDeposited(uint256 indexed escrowId, address buyer, uint256 amount);
    event DeliveryConfirmed(uint256 indexed escrowId, address seller, uint256 amount);
    event Refunded(uint256 indexed escrowId, address buyer, uint256 amount);
    event Cancelled(uint256 indexed escrowId);
    event DisputeVoteCast(uint256 indexed escrowId, address voter, bool forBuyer);
    event FeeCollected(uint256 indexed escrowId, uint256 fee);
    event Withdrawn(address indexed recipient, uint256 amount);

    // ─── Modifiers ───────────────────────────────────────────────────
    modifier notPaused() {
        if (paused) revert Paused();
        _;
    }

    modifier nonReentrant() {
        // Simple reentrancy guard without OpenZeppelin dependency
        uint256 _status;
        assembly { _status := sload(0x01) }
        require(_status != 2, "reentrant call");
        assembly { sstore(0x01, 2) }
        _;
        assembly { sstore(0x01, 1) }
    }

    // ─── Constructor ─────────────────────────────────────────────────
    constructor(address _feeRecipient) {
        arbiter      = msg.sender;
        feeRecipient = _feeRecipient;
    }

    // ─────────────────────────────────────────────────────────────────
    //  1. CREATE ESCROW
    // ─────────────────────────────────────────────────────────────────
    function createEscrow(
        address _buyer,
        address _seller,
        uint256 _deadlineDays,   // how many days buyer has to fund + confirm
        uint16  _feeBps          // platform fee e.g. 250 = 2.5%
    ) external notPaused returns (uint256) {
        if (_buyer  == address(0)) revert InvalidAddress();
        if (_seller == address(0)) revert InvalidAddress();
        if (_buyer  == _seller)    revert InvalidAddress();
        if (_feeBps > 1000)        revert InvalidAmount(); // max 10%

        unchecked { ++escrowCount; }  // gas: overflow impossible in practice

        uint64 deadline = uint64(block.timestamp + _deadlineDays * 1 days);

        escrows[escrowCount] = Escrow({
            buyer:        _buyer,
            seller:       _seller,
            amount:       0,
            deadline:     deadline,
            feeBps:       _feeBps,
            currentState: State.AWAITING_PAYMENT
        });

        emit EscrowCreated(escrowCount, _buyer, _seller, deadline);
        return escrowCount;
    }

    // ─────────────────────────────────────────────────────────────────
    //  2. DEPOSIT
    // ─────────────────────────────────────────────────────────────────
    function deposit(uint256 _escrowId) external payable notPaused nonReentrant {
        Escrow storage e = escrows[_escrowId];

        if (msg.sender != e.buyer)               revert NotBuyer();
        if (e.currentState != State.AWAITING_PAYMENT) revert InvalidState();
        if (block.timestamp > e.deadline)        revert DeadlineExpired();
        if (msg.value == 0)                      revert InvalidAmount();

        e.amount       = uint128(msg.value);
        e.currentState = State.AWAITING_DELIVERY;

        emit PaymentDeposited(_escrowId, msg.sender, msg.value);
    }

    // ─────────────────────────────────────────────────────────────────
    //  3. CONFIRM DELIVERY  — pull-payment pattern
    // ─────────────────────────────────────────────────────────────────
    function confirmDelivery(uint256 _escrowId) external notPaused nonReentrant {
        Escrow storage e = escrows[_escrowId];

        if (msg.sender != e.buyer)                   revert NotBuyer();
        if (e.currentState != State.AWAITING_DELIVERY) revert InvalidState();

        e.currentState = State.COMPLETE;

        // Calculate and withhold platform fee
        uint256 fee    = (uint256(e.amount) * e.feeBps) / 10_000;
        uint256 payout = uint256(e.amount) - fee;

        // Credit balances — no external calls here (pull pattern)
        claimable[e.seller]    += payout;
        claimable[feeRecipient] += fee;

        emit DeliveryConfirmed(_escrowId, e.seller, payout);
        if (fee > 0) emit FeeCollected(_escrowId, fee);
    }

    // ─────────────────────────────────────────────────────────────────
    //  4. WITHDRAW  — recipients pull their own funds
    // ─────────────────────────────────────────────────────────────────
    function withdraw() external nonReentrant {
        uint256 amount = claimable[msg.sender];
        if (amount == 0) revert InvalidAmount();

        claimable[msg.sender] = 0;          // zero before transfer (CEI pattern)

        (bool ok, ) = payable(msg.sender).call{value: amount}("");
        if (!ok) revert TransferFailed();

        emit Withdrawn(msg.sender, amount);
    }

    // ─────────────────────────────────────────────────────────────────
    //  5. REFUND  — arbiter only (disputed escrows)
    // ─────────────────────────────────────────────────────────────────
    function refundBuyer(uint256 _escrowId) external nonReentrant {
        if (msg.sender != arbiter)               revert NotArbiter();
        Escrow storage e = escrows[_escrowId];
        if (e.currentState != State.AWAITING_DELIVERY) revert InvalidState();

        e.currentState = State.REFUNDED;
        claimable[e.buyer] += uint256(e.amount);

        emit Refunded(_escrowId, e.buyer, uint256(e.amount));
    }

    // ─────────────────────────────────────────────────────────────────
    //  6. DEADLINE AUTO-REFUND  — anyone can trigger after expiry
    // ─────────────────────────────────────────────────────────────────
    function claimExpiredRefund(uint256 _escrowId) external nonReentrant {
        Escrow storage e = escrows[_escrowId];
        if (e.currentState != State.AWAITING_DELIVERY) revert InvalidState();
        if (block.timestamp <= e.deadline)             revert DeadlineNotExpired();

        e.currentState = State.REFUNDED;
        claimable[e.buyer] += uint256(e.amount);

        emit Refunded(_escrowId, e.buyer, uint256(e.amount));
    }

    // ─────────────────────────────────────────────────────────────────
    //  7. SELLER CANCEL  — only before deposit
    // ─────────────────────────────────────────────────────────────────
    function cancelBySeller(uint256 _escrowId) external {
        Escrow storage e = escrows[_escrowId];
        if (msg.sender != e.seller)                   revert NotSeller();
        if (e.currentState != State.AWAITING_PAYMENT) revert InvalidState();

        e.currentState = State.CANCELLED;
        emit Cancelled(_escrowId);
    }

    // ─────────────────────────────────────────────────────────────────
    //  8. DISPUTE VOTING  — multi-arbiter, 2-of-3
    // ─────────────────────────────────────────────────────────────────
    mapping(address => bool) public isArbiter;

    function castDisputeVote(uint256 _escrowId, bool forBuyer) external {
        if (!isArbiter[msg.sender]) revert NotArbiter();
        if (hasVoted[_escrowId][msg.sender]) revert AlreadyVoted();

        Escrow storage e = escrows[_escrowId];
        if (e.currentState != State.AWAITING_DELIVERY) revert InvalidState();

        hasVoted[_escrowId][msg.sender] = true;

        if (forBuyer) {
            unchecked { ++votesForBuyer[_escrowId]; }
            if (votesForBuyer[_escrowId] >= VOTES_REQUIRED) {
                e.currentState = State.REFUNDED;
                claimable[e.buyer] += uint256(e.amount);
                emit Refunded(_escrowId, e.buyer, uint256(e.amount));
            }
        } else {
            unchecked { ++votesForSeller[_escrowId]; }
            if (votesForSeller[_escrowId] >= VOTES_REQUIRED) {
                uint256 fee    = (uint256(e.amount) * e.feeBps) / 10_000;
                uint256 payout = uint256(e.amount) - fee;
                e.currentState = State.COMPLETE;
                claimable[e.seller]    += payout;
                claimable[feeRecipient] += fee;
                emit DeliveryConfirmed(_escrowId, e.seller, payout);
            }
        }

        emit DisputeVoteCast(_escrowId, msg.sender, forBuyer);
    }

    // ─────────────────────────────────────────────────────────────────
    //  ADMIN
    // ─────────────────────────────────────────────────────────────────
    function setPaused(bool _paused) external {
        if (msg.sender != arbiter) revert NotArbiter();
        paused = _paused;
    }

    function addArbiter(address _a) external {
        if (msg.sender != arbiter) revert NotArbiter();
        isArbiter[_a] = true;
    }

    function removeArbiter(address _a) external {
        if (msg.sender != arbiter) revert NotArbiter();
        isArbiter[_a] = false;
    }

    // ─────────────────────────────────────────────────────────────────
    //  VIEW
    // ─────────────────────────────────────────────────────────────────
    function getEscrow(uint256 _escrowId) external view returns (
        address buyer, address seller, uint256 amount, State currentState, uint64 deadline
    ) {
        Escrow memory e = escrows[_escrowId];
        return (e.buyer, e.seller, uint256(e.amount), e.currentState, e.deadline);
    }
}