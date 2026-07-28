require("dotenv").config({ path: "../.env" });

const fs = require("fs");
const https = require("https");
const path = require("path");
const { ethers } = require("ethers");

const networks = {
  sepolia: { chainId: "11155111", file: "flashusdt.sepolia.json" },
  ethereum: { chainId: "1", file: "flashusdt.ethereum.json" },
  polygon: { chainId: "137", file: "flashusdt.polygon.json" },
  bsc: { chainId: "56", file: "flashusdt.bsc.json" },
};

function loadJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function findBuildInfo() {
  const dir = path.join(__dirname, "..", "hh-artifacts", "build-info");
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith(".json")) {
      continue;
    }
    const fullPath = path.join(dir, file);
    const buildInfo = loadJson(fullPath);
    if (buildInfo.output?.contracts?.["contracts/FlashUSDT.sol"]?.FlashUSDT) {
      return buildInfo;
    }
  }
  throw new Error("Build info for FlashUSDT not found. Run npx hardhat compile first.");
}

function postForm(chainId, form) {
  const body = new URLSearchParams(form).toString();
  const options = {
    hostname: "api.etherscan.io",
    path: `/v2/api?chainid=${encodeURIComponent(chainId)}`,
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "Content-Length": Buffer.byteLength(body),
    },
  };

  return new Promise((resolve, reject) => {
    const request = https.request(options, (response) => {
      let data = "";
      response.on("data", (chunk) => {
        data += chunk;
      });
      response.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch (error) {
          reject(new Error(`Invalid Etherscan response: ${data}`));
        }
      });
    });
    request.on("error", reject);
    request.write(body);
    request.end();
  });
}

async function checkStatus(chainId, apiKey, guid) {
  const params = new URLSearchParams({
    chainid: chainId,
    module: "contract",
    action: "checkverifystatus",
    guid,
    apikey: apiKey,
  });
  const url = `https://api.etherscan.io/v2/api?${params}`;
  const response = await fetch(url);
  return response.json();
}

async function main() {
  const networkName = process.argv[2] || "sepolia";
  const network = networks[networkName];
  if (!network) {
    throw new Error(`Unsupported network: ${networkName}`);
  }

  const apiKey = process.env.ETHERSCAN_API_KEY;
  if (!apiKey) {
    throw new Error("Set ETHERSCAN_API_KEY in the root .env file.");
  }

  const deployment = loadJson(path.join(__dirname, "..", "deployments", network.file));
  const buildInfo = findBuildInfo();
  const constructorArguments = ""; // FlashUSDT (USDT clone) has no constructor params

  const result = await postForm(network.chainId, {
    module: "contract",
    action: "verifysourcecode",
    apikey: apiKey,
    contractaddress: deployment.address,
    sourceCode: JSON.stringify(buildInfo.input),
    codeformat: "solidity-standard-json-input",
    contractname: "contracts/FlashUSDT.sol:FlashUSDT",
    compilerversion: `v${buildInfo.solcLongVersion}`,
    optimizationUsed: "1",
    runs: "200",
    constructorArguements: constructorArguments,
    evmversion: "paris",
    licenseType: "3",
  });

  console.log(result.message);
  console.log(result.result);

  if (result.status !== "1") {
    if (String(result.result).toLowerCase().includes("already verified")) {
      return;
    }
    process.exitCode = 1;
    return;
  }

  for (let attempt = 0; attempt < 12; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 5000));
    const status = await checkStatus(network.chainId, apiKey, result.result);
    console.log(status.result);
    if (status.status === "1" || String(status.result).toLowerCase().includes("already verified")) {
      return;
    }
    if (!String(status.result).toLowerCase().includes("pending")) {
      process.exitCode = 1;
      return;
    }
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
