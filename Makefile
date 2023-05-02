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

# create a config file from the example
conf :; grep -v "^\s*\/\/" config/example.jsonc >> config/example.json

### TEST ###

# Run tests once
test :; python -m pytest -rfPs
test-e2e :; python -m pytest -rfPs reporter/test/scenario_testing/test_e2e.py

# run tests in watch mode
test-watch :; python -m pytest_watch reporter/test -- -rfPs

# Run tests with coverage
coverage :; python -m pytest --cov=reporter --cov-report=term-missing

### SCRIPTS ###

# create the claims database
claims :; python -m reporter.run

# Generate a merkle tree
tree :; yarn create-merkle-tree
tree-test :; yarn ts-node merkleTree/test.ts