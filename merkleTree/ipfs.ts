/// post to the IPFS
import { Web3Storage, getFilesFromPath } from "web3.storage";

function getFileNameFromPath(path: string) {
  const pathSplit = path.split("/");
  return pathSplit[pathSplit.length - 1];
}

export async function postToIPFS(path: string) {
  const API_KEY = process.env.WEB3_STORAGE_API_KEY;
  if (!API_KEY) throw "Missing Env Var WEB3_STORAGE_API_KEY";

  const storage = new Web3Storage({ token: API_KEY });

  try {
    const pathFiles = await getFilesFromPath(path);
    const cid = await storage.put(pathFiles);
    console.log(`Success! Link to the Merkle Tree Below:`);
    console.log(`https://${cid}.ipfs.w3s.link/${getFileNameFromPath(path)}\n`);
  } catch (err) {
    console.warn("There was a problem posting to IPFS", err);
  }
}
