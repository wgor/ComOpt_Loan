import pytest
import pickle

from comopt.model import Environment


@pytest.fixture(scope="function", autouse=True)
def simulation_environment() -> Environment:
    inputs = pickle.load(open("comopt/inputs.pickle", "rb"))
    return Environment(data=inputs)
