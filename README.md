# pie-reporter

A collection of scripts enabling analysis of PieDAO staking initiative.

## Folder structure overview

```
pie-reporter: a collection of scripts enabling analysis of PieDAO staking initiative
├── interfaces: helpful interfaces to interact with pie-dao contracts via brownie
├── reports: contains reports (atm only for the staking initiative)
│   ├── airdrops: airdrops reports (merkle tree, amounts...)
│   ├── epochs: staking rewards epochs (merkle tree, amounts, )
│   └── staking: staking reports (csv files, useful for data analysis & extraction)
└── scripts: the actual scripts
    ├── check-slice-redeem.py: script used to simulate the claim for all the stakers
    ├── CreateClaims.ts: used to generate merkle tree and claims
    ├── edough-compounding.py: used to generate and post transactions 
    ├── helpers.py: utility methods (mostly json/csv io)
    └── reporter.py: the reporter, generates all the staking reports and needed data
```

## How to run

First, install `brownie-eth`:

```
python3.7 -m venv ~/brownie_venv # creates a python virtualenv
source ~/brownie_venv/bin/activate
pip install eth-brownie (see https://eth-brownie.readthedocs.io/en/stable/install.html)
```

To run the `reporter`: 

```
brownie run reporter report
```

### Future improvements

- [ ] Implement a sqlite database for reports