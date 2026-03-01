// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// AgentCommerce — bilateral service agreements with on-chain dispute resolution.
//
// Design principals:
//   1. The contract holds money and verifies hashes. Nothing else.
//   2. Every balance change is explicit. The contract never holds unaccounted funds.
//   3. The arbitrator is a black box. It submits a payout and the contract enforces it.
//   4. A dispute unwinds cleanly in every path. No funds get stuck.
//   5. State is minimal. Reputation, history, and indexing belong off-chain.

interface IERC20 {
    function transferFrom(address, address, uint256) external returns (bool);
    function transfer(address, uint256) external returns (bool);
}

contract AgentCommerce {

    IERC20 public immutable usdc;

    // ─────────────────────────────────────────────────────────────────────────
    // Balances
    //
    // All funds flow through internal balances. No direct transfers mid-logic.
    // ─────────────────────────────────────────────────────────────────────────

    mapping(address => uint256) public balances;

    function deposit(uint256 amount) external {
        usdc.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        usdc.transfer(msg.sender, amount);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Services
    //
    // A service is identified by the hash of its SLA. Immutable — new terms
    // mean a new service. The provider posts a bond at registration that signals
    // commitment and backs any dispute. The bond is locked until the provider
    // requests deactivation and waits out a delay, giving consumers time to dispute.
    // ─────────────────────────────────────────────────────────────────────────

    struct Service {
        address provider;
        address arbitrator;
        uint256 minBond;         // minimum consumer stake to open a channel
        uint256 bond;            // provider's locked stake, backs all disputes
        bool    active;
        uint256 deactivatingAt;  // nonzero once deactivation is requested
    }

    mapping(bytes32 => Service) public services;

    uint256 public constant DEACTIVATION_DELAY = 30 days;

    event ServiceRegistered(bytes32 indexed id, address provider, address arbitrator, uint256 minBond, uint256 bond);
    event DeactivationRequested(bytes32 indexed id, uint256 claimableAt);
    event ServiceDeactivated(bytes32 indexed id);

    function registerService(bytes32 slaHash, address arbitrator, uint256 minBond, uint256 bond) external {
        require(services[slaHash].provider == address(0), "exists");
        require(arbitrator != address(0));
        require(bond >= minBond);
        require(balances[msg.sender] >= bond);

        balances[msg.sender] -= bond;
        services[slaHash] = Service(msg.sender, arbitrator, minBond, bond, true, 0);

        emit ServiceRegistered(slaHash, msg.sender, arbitrator, minBond, bond);
    }

    function requestDeactivation(bytes32 slaHash) external {
        Service storage s = services[slaHash];
        require(msg.sender == s.provider);
        require(s.active);

        s.active         = false;
        s.deactivatingAt = block.timestamp;

        emit DeactivationRequested(slaHash, block.timestamp + DEACTIVATION_DELAY);
    }

    function claimDeactivation(bytes32 slaHash) external {
        Service storage s = services[slaHash];
        require(msg.sender == s.provider);
        require(s.deactivatingAt > 0);
        require(block.timestamp >= s.deactivatingAt + DEACTIVATION_DELAY);

        uint256 bond = s.bond;
        s.bond = 0;
        balances[msg.sender] += bond;

        emit ServiceDeactivated(slaHash);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Channels
    //
    // A channel is an open relationship between a consumer and a provider under
    // a specific service. The consumer posts a bond. All interactions happen
    // off-chain as a signed hash chain. The channel tracks the last agreed head.
    //
    // Happy path: both parties co-sign a close with a payout split.
    // Unhappy path: either party opens a dispute.
    // Abandoned path: either party expires the channel after 30 days of silence.
    // ─────────────────────────────────────────────────────────────────────────

    enum ChannelStatus { Open, Frozen, Closed }

    struct Channel {
        bytes32       serviceId;
        address       consumer;
        address       provider;
        uint256       consumerBond;
        bytes32       head;
        uint256       lastActivity;
        ChannelStatus status;
    }

    mapping(bytes32 => Channel) public channels;
    uint256 private _channelNonce;

    uint256 public constant CHANNEL_TIMEOUT = 30 days;

    event ChannelOpened(bytes32 indexed channelId, bytes32 indexed serviceId, address consumer, address provider);
    event Checkpointed(bytes32 indexed channelId, bytes32 head);
    event ChannelClosed(bytes32 indexed channelId, uint256 providerPayout, uint256 consumerPayout);
    event ChannelExpired(bytes32 indexed channelId);

    function openChannel(bytes32 serviceId) external returns (bytes32 channelId) {
        Service storage s = services[serviceId];
        require(s.active);
        require(balances[msg.sender] >= s.minBond);

        balances[msg.sender] -= s.minBond;
        channelId = keccak256(abi.encodePacked(serviceId, msg.sender, s.provider, _channelNonce++));

        channels[channelId] = Channel({
            serviceId:    serviceId,
            consumer:     msg.sender,
            provider:     s.provider,
            consumerBond: s.minBond,
            head:         bytes32(0),
            lastActivity: block.timestamp,
            status:       ChannelStatus.Open
        });

        emit ChannelOpened(channelId, serviceId, msg.sender, s.provider);
    }

    // Both parties co-sign the current head to anchor it on-chain.
    // Neither party can dispute history before the latest checkpoint.
    function checkpoint(bytes32 channelId, bytes32 head, bytes calldata providerSig, bytes calldata consumerSig) external {
        Channel storage c = channels[channelId];
        require(c.status == ChannelStatus.Open);
        _verifySig(keccak256(abi.encodePacked(channelId, head)), providerSig, c.provider);
        _verifySig(keccak256(abi.encodePacked(channelId, head)), consumerSig, c.consumer);

        c.head         = head;
        c.lastActivity = block.timestamp;
        emit Checkpointed(channelId, head);
    }

    // Both parties co-sign the final state. Provider receives providerPayout
    // from the consumer bond. Consumer receives the remainder.
    function closeChannel(bytes32 channelId, bytes32 finalHead, uint256 providerPayout, bytes calldata providerSig, bytes calldata consumerSig) external {
        Channel storage c = channels[channelId];
        require(c.status == ChannelStatus.Open);
        require(providerPayout <= c.consumerBond);
        _verifySig(keccak256(abi.encodePacked(channelId, finalHead, providerPayout)), providerSig, c.provider);
        _verifySig(keccak256(abi.encodePacked(channelId, finalHead, providerPayout)), consumerSig, c.consumer);

        uint256 consumerPayout = c.consumerBond - providerPayout;
        c.status = ChannelStatus.Closed;
        c.consumerBond = 0;

        balances[c.provider] += providerPayout;
        balances[c.consumer] += consumerPayout;

        emit ChannelClosed(channelId, providerPayout, consumerPayout);
    }

    // After CHANNEL_TIMEOUT of silence, either party recovers their stake.
    // Consumer gets their bond back. Provider gets nothing — abandonment.
    function expireChannel(bytes32 channelId) external {
        Channel storage c = channels[channelId];
        require(c.status == ChannelStatus.Open);
        require(msg.sender == c.consumer || msg.sender == c.provider);
        require(block.timestamp >= c.lastActivity + CHANNEL_TIMEOUT);

        uint256 bond   = c.consumerBond;
        c.consumerBond = 0;
        c.status       = ChannelStatus.Closed;
        balances[c.consumer] += bond;

        emit ChannelExpired(channelId);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Disputes
    //
    // A dispute freezes the channel and puts both parties' stakes on the table.
    // Interactions are revealed as individual links — the contract verifies each
    // hash and emits the data for the arbitrator to evaluate.
    //
    // The arbitrator is a black box. It watches LinkRevealed events, evaluates
    // however it likes, and submits (winner, winnerAmount, arbitratorAmount).
    // Those two amounts must exactly equal the total pot. If they don't, the
    // dispute is canceled and everyone gets their money back.
    //
    // Worst-case timeline — 5 minutes:
    //   T+0:00  dispute opened
    //   T+2:00  respond window closes
    //   T+4:00  reveal window closes
    //   T+5:00  rule window closes — miss it and anyone can cancel
    // ─────────────────────────────────────────────────────────────────────────

    enum DisputeStatus { Open, Resolved }

    struct Dispute {
        bytes32       channelId;
        address       claimant;
        address       respondent;
        uint256       claimantStake;
        uint256       respondentStake;
        uint256       respondDeadline;
        uint256       revealDeadline;
        uint256       ruleDeadline;
        DisputeStatus status;
    }

    mapping(bytes32 => Dispute) public disputes;
    uint256 private _disputeNonce;

    uint256 public constant RESPOND_WINDOW = 2 minutes;
    uint256 public constant REVEAL_WINDOW  = 2 minutes;
    uint256 public constant RULE_WINDOW    = 1 minutes;

    event DisputeOpened(bytes32 indexed disputeId, bytes32 indexed channelId, address claimant);
    event DisputeResponded(bytes32 indexed disputeId, uint256 revealDeadline, uint256 ruleDeadline);
    event LinkRevealed(bytes32 indexed disputeId, address indexed revealer, bytes32 link, bytes32 message, uint64 timestamp, uint64 nonce, bytes32 prevLink);
    event Ruled(bytes32 indexed disputeId, address winner, uint256 winnerAmount, uint256 arbitratorAmount);
    event DisputeCanceled(bytes32 indexed disputeId);

    function openDispute(bytes32 channelId, uint256 stake) external returns (bytes32 disputeId) {
        Channel storage c = channels[channelId];
        require(c.status == ChannelStatus.Open);
        require(msg.sender == c.consumer || msg.sender == c.provider);
        require(balances[msg.sender] >= stake);

        balances[msg.sender] -= stake;
        c.status = ChannelStatus.Frozen;

        address respondent = msg.sender == c.consumer ? c.provider : c.consumer;
        disputeId = keccak256(abi.encodePacked(channelId, msg.sender, _disputeNonce++));

        disputes[disputeId] = Dispute({
            channelId:       channelId,
            claimant:        msg.sender,
            respondent:      respondent,
            claimantStake:   stake,
            respondentStake: 0,
            respondDeadline: block.timestamp + RESPOND_WINDOW,
            revealDeadline:  0,
            ruleDeadline:    0,
            status:          DisputeStatus.Open
        });

        emit DisputeOpened(disputeId, channelId, msg.sender);
    }

    function respondToDispute(bytes32 disputeId, uint256 stake) external {
        Dispute storage d = disputes[disputeId];
        require(d.status == DisputeStatus.Open);
        require(msg.sender == d.respondent);
        require(block.timestamp < d.respondDeadline);
        require(stake >= d.claimantStake);
        require(balances[msg.sender] >= stake);
        require(d.respondentStake == 0);

        balances[msg.sender] -= stake;
        d.respondentStake = stake;
        d.revealDeadline  = block.timestamp + REVEAL_WINDOW;
        d.ruleDeadline    = d.revealDeadline + RULE_WINDOW;

        emit DisputeResponded(disputeId, d.revealDeadline, d.ruleDeadline);
    }

    // Either party proves a link from the hash chain.
    // link = keccak256(message + serviceId + timestamp + nonce + prevLink)
    // The contract verifies the hash and emits the data. The arbitrator decides meaning.
    function revealLink(bytes32 disputeId, bytes32 link, bytes32 message, uint64 timestamp, uint64 nonce, bytes32 prevLink) external {
        Dispute storage d = disputes[disputeId];
        require(d.status == DisputeStatus.Open);
        require(d.respondentStake > 0);
        require(msg.sender == d.claimant || msg.sender == d.respondent);
        require(block.timestamp < d.revealDeadline);

        Channel storage c = channels[d.channelId];
        require(keccak256(abi.encodePacked(message, c.serviceId, timestamp, nonce, prevLink)) == link);

        emit LinkRevealed(disputeId, msg.sender, link, message, timestamp, nonce, prevLink);
    }

    // Respondent never staked. Claimant wins automatically.
    // Claimant recovers their stake plus the service bond as damages.
    // Consumer bond returned to consumer regardless of who filed.
    function claimNoResponse(bytes32 disputeId) external {
        Dispute storage d = disputes[disputeId];
        require(d.status == DisputeStatus.Open);
        require(d.respondentStake == 0);
        require(block.timestamp >= d.respondDeadline);

        d.status = DisputeStatus.Resolved;

        Channel storage c = channels[d.channelId];
        Service storage s = services[c.serviceId];

        uint256 damages = s.bond;
        s.bond          = 0;
        c.status        = ChannelStatus.Closed;

        balances[d.claimant]  += d.claimantStake + damages;
        balances[c.consumer]  += c.consumerBond;
        c.consumerBond         = 0;

        emit Ruled(disputeId, d.claimant, d.claimantStake + damages, 0);
    }

    // Arbitrator submits a ruling. winnerAmount + arbitratorAmount must equal
    // the total pot exactly. If not, the ruling is rejected and the dispute cancels.
    function rule(bytes32 disputeId, address winner, uint256 winnerAmount, uint256 arbitratorAmount) external {
        Dispute storage d = disputes[disputeId];
        require(d.status == DisputeStatus.Open);
        require(d.respondentStake > 0);
        require(winner == d.claimant || winner == d.respondent);
        require(block.timestamp < d.ruleDeadline);

        Channel storage c = channels[d.channelId];
        Service storage s = services[c.serviceId];
        require(msg.sender == s.arbitrator);

        uint256 pot = d.claimantStake + d.respondentStake + c.consumerBond;

        if (winnerAmount + arbitratorAmount != pot) {
            _cancelDispute(disputeId);
            return;
        }

        d.status       = DisputeStatus.Resolved;
        c.status       = ChannelStatus.Closed;
        c.consumerBond = 0;

        balances[winner]     += winnerAmount;
        balances[s.arbitrator] += arbitratorAmount;

        emit Ruled(disputeId, winner, winnerAmount, arbitratorAmount);
    }

    // Arbitrator missed the rule window. Dispute cancels. Channel reopens.
    function claimNoRuling(bytes32 disputeId) external {
        Dispute storage d = disputes[disputeId];
        require(d.status == DisputeStatus.Open);
        require(d.respondentStake > 0);
        require(block.timestamp >= d.ruleDeadline);
        require(msg.sender == d.claimant || msg.sender == d.respondent);

        _cancelDispute(disputeId);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Internal
    // ─────────────────────────────────────────────────────────────────────────

    // Cancel a dispute: return stakes, reopen channel.
    // Consumer stake returned first — consumer is made whole before provider.
    function _cancelDispute(bytes32 disputeId) internal {
        Dispute storage d = disputes[disputeId];
        d.status = DisputeStatus.Resolved;

        Channel storage c = channels[d.channelId];
        c.status       = ChannelStatus.Open;
        c.lastActivity = block.timestamp;

        uint256 consumerStake = d.claimant == c.consumer ? d.claimantStake : d.respondentStake;
        uint256 providerStake = d.claimant == c.provider ? d.claimantStake : d.respondentStake;

        balances[c.consumer] += consumerStake;
        balances[c.provider] += providerStake;

        emit DisputeCanceled(disputeId);
    }

    function _verifySig(bytes32 hash, bytes calldata sig, address expected) internal pure {
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", hash));
        (bytes32 r, bytes32 s, uint8 v) = _splitSig(sig);
        require(ecrecover(ethHash, v, r, s) == expected, "bad sig");
    }

    function _splitSig(bytes calldata sig) internal pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(sig.length == 65);
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────────

    // Canonical link hash. Use this off-chain to ensure both sides hash identically.
    function linkHash(bytes32 message, bytes32 slaHash, uint64 timestamp, uint64 nonce, bytes32 prevLink) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(message, slaHash, timestamp, nonce, prevLink));
    }

    constructor(address _usdc) {
        usdc = IERC20(_usdc);
    }
}
