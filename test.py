import numpy as np
import xlwings as xw
import pandas as pd
import sys

#a = np.array
excelfile = ("input_comOpt_24.xlsm")
wb = xw.Book(excelfile)
df = wb.sheets['a01'].range("C3:Q27").options(pd.DataFrame).value
time = wb.sheets['a01'].range("C3:D27").options(pd.Series).value

#df
type(time)
time.values
