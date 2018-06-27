import pandas as pd


######################### CLASSES #########################
class Agent:
    """
    Base class for a model agent.
    """

    def __init__(self, agent_id, environ):
        """ Create a new agent. """
        self.agent_id = agent_id
        self.environ = environ

    def step(self):
        """ A single step of the agent. """
        pass


######################### FUNCTIONS #########################
def data_import(filename):
    ems_ts = dict()
    ems_p = dict()
    wb = xw.Book(filename)
    MA_ts = wb.sheets["MA"].range("C3:H27").options(pd.DataFrame, header=1, index=True, expand="table").value
    MA_param = wb.sheets["MA"].range("A1:B14").options(pd.Series, header=1, index=True).value
    TA_ts = wb.sheets["TA"].range("C3:H27").options(pd.DataFrame, header=1, index=True, expand="table").value
    TA_param = wb.sheets["TA"].range("A1:B14").options(pd.Series, header=1, index=True).value
    active_EMS = ["a0"+str(int(i)) for i in wb.sheets['IO'].range("I3:I12").value if int(i) > 0]
    for a in enumerate(active_EMS):
        ems_ts[a[1]]=wb.sheets[a[1]].range("C3:Q27").options(pd.DataFrame, header=1, index=True, expand="table").value
        ems_p[a[1]]=wb.sheets[a[1]].range("A1:B14").options(pd.Series,index=True).value
    return {"active_EMS": active_EMS, "ems_ts":ems_ts, "ems_p":ems_p, "MA_ts":MA_ts,
            "MA_param":MA_param, "TA_ts":TA_ts, "TA_param":TA_param}


def data_export(file, agents, costs, run_status):
    wb = xw.Book(file)
    sht = wb.sheets[agents.agent_id]
    sht.range('C3:Q28').value = agents.ts
    sht.range('Total_Costs').value = costs
    sht.range('Status').value = run_status
    return
