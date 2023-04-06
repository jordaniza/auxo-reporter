import { readFile, writeFile } from "fs/promises";
import { treePath } from "./utils";

// Returns the MerkleDistributor for the given epoch and token.
// The MerkleDistributor is read from the file system.
async function readTree(epoch: string, token: AuxoTokenSymbol): Promise<MerkleDistributor> {
  const path = treePath(token, epoch);
  const file = await readFile(path, { encoding: "utf8" });
  return JSON.parse(file) as MerkleDistributor;
}

/// read both new token trees from the epoch folder
const treesByMonth = async (epoch: string): Promise<MerkleTreesByMonth> => {
  const [ARV, PRV] = await Promise.all([readTree(epoch, "ARV"), readTree(epoch, "PRV")]);
  return {
    [epoch]: {
      ARV,
      PRV,
    },
  };
};

const latestTree = async (): Promise<MerkleTreesByUser> => {
  try {
    return JSON.parse(
      await readFile("reports/latest/merkle-tree-combined.json", { encoding: "utf8" })
    ) as MerkleTreesByUser;
  } catch {
    return {};
  }
};

// treesByUser creates a lookup table from user address to a tree of trees
// of recipients. The first level of the tree corresponds to tokens, the
// second level corresponds to months, and the third level corresponds to recipients.
// adds it to the current latest tree
const treesByUser = (trees: MerkleTreesByMonth, latest: MerkleTreesByUser): MerkleTreesByUser => {
  // save the month
  for (const [month, treesByToken] of Object.entries(trees)) {
    // save the token
    for (const [token, tree] of Object.entries(treesByToken) as [AuxoTokenSymbol, MerkleDistributor][]) {
      // save the user
      for (const userAddress of Object.keys(tree.recipients)) {
        // create the user entry if it doesn't exist
        if (!latest[userAddress]) {
          latest[userAddress] = {} as any;
        }
        // create the token entry if it doesn't exist
        if (!latest[userAddress][token]) {
          latest[userAddress][token] = {};
        }
        // grab the user data
        const userTree = tree.recipients[userAddress] as MRecipientData;
        if (userTree) {
          // create the final entry
          latest[userAddress][token][month] = userTree;
        }
      }
    }
  }
  return latest;
};

/**
 * This function combines the trees by month and trees by user functions. It takes the epoch
 * as an argument and returns the trees by user data.
 * @param epoch will correspond to the folder with existing trees
 */
export const combineTrees = async (epoch: string): Promise<MerkleTreesByUser> => {
  const [tbm, latest] = await Promise.all([treesByMonth(epoch), latestTree()]);
  const tbu = treesByUser(tbm, latest);
  await writeFile(`reports/${epoch}/combined-trees.json`, JSON.stringify(tbu, null, 4));
  return tbu;
};
