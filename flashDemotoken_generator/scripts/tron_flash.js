require("dotenv").config({ path: "../.env" });

const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");

function getTronWeb() {
  const tronwebModule = require("tronweb");
  const TronWeb = tronwebModule.TronWeb || tronwebModule;
  const fullHost = process.env.TRON_FULL_HOST || "https://api.shasta.trongrid.io";
  const privateKey = process.env.TRON_PRIVATE_KEY || process.env.PRIVATE_KEY;
  const apiKey = process.env.TRON_PRO_API_KEY || "";
  if (!privateKey) {
    throw new Error("Set TRON_PRIVATE_KEY in the root .env file.");
  }
  return new TronWeb({
    fullHost,
    privateKey,
    headers: apiKey ? { "TRON-PRO-API-KEY": apiKey } : {},
  });
}

function loadDeployment() {
  const explicit = process.env.FLASH_USDT_TRON_ADDRESS;
  if (explicit) {
    return { address: explicit };
  }

  const dir = path.join(__dirname, "..", "deployments");
  const fullHost = process.env.TRON_FULL_HOST || "";
  const fileName = fullHost.includes("shasta") ? "flashusdt.tron_shasta.json" : "flashusdt.tron_mainnet.json";
  const file = path.join(dir, fileName);
  if (!fs.existsSync(file)) {
    throw new Error(`Tron deployment not found. Deploy first: ${file}`);
  }
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

async function contractInstance(tronWeb) {
  const deployment = loadDeployment();
  const artifactPath = path.join(__dirname, "..", "hh-artifacts", "contracts", "FlashUSDTTron.sol", "FlashUSDTTron.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  return tronWeb.contract(artifact.abi, deployment.address);
}

async function mint(recipient, amount) {
  if (!recipient || !amount) {
    throw new Error("Usage: node scripts/tron_flash.js mint <recipient> <amount>");
  }
  const tronWeb = getTronWeb();
  if (!tronWeb.isAddress(recipient)) {
    throw new Error(`Invalid Tron recipient address: ${recipient}`);
  }
  const contract = await contractInstance(tronWeb);
  const decimals = Number(await contract.decimals().call());
  const rawAmount = ethers.parseUnits(String(amount), decimals).toString();
  const txId = await contract.mint(recipient, rawAmount).send({
    feeLimit: Number(process.env.TRON_FEE_LIMIT || 1_000_000_000),
  });
  console.log(`Mint submitted: ${txId}`);
}

async function balance(address) {
  if (!address) {
    throw new Error("Usage: node scripts/tron_flash.js balance <address>");
  }
  const tronWeb = getTronWeb();
  if (!tronWeb.isAddress(address)) {
    throw new Error(`Invalid Tron address: ${address}`);
  }
  const contract = await contractInstance(tronWeb);
  const decimals = Number(await contract.decimals().call());
  const raw = await contract.balanceOf(address).call();
  const value = Number(raw.toString()) / 10 ** decimals;
  console.log(`${value} FUSDT`);
}

async function info() {
  const tronWeb = getTronWeb();
  const deployment = loadDeployment();
  const contract = await contractInstance(tronWeb);
  const [symbol, expiry, expired] = await Promise.all([
    contract.symbol().call(),
    contract.getExpiry().call(),
    contract.isExpired().call(),
  ]);
  console.log(`Address: ${deployment.address}`);
  console.log(`Symbol: ${symbol}`);
  console.log(`Expiry: ${expiry.toString()}`);
  console.log(`Expired: ${expired}`);
}

async function main() {
  const [command, first, second] = process.argv.slice(2);
  if (command === "mint") {
    await mint(first, second);
  } else if (command === "balance") {
    await balance(first);
  } else if (command === "info") {
    await info();
  } else {
    throw new Error("Usage: node scripts/tron_flash.js <info|mint|balance> [args]");
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
