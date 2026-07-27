const fs = require("fs");
const path = require("path");

require("dotenv").config({ path: path.join(__dirname, "..", "..", ".env") });

const MIN_MONTHS = 3;
const MAX_MONTHS = 6;

function validitySeconds(months) {
  const parsed = Number(months || 6);
  if (!Number.isInteger(parsed) || parsed < MIN_MONTHS || parsed > MAX_MONTHS) {
    throw new Error(`Validity must be an integer between ${MIN_MONTHS} and ${MAX_MONTHS} months`);
  }
  return parsed * 30 * 24 * 60 * 60;
}

function writeDeployment(record) {
  const dir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `flashusdt.tron_${record.network}.json`);
  fs.writeFileSync(file, `${JSON.stringify(record, null, 2)}\n`, "utf8");
  return file;
}

async function main() {
  let TronWeb;
  try {
    const tronwebModule = require("tronweb");
    TronWeb = tronwebModule.TronWeb || tronwebModule;
  } catch (error) {
    throw new Error("Install tronweb before deploying on Tron: npm install tronweb");
  }

  const fullHost = process.env.TRON_FULL_HOST || "https://api.shasta.trongrid.io";
  const privateKey = process.env.TRON_PRIVATE_KEY || process.env.PRIVATE_KEY;
  const apiKey = process.env.TRON_PRO_API_KEY || "";
  const months = Number(process.env.FLASH_VALIDITY_MONTHS || 6);

  if (!privateKey) {
    throw new Error("Set TRON_PRIVATE_KEY or PRIVATE_KEY before deploying to Tron.");
  }

  const tronWeb = new TronWeb({
    fullHost,
    privateKey,
    headers: apiKey ? { "TRON-PRO-API-KEY": apiKey } : {},
  });

  const artifactPath = path.join(__dirname, "..", "hh-artifacts", "contracts", "FlashUSDTTron.sol", "FlashUSDTTron.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  const expiry = Math.floor(Date.now() / 1000) + validitySeconds(months);

  const deployed = await tronWeb.contract().new({
    abi: artifact.abi,
    bytecode: artifact.bytecode,
    feeLimit: Number(process.env.TRON_FEE_LIMIT || 1_000_000_000),
    callValue: 0,
    parameters: ["FlashUSDT", "FUSDT", expiry],
  });

  const address = deployed.address;
  const base58Address = String(address).startsWith("T") ? address : tronWeb.address.fromHex(address);
  const hexAddress = String(address).startsWith("T") ? tronWeb.address.toHex(address) : address;
  const record = {
    contract: "FlashUSDTTron",
    network: fullHost.includes("shasta") ? "shasta" : "mainnet",
    address: base58Address,
    hexAddress,
    expiry,
    validityMonths: months,
    deployedAt: new Date().toISOString(),
  };
  const file = writeDeployment(record);

  console.log(`FlashUSDTTron deployed to ${record.network}`);
  console.log(`Address: ${base58Address}`);
  console.log(`Expiry: ${expiry}`);
  console.log(`Deployment record: ${file}`);
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
