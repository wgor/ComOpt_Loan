from datetime import datetime, timedelta

from comopt.data_structures.commitments import PiecewiseConstantProfileCommitment, DeviationCostCurve

def test_get_total_costs():
    start = datetime(year=2018, month=12, day=17)
    end = start + timedelta(minutes=45)
    penalty_function = DeviationCostCurve(flow_unit_multiplier=1/4, gradient=0.01)
    commitment = PiecewiseConstantProfileCommitment(constants=[3, 6, 3], deviation_cost_curve=penalty_function, start=start, end=end, resolution=timedelta(minutes=15))
    assert commitment.get_total_costs([3, 5, 3]) == 0.0025

