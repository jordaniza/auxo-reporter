# include .env file and export its env vars
# (-include to ignore error if it does not exist)
-include .env

### SETUP ###

# install for JS and Python
setup :; make setup-py && yarn

# Setup just the python virtual env and install dependencies
setup-py :; python -m venv venv && pip install -r requirements.txt

# format 
format :; black reporter && yarn prettier -w merkleTree

# Run mypy for python static analysis
type-check :; python -m mypy reporter

# Format and type check python files
lint :; make type-check && make format


### TEST ###

test :; python -m pytest reporter/test -rfP


### SCRIPTS ###

merkle-tree :; yarn create-merkle-tree
