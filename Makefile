# include .env file and export its env vars
# (-include to ignore error if it does not exist)
-include .env

### SETUP ###

# Setup the pyton env
venv :; python -m venv venv 


# install for JS and Python
# run after activating the env
setup :; make setup-py && yarn 

setup-py :; pip install -r requirements.txt

# format 
format :; black reporter && yarn prettier -w merkleTree

# Run mypy for python static analysis
type-check :; python -m mypy reporter

# Format and type check python files
lint :; make type-check && make format

### TEST ###
test :; python -m pytest -rfPs

### SCRIPTS ###

# scenario testing
scenario-setup :; python -m pytest -rfPs reporter/test/scenario_testing/create_scenario.py
scenario-test :; python -m pytest -rfPs reporter/test/test_xauxo_veauxo.py
scenario :; make scenario-setup && make scenario-test


# create the claims database
claims :; python -m reporter.run all

# Generate a merkle tree
tree :; yarn create-merkle-tree
