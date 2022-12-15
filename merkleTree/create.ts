import { StandardMerkleTree } from "@openzeppelin/merkle-tree";
import { generateInputData } from "./sample";
import * as fs from "fs";

type RecipientAddress = keyof ReturnType<
  typeof generateInputData
>["recipients"];

export function createMerkleTree(
  input: MerkleDistributorInput
): MerkleDistributor {
  // transform sample recipients to array of values in correct order for merkle tree
  const inputData = Object.entries(input.recipients).map(([address, claim]) => [
    address,
    claim.accountIndex,
    claim.windowIndex,
    claim.rewards,
  ]);

  // The order of variables here must match those in the smart contract, or the hash will be different
  // and the proof will show the leaf as invalid.
  // Importantly, this goes for order of variables inside the struct as well.
  const tree = StandardMerkleTree.of(inputData, [
    "address claimant",
    "uint256 accountIndex",
    "uint256 windowIndex",
    "tuple(uint256 amount, address token)[] rewards",
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
