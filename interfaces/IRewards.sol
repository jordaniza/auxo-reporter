// SPDX-License-Identifier: MIT
pragma solidity ^0.8;

interface IRewards {
    function setParticipationMerkleRoot(bytes32 newParticipationMerkleRoot)
        external;

    function participationMerkleRoot() external view returns (bytes32);

    function distributeRewards(uint256 amount) external;

    function redistribute(
        address[] calldata accounts,
        bytes32[][] calldata proofs
    ) external;

    function claim(bytes32[] calldata proof) external;
}
