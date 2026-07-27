require("dotenv").config({ path: "../.env" });
require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-verify");

const { task } = require("hardhat/config");

const PRIVATE_KEY = process.env.PRIVATE_KEY || "";
const INFURA_ID = process.env.INFURA_PROJECT_ID || "";

function accounts() {
  return PRIVATE_KEY ? [PRIVATE_KEY] : [];
}

task("deploy-flash", "Deploy FlashUSDT and write a deployment JSON record")
  .addOptionalParam("months", "Validity in months, from 3 to 6", "6")
  .setAction(async (taskArgs, hre) => {
    const { main } = require("./scripts/deploy");
    return main(hre, taskArgs);
  });

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  paths: {
    artifacts: "./hh-artifacts",
    cache: "./hh-cache",
  },
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    hardhat: {
      chainId: 31337,
    },
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || (INFURA_ID ? `https://sepolia.infura.io/v3/${INFURA_ID}` : "https://ethereum-sepolia.publicnode.com"),
      accounts: accounts(),
      chainId: 11155111,
    },
    ethereum: {
      url: process.env.ETHEREUM_RPC_URL || (INFURA_ID ? `https://mainnet.infura.io/v3/${INFURA_ID}` : "https://eth.llamarpc.com"),
      accounts: accounts(),
      chainId: 1,
    },
    polygon: {
      url: process.env.POLYGON_RPC_URL || "https://polygon-rpc.com",
      accounts: accounts(),
      chainId: 137,
    },
    polygon_amoy: {
      url: process.env.POLYGON_AMOY_RPC_URL || "https://rpc-amoy.polygon.technology",
      accounts: accounts(),
      chainId: 80002,
    },
    bsc: {
      url: process.env.BSC_RPC_URL || "https://bsc-dataseed.binance.org",
      accounts: accounts(),
      chainId: 56,
    },
    bsc_testnet: {
      url: process.env.BSC_TESTNET_RPC_URL || "https://data-seed-prebsc-1-s1.binance.org:8545",
      accounts: accounts(),
      chainId: 97,
    },
  },
  etherscan: {
    apiKey: {
      mainnet: process.env.ETHERSCAN_API_KEY || "",
      sepolia: process.env.ETHERSCAN_API_KEY || "",
      polygon: process.env.POLYGONSCAN_API_KEY || "",
      polygonAmoy: process.env.POLYGONSCAN_API_KEY || "",
      bsc: process.env.BSCSCAN_API_KEY || "",
      bscTestnet: process.env.BSCSCAN_API_KEY || "",
    },
  },
};
