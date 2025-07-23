// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title CryptoPayments
 * @dev Comprehensive payment system supporting ETH and ERC20 tokens
 */
contract CryptoPayments is ReentrancyGuard, Pausable, Ownable {
    using SafeERC20 for IERC20;
    using Counters for Counters.Counter;

    Counters.Counter private _paymentIdCounter;

    // Events
    event PaymentCreated(
        uint256 indexed paymentId,
        address indexed payer,
        address indexed recipient,
        uint256 amount,
        address token,
        string purpose
    );
    
    event PaymentCompleted(
        uint256 indexed paymentId,
        address indexed payer,
        address indexed recipient,
        uint256 amount,
        address token
    );
    
    event PaymentRefunded(
        uint256 indexed paymentId,
        address indexed payer,
        uint256 amount,
        address token
    );
    
    event EscrowReleased(
        uint256 indexed paymentId,
        address indexed recipient,
        uint256 amount,
        address token
    );
    
    event DisputeRaised(
        uint256 indexed paymentId,
        address indexed raiser,
        string reason
    );
    
    event DisputeResolved(
        uint256 indexed paymentId,
        address indexed resolver,
        bool refundToPayer
    );

    // Structs
    struct Payment {
        uint256 id;
        address payer;
        address recipient;
        uint256 amount;
        address token; // address(0) for ETH
        uint256 createdAt;
        uint256 completedAt;
        PaymentStatus status;
        PaymentType paymentType;
        string purpose;
        uint256 escrowReleaseTime;
        bool disputeRaised;
        string disputeReason;
    }

    struct Subscription {
        uint256 paymentId;
        address subscriber;
        address recipient;
        uint256 amount;
        address token;
        uint256 interval; // in seconds
        uint256 nextPaymentDue;
        uint256 paymentsRemaining; // 0 for unlimited
        bool active;
        string subscriptionType;
    }

    struct Invoice {
        uint256 invoiceId;
        address issuer;
        address payer;
        uint256 amount;
        address token;
        uint256 dueDate;
        string description;
        bytes32 invoiceHash;
        bool paid;
        uint256 paidAt;
    }

    enum PaymentStatus {
        PENDING,
        COMPLETED,
        REFUNDED,
        ESCROWED,
        DISPUTED,
        CANCELLED
    }

    enum PaymentType {
        DIRECT,
        ESCROW,
        SUBSCRIPTION,
        INVOICE
    }

    // Storage
    mapping(uint256 => Payment) public payments;
    mapping(uint256 => Subscription) public subscriptions;
    mapping(uint256 => Invoice) public invoices;
    mapping(address => uint256[]) public userPayments;
    mapping(address => uint256[]) public userSubscriptions;
    mapping(address => uint256[]) public userInvoices;
    mapping(address => bool) public supportedTokens;
    mapping(address => bool) public arbitrators;
    
    // Payment settings
    uint256 public escrowPeriod = 7 days;
    uint256 public platformFeePercentage = 250; // 2.5%
    address public platformFeeRecipient;
    uint256 public minimumEscrowAmount = 0.01 ether;
    
    // Counters
    Counters.Counter private _subscriptionIdCounter;
    Counters.Counter private _invoiceIdCounter;

    modifier onlyArbitrator() {
        require(arbitrators[msg.sender] || msg.sender == owner(), "Not authorized arbitrator");
        _;
    }

    modifier onlyValidToken(address token) {
        require(token == address(0) || supportedTokens[token], "Token not supported");
        _;
    }

    constructor(address _platformFeeRecipient) {
        require(_platformFeeRecipient != address(0), "Invalid fee recipient");
        platformFeeRecipient = _platformFeeRecipient;
        arbitrators[msg.sender] = true;
    }

    /**
     * @dev Create a direct payment
     */
    function createDirectPayment(
        address recipient,
        address token,
        string memory purpose
    ) external payable whenNotPaused onlyValidToken(token) nonReentrant {
        require(recipient != address(0), "Invalid recipient");
        require(recipient != msg.sender, "Cannot pay yourself");
        
        uint256 amount;
        if (token == address(0)) {
            amount = msg.value;
            require(amount > 0, "Amount must be greater than 0");
        } else {
            // For ERC20 tokens, amount should be passed separately
            // This is a simplified version - in production, you'd handle this differently
            revert("ERC20 payments need separate amount parameter");
        }

        uint256 paymentId = _paymentIdCounter.current();
        _paymentIdCounter.increment();

        payments[paymentId] = Payment({
            id: paymentId,
            payer: msg.sender,
            recipient: recipient,
            amount: amount,
            token: token,
            createdAt: block.timestamp,
            completedAt: 0,
            status: PaymentStatus.PENDING,
            paymentType: PaymentType.DIRECT,
            purpose: purpose,
            escrowReleaseTime: 0,
            disputeRaised: false,
            disputeReason: ""
        });

        userPayments[msg.sender].push(paymentId);
        userPayments[recipient].push(paymentId);

        emit PaymentCreated(paymentId, msg.sender, recipient, amount, token, purpose);

        // Complete direct payment immediately
        _completePayment(paymentId);
    }

    /**
     * @dev Create an ERC20 token payment
     */
    function createTokenPayment(
        address recipient,
        address token,
        uint256 amount,
        string memory purpose
    ) external whenNotPaused onlyValidToken(token) nonReentrant {
        require(recipient != address(0), "Invalid recipient");
        require(recipient != msg.sender, "Cannot pay yourself");
        require(token != address(0), "Use createDirectPayment for ETH");
        require(amount > 0, "Amount must be greater than 0");

        // Transfer tokens from payer to contract
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        uint256 paymentId = _paymentIdCounter.current();
        _paymentIdCounter.increment();

        payments[paymentId] = Payment({
            id: paymentId,
            payer: msg.sender,
            recipient: recipient,
            amount: amount,
            token: token,
            createdAt: block.timestamp,
            completedAt: 0,
            status: PaymentStatus.PENDING,
            paymentType: PaymentType.DIRECT,
            purpose: purpose,
            escrowReleaseTime: 0,
            disputeRaised: false,
            disputeReason: ""
        });

        userPayments[msg.sender].push(paymentId);
        userPayments[recipient].push(paymentId);

        emit PaymentCreated(paymentId, msg.sender, recipient, amount, token, purpose);

        // Complete token payment immediately
        _completePayment(paymentId);
    }

    /**
     * @dev Create an escrow payment
     */
    function createEscrowPayment(
        address recipient,
        address token,
        string memory purpose
    ) external payable whenNotPaused onlyValidToken(token) nonReentrant {
        require(recipient != address(0), "Invalid recipient");
        require(recipient != msg.sender, "Cannot pay yourself");
        
        uint256 amount = msg.value;
        require(amount >= minimumEscrowAmount, "Amount below minimum escrow");

        uint256 paymentId = _paymentIdCounter.current();
        _paymentIdCounter.increment();

        uint256 releaseTime = block.timestamp + escrowPeriod;

        payments[paymentId] = Payment({
            id: paymentId,
            payer: msg.sender,
            recipient: recipient,
            amount: amount,
            token: token,
            createdAt: block.timestamp,
            completedAt: 0,
            status: PaymentStatus.ESCROWED,
            paymentType: PaymentType.ESCROW,
            purpose: purpose,
            escrowReleaseTime: releaseTime,
            disputeRaised: false,
            disputeReason: ""
        });

        userPayments[msg.sender].push(paymentId);
        userPayments[recipient].push(paymentId);

        emit PaymentCreated(paymentId, msg.sender, recipient, amount, token, purpose);
    }

    /**
     * @dev Release escrowed funds
     */
    function releaseEscrow(uint256 paymentId) external whenNotPaused nonReentrant {
        Payment storage payment = payments[paymentId];
        require(payment.status == PaymentStatus.ESCROWED, "Payment not in escrow");
        require(
            msg.sender == payment.payer || 
            msg.sender == payment.recipient || 
            block.timestamp >= payment.escrowReleaseTime,
            "Not authorized to release escrow"
        );
        require(!payment.disputeRaised, "Payment is disputed");

        _completePayment(paymentId);
        emit EscrowReleased(paymentId, payment.recipient, payment.amount, payment.token);
    }

    /**
     * @dev Create a subscription payment
     */
    function createSubscription(
        address recipient,
        address token,
        uint256 amount,
        uint256 interval,
        uint256 totalPayments,
        string memory subscriptionType
    ) external whenNotPaused onlyValidToken(token) nonReentrant {
        require(recipient != address(0), "Invalid recipient");
        require(recipient != msg.sender, "Cannot subscribe to yourself");
        require(amount > 0, "Amount must be greater than 0");
        require(interval > 0, "Interval must be greater than 0");

        uint256 subscriptionId = _subscriptionIdCounter.current();
        _subscriptionIdCounter.increment();

        subscriptions[subscriptionId] = Subscription({
            paymentId: subscriptionId,
            subscriber: msg.sender,
            recipient: recipient,
            amount: amount,
            token: token,
            interval: interval,
            nextPaymentDue: block.timestamp + interval,
            paymentsRemaining: totalPayments,
            active: true,
            subscriptionType: subscriptionType
        });

        userSubscriptions[msg.sender].push(subscriptionId);
        userSubscriptions[recipient].push(subscriptionId);

        // Make first payment immediately
        if (token == address(0)) {
            require(msg.value >= amount, "Insufficient ETH for first payment");
            payable(recipient).transfer(amount);
            
            // Refund excess
            if (msg.value > amount) {
                payable(msg.sender).transfer(msg.value - amount);
            }
        } else {
            IERC20(token).safeTransferFrom(msg.sender, recipient, amount);
        }

        if (totalPayments > 0) {
            subscriptions[subscriptionId].paymentsRemaining--;
        }
    }

    /**
     * @dev Process subscription payment
     */
    function processSubscriptionPayment(uint256 subscriptionId) external whenNotPaused nonReentrant {
        Subscription storage subscription = subscriptions[subscriptionId];
        require(subscription.active, "Subscription not active");
        require(block.timestamp >= subscription.nextPaymentDue, "Payment not due yet");
        require(
            subscription.paymentsRemaining > 0 || subscription.paymentsRemaining == 0,
            "No payments remaining"
        );

        // Update next payment due
        subscription.nextPaymentDue = block.timestamp + subscription.interval;
        
        if (subscription.paymentsRemaining > 0) {
            subscription.paymentsRemaining--;
            if (subscription.paymentsRemaining == 0) {
                subscription.active = false;
            }
        }

        // Transfer payment
        if (subscription.token == address(0)) {
            // For ETH, the subscriber needs to send the payment with this transaction
            require(msg.value >= subscription.amount, "Insufficient payment");
            payable(subscription.recipient).transfer(subscription.amount);
            
            // Refund excess
            if (msg.value > subscription.amount) {
                payable(msg.sender).transfer(msg.value - subscription.amount);
            }
        } else {
            IERC20(subscription.token).safeTransferFrom(
                subscription.subscriber,
                subscription.recipient,
                subscription.amount
            );
        }
    }

    /**
     * @dev Create an invoice
     */
    function createInvoice(
        address payer,
        address token,
        uint256 amount,
        uint256 dueDate,
        string memory description
    ) external whenNotPaused onlyValidToken(token) returns (uint256) {
        require(payer != address(0), "Invalid payer");
        require(amount > 0, "Amount must be greater than 0");
        require(dueDate > block.timestamp, "Due date must be in future");

        uint256 invoiceId = _invoiceIdCounter.current();
        _invoiceIdCounter.increment();

        bytes32 invoiceHash = keccak256(
            abi.encodePacked(invoiceId, msg.sender, payer, amount, token, dueDate, description)
        );

        invoices[invoiceId] = Invoice({
            invoiceId: invoiceId,
            issuer: msg.sender,
            payer: payer,
            amount: amount,
            token: token,
            dueDate: dueDate,
            description: description,
            invoiceHash: invoiceHash,
            paid: false,
            paidAt: 0
        });

        userInvoices[msg.sender].push(invoiceId);
        userInvoices[payer].push(invoiceId);

        return invoiceId;
    }

    /**
     * @dev Pay an invoice
     */
    function payInvoice(uint256 invoiceId) external payable whenNotPaused nonReentrant {
        Invoice storage invoice = invoices[invoiceId];
        require(!invoice.paid, "Invoice already paid");
        require(msg.sender == invoice.payer, "Not the invoice payer");
        require(block.timestamp <= invoice.dueDate, "Invoice overdue");

        if (invoice.token == address(0)) {
            require(msg.value >= invoice.amount, "Insufficient payment");
            payable(invoice.issuer).transfer(invoice.amount);
            
            // Refund excess
            if (msg.value > invoice.amount) {
                payable(msg.sender).transfer(msg.value - invoice.amount);
            }
        } else {
            IERC20(invoice.token).safeTransferFrom(msg.sender, invoice.issuer, invoice.amount);
        }

        invoice.paid = true;
        invoice.paidAt = block.timestamp;
    }

    /**
     * @dev Raise a dispute for a payment
     */
    function raiseDispute(uint256 paymentId, string memory reason) external whenNotPaused {
        Payment storage payment = payments[paymentId];
        require(
            msg.sender == payment.payer || msg.sender == payment.recipient,
            "Not authorized to raise dispute"
        );
        require(payment.status == PaymentStatus.ESCROWED, "Payment not eligible for dispute");
        require(!payment.disputeRaised, "Dispute already raised");

        payment.disputeRaised = true;
        payment.disputeReason = reason;
        payment.status = PaymentStatus.DISPUTED;

        emit DisputeRaised(paymentId, msg.sender, reason);
    }

    /**
     * @dev Resolve a dispute
     */
    function resolveDispute(uint256 paymentId, bool refundToPayer) 
        external 
        onlyArbitrator 
        whenNotPaused 
        nonReentrant 
    {
        Payment storage payment = payments[paymentId];
        require(payment.status == PaymentStatus.DISPUTED, "Payment not disputed");

        if (refundToPayer) {
            _refundPayment(paymentId);
        } else {
            _completePayment(paymentId);
        }

        emit DisputeResolved(paymentId, msg.sender, refundToPayer);
    }

    /**
     * @dev Complete a payment
     */
    function _completePayment(uint256 paymentId) internal {
        Payment storage payment = payments[paymentId];
        
        // Calculate platform fee
        uint256 platformFee = (payment.amount * platformFeePercentage) / 10000;
        uint256 recipientAmount = payment.amount - platformFee;

        // Transfer payment
        if (payment.token == address(0)) {
            if (platformFee > 0) {
                payable(platformFeeRecipient).transfer(platformFee);
            }
            payable(payment.recipient).transfer(recipientAmount);
        } else {
            if (platformFee > 0) {
                IERC20(payment.token).safeTransfer(platformFeeRecipient, platformFee);
            }
            IERC20(payment.token).safeTransfer(payment.recipient, recipientAmount);
        }

        payment.status = PaymentStatus.COMPLETED;
        payment.completedAt = block.timestamp;

        emit PaymentCompleted(
            paymentId,
            payment.payer,
            payment.recipient,
            payment.amount,
            payment.token
        );
    }

    /**
     * @dev Refund a payment
     */
    function _refundPayment(uint256 paymentId) internal {
        Payment storage payment = payments[paymentId];

        // Transfer refund
        if (payment.token == address(0)) {
            payable(payment.payer).transfer(payment.amount);
        } else {
            IERC20(payment.token).safeTransfer(payment.payer, payment.amount);
        }

        payment.status = PaymentStatus.REFUNDED;

        emit PaymentRefunded(paymentId, payment.payer, payment.amount, payment.token);
    }

    /**
     * @dev Cancel a subscription
     */
    function cancelSubscription(uint256 subscriptionId) external whenNotPaused {
        Subscription storage subscription = subscriptions[subscriptionId];
        require(
            msg.sender == subscription.subscriber || msg.sender == subscription.recipient,
            "Not authorized to cancel subscription"
        );
        require(subscription.active, "Subscription already inactive");

        subscription.active = false;
    }

    /**
     * @dev Add supported token
     */
    function addSupportedToken(address token) external onlyOwner {
        require(token != address(0), "Invalid token address");
        supportedTokens[token] = true;
    }

    /**
     * @dev Remove supported token
     */
    function removeSupportedToken(address token) external onlyOwner {
        supportedTokens[token] = false;
    }

    /**
     * @dev Add arbitrator
     */
    function addArbitrator(address arbitrator) external onlyOwner {
        require(arbitrator != address(0), "Invalid arbitrator address");
        arbitrators[arbitrator] = true;
    }

    /**
     * @dev Remove arbitrator
     */
    function removeArbitrator(address arbitrator) external onlyOwner {
        arbitrators[arbitrator] = false;
    }

    /**
     * @dev Update platform fee
     */
    function updatePlatformFee(uint256 _feePercentage, address _feeRecipient) 
        external 
        onlyOwner 
    {
        require(_feePercentage <= 1000, "Fee too high"); // Max 10%
        require(_feeRecipient != address(0), "Invalid fee recipient");
        
        platformFeePercentage = _feePercentage;
        platformFeeRecipient = _feeRecipient;
    }

    /**
     * @dev Update escrow period
     */
    function updateEscrowPeriod(uint256 _escrowPeriod) external onlyOwner {
        require(_escrowPeriod >= 1 days && _escrowPeriod <= 30 days, "Invalid escrow period");
        escrowPeriod = _escrowPeriod;
    }

    /**
     * @dev Get user payments
     */
    function getUserPayments(address user) external view returns (uint256[] memory) {
        return userPayments[user];
    }

    /**
     * @dev Get user subscriptions
     */
    function getUserSubscriptions(address user) external view returns (uint256[] memory) {
        return userSubscriptions[user];
    }

    /**
     * @dev Get user invoices
     */
    function getUserInvoices(address user) external view returns (uint256[] memory) {
        return userInvoices[user];
    }

    /**
     * @dev Get payment details
     */
    function getPayment(uint256 paymentId) external view returns (Payment memory) {
        return payments[paymentId];
    }

    /**
     * @dev Get subscription details
     */
    function getSubscription(uint256 subscriptionId) external view returns (Subscription memory) {
        return subscriptions[subscriptionId];
    }

    /**
     * @dev Get invoice details
     */
    function getInvoice(uint256 invoiceId) external view returns (Invoice memory) {
        return invoices[invoiceId];
    }

    /**
     * @dev Pause contract
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @dev Unpause contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @dev Emergency withdraw (only owner)
     */
    function emergencyWithdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }

    /**
     * @dev Emergency withdraw tokens (only owner)
     */
    function emergencyWithdrawToken(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
}