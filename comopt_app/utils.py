import pandas as pd
import xlwings as xw
import copy

class Agent:
    """ Base class for a model agent. """
    def __init__(self, agent_id, environ):
        """ Create a new agent. """
        self.agent_id = agent_id
        self.environ = environ

    def step(self):
        """ A single step of the agent. """
        pass

######################### FUNCTIONS #########################
def data_import(file):
    xl = pd.ExcelFile(file)
    output = dict()
    for sheet in xl.sheet_names:
        if "Flags" in sheet:
            output[sheet] = xl.parse(sheet_name=sheet, index_col="Parameter")
        elif "EMS" in sheet:
            output[sheet] = xl.parse(sheet_name=sheet, index_col="Parameter")
        else:
            output[sheet] = xl.parse(sheet_name=sheet, index_col="time")
    return output
