import pandas as pd
import xlwings as xw
import copy
import pulp
from globals import *


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
