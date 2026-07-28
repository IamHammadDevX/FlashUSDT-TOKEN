const fs = require("fs");
const path = require("path");

function explorerUrl(network, address) {
  const explorers = {
    ethereum: `https://etherscan.io/address/${address}`,
    sepolia: `https://sepolia.etherscan.io/address/${address}`,
    polygon: `https://polygonscan.com/address/${address}`,
    polygon_amoy: `https://www.oklink.com/amoy/address/${address}`,
    bsc: `https://bscscan.com/address/${address}`,
    bsc_testnet: `https://testnet.bscscan.com/address/${address}`,
    hardhat: "(local network)",
  };
  return explorers[network] || "(unknown explorer)";
}

function writeDeployment(record) {
  const dir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `flashusdt.${record.network}.json`);
  fs.writeFileSync(file, `${JSON.stringify(record, null, 2)}\n`, "utf8");
  return file;
}

async function main(hre = require("hardhat"), args = {}) {
  const { ethers } = hre;
  const [deployer] = await ethers.getSigners();
  if (!deployer) {
    throw new Error("No deployer account configured. Set PRIVATE_KEY in the root .env file.");
  }

  const network = hre.network.name;

  const FlashUSDT = await ethers.getContractFactory("FlashUSDT");
  const contract = await FlashUSDT.deploy(0); // initialSupply = 0, mint via owner later
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  const record = {
    contract: "FlashUSDT",
    network,
    chainId: hre.network.config.chainId || 31337,
    address,
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
    explorer: explorerUrl(network, address),
  };
  const file = writeDeployment(record);

  console.log(`FlashUSDT deployed on ${network}`);
  console.log(`Address: ${address}`);
  console.log(`Explorer: ${record.explorer}`);
  console.log(`Deployment record: ${file}`);

  return record;
}

module.exports = { main, writeDeployment };

if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
