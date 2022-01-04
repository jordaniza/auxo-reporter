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

Reports generated explained for Dummies
**address.csv**: All voting addresses
**proposals.csv**: All eligible proposals considered for the reporting month
**slice_amounts.csv**: Slice amounts entitled for each address for the current month's treasury distribution depending on their voting weight
**slice_amounts_after_unclaimed.csv**: every eligible and non eligible addresses and their accrued rewards. Use for the notarization but delete the not eligible addressess to leave only those eligible during the reporting month.
**stakers.csv**: Amount of veDough staked per address
**unclaimed.csv**: amount of unclaimed rewards per address
**voted.csv**: addresses that voted on the reporting month

### Future improvements

- [ ] Implement a sqlite database for reports
