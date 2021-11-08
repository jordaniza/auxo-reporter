// SPDX-License-Identifier: MIT
pragma solidity ^0.8;

interface IMerkleDistributor {
    // A Window maps a Merkle root to a reward token address.
    struct Window {
        // Merkle root describing the distribution.
        bytes32 merkleRoot;
        // Currency in which reward is processed.
        address rewardToken;
        // IPFS hash of the merkle tree. Can be used to independently fetch recipient proofs and tree. Note that the canonical
        // data type for storing an IPFS hash is a multihash which is the concatenation of  <varint hash function code>
        // <varint digest size in bytes><hash function output>. We opted to store this in a string type to make it easier
        // for users to query the ipfs data without needing to reconstruct the multihash. to view the IPFS data simply
        // go to https://cloudflare-ipfs.com/ipfs/<IPFS-HASH>.
        string ipfsHash;
    }

    // Represents an account's claim for `amount` within the Merkle root located at the `windowIndex`.
    struct Claim {
        uint256 windowIndex;
        uint256 amount;
        uint256 accountIndex; // Used only for bitmap. Assumed to be unique for each claim.
        address account;
        bytes32[] merkleProof;
    }

    // Windows are mapped to arbitrary indices.
    function merkleWindows(uint256 index) external view returns(Window memory);

    function initialize() external;

    /**
     * @notice Set merkle root for the next available window index and seed allocations.
     * @notice Callable only by owner of this contract. Caller must have approved this contract to transfer
     *      `rewardsToDeposit` amount of `rewardToken` or this call will fail. Importantly, we assume that the
     *      owner of this contract correctly chooses an amount `rewardsToDeposit` that is sufficient to cover all
     *      claims within the `merkleRoot`. Otherwise, a race condition can be created. This situation can occur
     *      because we do not segregate reward balances by window, for code simplicity purposes.
     *      (If `rewardsToDeposit` is purposefully insufficient to payout all claims, then the admin must
     *      subsequently transfer in rewards or the following situation can occur).
     *      Example race situation:
     *          - Window 1 Tree: Owner sets `rewardsToDeposit=100` and insert proofs that give claimant A 50 tokens and
     *            claimant B 51 tokens. The owner has made an error by not setting the `rewardsToDeposit` correctly to 101.
     *          - Window 2 Tree: Owner sets `rewardsToDeposit=1` and insert proofs that give claimant A 1 token. The owner
     *            correctly set `rewardsToDeposit` this time.
     *          - At this point contract owns 100 + 1 = 101 tokens. Now, imagine the following sequence:
     *              (1) Claimant A claims 50 tokens for Window 1, contract now has 101 - 50 = 51 tokens.
     *              (2) Claimant B claims 51 tokens for Window 1, contract now has 51 - 51 = 0 tokens.
     *              (3) Claimant A tries to claim 1 token for Window 2 but fails because contract has 0 tokens.
     *          - In summary, the contract owner created a race for step(2) and step(3) in which the first claim would
     *            succeed and the second claim would fail, even though both claimants would expect their claims to succeed.
     * @param rewardsToDeposit amount of rewards to deposit to seed this allocation.
     * @param rewardToken ERC20 reward token.
     * @param merkleRoot merkle root describing allocation.
     * @param ipfsHash hash of IPFS object, conveniently stored for clients
     */
    function setWindow(
        uint256 rewardsToDeposit,
        address rewardToken,
        bytes32 merkleRoot,
        string memory ipfsHash
    ) external;

    /**
     * @notice Claim amount of reward tokens for account, as described by Claim input object.
     * @dev    If the `_claim`'s `amount`, `accountIndex`, and `account` do not exactly match the
     *         values stored in the merkle root for the `_claim`'s `windowIndex` this method
     *         will revert.
     * @param _claim claim object describing amount, accountIndex, account, window index, and merkle proof.
     */
    function claim(Claim memory _claim) external;
}
