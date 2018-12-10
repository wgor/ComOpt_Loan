from typing import Dict

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
