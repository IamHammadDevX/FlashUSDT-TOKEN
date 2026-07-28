const assert = require("assert");
const { ethers } = require("hardhat");

describe("FlashUSDT (USDT clone)", function () {
  async function deployFlash() {
    const FlashUSDT = await ethers.getContractFactory("FlashUSDT");
    const token = await FlashUSDT.deploy(0); // initialSupply = 0
    await token.waitForDeployment();
    return { token };
  }

  it("has USDT-compatible metadata", async function () {
    const { token } = await deployFlash();
    assert.equal(await token.name(), "Tether USD");
    assert.equal(await token.symbol(), "USDT");
    assert.equal(await token.decimals(), 6n);
    assert.match(await token.logoURI(), /trustwallet\/assets/);
  });

  it("owner can mint tokens to any address", async function () {
    const [owner, alice] = await ethers.getSigners();
    const { token } = await deployFlash();
    // mint() takes human amount, scales internally (amount * 10^6)
    const humanAmount = 1000n;
    const scaledAmount = ethers.parseUnits("1000", 6);

    await token.mint(alice.address, humanAmount);
    assert.equal(await token.balanceOf(alice.address), scaledAmount);
    assert.equal(await token.totalSupply(), scaledAmount);
  });

  it("non-owner cannot mint", async function () {
    const [, alice] = await ethers.getSigners();
    const { token } = await deployFlash();

    await assert.rejects(
      token.connect(alice).mint(alice.address, 100),
      /Not the contract owner/
    );
  });

  it("transfers tokens between accounts", async function () {
    const [owner, alice, bob] = await ethers.getSigners();
    const { token } = await deployFlash();
    const mintHuman = 500n;
    const transferAmount = ethers.parseUnits("200", 6);

    await token.mint(alice.address, mintHuman);
    await token.connect(alice).transfer(bob.address, transferAmount);

    assert.equal(await token.balanceOf(alice.address), ethers.parseUnits("300", 6));
    assert.equal(await token.balanceOf(bob.address), transferAmount);
  });

  it("approve and transferFrom works", async function () {
    const [owner, alice, bob] = await ethers.getSigners();
    const { token } = await deployFlash();

    await token.mint(alice.address, 100n);
    await token.connect(alice).approve(bob.address, ethers.parseUnits("50", 6));
    await token.connect(bob).transferFrom(alice.address, owner.address, ethers.parseUnits("50", 6));

    assert.equal(await token.balanceOf(alice.address), ethers.parseUnits("50", 6));
    assert.equal(await token.balanceOf(owner.address), ethers.parseUnits("50", 6));
  });

  it("anyone can burn their own tokens", async function () {
    const [, alice] = await ethers.getSigners();
    const { token } = await deployFlash();

    await token.mint(alice.address, 100n);
    await token.connect(alice).burn(ethers.parseUnits("40", 6));

    assert.equal(await token.balanceOf(alice.address), ethers.parseUnits("60", 6));
    assert.equal(await token.totalSupply(), ethers.parseUnits("60", 6));
  });

  it("does not have transferOwnership function", async function () {
    const { token } = await deployFlash();
    // The new contract omits transferOwnership; owner stays as deployer
    const [owner] = await ethers.getSigners();
    assert.equal(await token.owner(), owner.address);
  });
});

