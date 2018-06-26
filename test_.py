#% load_ext autoreload
#% autoreload 2
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
import pytest


@pytest.fixture
def setup_env():
    inputs = data_import("ComOpt.xlsm")
    env = Environment(data=inputs)
    return

@setup_env
def test_step_ends():
    assert env.step() == "Step Completed"
