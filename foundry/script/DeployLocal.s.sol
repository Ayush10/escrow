// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "../src/MockUSDC.sol";
import "../src/Vault.sol";
import "../src/JudgeRegistry.sol";
import "../src/Court.sol";
import "../src/EvidenceAnchor.sol";

contract DeployLocal is Script {
    function run() external {
        address provider = vm.envAddress("PROVIDER_ADDRESS");
        address consumer = vm.envAddress("CONSUMER_ADDRESS");
        address judge = vm.envAddress("JUDGE_ADDRESS");
        address charity = vm.envAddress("CHARITY_ADDRESS");
        string memory outputPath = vm.envOr("DEPLOY_OUTPUT_PATH", string("./deployments/split-local-deployment.json"));

        vm.startBroadcast();

        MockUSDC usdc = new MockUSDC();
        uint256 seedAmount = 1_000_000_000_000_000;
        usdc.mint(provider, seedAmount);
        usdc.mint(consumer, seedAmount);
        usdc.mint(judge, seedAmount);

        Vault vault = new Vault(address(usdc));
        JudgeRegistry registry = new JudgeRegistry(address(vault));
        Court court = new Court(address(vault), address(registry), charity);
        EvidenceAnchor evidenceAnchor = new EvidenceAnchor();

        vault.authorize(address(registry));
        vault.authorize(address(court));
        registry.authorize(address(court));

        vault.seal();
        registry.seal();

        vm.stopBroadcast();

        string memory deployment = "deployment";
        vm.serializeUint(deployment, "chainId", block.chainid);
        vm.serializeAddress(deployment, "provider", provider);
        vm.serializeAddress(deployment, "consumer", consumer);
        vm.serializeAddress(deployment, "judge", judge);
        vm.serializeAddress(deployment, "charity", charity);
        vm.serializeAddress(deployment, "mockUsdc", address(usdc));
        vm.serializeAddress(deployment, "vault", address(vault));
        vm.serializeAddress(deployment, "judgeRegistry", address(registry));
        vm.serializeAddress(deployment, "court", address(court));
        string memory json = vm.serializeAddress(deployment, "evidenceAnchor", address(evidenceAnchor));
        vm.writeJson(json, outputPath);

        console.log("MockUSDC:", address(usdc));
        console.log("Vault:", address(vault));
        console.log("JudgeRegistry:", address(registry));
        console.log("Court:", address(court));
        console.log("EvidenceAnchor:", address(evidenceAnchor));
    }
}
