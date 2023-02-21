import { StandardMerkleTree } from "@openzeppelin/merkle-tree";

type RecipientAddress = keyof RecipientData;

export function createMerkleTree(
  input: MerkleDistributorInput
): MerkleDistributor {
  // transform sample recipients to array of values in correct order for merkle tree
  const inputData = Object.entries(input.recipients).map(([address, claim]) => [
    address,
    claim.accountIndex,
    claim.windowIndex,
    claim.rewards,
    claim.token,
  ]);

  // The order of variables here must match those in the smart contract, or the hash will be different
  // and the proof will show the leaf as invalid.
  // Importantly, this goes for order of variables inside the struct as well.
  const tree = StandardMerkleTree.of(inputData, [
    "address claimant",
    "uint256 accountIndex",
    "uint256 windowIndex",
    "uint256 rewards",
    "address token",
  ]);

  // add proofs to each recipient
  const merkleRecipients = Array.from(tree.entries()).reduce(
    (prev, [node, value]) => {
      const recipient = value[0] as RecipientAddress;
      const recipientWithProof = {
        [recipient]: {
          ...input.recipients[recipient],
          proof: tree.getProof(node),
        },
      };
      return { ...prev, ...recipientWithProof };
    },
    {}
  );
  // finally add the root
  return {
    ...input,
    root: tree.root,
    recipients: merkleRecipients,
  };
}
