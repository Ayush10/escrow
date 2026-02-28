// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @notice Minimal interface for ERC-8004 IdentityRegistry
interface IIdentityRegistry {
    function ownerOf(uint256 tokenId) external view returns (address);
    function balanceOf(address owner) external view returns (uint256);
}

/// @notice Minimal interface for ERC-8004 ReputationRegistry
interface IReputationRegistry {
    function updateReputation(address agent, string calldata category, int256 delta) external;
}

/// @title AgentCourt — The clearinghouse for the machine economy
/// @notice One contract. Every agent, every transaction, every dispute. All on-chain.
contract AgentCourt {

    // ===== STATE =====

    address public judge;
    uint256 public minDeposit;
    uint256 public serviceFeeRate;  // basis points (100 = 1%)

    // Tiered judge fees: $0.05, $0.10, $0.20 (in wei at deploy time)
    uint256[3] public judgeFees;
    // Track dispute count per agent for tier escalation
    mapping(address => uint8) public disputeLossCount;

    IIdentityRegistry public identityRegistry;
    IReputationRegistry public reputationRegistry;
    bool public requireIdentity;

    // Agent balances — your bond IS your reputation
    mapping(address => uint256) public balances;

    // Agent stats — on-chain track record
    mapping(address => AgentStats) public stats;

    // Service agreements — provider registers their API terms
    mapping(uint256 => Service) public services;
    uint256 public serviceCount;

    // Transactions — every API call between agents
    mapping(uint256 => Transaction) public transactions;
    uint256 public transactionCount;

    // Disputes
    mapping(uint256 => Dispute) public disputes;
    uint256 public disputeCount;

    // Evidence hash commits
    mapping(bytes32 => bytes32) public evidenceCommits;

    // ===== STRUCTS =====

    struct AgentStats {
        uint256 totalTransactions;
        uint256 successfulTransactions;
        uint256 disputesWon;
        uint256 disputesLost;
        uint256 totalEarned;
        uint256 totalSpent;
        uint64 registeredAt;
    }

    enum ServiceStatus { Active, Paused, Retired }

    struct Service {
        address provider;
        bytes32 termsHash;        // hash of off-chain terms (API spec, SLA, pricing)
        uint256 price;            // price per call in wei
        uint256 bondRequired;     // min bond consumer must hold
        ServiceStatus status;
        uint256 totalCalls;
        uint256 totalDisputes;
    }

    enum TxStatus { Requested, Fulfilled, Completed, Disputed }

    struct Transaction {
        uint256 serviceId;
        address consumer;         // who's calling the API
        address provider;         // who's serving it
        uint256 payment;          // amount locked for this call
        bytes32 requestHash;      // hash of the request data
        bytes32 responseHash;     // hash of the response data (set by provider)
        TxStatus status;
        uint64 createdAt;
        uint64 fulfilledAt;
        uint256 disputeId;        // if disputed, link to dispute
    }

    struct Dispute {
        uint256 transactionId;
        address plaintiff;
        address defendant;
        uint256 stake;
        uint256 judgeFee;         // fee for this dispute's tier
        uint8 tier;               // 0=district, 1=appeals, 2=supreme
        bytes32 plaintiffEvidence;
        bytes32 defendantEvidence;
        bool resolved;
        address winner;
    }

    // ===== EVENTS =====

    event AgentRegistered(address indexed agent, uint256 deposit);
    event Deposited(address indexed agent, uint256 amount, uint256 newBalance);
    event Withdrawn(address indexed agent, uint256 amount, uint256 newBalance);

    event ServiceRegistered(uint256 indexed serviceId, address indexed provider, uint256 price);
    event ServiceUpdated(uint256 indexed serviceId, ServiceStatus status);

    event TransactionCreated(uint256 indexed txId, uint256 indexed serviceId, address indexed consumer, uint256 payment);
    event TransactionFulfilled(uint256 indexed txId, address indexed provider, bytes32 responseHash);
    event TransactionCompleted(uint256 indexed txId, uint256 payment);

    event DisputeFiled(uint256 indexed disputeId, uint256 indexed txId, address indexed plaintiff, uint256 stake);
    event RulingSubmitted(uint256 indexed disputeId, address indexed winner, address indexed loser, uint256 award);

    // ===== MODIFIERS =====

    modifier onlyJudge() {
        require(msg.sender == judge, "Not judge");
        _;
    }

    modifier hasBalance(uint256 amount) {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        _;
    }

    modifier registered() {
        require(stats[msg.sender].registeredAt > 0, "Not registered");
        _;
    }

    // ===== CONSTRUCTOR =====

    constructor(
        address _judge,
        uint256 _minDeposit,
        uint256[3] memory _judgeFees,
        uint256 _serviceFeeRate,
        address _identityRegistry,
        address _reputationRegistry,
        bool _requireIdentity
    ) {
        judge = _judge;
        minDeposit = _minDeposit;
        judgeFees = _judgeFees;  // [district, appeals, supreme]
        serviceFeeRate = _serviceFeeRate;
        identityRegistry = IIdentityRegistry(_identityRegistry);
        reputationRegistry = IReputationRegistry(_reputationRegistry);
        requireIdentity = _requireIdentity;
    }

    // ===== AGENT LIFECYCLE =====

    /// Register as an agent. Deposit is your bond/reputation.
    function register() external payable {
        require(stats[msg.sender].registeredAt == 0, "Already registered");
        require(msg.value >= minDeposit, "Below min deposit");
        if (requireIdentity) {
            require(identityRegistry.balanceOf(msg.sender) > 0, "No ERC-8004 identity");
        }
        balances[msg.sender] = msg.value;
        stats[msg.sender].registeredAt = uint64(block.timestamp);
        emit AgentRegistered(msg.sender, msg.value);
    }

    /// Add more to your bond.
    function deposit() external payable registered {
        require(msg.value > 0, "Zero deposit");
        balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value, balances[msg.sender]);
    }

    /// Withdraw unused balance. Must keep minDeposit to stay active.
    function withdraw(uint256 amount) external hasBalance(amount) {
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
        emit Withdrawn(msg.sender, amount, balances[msg.sender]);
    }

    // ===== SERVICE REGISTRY =====

    /// Provider registers an API service with terms and pricing.
    function registerService(
        bytes32 termsHash,
        uint256 price,
        uint256 bondRequired
    ) external registered returns (uint256) {
        uint256 id = serviceCount++;
        services[id] = Service({
            provider: msg.sender,
            termsHash: termsHash,
            price: price,
            bondRequired: bondRequired,
            status: ServiceStatus.Active,
            totalCalls: 0,
            totalDisputes: 0
        });
        emit ServiceRegistered(id, msg.sender, price);
        return id;
    }

    /// Provider updates service status.
    function updateService(uint256 serviceId, ServiceStatus status) external {
        Service storage s = services[serviceId];
        require(msg.sender == s.provider, "Not provider");
        s.status = status;
        emit ServiceUpdated(serviceId, status);
    }

    // ===== TRANSACTIONS =====

    /// Consumer requests a service. Payment locked from their balance.
    function requestService(
        uint256 serviceId,
        bytes32 requestHash
    ) external registered returns (uint256) {
        Service storage s = services[serviceId];
        require(s.status == ServiceStatus.Active, "Service not active");
        require(balances[msg.sender] >= s.bondRequired, "Below service bond requirement");
        require(balances[msg.sender] >= s.price, "Cannot afford service");
        require(msg.sender != s.provider, "Cannot call own service");

        // Lock payment from consumer's balance
        balances[msg.sender] -= s.price;

        uint256 txId = transactionCount++;
        transactions[txId] = Transaction({
            serviceId: serviceId,
            consumer: msg.sender,
            provider: s.provider,
            payment: s.price,
            requestHash: requestHash,
            responseHash: bytes32(0),
            status: TxStatus.Requested,
            createdAt: uint64(block.timestamp),
            fulfilledAt: 0,
            disputeId: 0
        });

        s.totalCalls++;
        stats[msg.sender].totalTransactions++;
        stats[msg.sender].totalSpent += s.price;

        emit TransactionCreated(txId, serviceId, msg.sender, s.price);
        return txId;
    }

    /// Provider fulfills the request by committing the response hash.
    function fulfillTransaction(uint256 txId, bytes32 responseHash) external {
        Transaction storage t = transactions[txId];
        require(msg.sender == t.provider, "Not provider");
        require(t.status == TxStatus.Requested, "Not in requested state");

        t.responseHash = responseHash;
        t.status = TxStatus.Fulfilled;
        t.fulfilledAt = uint64(block.timestamp);

        emit TransactionFulfilled(txId, msg.sender, responseHash);
    }

    /// Consumer confirms satisfaction. Payment released to provider.
    function confirmTransaction(uint256 txId) external {
        Transaction storage t = transactions[txId];
        require(msg.sender == t.consumer, "Not consumer");
        require(t.status == TxStatus.Fulfilled, "Not fulfilled");

        t.status = TxStatus.Completed;

        // Pay provider (minus platform fee)
        uint256 fee = (t.payment * serviceFeeRate) / 10000;
        uint256 payout = t.payment - fee;
        balances[t.provider] += payout;
        balances[judge] += fee;  // platform fee to judge/operator

        stats[t.provider].totalTransactions++;
        stats[t.provider].successfulTransactions++;
        stats[t.provider].totalEarned += payout;
        stats[t.consumer].successfulTransactions++;

        // Reputation boost for both sides
        try reputationRegistry.updateReputation(t.provider, "service_completed", int256(1)) {} catch {}
        try reputationRegistry.updateReputation(t.consumer, "service_used", int256(1)) {} catch {}

        emit TransactionCompleted(txId, payout);
    }

    /// Auto-complete after timeout if consumer doesn't confirm or dispute.
    function autoComplete(uint256 txId) external {
        Transaction storage t = transactions[txId];
        require(t.status == TxStatus.Fulfilled, "Not fulfilled");
        require(block.timestamp > t.fulfilledAt + 1 hours, "Too early");

        t.status = TxStatus.Completed;

        uint256 fee = (t.payment * serviceFeeRate) / 10000;
        uint256 payout = t.payment - fee;
        balances[t.provider] += payout;
        balances[judge] += fee;

        stats[t.provider].totalTransactions++;
        stats[t.provider].successfulTransactions++;
        stats[t.provider].totalEarned += payout;
        stats[t.consumer].successfulTransactions++;

        try reputationRegistry.updateReputation(t.provider, "service_completed", int256(1)) {} catch {}

        emit TransactionCompleted(txId, payout);
    }

    // ===== DISPUTES =====

    /// Get the current judge fee tier for an agent based on their loss count.
    function getJudgeFee(address agent) public view returns (uint256 fee, uint8 tier) {
        uint8 losses = disputeLossCount[agent];
        if (losses >= 2) {
            return (judgeFees[2], 2);  // supreme: $0.20
        } else if (losses >= 1) {
            return (judgeFees[1], 1);  // appeals: $0.10
        } else {
            return (judgeFees[0], 0);  // district: $0.05
        }
    }

    /// File a dispute on a fulfilled transaction. Fee tier based on filer's loss history.
    function fileDispute(
        uint256 txId,
        uint256 stake,
        bytes32 evidence
    ) external returns (uint256) {
        // Determine fee tier for the filer
        (uint256 fee, uint8 tier) = getJudgeFee(msg.sender);
        require(balances[msg.sender] >= stake + fee, "Insufficient balance for stake + judge fee");

        Transaction storage t = transactions[txId];
        require(t.status == TxStatus.Fulfilled, "Can only dispute fulfilled txns");
        require(msg.sender == t.consumer || msg.sender == t.provider, "Not party to txn");

        address defendant = msg.sender == t.consumer ? t.provider : t.consumer;
        require(balances[defendant] >= stake, "Defendant underfunded");

        // Freeze stakes + judge fee
        balances[msg.sender] -= (stake + fee);
        balances[defendant] -= stake;

        t.status = TxStatus.Disputed;

        uint256 id = disputeCount++;
        disputes[id] = Dispute({
            transactionId: txId,
            plaintiff: msg.sender,
            defendant: defendant,
            stake: stake,
            judgeFee: fee,
            tier: tier,
            plaintiffEvidence: evidence,
            defendantEvidence: bytes32(0),
            resolved: false,
            winner: address(0)
        });

        t.disputeId = id;
        services[t.serviceId].totalDisputes++;

        emit DisputeFiled(id, txId, msg.sender, stake);
        return id;
    }

    /// Defendant responds with evidence.
    function respondDispute(uint256 disputeId, bytes32 evidence) external {
        Dispute storage d = disputes[disputeId];
        require(msg.sender == d.defendant, "Not defendant");
        require(!d.resolved, "Already resolved");
        require(d.defendantEvidence == bytes32(0), "Already responded");
        d.defendantEvidence = evidence;
    }

    /// Judge submits ruling. Contract enforces payout.
    /// Judge fee paid from the frozen amount. Loser's loss count escalates their future tier.
    function submitRuling(uint256 disputeId, address winner) external onlyJudge {
        Dispute storage d = disputes[disputeId];
        require(!d.resolved, "Already resolved");
        require(winner == d.plaintiff || winner == d.defendant, "Winner not in dispute");

        d.resolved = true;
        d.winner = winner;

        uint256 totalStake = d.stake * 2;
        address loser = winner == d.plaintiff ? d.defendant : d.plaintiff;

        // Winner gets both stakes
        balances[winner] += totalStake;
        // Judge gets the tiered fee (already deducted from plaintiff)
        balances[judge] += d.judgeFee;

        // Escalate loser's tier for next dispute
        if (disputeLossCount[loser] < 3) {
            disputeLossCount[loser]++;
        }
        // 3 losses = effectively banned (tier 2 fee is max, balance likely drained)

        // Also release the locked transaction payment
        Transaction storage t = transactions[d.transactionId];
        if (winner == t.consumer) {
            balances[t.consumer] += t.payment;
        } else {
            uint256 fee = (t.payment * serviceFeeRate) / 10000;
            balances[t.provider] += t.payment - fee;
            balances[judge] += fee;
        }

        // Stats
        stats[winner].disputesWon++;
        stats[loser].disputesLost++;

        // ERC-8004 reputation
        try reputationRegistry.updateReputation(winner, "court_wins", int256(1)) {} catch {}
        try reputationRegistry.updateReputation(loser, "court_losses", int256(-1)) {} catch {}

        emit RulingSubmitted(disputeId, winner, loser, totalStake);
    }

    // ===== EVIDENCE =====

    /// Commit evidence hash during any interaction.
    function commitEvidence(bytes32 txKey, bytes32 evidenceHash) external registered {
        evidenceCommits[keccak256(abi.encodePacked(txKey, msg.sender))] = evidenceHash;
    }

    // ===== VIEW FUNCTIONS =====

    function getService(uint256 serviceId) external view returns (Service memory) {
        return services[serviceId];
    }

    function getTransaction(uint256 txId) external view returns (Transaction memory) {
        return transactions[txId];
    }

    function getDispute(uint256 disputeId) external view returns (Dispute memory) {
        return disputes[disputeId];
    }

    function getStats(address agent) external view returns (AgentStats memory) {
        return stats[agent];
    }

    function getBalance(address agent) external view returns (uint256) {
        return balances[agent];
    }

    function isEligible(address agent) external view returns (bool) {
        return balances[agent] >= minDeposit;
    }

    function isRegistered(address agent) external view returns (bool) {
        return stats[agent].registeredAt > 0;
    }

    function hasIdentity(address agent) external view returns (bool) {
        return identityRegistry.balanceOf(agent) > 0;
    }

    function getSuccessRate(address agent) external view returns (uint256) {
        AgentStats memory s = stats[agent];
        if (s.totalTransactions == 0) return 0;
        return (s.successfulTransactions * 100) / s.totalTransactions;
    }
}
