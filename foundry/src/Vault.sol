// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract Vault {
    using SafeERC20 for IERC20;

    IERC20 public immutable usdc;
    address public immutable deployer;

    mapping(address => uint256) private balances;
    mapping(address => uint256) public bonds;

    mapping(address => bool) public authorized;
    bool public locked;

    event Deposited(address indexed who, uint256 amount);
    event Withdrawn(address indexed who, uint256 amount);
    event MovedToBond(address indexed who, uint256 amount);

    constructor(address usdcAddress) {
        usdc = IERC20(usdcAddress);
        deployer = msg.sender;
    }

    function authorize(address contract_) external {
        require(msg.sender == deployer, "Only deployer");
        require(!locked, "Vault is locked");
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

    // --- user functions ---

    function deposit(uint256 amount) external {
        require(amount > 0, "Amount must be > 0");
        usdc.safeTransferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
        emit Deposited(msg.sender, amount);
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        usdc.safeTransfer(msg.sender, amount);
        emit Withdrawn(msg.sender, amount);
    }

    function moveToBond(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        bonds[msg.sender] += amount;
        emit MovedToBond(msg.sender, amount);
    }

    function getBalance() external view returns (uint256) {
        return balances[msg.sender];
    }

    function getBond(address who) external view returns (uint256) {
        return bonds[who];
    }

    // --- authorized contract functions ---

    function lockBond(address who, uint256 amount) external onlyAuthorized {
        require(bonds[who] >= amount, "Insufficient bond");
        bonds[who] -= amount;
    }

    function releaseBond(address who, uint256 amount) external onlyAuthorized {
        bonds[who] += amount;
    }

    function transferBalance(address from, address to, uint256 amount) external onlyAuthorized {
        require(balances[from] >= amount, "Insufficient balance");
        balances[from] -= amount;
        balances[to] += amount;
    }

    function sendExternal(address to, uint256 amount) external onlyAuthorized {
        usdc.safeTransfer(to, amount);
    }
}
