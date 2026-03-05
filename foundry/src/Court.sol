// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./Vault.sol";
import "./JudgeRegistry.sol";

contract Court {
    Vault public immutable vault;
    JudgeRegistry public immutable registry;
    address public immutable charity;

    // appeal window = superior judge's maxResponseTime (computed per dispute)
    uint256 public constant ABANDON_TIMEOUT = 30 days;
    uint256 public constant COMPLETION_WINDOW = 7 days;

    enum Status { Proposed, Active, Completed, Disputed, Resolved, Canceled, CompletionRequested }

    struct Contract {
        address principal;
        address client;
        address judge;
        uint256 consideration;
        uint256 chainFeeSum;
        bytes32 termsHash;
        address proposer;
        uint256 createdAt;
        address ruling;
        Status status;
        uint256 principalLocked;
        uint256 clientLocked;
        uint256 resolvedAt;         // when ruling was made (appeal window starts)
        uint256 lastActivity;       // for abandonment timeout
        uint256 completionRequestedAt; // when principal requested completion
    }

    struct Dispute {
        address plaintiff;
        address defendant;
        address currentJudge;
        address lastSubmitter;    // who spoke last -- defendant must speak last before ruling
        uint256 filedAt;
        uint256 escalatedAt;
        bytes32 rulingHash;
    }

    mapping(uint256 => Contract) public contracts;
    mapping(uint256 => Dispute) public disputes;
    // evidence trail: disputes[id] -> array of (submitter, hash) pairs
    mapping(uint256 => bytes32[]) public evidenceHashes;
    mapping(uint256 => address[]) public evidenceSubmitters;
    uint256 public nextContractId;

    event Proposed(uint256 indexed id, address indexed principal, address indexed client, address judge, uint256 consideration);
    event Accepted(uint256 indexed id);
    event CompletionRequested(uint256 indexed id, address indexed principal);
    event Completed(uint256 indexed id);
    event Canceled(uint256 indexed id);
    event Abandoned(uint256 indexed id);
    event DisputeFiled(uint256 indexed id, address indexed plaintiff);
    event EvidenceAdded(uint256 indexed id, address indexed submitter, bytes32 evidenceHash, uint256 index);
    event Ruled(uint256 indexed id, address indexed winner, address indexed judge, bytes32 rulingHash);
    event Finalized(uint256 indexed id, address indexed winner);
    event Appealed(uint256 indexed id, address indexed appellant, address indexed newJudge);
    event TimedOut(uint256 indexed id, address indexed judge, address indexed escalatedTo);
    event SupremeTimeout(uint256 indexed id, address indexed judge);

    constructor(address vaultAddress, address registryAddress, address charityAddress) {
        vault = Vault(vaultAddress);
        registry = JudgeRegistry(registryAddress);
        charity = charityAddress;
    }

    function _touch(Contract storage c) internal {
        c.lastActivity = block.timestamp;
    }

    // appeal window = superior judge's maxResponseTime (or 0 if no superior)
    function _appealWindow(Dispute storage d) internal view returns (uint256) {
        (address superior, , , , , , , ) = registry.judges(d.currentJudge);
        if (superior == address(0)) return 0; // supreme ruled, no appeal
        (, , , , , , , uint256 maxResponseTime) = registry.judges(superior);
        return maxResponseTime;
    }

    // --- 1. Propose ---
    function propose(
        address principal,
        address client,
        address judge,
        uint256 consideration,
        bytes32 termsHash
    ) external returns (uint256) {
        require(msg.sender == principal || msg.sender == client, "Must be a party");

        (, , , , bool active, bool registered, , ) = registry.judges(judge);
        require(registered, "Judge not registered");
        require(active, "Judge not active");

        uint256 fees = registry.chainFeeSum(judge);
        uint256 lockAmount = fees + consideration;

        vault.lockBond(msg.sender, lockAmount);

        uint256 id = nextContractId++;
        contracts[id] = Contract({
            principal: principal,
            client: client,
            judge: judge,
            consideration: consideration,
            chainFeeSum: fees,
            termsHash: termsHash,
            proposer: msg.sender,
            createdAt: block.timestamp,
            ruling: address(0),
            status: Status.Proposed,
            principalLocked: msg.sender == principal ? lockAmount : 0,
            clientLocked: msg.sender == client ? lockAmount : 0,
            resolvedAt: 0,
            lastActivity: block.timestamp,
            completionRequestedAt: 0
        });

        emit Proposed(id, principal, client, judge, consideration);
        return id;
    }

    // --- 2. Accept ---
    function accept(uint256 id) external {
        Contract storage c = contracts[id];
        require(c.status == Status.Proposed, "Not proposed");

        address other = c.proposer == c.principal ? c.client : c.principal;
        require(msg.sender == other, "Not the counterparty");

        uint256 lockAmount = c.chainFeeSum + c.consideration;
        vault.lockBond(msg.sender, lockAmount);

        if (msg.sender == c.principal) {
            c.principalLocked = lockAmount;
        } else {
            c.clientLocked = lockAmount;
        }

        c.status = Status.Active;
        _touch(c);
        emit Accepted(id);
    }

    // --- 3. Cancel ---
    function cancel(uint256 id) external {
        Contract storage c = contracts[id];
        require(c.status == Status.Proposed, "Not proposed");
        require(msg.sender == c.proposer, "Only proposer can cancel");

        uint256 lockAmount = c.chainFeeSum + c.consideration;
        vault.releaseBond(c.proposer, lockAmount);

        if (msg.sender == c.principal) {
            c.principalLocked = 0;
        } else {
            c.clientLocked = 0;
        }

        c.status = Status.Canceled;
        emit Canceled(id);
    }

    // --- 4. Complete (client releases directly) ---
    function complete(uint256 id) external {
        Contract storage c = contracts[id];
        require(c.status == Status.Active || c.status == Status.CompletionRequested, "Not active");
        require(msg.sender == c.client, "Only client can release");

        _complete(c);
    }

    // --- 5. Request completion (principal asks, client has COMPLETION_WINDOW to dispute) ---
    function requestCompletion(uint256 id) external {
        Contract storage c = contracts[id];
        require(c.status == Status.Active, "Not active");
        require(msg.sender == c.principal, "Only principal");

        c.status = Status.CompletionRequested;
        c.completionRequestedAt = block.timestamp;
        _touch(c);
        emit CompletionRequested(id, msg.sender);
    }

    // --- 6. Finalize completion (anyone calls after window expires) ---
    function finalizeCompletion(uint256 id) external {
        Contract storage c = contracts[id];
        require(c.status == Status.CompletionRequested, "Not requested");
        require(block.timestamp > c.completionRequestedAt + COMPLETION_WINDOW, "Window still open");

        _complete(c);
    }

    function _complete(Contract storage c) internal {
        vault.releaseBond(c.principal, c.chainFeeSum);
        vault.releaseBond(c.client, c.chainFeeSum);
        vault.releaseBond(c.principal, c.consideration * 2);

        c.principalLocked = 0;
        c.clientLocked = 0;
        c.status = Status.Completed;
        emit Completed(c.createdAt); // use createdAt as a proxy; event indexed by id in caller
    }

    // --- 7. Dispute ---
    function dispute(uint256 id) external {
        Contract storage c = contracts[id];
        require(
            c.status == Status.Active || c.status == Status.CompletionRequested,
            "Not active"
        );
        require(msg.sender == c.principal || msg.sender == c.client, "Not a party");

        address defendant = msg.sender == c.principal ? c.client : c.principal;

        c.status = Status.Disputed;
        _touch(c);

        disputes[id] = Dispute({
            plaintiff: msg.sender,
            defendant: defendant,
            currentJudge: c.judge,
            lastSubmitter: address(0), // either side can submit first
            filedAt: block.timestamp,
            escalatedAt: block.timestamp,
            rulingHash: bytes32(0)
        });

        emit DisputeFiled(id, msg.sender);
    }

    // --- 8. Submit evidence ---
    // Either party can add evidence. Must alternate. Defendant speaks last before ruling.
    function submitEvidence(uint256 id, bytes32 evidenceHash) external {
        Contract storage c = contracts[id];
        Dispute storage d = disputes[id];
        require(c.status == Status.Disputed, "Not disputed");
        require(msg.sender == c.principal || msg.sender == c.client, "Not a party");
        require(msg.sender != d.lastSubmitter, "Wait for the other side");

        evidenceHashes[id].push(evidenceHash);
        evidenceSubmitters[id].push(msg.sender);
        d.lastSubmitter = msg.sender;
        _touch(c);

        uint256 idx = evidenceHashes[id].length - 1;
        emit EvidenceAdded(id, msg.sender, evidenceHash, idx);
    }

    // --- 9. Rule ---
    // Funds stay locked during appeal window. Use finalize() after window expires.
    function rule(uint256 id, address winner, bytes32 rulingHash) external {
        Contract storage c = contracts[id];
        Dispute storage d = disputes[id];
        require(c.status == Status.Disputed, "Not disputed");
        require(msg.sender == d.currentJudge, "Not the assigned judge");
        require(registry.canRule(msg.sender), "Judge bond insufficient");
        require(winner == c.principal || winner == c.client, "Winner must be a party");
        // defendant should speak last, but if they don't show up, judge rules on what's there
        // evidence trail is public -- judge can see who submitted what

        d.rulingHash = rulingHash;
        c.ruling = winner;
        c.resolvedAt = block.timestamp;
        c.status = Status.Resolved;
        _touch(c);
        emit Ruled(id, winner, d.currentJudge, rulingHash);
    }

    // --- 10. Finalize ruling (after appeal window, actually move the funds) ---
    function finalizeRuling(uint256 id) external {
        Contract storage c = contracts[id];
        Dispute storage d = disputes[id];
        require(c.status == Status.Resolved, "Not resolved");
        uint256 window = _appealWindow(disputes[id]);
        require(block.timestamp > c.resolvedAt + window, "Appeal window still open");

        address winner = c.ruling;
        address loser = winner == c.principal ? c.client : c.principal;

        // pay judge
        (, uint256 judgeFee, , , , , , ) = registry.judges(d.currentJudge);
        if (judgeFee > 0) {
            vault.releaseBond(d.currentJudge, judgeFee);
        }

        // winner: chain fees + both considerations
        vault.releaseBond(winner, c.chainFeeSum + c.consideration * 2);

        // loser: chain fees minus judge fee
        if (c.chainFeeSum > judgeFee) {
            vault.releaseBond(loser, c.chainFeeSum - judgeFee);
        }

        c.principalLocked = 0;
        c.clientLocked = 0;
        c.status = Status.Completed;
        emit Finalized(id, winner);
    }

    // --- 11. Appeal (must be within appeal window) ---
    function appeal(uint256 id) external {
        Contract storage c = contracts[id];
        Dispute storage d = disputes[id];
        require(c.status == Status.Resolved, "Not resolved");
        uint256 window = _appealWindow(d);
        require(window > 0, "No superior -- ruling is final");
        require(block.timestamp <= c.resolvedAt + window, "Appeal window closed");

        address loser = c.ruling == c.principal ? c.client : c.principal;
        require(msg.sender == loser, "Only loser can appeal");

        (address superior, , , , , , , ) = registry.judges(d.currentJudge);
        // window > 0 already guarantees superior exists

        (, , , , bool active, bool registered, , ) = registry.judges(superior);
        require(registered && active, "Superior not available");

        d.currentJudge = superior;
        d.escalatedAt = block.timestamp;
        d.rulingHash = bytes32(0);
        d.lastSubmitter = address(0); // either party can speak first in new round

        c.ruling = address(0);
        c.resolvedAt = 0;
        c.status = Status.Disputed;
        _touch(c);
        emit Appealed(id, msg.sender, superior);
    }

    // --- 12. Timeout ---
    function timeout(uint256 id) external {
        Contract storage c = contracts[id];
        Dispute storage d = disputes[id];
        require(c.status == Status.Disputed, "Not disputed");

        (, uint256 judgeFee, , , , , , uint256 maxResponseTime) = registry.judges(d.currentJudge);
        require(block.timestamp > d.escalatedAt + maxResponseTime, "Judge still has time");

        registry.slashBond(d.currentJudge, judgeFee);

        (address superior, , , , , , , ) = registry.judges(d.currentJudge);

        if (superior == address(0)) {
            vault.releaseBond(c.principal, c.principalLocked);
            vault.releaseBond(c.client, c.clientLocked);

            c.principalLocked = 0;
            c.clientLocked = 0;
            c.status = Status.Canceled;
            emit SupremeTimeout(id, d.currentJudge);
        } else {
            (, , , , bool active, bool registered, , ) = registry.judges(superior);
            require(registered && active, "Superior not available");

            d.currentJudge = superior;
            d.escalatedAt = block.timestamp;
            _touch(c);
            emit TimedOut(id, d.currentJudge, superior);
        }
    }

    // how many evidence submissions for a dispute
    function evidenceCount(uint256 id) external view returns (uint256) {
        return evidenceHashes[id].length;
    }

    // --- 13. Abandon ---
    // Either party can trigger if no activity for ABANDON_TIMEOUT. Funds returned.
    function abandon(uint256 id) external {
        Contract storage c = contracts[id];
        require(
            c.status == Status.Active || c.status == Status.CompletionRequested,
            "Not active"
        );
        require(block.timestamp > c.lastActivity + ABANDON_TIMEOUT, "Not abandoned yet");

        vault.releaseBond(c.principal, c.principalLocked);
        vault.releaseBond(c.client, c.clientLocked);

        c.principalLocked = 0;
        c.clientLocked = 0;
        c.status = Status.Canceled;
        emit Abandoned(id);
    }
}
