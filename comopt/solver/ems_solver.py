from typing import List, Tuple, Union
import cplex

from pandas import DataFrame, MultiIndex, Series, to_timedelta, DatetimeIndex
from numpy import isnan, nanmin, nanmax
from pyomo.core import (
    ConcreteModel,
    Var,
    Set,
    RangeSet,
    Param,
    Reals,
    Binary,
    Constraint,
    Objective,
    minimize,
    TransformationFactory,
    BuildAction
)
from pyomo.gdp import Disjunct, Disjunction
from pyomo.environ import UnknownSolver, Suffix
from pyomo.core.kernel.numvalue import value
from pyomo.opt import SolverFactory

from comopt.model.utils import initialize_series

import logging
# logging.getLogger('pyomo.core').setLevel(logging.ERROR)
#
infinity = float("inf")


def device_scheduler(
    device_constraints: List[DataFrame],
    ems_constraints: DataFrame,
    commitment_quantities: List[Series],
    commitment_downwards_deviation_price: Union[List[Series], List[float]],
    commitment_upwards_deviation_price: Union[List[Series], List[float]],
) -> Tuple[List[Series], List[float]]:
    """Schedule devices given constraints on a device and EMS level, and given a list of commitments by the EMS.
    The commitments are assumed to be with regards to the flow of energy to the device (positive for consumption,
    negative for production). The solver minimises the costs of deviating from the commitments, and returns the costs
    per commitment.
    Device constraints are on a device level. Handled constraints (listed by column name):
        max: maximum stock assuming an initial stock of zero (e.g. in MWh or boxes)
        min: minimum stock assuming an initial stock of zero
        derivative max: maximum flow (e.g. in MW or boxes/h)
        derivative min: minimum flow
        derivative equals: exact amount of flow
    EMS constraints are on an EMS level. Handled constraints (listed by column name):
        derivative max: maximum flow
        derivative min: minimum flow
    Commitments are on an EMS level. Parameter explanations:
        commitment_quantities: amounts of flow specified in commitments (both previously ordered and newly requested)
            - e.g. in MW or boxes/h
        commitment_downwards_deviation_price: penalty for downwards deviations of the flow
            - e.g. in EUR/MW or EUR/(boxes/h)
            - either a single value (same value for each flow value) or a Series (different value for each flow value)
        commitment_upwards_deviation_price: penalty for upwards deviations of the flow
    All Series and DataFrames should have the same resolution.
    For now we pass in the various constraints and prices as separate variables, from which we make a MultiIndex
    DataFrame. Later we could pass in a MultiIndex DataFrame directly.
    """

    # If the EMS has no devices, don't bother
    if len(device_constraints) == 0:
        return [], [] * len(commitment_quantities)

    # Check if commitments have the same time window and resolution as the constraints
    start = device_constraints[0].index.values[0]
    resolution = to_timedelta(device_constraints[0].index.freq)
    end = device_constraints[0].index.values[-1] + resolution
    if len(commitment_quantities) != 0:
        start_c = commitment_quantities[0].index.values[0]
        resolution_c = to_timedelta(commitment_quantities[0].index.freq)
        end_c = commitment_quantities[0].index.values[-1] + resolution
        if not (start_c == start and end_c == end):
            raise Exception(
                "Not implemented for different time windows.\n(%s,%s)\n(%s,%s)"
                % (start, end, start_c, end_c)
            )
        if resolution_c != resolution:
            raise Exception(
                "Not implemented for different resolutions.\n%s\n%s"
                % (resolution, resolution_c)
            )

    # Turn prices per commitment into prices per commitment flow
    if len(commitment_downwards_deviation_price) != 0:
        if all(
            not isinstance(price, Series)
            for price in commitment_downwards_deviation_price
        ):
            commitment_downwards_deviation_price = [
                initialize_series(price, start, end, resolution)
                for price in commitment_downwards_deviation_price
            ]
    if len(commitment_upwards_deviation_price) != 0:
        if all(
            not isinstance(price, Series)
            for price in commitment_upwards_deviation_price
        ):
            commitment_upwards_deviation_price = [
                initialize_series(price, start, end, resolution)
                for price in commitment_upwards_deviation_price
            ]

    # Determine appropriate overall bounds for power and price
    min_down_price = min(min(p) for p in commitment_downwards_deviation_price)
    max_down_price = max(max(p) for p in commitment_downwards_deviation_price)
    min_up_price = min(min(p) for p in commitment_upwards_deviation_price)
    max_up_price = max(max(p) for p in commitment_upwards_deviation_price)
    overall_min_price = min(min_down_price, min_up_price)
    overall_max_price = max(max_down_price, max_up_price)
    overall_min_power = min(ems_constraints["derivative min"])
    overall_max_power = max(ems_constraints["derivative max"])

    model = ConcreteModel()

    # Add indices for devices (d), datetimes (j) and commitments (c)
    model.d = RangeSet(0, len(device_constraints) - 1, doc="Set of devices")
    model.j = RangeSet(
        0, len(device_constraints[0].index.values) - 1, doc="Set of datetimes"
    )
    model.c = RangeSet(0, len(commitment_quantities) - 1, doc="Set of commitments")

    # Add parameters
    def commitment_quantity_select(m, c, j):
        v = commitment_quantities[c].iloc[j]
        if isnan(v):  # Discount this nan commitment by setting the prices to 0
            commitment_downwards_deviation_price[c].iloc[j] = 0
            commitment_upwards_deviation_price[c].iloc[j] = 0
            return 0
        else:
            return v

    def price_down_select(m, c, j):
        return commitment_downwards_deviation_price[c].iloc[j]

    def price_up_select(m, c, j):
        return commitment_upwards_deviation_price[c].iloc[j]

    def device_max_select(m, d, j):
        v = device_constraints[d]["max"].iloc[j]
        if isnan(v):
            return infinity
        else:
            return v

    def device_min_select(m, d, j):
        v = device_constraints[d]["min"].iloc[j]
        if isnan(v):
            return -infinity
        else:
            return v

    def device_derivative_max_select(m, d, j):
        max_v = device_constraints[d]["derivative max"].iloc[j]
        equal_v = device_constraints[d]["derivative equals"].iloc[j]
        if isnan(max_v) and isnan(equal_v):
            return infinity
        else:
            return nanmin([max_v])

    def device_derivative_min_select(m, d, j):
        min_v = device_constraints[d]["derivative min"].iloc[j]
        equal_v = device_constraints[d]["derivative equals"].iloc[j]
        if isnan(min_v) and isnan(equal_v):
            return -infinity
        else:
            return nanmax([min_v])

    def device_derivative_equal_select(m, d, j):
        min_v = device_constraints[d]["derivative min"].iloc[j]
        equal_v = device_constraints[d]["derivative equals"].iloc[j]
        if isnan(equal_v):
            return 0
        else:
            return nanmax([equal_v])

    def ems_derivative_max_select(m, j):
        v = ems_constraints["derivative max"].iloc[j]
        if isnan(v):
            return infinity
        else:
            return v

    def ems_derivative_min_select(m, j):
        v = ems_constraints["derivative min"].iloc[j]
        if isnan(v):
            return -infinity
        else:
            return v

    model.commitment_quantity = Param(
        model.c, model.j, initialize=commitment_quantity_select
    )
    model.up_price = Param(model.c, model.j, initialize=price_up_select)
    model.down_price = Param(model.c, model.j, initialize=price_down_select)
    model.device_max = Param(model.d, model.j, initialize=device_max_select)
    model.device_min = Param(model.d, model.j, initialize=device_min_select)
    model.device_derivative_max = Param(
        model.d, model.j, initialize=device_derivative_max_select
    )
    model.device_derivative_min = Param(
        model.d, model.j, initialize=device_derivative_min_select
    )
    model.device_derivative_equal = Param(model.d, model.j, initialize=device_derivative_equal_select)

    model.ems_derivative_max = Param(model.j, initialize=ems_derivative_max_select)
    model.ems_derivative_min = Param(model.j, initialize=ems_derivative_min_select)

    # Add variables
    model.power = Var(
        model.d,
        model.j,
        domain=Reals,
        initialize=0,
        bounds=(overall_min_power, overall_max_power),
    )

    # Add constraints as a tuple of (lower bound, value, upper bound)
    def device_bounds(m, d, j):
        return (
            m.device_min[d, j],
            sum(m.power[d, k] for k in range(0, j + 1)),
            m.device_max[d, j],
        )

    def device_derivative_bounds(m, d, j):
        return (
            m.device_derivative_min[d, j],
            m.power[d,j] - m.device_derivative_equal[d, j] ,
            m.device_derivative_max[d, j],
        )

    def ems_derivative_bounds(m, j):
        return m.ems_derivative_min[j], sum(m.power[:, j]), m.ems_derivative_max[j]

    model.device_energy_bounds = Constraint(model.d, model.j, rule=device_bounds)
    model.device_power_bounds = Constraint(
        model.d, model.j, rule=device_derivative_bounds
    )
    model.ems_power_bounds = Constraint(model.j, rule=ems_derivative_bounds)

    # Add logical disjunction for deviations
    model.price = Var(
        model.c, model.j, initialize=0, bounds=(overall_min_price, overall_max_price)
    )

    def up_linker(b, c, d, j):
        #print("In up linker")
        m = b.model()
        ems_power_in_j = sum(m.power[d, j] for d in m.d)
        ems_power_deviation = ems_power_in_j - m.commitment_quantity[c, j]
        #try:
            #print(value(ems_power_deviation))
        #except:
            #pass
        b.linker = Constraint(expr=m.price[c, j] == m.up_price[c, j])
        b.constr = Constraint(expr=ems_power_deviation >= 0)
        b.BigM = Suffix(direction=Suffix.LOCAL)
        b.BigM[b.linker] = 10e5
        return


    def down_linker(b, c, d, j):
        #print("In down linker")
        m = b.model()
        ems_power_in_j = sum(m.power[d, j] for d in m.d)
        ems_power_deviation = ems_power_in_j - m.commitment_quantity[c, j]
        #try:
            #print(value(ems_power_deviation))
        #except:
            #pass
        b.linker = Constraint(expr=m.price[c, j] == m.down_price[c, j])
        b.constr = Constraint(expr=ems_power_deviation <= 0)
        b.BigM = Suffix(direction=Suffix.LOCAL)
        b.BigM[b.linker] = 10e5
        return

    # def zero_linker(b, c, d, j):
    #     #print("In down linker")
    #     m = b.model()
    #     ems_power_in_j = sum(m.power[d, j] for d in m.d)
    #     ems_power_deviation = ems_power_in_j - m.commitment_quantity[c, j]
    #     #try:
    #         #print(value(ems_power_deviation))
    #     #except:
    #         #pass
    #     b.linker = Constraint(expr=m.price[c, j] == 0)
    #     b.constr = Constraint(expr=ems_power_deviation == 0)
    #     #b.BigM = Suffix(direction=Suffix.LOCAL)
    #     #b.BigM[b.linker] = 10e10
    #     return

    model.up_deviation = Disjunct(model.c, model.d, model.j, rule=up_linker)
    model.down_deviation = Disjunct(model.c, model.d, model.j, rule=down_linker)
    #model.zero_deviation = Disjunct(model.c, model.d, model.j, rule=zero_linker)


    def bind_prices(m, c, d, j):
        return [model.up_deviation[c, d, j], model.down_deviation[c, d, j],
                #model.zero_deviation[c, d, j]
                ]

    model.up_or_down_deviation = Disjunction(
        model.c, model.d, model.j, rule=bind_prices, xor=True,
    )

    # Add objective
    def cost_function(m):
        costs = 0
        for j in m.j:
            for c in m.c:
                ems_power_in_j = sum(m.power[d, j] for d in m.d)
                ems_power_deviation = ems_power_in_j - m.commitment_quantity[c, j]
                costs += ems_power_deviation * m.price[c, j]
        return costs

    model.costs = Objective(rule=cost_function, sense=minimize)

    # def xfrm(m):
    #     TransformationFactory('gdp.chull').apply_to(m)
    # model.xfrm = BuildAction(rule=xfrm)

    # Transform and solve
    xfrm = TransformationFactory("gdp.bigm")
    xfrm.apply_to(model)
    solver = SolverFactory("cplex", executable="D:/CPLEX/Studio/cplex/bin/x64_win64/cplex")
    #solver.options['CPXchgprobtype'] = "CPXPROB_QP"
    #solver.options["solver"] = "CPXqpopt"
    solver.options["qpmethod"] = 1
    solver.options["optimalitytarget"] = 3

    #solver.options["acceptable_constr_viol_tol"] = 10
    #solver.options['acceptable_tol'] = 1
    #solver.options['acceptable_dual_inf_tol'] = 10
    #solver.options['acceptable_compl_inf_tol'] = 10
    results = solver.solve(model, tee=False)

    planned_costs = value(model.costs)
    planned_power_per_device = dict()
    # last_commitment = model.commitment_quantity[-1,:]
    # print(last_commitment[0,0])
    # if abs(model.power[d, j].value) > 0.1 else model.commitment_quantity[model.c[1],j]

    #TODO: Find better solution to assign Devices
    # print("SOLVER: Device power bound: {}\n".format(model.device_power_bounds.pprint()))
    for enum, d in enumerate(model.d):
        planned_device_power = [round(model.power[d, j].value,5) for j in model.j]
        #TODO: Modify logic for batteries and buffers

        if enum == 0:
            planned_power_per_device["Load"] = initialize_series(planned_device_power, start=start, end=end, resolution=resolution)
        elif enum == 1:
            planned_power_per_device["Generation"] = initialize_series(planned_device_power, start=start, end=end, resolution=resolution)
        elif enum == 2:
            planned_power_per_device["Battery"] = initialize_series(planned_device_power, start=start, end=end, resolution=resolution)
        else:
            # TODO: Buffer
            pass
        # if sum(planned_device_power) > 0:
        #     planned_power_per_device["Load"] = initialize_series(planned_device_power, start=start, end=end, resolution=resolution)
        # else:
        #     planned_power_per_device["Generation"] = initialize_series(planned_device_power, start=start, end=end, resolution=resolution)


    #model.display()
    #results.pprint()
    #model.down_deviation.pprint()
    #model.up_deviation.pprint()
    # model.power.pprint()

    # print(planned_costs)
    # input()

    # Redo the cost calculation, because before the solver actually approximated the prices.
    def redo_cost_calculation(m):
        commitments_costs = []
        for c in m.c:
            commitment_cost = 0
            for j in m.j:

                ems_power_in_j = sum(m.power[d, j] for d in m.d)
                ems_power_deviation = ems_power_in_j - m.commitment_quantity[c, j]

                if value(ems_power_deviation) >= 0:
                    commitment_cost += round(value(ems_power_deviation * m.up_price[c, j]),3)

                else:
                    commitment_cost += round(value(ems_power_deviation * m.down_price[c, j]),3)

            commitments_costs.append(commitment_cost)
        return commitments_costs
    planned_costs_per_commitment = redo_cost_calculation(model)
    print(planned_costs_per_commitment)

    return planned_power_per_device, planned_costs_per_commitment
