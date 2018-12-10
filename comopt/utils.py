import os
from typing import Dict
import pickle

from pandas import DataFrame, ExcelFile


class Agent:
    """ Base class for a model agent. """

    def __init__(self, name: str, environment):
        """ Create a new agent. """
        self.name = name
        self.environment = environment

    def step(self):
        """ A single step of the agent. """
        pass


def data_import(file) -> Dict[str, DataFrame]:
    xl = ExcelFile(file)
    output = dict()
    for sheet in xl.sheet_names:
        if "Flags" in sheet or "EMS" in sheet:
            output[sheet] = xl.parse(sheet_name=sheet, index_col="Parameter")
        else:
            try:
                output[sheet] = xl.parse(sheet_name=sheet, index_col="time")
            except ValueError:
                output[sheet] = xl.parse(sheet_name=sheet)
    return output


def save_env(env):
    """Save an environment as a pickle."""
    path = './results/'
    if not os.path.exists(path):
        os.makedirs(path)
    path = './results/simulation_environment_%s.pickle'
    i = 0
    while os.path.exists(path % i):
        i += 1
    with open(path % i, 'wb') as handle:
        pickle.dump(env, handle, protocol=pickle.HIGHEST_PROTOCOL)
