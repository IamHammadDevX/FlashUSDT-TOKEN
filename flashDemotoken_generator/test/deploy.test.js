const assert = require("assert");
const fs = require("fs");
const path = require("path");
const { writeDeployment } = require("../scripts/deploy");

describe("deployment helpers", function () {
  it("writes a per-network deployment record", function () {
    const record = {
      network: "hardhat_test",
      address: "0x0000000000000000000000000000000000000001",
    };
    const file = writeDeployment(record);
    const loaded = JSON.parse(fs.readFileSync(file, "utf8"));

    assert.equal(loaded.network, record.network);
    assert.equal(loaded.address, record.address);
    fs.unlinkSync(file);
    const dir = path.dirname(file);
    if (fs.existsSync(dir) && fs.readdirSync(dir).length === 0) {
      fs.rmdirSync(dir);
    }
  });
});
