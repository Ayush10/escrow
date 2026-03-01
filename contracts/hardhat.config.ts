import "@nomicfoundation/hardhat-toolbox";
import { HardhatUserConfig } from "hardhat/config";

const config: HardhatUserConfig = {
  solidity: "0.8.19",
  networks: {
    "goat-testnet3": {
      url: process.env.GOAT_RPC_URL || "https://rpc.testnet3.goat.network",
      chainId: Number(process.env.GOAT_CHAIN_ID || "48816"),
      accounts: process.env.DEPLOYER_PRIVATE_KEY ? [process.env.DEPLOYER_PRIVATE_KEY] : [],
    },
  },
};

export default config;
