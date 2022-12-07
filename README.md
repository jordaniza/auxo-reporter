# Auxo-Reporter

Largely derived from the existing Pie Reporter, this repository contains the scripts used to compute the rewards for veAUXO and xAUXO holders.

## Setup

Nodejs, yarn and python are required:

### Setup the python environment
```sh
python -m venv venv

# unix only
source venv/bin/activate

pip install -r requirements.txt
```

On windows use:
```sh
# windows only
source venv/lib/activate
```

### Setup the node environment
```sh
yarn
```
## Generating the Merkle Tree

```sh
yarn create-merkle-tree
```

