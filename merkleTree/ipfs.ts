/// post to the IPFS
import { Web3Storage, getFilesFromPath } from "web3.storage";

export async function postToIPFS(path: string) {
  const token = process.env.WEB3_STORAGE_API_KEY;
  if (!token) throw "Missing Env Var WEB3_STORAGE_API_KEY";

  const storage = new Web3Storage({ token });

  try {
    const pathFiles = await getFilesFromPath(path);
    const cid = await storage.put(pathFiles);
    console.log(`Success! Link to the Merkle Tree Below:`);
    console.log(`https://${cid}.ipfs.w3s.link/merkle-tree.json`);
  } catch (err) {
    console.warn("There was a problem posting to IPFS", err);
  }
}
