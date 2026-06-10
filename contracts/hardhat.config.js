require("dotenv").config();
require("@nomicfoundation/hardhat-toolbox");

const ZKTANENBAUM_RPC_URL = process.env.ZKTANENBAUM_RPC_URL || "https://rpc-zk.tanenbaum.io";
const ZKTANENBAUM_CHAIN_ID = Number(process.env.ZKTANENBAUM_CHAIN_ID || 57057);
const IDENTITY_ANCHOR_PRIVATE_KEY = process.env.IDENTITY_ANCHOR_PRIVATE_KEY || "";

module.exports = {
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    zktanenbaum: {
      url: ZKTANENBAUM_RPC_URL,
      chainId: ZKTANENBAUM_CHAIN_ID,
      accounts: IDENTITY_ANCHOR_PRIVATE_KEY ? [IDENTITY_ANCHOR_PRIVATE_KEY] : []
    }
  }
};
