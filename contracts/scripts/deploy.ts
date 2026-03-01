import { ethers } from "hardhat";

async function main() {
  const judge = process.env.JUDGE_ADDRESS;
  const minDeposit = process.env.MIN_DEPOSIT_WEI || "1000000000000000";
  const judgeFee = process.env.JUDGE_FEE_WEI || "500000000000000";
  const identityRegistry = process.env.IDENTITY_REGISTRY || ethers.ZeroAddress;
  const reputationRegistry = process.env.REPUTATION_REGISTRY || ethers.ZeroAddress;
  const requireIdentity = (process.env.REQUIRE_IDENTITY || "false").toLowerCase() === "true";

  if (!judge) {
    throw new Error("JUDGE_ADDRESS is required");
  }

  const factory = await ethers.getContractFactory("AgentCourt");
  const contract = await factory.deploy(
    judge,
    minDeposit,
    judgeFee,
    identityRegistry,
    reputationRegistry,
    requireIdentity,
  );

  await contract.waitForDeployment();
  console.log("AgentCourt deployed:", await contract.getAddress());
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
