import os, sys

# module import resolution consistency across mypy, pytest and scripting
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
