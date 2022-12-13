import { StandardMerkleTree } from "@openzeppelin/merkle-tree";
import { generateInputData } from "./sample";
import * as fs from "fs";

type RecipientAddress = keyof ReturnType<
  typeof generateInputData
>["recipients"];

export function createMerkleTree(
  input: MerkleDistributorInput,
  printSummary = true
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
        [recipient]: input.recipients[recipient],
        proof: tree.getProof(node),
      };
      return { ...prev, ...recipientWithProof };
    },
    {}
  );

  // print a value in the console if you want to test in a contract
  if (printSummary) printTreeSummary(tree);

  // finally add the root
  return {
    ...input,
    root: tree.root,
    recipients: merkleRecipients,
  };
}

/// pretty prints the merkle tree
function printFullTree(): void {
  const tree = createMerkleTree(generateInputData(0));
  console.log(JSON.stringify(tree, null, 4));
}

// summarize the merkle tree
function printTreeSummary(
  tree: StandardMerkleTree<(string | number | Reward[])[]>,
  address = "0x00C67d9D6D3D13b42a87424E145826c467CcCd84"
): void {
  console.log("Merkle Root:", tree.root);
  for (const [i, v] of tree.entries()) {
    if (v[0] === address) {
      const proof = tree.getProof(i);
      console.log("Value:", v);
      console.log("Proof:", proof);
    }
  }
}

[0, 1].forEach((idx) =>
  fs.writeFileSync(
    `merkleTree/examples/merkle-tree-${idx}.json`,
    JSON.stringify(createMerkleTree(generateInputData(0)), null, 4)
  )
);