// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./Vault.sol";

contract JudgeRegistry {
    Vault public immutable vault;
    address public immutable deployer;

    struct Judge {
        address superior;
        uint256 fee;
        uint256 bond;            // permanent, slashable, never withdrawable
        uint8 tier;              // 1 = supreme, up to 5
        bool active;
        bool registered;
        string endpoint;
        uint256 maxResponseTime; // seconds
    }

    mapping(address => Judge) public judges;

    mapping(address => bool) public authorized;
    bool public locked;

    event JudgeRegistered(address indexed judge, address indexed superior, uint256 fee, uint8 tier);
    event JudgeDeactivated(address indexed judge);
    event JudgeSlashed(address indexed judge, uint256 amount);
    event JudgeToppedUp(address indexed judge, uint256 amount);

    constructor(address vaultAddress) {
        vault = Vault(vaultAddress);
        deployer = msg.sender;
    }

    function authorize(address contract_) external {
        require(msg.sender == deployer, "Only deployer");
        require(!locked, "Registry is locked");
        authorized[contract_] = true;
    }

    function seal() external {
        require(msg.sender == deployer, "Only deployer");
        require(!locked, "Already locked");
        locked = true;
    }

    modifier onlyAuthorized() {
        require(authorized[msg.sender], "Not authorized");
        _;
    }

    function registerJudge(address superior, uint256 fee, string calldata endpoint, uint256 maxResponseTime) external {
        require(!judges[msg.sender].registered, "Already registered");

        uint8 tier;
        uint256 bond = 0;

        if (superior == address(0)) {
            tier = 1;
        } else {
            address cursor = superior;
            uint8 depth = 0;
            while (true) {
                require(judges[cursor].registered, "Superior not registered");
                require(judges[cursor].active, "Superior not active");
                depth++;
                require(depth <= 4, "Chain too deep (max 5 tiers)");
                if (judges[cursor].superior == address(0)) {
                    break;
                }
                cursor = judges[cursor].superior;
            }
            tier = judges[superior].tier + 1;

            vault.lockBond(msg.sender, fee);
            bond = fee;
        }

        judges[msg.sender] = Judge({
            superior: superior,
            fee: fee,
            bond: bond,
            tier: tier,
            active: true,
            registered: true,
            endpoint: endpoint,
            maxResponseTime: maxResponseTime
        });

        emit JudgeRegistered(msg.sender, superior, fee, tier);
    }

    function topUpBond(uint256 amount) external {
        require(judges[msg.sender].registered, "Not registered");
        vault.lockBond(msg.sender, amount);
        judges[msg.sender].bond += amount;
        emit JudgeToppedUp(msg.sender, amount);
    }

    function canRule(address judge) external view returns (bool) {
        Judge storage j = judges[judge];
        return j.registered && j.active && j.bond >= j.fee;
    }

    function slashBond(address judge, uint256 amount) external onlyAuthorized returns (uint256 slashed) {
        Judge storage j = judges[judge];
        if (amount > j.bond) {
            amount = j.bond;
        }
        j.bond -= amount;
        emit JudgeSlashed(judge, amount);
        return amount;
    }

    function deactivateJudge() external {
        require(judges[msg.sender].registered, "Not registered");
        require(judges[msg.sender].active, "Already inactive");
        judges[msg.sender].active = false;
        emit JudgeDeactivated(msg.sender);
    }

    function chainFeeSum(address judge) external view returns (uint256) {
        uint256 total = 0;
        address cursor = judge;
        while (cursor != address(0)) {
            require(judges[cursor].registered, "Invalid judge in chain");
            total += judges[cursor].fee;
            cursor = judges[cursor].superior;
        }
        return total;
    }
}
