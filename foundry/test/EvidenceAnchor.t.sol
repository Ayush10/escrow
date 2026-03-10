// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../src/EvidenceAnchor.sol";

contract EvidenceAnchorTest is Test {
    EvidenceAnchor anchor;

    function setUp() public {
        anchor = new EvidenceAnchor();
    }

    function test_commit_and_get_anchor() public {
        anchor.commitEvidence(
            "agreement-1",
            keccak256("root"),
            keccak256("bundle"),
            "ipfs://bafy-test-bundle"
        );

        (bytes32 rootHash, bytes32 bundleHash, string memory bundleCid, address submitter, uint256 anchoredAt) =
            anchor.getAnchor("agreement-1");

        assertEq(rootHash, keccak256("root"));
        assertEq(bundleHash, keccak256("bundle"));
        assertEq(bundleCid, "ipfs://bafy-test-bundle");
        assertEq(submitter, address(this));
        assertGt(anchoredAt, 0);
    }

    function test_idempotent_same_anchor() public {
        anchor.commitEvidence(
            "agreement-1",
            keccak256("root"),
            keccak256("bundle"),
            "ipfs://bafy-test-bundle"
        );
        anchor.commitEvidence(
            "agreement-1",
            keccak256("root"),
            keccak256("bundle"),
            "ipfs://bafy-test-bundle"
        );
    }

    function test_rejects_conflicting_root() public {
        anchor.commitEvidence(
            "agreement-1",
            keccak256("root"),
            keccak256("bundle"),
            "ipfs://bafy-test-bundle"
        );

        vm.expectRevert("agreement already anchored with different root");
        anchor.commitEvidence(
            "agreement-1",
            keccak256("other-root"),
            keccak256("bundle"),
            "ipfs://bafy-test-bundle"
        );
    }
}
