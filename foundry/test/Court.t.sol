// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../src/Vault.sol";
import "../src/JudgeRegistry.sol";
import "../src/Court.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockUSDC is ERC20 {
    constructor() ERC20("USD Coin", "USDC") {}
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract CourtTest is Test {
    MockUSDC usdc;
    Vault vault;
    JudgeRegistry registry;
    Court court;

    address deployer = address(this);
    address charity = address(0xC4A417);
    address alice = address(0xA11CE);
    address bob = address(0xB0B);
    address judge1 = address(0x1);
    address judge2 = address(0x2);
    address supreme = address(0x999);

    function setUp() public {
        usdc = new MockUSDC();
        vault = new Vault(address(usdc));
        registry = new JudgeRegistry(address(vault));
        court = new Court(address(vault), address(registry), charity);

        vault.authorize(address(registry));
        vault.authorize(address(court));
        registry.authorize(address(court));
        vault.seal();
        registry.seal();

        usdc.mint(alice, 10000);
        usdc.mint(bob, 10000);
        usdc.mint(judge1, 10000);
        usdc.mint(judge2, 10000);

        _depositAndBond(alice, 10000);
        _depositAndBond(bob, 10000);
        _depositAndBond(judge1, 10000);
        _depositAndBond(judge2, 10000);

        vm.prank(supreme);
        registry.registerJudge(address(0), 0, "https://supreme.example.com", 3600);

        vm.prank(judge1);
        registry.registerJudge(supreme, 10, "https://judge1.example.com", 300);

        vm.prank(judge2);
        registry.registerJudge(judge1, 5, "https://judge2.example.com", 60);
    }

    function _depositAndBond(address who, uint256 amount) internal {
        vm.startPrank(who);
        usdc.approve(address(vault), amount);
        vault.deposit(amount);
        vault.moveToBond(amount);
        vm.stopPrank();
    }

    function _activeContract() internal returns (uint256) {
        vm.prank(alice);
        uint256 id = court.propose(bob, alice, judge2, 100, keccak256("terms"));
        vm.prank(bob);
        court.accept(id);
        return id;
    }

    // helper: full dispute flow
    function _disputeAndRule(uint256 id, address winner) internal {
        vm.prank(alice);
        court.dispute(id);
        vm.prank(alice);
        court.submitEvidence(id, keccak256("alice evidence"));
        vm.prank(bob);
        court.submitEvidence(id, keccak256("bob evidence"));
        vm.prank(judge2);
        court.rule(id, winner, keccak256("ruling"));
    }

    // --- Happy path ---

    function test_propose_accept_complete() public {
        uint256 id = _activeContract();

        vm.prank(alice);
        court.complete(id);

        assertEq(vault.bonds(alice), 10000 - 100);
        assertEq(vault.bonds(bob), 10000 + 100);
    }

    // --- Cancel ---

    function test_cancel_before_accept() public {
        vm.prank(alice);
        uint256 id = court.propose(bob, alice, judge2, 100, keccak256("terms"));

        vm.prank(alice);
        court.cancel(id);

        assertEq(vault.bonds(alice), 10000);
    }

    function test_cannot_cancel_after_accept() public {
        uint256 id = _activeContract();

        vm.prank(alice);
        vm.expectRevert("Not proposed");
        court.cancel(id);
    }

    // --- Principal requests completion ---

    function test_request_completion_auto_finalizes() public {
        uint256 id = _activeContract();

        vm.prank(bob);
        court.requestCompletion(id);

        vm.warp(block.timestamp + 7 days + 1);
        court.finalizeCompletion(id);

        assertEq(vault.bonds(alice), 10000 - 100);
        assertEq(vault.bonds(bob), 10000 + 100);
    }

    function test_client_disputes_during_completion_window() public {
        uint256 id = _activeContract();

        vm.prank(bob);
        court.requestCompletion(id);

        vm.prank(alice);
        court.dispute(id);

        vm.warp(block.timestamp + 7 days + 1);
        vm.expectRevert("Not requested");
        court.finalizeCompletion(id);
    }

    function test_cannot_finalize_before_window() public {
        uint256 id = _activeContract();

        vm.prank(bob);
        court.requestCompletion(id);

        vm.expectRevert("Window still open");
        court.finalizeCompletion(id);
    }

    // --- Evidence system ---

    function test_either_party_submits_first() public {
        uint256 id = _activeContract();

        // bob (defendant-to-be) files dispute
        vm.prank(bob);
        court.dispute(id);

        // either side can submit first — bob goes first
        vm.prank(bob);
        court.submitEvidence(id, keccak256("bob first"));

        // alice responds
        vm.prank(alice);
        court.submitEvidence(id, keccak256("alice responds"));

        assertEq(court.evidenceCount(id), 2);
    }

    function test_cannot_submit_twice_in_row() public {
        uint256 id = _activeContract();

        vm.prank(alice);
        court.dispute(id);
        vm.prank(alice);
        court.submitEvidence(id, keccak256("first"));

        vm.prank(alice);
        vm.expectRevert("Wait for the other side");
        court.submitEvidence(id, keccak256("second"));
    }

    function test_judge_rules_without_defendant_evidence() public {
        uint256 id = _activeContract();

        vm.prank(alice);
        court.dispute(id);
        vm.prank(alice);
        court.submitEvidence(id, keccak256("only plaintiff"));

        // judge rules with only plaintiff evidence (defendant no-show)
        vm.prank(judge2);
        court.rule(id, bob, keccak256("default judgment"));

        vm.warp(block.timestamp + 301);
        court.finalizeRuling(id);

        assertGt(vault.bonds(bob), 10000);
    }

    // --- Dispute and rule with appeal window ---

    function test_dispute_rule_finalize() public {
        uint256 id = _activeContract();
        _disputeAndRule(id, bob);

        vm.expectRevert("Appeal window still open");
        court.finalizeRuling(id);

        // judge1 maxResponseTime = 300s (superior of judge2)
        vm.warp(block.timestamp + 301);
        court.finalizeRuling(id);

        assertGt(vault.bonds(bob), 10000);
    }

    function test_winner_cannot_dodge_appeal() public {
        uint256 id = _activeContract();
        _disputeAndRule(id, bob);

        // alice appeals within window
        vm.prank(alice);
        court.appeal(id);

        // submit evidence for new round
        vm.prank(alice);
        court.submitEvidence(id, keccak256("new evidence"));
        vm.prank(bob);
        court.submitEvidence(id, keccak256("rebuttal"));

        // judge1 (superior) rules for alice
        vm.prank(judge1);
        court.rule(id, alice, keccak256("reversed"));

        // supreme maxResponseTime = 3600s
        vm.warp(block.timestamp + 3601);
        court.finalizeRuling(id);

        assertGt(vault.bonds(alice), vault.bonds(bob));
    }

    function test_cannot_appeal_after_window() public {
        uint256 id = _activeContract();
        _disputeAndRule(id, bob);

        vm.warp(block.timestamp + 301);

        vm.prank(alice);
        vm.expectRevert("Appeal window closed");
        court.appeal(id);
    }

    // --- Timeout ---

    function test_timeout_escalates() public {
        uint256 id = _activeContract();

        vm.prank(alice);
        court.dispute(id);

        vm.warp(block.timestamp + 61);
        court.timeout(id);

        (, , address currentJudge, , , , ) = court.disputes(id);
        assertEq(currentJudge, judge1);
    }

    function test_supreme_timeout_cancels() public {
        vm.prank(alice);
        uint256 id = court.propose(bob, alice, supreme, 100, keccak256("terms"));
        vm.prank(bob);
        court.accept(id);

        vm.prank(alice);
        court.dispute(id);

        vm.warp(block.timestamp + 3601);

        uint256 aliceBefore = vault.bonds(alice);
        uint256 bobBefore = vault.bonds(bob);
        court.timeout(id);

        assertGt(vault.bonds(alice), aliceBefore);
        assertGt(vault.bonds(bob), bobBefore);
    }

    function test_timeout_slashes_judge() public {
        uint256 id = _activeContract();

        vm.prank(alice);
        court.dispute(id);

        (, , uint256 bondBefore, , , , , ) = registry.judges(judge2);
        vm.warp(block.timestamp + 61);
        court.timeout(id);
        (, , uint256 bondAfter, , , , , ) = registry.judges(judge2);

        assertLt(bondAfter, bondBefore);
    }

    // --- Abandon ---

    function test_abandon_after_timeout() public {
        uint256 id = _activeContract();

        vm.warp(block.timestamp + 30 days + 1);

        uint256 aliceBefore = vault.bonds(alice);
        uint256 bobBefore = vault.bonds(bob);

        court.abandon(id);

        assertGt(vault.bonds(alice), aliceBefore);
        assertGt(vault.bonds(bob), bobBefore);
    }

    function test_cannot_abandon_early() public {
        uint256 id = _activeContract();

        vm.expectRevert("Not abandoned yet");
        court.abandon(id);
    }

    function test_activity_resets_abandon_timer() public {
        uint256 id = _activeContract();

        vm.warp(block.timestamp + 20 days);

        vm.prank(bob);
        court.requestCompletion(id);

        vm.warp(block.timestamp + 20 days);

        vm.expectRevert("Not abandoned yet");
        court.abandon(id);
    }

    // --- Access control ---

    function test_only_counterparty_can_accept() public {
        vm.prank(alice);
        uint256 id = court.propose(bob, alice, judge2, 100, keccak256("terms"));

        vm.prank(alice);
        vm.expectRevert("Not the counterparty");
        court.accept(id);
    }

    function test_only_client_can_complete() public {
        uint256 id = _activeContract();

        vm.prank(bob);
        vm.expectRevert("Only client can release");
        court.complete(id);
    }

    function test_vault_sealed() public {
        vm.expectRevert("Vault is locked");
        vault.authorize(address(0xDEAD));
    }
}
