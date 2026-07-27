const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const networkToFile = {
  sepolia: "flashusdt.sepolia.json",
  ethereum: "flashusdt.ethereum.json",
  polygon: "flashusdt.polygon.json",
  polygon_amoy: "flashusdt.polygon_amoy.json",
  bsc: "flashusdt.bsc.json",
  bsc_testnet: "flashusdt.bsc_testnet.json",
};

function loadDeployment(network) {
  const fileName = networkToFile[network];
  if (!fileName) {
    throw new Error(`Unsupported verification network: ${network}`);
  }
  const file = path.join(__dirname, "..", "deployments", fileName);
  if (!fs.existsSync(file)) {
    throw new Error(`Deployment file not found: ${file}`);
  }
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function main() {
  const network = process.argv[2] || "sepolia";
  const deployment = loadDeployment(network);
  const args = [
    "hardhat",
    "verify",
    "--network",
    network,
    "--contract",
    "contracts/FlashUSDT.sol:FlashUSDT",
    deployment.address,
    "FlashUSDT",
    "FUSDT",
    String(deployment.expiry),
  ];

  const command = process.platform === "win32" ? "npx.cmd" : "npx";
  execFileSync(command, args, { stdio: "inherit", shell: process.platform === "win32" });
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
