const assert = require("assert");
const { ethers, network } = require("hardhat");

const DAY = 24 * 60 * 60;

async function latestTimestamp() {
  const block = await ethers.provider.getBlock("latest");
  return block.timestamp;
}

async function deployFlash(validityDays = 180) {
  const expiry = (await latestTimestamp()) + validityDays * DAY;
  const FlashUSDT = await ethers.getContractFactory("FlashUSDT");
  const token = await FlashUSDT.deploy("FlashUSDT", "FUSDT", expiry);
  await token.waitForDeployment();
  return { token, expiry };
}

describe("FlashUSDT", function () {
  it("mints, transfers, and tracks flash holders", async function () {
    const [owner, alice, bob] = await ethers.getSigners();
    const { token } = await deployFlash();
    const amount = ethers.parseUnits("100", 18);

    await token.mint(alice.address, amount);
    assert.equal(await token.balanceOf(alice.address), amount);
    assert.equal(await token.isFlash(alice.address), true);

    await token.connect(alice).transfer(bob.address, ethers.parseUnits("25", 18));
    assert.equal(await token.isFlash(bob.address), true);
    assert.equal(await token.owner(), owner.address);
  });

  it("burns tokens and clears flash status when balance reaches zero", async function () {
    const [, alice] = await ethers.getSigners();
    const { token } = await deployFlash();
    const amount = ethers.parseUnits("10", 18);

    await token.mint(alice.address, amount);
    await token.burn(alice.address, amount);

    assert.equal(await token.balanceOf(alice.address), 0n);
    assert.equal(await token.isFlash(alice.address), false);
  });

  it("blocks transfers after expiry", async function () {
    const [, alice, bob] = await ethers.getSigners();
    const { token } = await deployFlash(91);

    await token.mint(alice.address, ethers.parseUnits("1", 18));
    await network.provider.send("evm_increaseTime", [92 * DAY]);
    await network.provider.send("evm_mine");

    await assert.rejects(
      token.connect(alice).transfer(bob.address, ethers.parseUnits("1", 18)),
      /FlashUSDT: token is expired/
    );
  });

  it("allows owner to extend expiry only inside the 3-6 month window", async function () {
    const { token } = await deployFlash(91);
    const newExpiry = (await latestTimestamp()) + 120 * DAY;

    await token.setExpiry(newExpiry);
    assert.equal(await token.getExpiry(), BigInt(newExpiry));

    const tooFar = (await latestTimestamp()) + 181 * DAY;
    await assert.rejects(token.setExpiry(tooFar), /validity above 6 months/);
  });

  it("pauses mint and transfer paths", async function () {
    const [, alice, bob] = await ethers.getSigners();
    const { token } = await deployFlash();

    await token.mint(alice.address, ethers.parseUnits("1", 18));
    await token.pause();

    await assert.rejects(
      token.mint(bob.address, ethers.parseUnits("1", 18)),
      /EnforcedPause/
    );
    await assert.rejects(
      token.connect(alice).transfer(bob.address, ethers.parseUnits("1", 18)),
      /EnforcedPause/
    );
  });
});

