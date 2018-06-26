from supporters import data_import, data_export, Agent
from model import Environment, EMS, TradingAgent
from messages import Prognosis, FlexReq, FlexOffer, FlexOrder, UDIevent
#from solvers import milp_solver
from pulp import *
import random
import datetime as dt
import xlwings as xw
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pytest as pt

def test_answer():
    assert inc(3) == 5
    assert 4 == 5
    +  where 4 = inc(3)
