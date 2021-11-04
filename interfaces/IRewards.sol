// SPDX-License-Identifier: MIT
pragma solidity ^0.8;

interface IRewards {
    event RewardsDistributed(address indexed by, uint256 rewardsDistributed);
    event RewardsRedistributed(uint256 amount, address indexed account);
    event RewardsWithdrawn(address indexed by, uint256 fundsWithdrawn);

    function setParticipationMerkleRoot(bytes32 newParticipationMerkleRoot)
        external;

    function withdrawableRewardsOf(address account)
        external
        view
        returns (uint256);

    function participationMerkleRoot() external view returns (bytes32);

    function distributeRewards(uint256 amount) external;

    function redistribute(
        address[] calldata accounts,
        bytes32[][] calldata proofs
    ) external;

    function pointsPerShare() external view returns (uint256);

    function claim(bytes32[] calldata proof) external;
}
