// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "../src/Vault.sol";
import "../src/JudgeRegistry.sol";
import "../src/Court.sol";

contract Deploy is Script {
    function run() external {
        address usdc = vm.envAddress("USDC_ADDRESS");
        address charity = vm.envAddress("CHARITY_ADDRESS");

        vm.startBroadcast();

        // 1. Deploy
        Vault vault = new Vault(usdc);
        JudgeRegistry registry = new JudgeRegistry(address(vault));
        Court court = new Court(address(vault), address(registry), charity);

        // 2. Authorize
        vault.authorize(address(registry));
        vault.authorize(address(court));
        registry.authorize(address(court));

        // 3. Seal -- no more changes, ever
        vault.seal();
        registry.seal();

        vm.stopBroadcast();

        console.log("Vault:", address(vault));
        console.log("JudgeRegistry:", address(registry));
        console.log("Court:", address(court));
    }
}
