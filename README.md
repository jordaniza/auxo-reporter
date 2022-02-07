# pie-reporter

A collection of scripts enabling analysis of PieDAO staking initiative.

## How to run

First, init a virtualenv:

```
python3.8 -m venv ./env # creates a python virtualenv
source ./env/activate
pip install -r requirements.txt
```

To build a distribution:

```
python ./reporter/run.py conf
python ./reporter/run.py build <current-epoch-folder> <previous-epoch-folder>
python ./reporter/run.py report <current-epoch-folder> <previous-epoch-folder>
```

## Reports generated explained for Dummies

```
reports/<month-year>
├── csv
     ├── distribution.csv: Rewards distributed for this epoch (including slashed)
     ├── rewards.csv: Rewards distributed including any unclaimed reward
     ├── voters.csv: Addresses that voted on the reporting epoch
     ├── non_voters.csv: Addresses that did not vote on the reporting epoch
     ├── votes.csv: Address vote history per proposal during the reporting epoch
     ├── proposals.csv: All eligible proposals considered for the reporting epoch
     └── stakers.csv: Amount of veDough staked per address
├── json
     ├── rewards.json: rewards.csv in a JSON format
     └── stakers.json: stakers.csv in a JSON format
├── claims.json: Claims for this epoch (used to generate the merkle tree)
├── epoch-conf.json: Epoch configuration
├── reporter-db.json: JSON format document-based database (used by the reporter)
└── merkle-tree.json: Final merkle tree
```

### Future improvements

- [ ] Implement a CLI to query `reporter-db`
