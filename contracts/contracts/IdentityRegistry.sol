// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract IdentityRegistry {
    struct IdentityRecord {
        bytes32 profileHash;
        bool verified;
        bool revoked;
        uint256 updatedAt;
    }

    address public owner;
    mapping(address => IdentityRecord) public identities;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event IdentityAnchored(address indexed wallet, bytes32 indexed profileHash);
    event IdentityRevoked(address indexed wallet);

    modifier onlyOwner() {
        require(msg.sender == owner, "IdentityRegistry: caller is not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "IdentityRegistry: zero owner");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function anchorIdentity(address wallet, bytes32 profileHash) external onlyOwner {
        require(wallet != address(0), "IdentityRegistry: zero wallet");
        require(profileHash != bytes32(0), "IdentityRegistry: zero hash");

        identities[wallet] = IdentityRecord({
            profileHash: profileHash,
            verified: true,
            revoked: false,
            updatedAt: block.timestamp
        });

        emit IdentityAnchored(wallet, profileHash);
    }

    function revokeIdentity(address wallet) external onlyOwner {
        require(wallet != address(0), "IdentityRegistry: zero wallet");
        IdentityRecord storage record = identities[wallet];
        record.verified = false;
        record.revoked = true;
        record.updatedAt = block.timestamp;

        emit IdentityRevoked(wallet);
    }

    function isVerified(address wallet, bytes32 profileHash) external view returns (bool) {
        IdentityRecord memory record = identities[wallet];
        return record.verified && !record.revoked && record.profileHash == profileHash;
    }
}
