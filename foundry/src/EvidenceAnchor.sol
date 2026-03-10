// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EvidenceAnchor {
    struct Anchor {
        string agreementId;
        bytes32 rootHash;
        bytes32 bundleHash;
        string bundleCid;
        address submitter;
        uint256 anchoredAt;
    }

    mapping(bytes32 => Anchor) private anchors;

    event EvidenceCommitted(
        string agreementId,
        bytes32 indexed rootHash,
        bytes32 indexed bundleHash,
        string bundleCid,
        address indexed submitter
    );

    function commitEvidence(
        string calldata agreementId,
        bytes32 rootHash,
        bytes32 bundleHash,
        string calldata bundleCid
    ) external {
        require(bytes(agreementId).length > 0, "agreementId required");
        require(rootHash != bytes32(0), "rootHash required");
        require(bundleHash != bytes32(0), "bundleHash required");
        require(bytes(bundleCid).length > 0, "bundleCid required");

        bytes32 key = keccak256(bytes(agreementId));
        Anchor storage current = anchors[key];
        if (current.anchoredAt != 0) {
            require(current.rootHash == rootHash, "agreement already anchored with different root");
            require(current.bundleHash == bundleHash, "agreement already anchored with different bundle");
            require(
                keccak256(bytes(current.bundleCid)) == keccak256(bytes(bundleCid)),
                "agreement already anchored with different cid"
            );
            return;
        }

        anchors[key] = Anchor({
            agreementId: agreementId,
            rootHash: rootHash,
            bundleHash: bundleHash,
            bundleCid: bundleCid,
            submitter: msg.sender,
            anchoredAt: block.timestamp
        });

        emit EvidenceCommitted(agreementId, rootHash, bundleHash, bundleCid, msg.sender);
    }

    function getAnchor(string calldata agreementId)
        external
        view
        returns (
            bytes32 rootHash,
            bytes32 bundleHash,
            string memory bundleCid,
            address submitter,
            uint256 anchoredAt
        )
    {
        Anchor storage anchor = anchors[keccak256(bytes(agreementId))];
        return (
            anchor.rootHash,
            anchor.bundleHash,
            anchor.bundleCid,
            anchor.submitter,
            anchor.anchoredAt
        );
    }
}
