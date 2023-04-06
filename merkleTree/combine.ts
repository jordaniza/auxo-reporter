import { readFile, writeFile } from "fs/promises";
import { treePath } from "./utils";

// Returns the MerkleDistributor for the given epoch and token.
// The MerkleDistributor is read from the file system.
async function readTree(epoch: string, token: AuxoTokenSymbol): Promise<MerkleDistributor> {
  const path = treePath(token, epoch);
  const file = await readFile(path, { encoding: "utf8" });
  return JSON.parse(file) as MerkleDistributor;
}

/// read both token trees from the epoch folder
const treesByMonth = async (epoch: string): Promise<MerkleTreesByMonth> => {
  const [ARV, PRV] = await Promise.all([readTree(epoch, "ARV"), readTree(epoch, "PRV")]);
  return {
    [epoch]: {
      ARV,
      PRV,
    },
  };
};

// treesByUser creates a lookup table from user address to a tree of trees
// of recipients. The first level of the tree corresponds to tokens, the
// second level corresponds to months, and the third level corresponds to
// recipients.
const treesByUser = (trees: MerkleTreesByMonth): MerkleTreesByUser => {
  const treesByUser = {} as MerkleTreesByUser;
  // save the month
  for (const [month, treesByToken] of Object.entries(trees)) {
    // save the token
    for (const [token, tree] of Object.entries(treesByToken) as [AuxoTokenSymbol, MerkleDistributor][]) {
      // save the user
      for (const userAddress of Object.keys(tree.recipients)) {
        // create the user entry if it doesn't exist
        if (!treesByUser[userAddress]) {
          treesByUser[userAddress] = {} as any;
        }
        // create the token entry if it doesn't exist
        if (!treesByUser[userAddress][token]) {
          treesByUser[userAddress][token] = {};
        }
        // grab the user data
        const userTree = tree.recipients[userAddress] as MRecipientData;
        if (userTree) {
          // create the final entry
          treesByUser[userAddress][token][month] = userTree;
        }
      }
    }
  }
  return treesByUser;
};

/**
 * This function combines the trees by month and trees by user functions. It takes the epoch
 * as an argument and returns the trees by user data.
 * @param epoch will correspond to the folder with existing trees
 */
export const combineTrees = async (epoch: string): Promise<MerkleTreesByUser> => {
  const tbm = await treesByMonth(epoch);
  const tbu = treesByUser(tbm);
  await writeFile(`reports/${epoch}/combined-trees.json`, JSON.stringify(tbu, null, 4));
  return tbu;
};
