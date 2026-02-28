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

contract AgentCourt {
    // --- State ---
    address public judge;
    uint256 public minDeposit;
    uint256 public judgeFee;

    // ERC-8004 registries on GOAT Testnet3
    IIdentityRegistry public identityRegistry;
    IReputationRegistry public reputationRegistry;
    bool public requireIdentity;  // if true, agents must have ERC-8004 identity

    mapping(address => uint256) public balances;
    mapping(uint256 => Dispute) public disputes;
    uint256 public disputeCount;

    // Evidence hash commits: keccak256(request + response + timestamp)
    // Keyed by hash(agentA, agentB, nonce) -> hash from each side
    mapping(bytes32 => bytes32) public evidenceCommits;

    struct Dispute {
        address plaintiff;
        address defendant;
        uint256 plaintiffStake;
        uint256 defendantStake;
        bytes32 plaintiffEvidence;
        bytes32 defendantEvidence;
        bool resolved;
        address winner;
    }

    // --- Events ---
    event Deposited(address indexed agent, uint256 amount, uint256 newBalance);
    event Withdrawn(address indexed agent, uint256 amount, uint256 newBalance);
    event EvidenceCommitted(address indexed agent, bytes32 indexed txKey, bytes32 evidenceHash);
    event DisputeFiled(uint256 indexed disputeId, address indexed plaintiff, address indexed defendant, uint256 stake);
    event RulingSubmitted(uint256 indexed disputeId, address indexed winner, address indexed loser, uint256 award);

    // --- Modifiers ---
    modifier onlyJudge() {
        require(msg.sender == judge, "Not judge");
        _;
    }

    modifier hasBalance(uint256 amount) {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        _;
    }

    // --- Constructor ---
    constructor(
        address _judge,
        uint256 _minDeposit,
        uint256 _judgeFee,
        address _identityRegistry,
        address _reputationRegistry,
        bool _requireIdentity
    ) {
        judge = _judge;
        minDeposit = _minDeposit;
        judgeFee = _judgeFee;
        identityRegistry = IIdentityRegistry(_identityRegistry);
        reputationRegistry = IReputationRegistry(_reputationRegistry);
        requireIdentity = _requireIdentity;
    }

    // --- Core Functions ---

    /// Deposit into the court. Your balance is your reputation.
    function deposit() external payable {
        require(msg.value > 0, "Zero deposit");
        if (requireIdentity) {
            require(identityRegistry.balanceOf(msg.sender) > 0, "No ERC-8004 identity");
        }
        balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value, balances[msg.sender]);
    }

    /// Withdraw unused balance.
    function withdraw(uint256 amount) external hasBalance(amount) {
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
        emit Withdrawn(msg.sender, amount, balances[msg.sender]);
    }

    /// Commit evidence hash during a transaction (cheap, do this per-interaction).
    /// txKey = keccak256(abi.encodePacked(agentA, agentB, nonce))
    function commitEvidence(bytes32 txKey, bytes32 evidenceHash) external {
        require(balances[msg.sender] >= minDeposit, "Below min deposit");
        evidenceCommits[keccak256(abi.encodePacked(txKey, msg.sender))] = evidenceHash;
        emit EvidenceCommitted(msg.sender, txKey, evidenceHash);
    }

    /// File a dispute. Plaintiff stakes from their balance.
    function fileDispute(
        address defendant,
        uint256 stake,
        bytes32 plaintiffEvidence
    ) external hasBalance(stake + judgeFee) returns (uint256) {
        require(defendant != msg.sender, "Cannot dispute self");
        require(balances[defendant] >= stake, "Defendant underfunded");

        // Freeze stakes from both balances
        balances[msg.sender] -= (stake + judgeFee);
        balances[defendant] -= stake;

        uint256 id = disputeCount++;
        disputes[id] = Dispute({
            plaintiff: msg.sender,
            defendant: defendant,
            plaintiffStake: stake,
            defendantStake: stake,
            plaintiffEvidence: plaintiffEvidence,
            defendantEvidence: bytes32(0),
            resolved: false,
            winner: address(0)
        });

        emit DisputeFiled(id, msg.sender, defendant, stake);
        return id;
    }

    /// Defendant submits their evidence after a dispute is filed.
    function respondDispute(uint256 disputeId, bytes32 evidence) external {
        Dispute storage d = disputes[disputeId];
        require(msg.sender == d.defendant, "Not defendant");
        require(!d.resolved, "Already resolved");
        require(d.defendantEvidence == bytes32(0), "Already responded");
        d.defendantEvidence = evidence;
    }

    /// Judge submits ruling. Never touches money — contract enforces payout.
    /// Also updates ERC-8004 reputation: winner +1, loser -1.
    function submitRuling(uint256 disputeId, address winner) external onlyJudge {
        Dispute storage d = disputes[disputeId];
        require(!d.resolved, "Already resolved");
        require(winner == d.plaintiff || winner == d.defendant, "Winner not in dispute");

        d.resolved = true;
        d.winner = winner;

        uint256 totalStake = d.plaintiffStake + d.defendantStake;
        address loser = winner == d.plaintiff ? d.defendant : d.plaintiff;

        // Winner gets both stakes back
        balances[winner] += totalStake;
        // Judge gets paid from the frozen judge fee (already deducted from plaintiff)
        balances[judge] += judgeFee;

        // Update ERC-8004 reputation (best-effort, don't revert if registry fails)
        try reputationRegistry.updateReputation(winner, "court_wins", int256(1)) {} catch {}
        try reputationRegistry.updateReputation(loser, "court_losses", int256(-1)) {} catch {}

        emit RulingSubmitted(disputeId, winner, loser, totalStake);
    }

    // --- View Functions ---

    function getDispute(uint256 disputeId) external view returns (Dispute memory) {
        return disputes[disputeId];
    }

    function getBalance(address agent) external view returns (uint256) {
        return balances[agent];
    }

    function isEligible(address agent) external view returns (bool) {
        return balances[agent] >= minDeposit;
    }

    function hasIdentity(address agent) external view returns (bool) {
        return identityRegistry.balanceOf(agent) > 0;
    }
}
