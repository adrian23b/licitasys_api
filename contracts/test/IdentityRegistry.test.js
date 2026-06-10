const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("IdentityRegistry", function () {
  async function deployRegistry() {
    const [owner, user, other] = await ethers.getSigners();
    const IdentityRegistry = await ethers.getContractFactory("IdentityRegistry");
    const registry = await IdentityRegistry.deploy();
    await registry.waitForDeployment();
    const profileHash = ethers.keccak256(ethers.toUtf8Bytes("corporate-profile"));
    const otherHash = ethers.keccak256(ethers.toUtf8Bytes("other-profile"));
    return { registry, owner, user, other, profileHash, otherHash };
  }

  it("allows the owner to anchor and verify an identity", async function () {
    const { registry, user, profileHash } = await deployRegistry();

    await expect(registry.anchorIdentity(user.address, profileHash))
      .to.emit(registry, "IdentityAnchored")
      .withArgs(user.address, profileHash);

    expect(await registry.isVerified(user.address, profileHash)).to.equal(true);
  });

  it("rejects anchoring from non-owners", async function () {
    const { registry, user, other, profileHash } = await deployRegistry();

    await expect(
      registry.connect(other).anchorIdentity(user.address, profileHash)
    ).to.be.revertedWith("IdentityRegistry: caller is not owner");
  });

  it("does not verify a changed hash or revoked identity", async function () {
    const { registry, user, profileHash, otherHash } = await deployRegistry();

    await registry.anchorIdentity(user.address, profileHash);
    expect(await registry.isVerified(user.address, otherHash)).to.equal(false);

    await registry.revokeIdentity(user.address);
    expect(await registry.isVerified(user.address, profileHash)).to.equal(false);
  });
});
