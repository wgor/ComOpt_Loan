from pyomo.environ import *
from pyomo.core.base.block import *
from pyomo.opt import SolverFactory
from pyomo.core import (
    Var,
    Set,
    Param,
    NonNegativeReals,
    Binary,
    Constraint,
    Objective,
    minimize,
    ConcreteModel,
)
import pandas as pd

from pandas import DataFrame
from datetime import datetime, timedelta

from comopt.solver.utils import (
    preprocess_solver_data,
    plot_solver_results,
    create_solver_results_dataframes,
)
import os


def preprocess_solver_data(data: pd.DataFrame):
    # Create multiindex dataframe with indizes "time","ems","devices".
    data.set_index(["time", "ems", "devices"], inplace=True)
    data.sort_index(inplace=True)
    data.fillna(0, inplace=True)
    idx = pd.IndexSlice

    # Check for activated devices.
    activated_device_names = (
        data.index.get_level_values(level="devices").unique().tolist()
    )
    activated_device_types = dict()
    for device in activated_device_names:
        if "_Load_NON" in device:
            activated_device_types["Loads_NON"] = "Active"
        elif "_Load_SHIFT" in device:
            activated_device_types["Loads_SHIFT"] = "Active"
        elif "_Storage" in device:
            activated_device_types["Storages"] = "Active"
        elif "_Buffer" in device:
            activated_device_types["Buffers"] = "Active"
        elif "_Gen_NON" in device:
            activated_device_types["Gen_NON"] = "Active"
        elif "_Gen_SHIFT" in device:
            activated_device_types["Gen_SHIFT"] = "Active"
        else:
            print("Wrong input name: \n")
            print(device)

    # If buffers are activated, create buffer data.
    if activated_device_types["Buffers"] == "Active":
        buffers_list = [
            device for device in activated_device_names if "_Buffer" in device
        ]
        buffer_windows_timeperiods = dict()
        buffer_windows_list = []
        buffer_data = {
            buffer: data.loc[idx[:, :, buffer], "integral_equal"]
            for buffer in buffers_list
        }
        buffer_shift = {buffer: [] for buffer in buffers_list}

        for key, val in buffer_data.items():
            buffer_shift[key] = np.where(buffer_data[key] != 0)[0].tolist()

        for key, val in buffer_shift.items():
            # shift array values one index up
            buffer_shift[key] = [x + 1 for x in val]
            # create consecutive shifting windows
            buffer_shift[key] = [
                list(group) for group in mit.consecutive_groups(buffer_shift[key])
            ]

        for key, val in buffer_shift.items():
            # Sets for buffer_windows and buffer_windows_timeperiods
            cnt = 1
            for x in val:
                window_name = "_window_" + str(cnt)
                cnt += 1
                buffer_windows_timeperiods[key + window_name] = x
                buffer_windows_list.append(key + window_name)
    else:
        buffer_windows_timeperiods = dict()
        buffer_windows_list = []
    return (
        activated_device_names,
        activated_device_types,
        buffer_windows_list,
        buffer_windows_timeperiods,
    )


def create_solver_results_dataframes(model: ConcreteModel):
    for ems in model.ems:
        for storage in model.storages:
            model.storages_SOC[
                model.timeperiods[-1], ems, storage
            ].value = model.storages_SOC_end[ems, storage]

    time_ems_index = model.timeperiods * model.ems

    ems_output = []
    for timeperiod in model.timeperiods:
        for ems in model.ems:
            var_output = {
                "time": timeperiod,
                "ems": ems,
                "Net_Demand": (round(value(model.net_demand[timeperiod, ems]), 1)),
                "Net_Generation": (
                    round(value(model.net_generation[timeperiod, ems]) * -1, 1)
                ),
                "Active_Net_Generation": (
                    round(value(model.net_generation_active[timeperiod, ems]), 1)
                ),
                "Active_Net_Demand": (
                    round(value(model.net_demand_active[timeperiod, ems]), 1)
                ),
            }
            ems_output.append(var_output)
    ems_output

    device_output = []
    for timeperiod, ems in time_ems_index:
        for device in model.nonshiftable_loads:
            nonshiftable_loads_output = {
                "time": timeperiod,
                "ems": ems,
                "device": device,
                "Demand_NON": (
                    round(value(model.demand_nonshiftables[timeperiod, ems, device]), 1)
                ),
            }
            device_output.append(nonshiftable_loads_output)

        for device in model.nonshiftable_generators:
            nonshiftable_generators_output = {
                "time": timeperiod,
                "ems": ems,
                "device": device,
                "Generation_NON": (
                    round(
                        value(model.generation_nonshiftables[timeperiod, ems, device])
                        * -1,
                        1,
                    )
                ),
            }
            device_output.append(nonshiftable_generators_output)

        for device in model.storages:
            storages_output = {
                "time": timeperiod,
                "ems": ems,
                "device": device,
                "Storage_Charging": (
                    round(value(model.storages_charging[timeperiod, ems, device]), 1)
                ),
                "Storage_Discharging": (
                    round(
                        value(model.storages_discharging[timeperiod, ems, device]) * -1,
                        1,
                    )
                ),
                "Storage_SOC": (
                    round(value(model.storages_SOC[timeperiod, ems, device]), 1)
                ),
                "Storage_Active_Charging": (
                    round(
                        value(model.storages_charging_active[timeperiod, ems, device]),
                        1,
                    )
                ),
                "Storage_Active_Discharging": (
                    round(
                        value(
                            model.storages_discharging_active[timeperiod, ems, device]
                        ),
                        1,
                    )
                ),
            }
            device_output.append(storages_output)

        for device in model.buffers:
            buffers_output = {
                "time": timeperiod,
                "ems": ems,
                "device": device,
                "Buffer_Charging": (
                    round(value(model.buffers_charging[timeperiod, ems, device]), 1)
                ),
            }
            device_output.append(buffers_output)

    device_output_df = pd.DataFrame(device_output).sort_values(
        ["time", "ems", "device"]
    )
    device_output_df.set_index(["time", "ems", "device"], inplace=True)

    ems_output_df = pd.DataFrame.from_records(ems_output)
    ems_output_df.set_index(["time", "ems"], inplace=True)

    return device_output_df, ems_output_df


def plot_solver_results(device_output_df: pd.DataFrame, ems_output_df: pd.DataFrame):
    # required to use plotly offline (no account required).
    cf.go_offline()
    # graphs charts inline (IPython).
    py.init_notebook_mode()

    blue_colors = [
        "lightskyblue",
        "deepskyblue",
        "cornflowerblue",
        "dodgerblue",
        "steelblue",
        "darkslateblue",
        "royalblue",
        "blue",
        "midnightblue",
    ]
    yellow_colors = [
        "rgb(249, 200, 6)",
        "moccasin",
        "peachpuff",
        "khaki",
        "yellow",
        "rgb(204,204,0)",
        "rgb(153,153,0)",
        "rgb(102,102,0)",
        "rgb(128,128,0)",
    ]
    purple_colors = [
        "plum",
        "fuchsia",
        "hotpink",
        "deeppink",
        "mediumorchid",
        "mediumpurple",
        "mediumvioletred",
        "blueviolet",
        "indigo",
    ]
    light_green_colors = [
        "lawngreen",
        "limegreen",
        "springgreen",
        "mediumseagreen",
        "seagreen",
        "darkgreen",
        "olivedrab",
        "darkolivegreen",
        "darkgreen",
    ]
    dark_green_colors = [
        "olivedrab",
        "darkgreen",
        "darkolivegreen",
        "darkgreen",
        "lawngreen",
        "limegreen",
        "springgreen",
        "mediumseagreen",
        "seagreen",
    ]
    red_colors = [
        "indianred",
        "darkred",
        "crimson",
        "darkred",
        "darksalmon",
        "red",
        "firebrick",
        "salmon",
        "lightsalmon",
    ]
    brown_colors = [
        "burlywood",
        "goldenrod",
        "chocolate",
        "tan",
        "rosybrown",
        "saddlebrown",
        "sandybrown",
        "peru",
        "brown",
    ]
    grey_colors_1 = [
        "gainsboro",
        "darkslategray",
        "black",
        "lightgray",
        "gray",
        "lightslategray",
        "silver",
        "dimgray",
        "lightslategray",
        "gainsboro",
        "darkslategray",
        "black",
    ]
    grey_colors_2 = [
        "gainsboro",
        "darkslategray",
        "black",
        "silver",
        "dimgray",
        "lightslategray",
        "lightgray",
        "gray",
        "lightslategray",
    ]
    cyan_colors = [
        "cyan",
        "aquamarine",
        "darkcyan",
        "aqua",
        "turquoise",
        "teal",
        "darkturquoise",
        "paleturquoise",
        "lightseagreen",
    ]
    orange_colors = [
        "coral",
        "orange",
        "darkorange",
        "tomato",
        "firebrick",
        "firebrick",
        "salmon",
        "orange",
        "darkred",
    ]

    timeindex = device_output_df.index.get_level_values(level="time").unique()
    active_ems = device_output_df.index.get_level_values("ems").unique()
    active_devices = device_output_df.index.get_level_values("device").unique()

    demand_NON_traces = dict()
    generation_NON_traces = dict()
    storage_charging_traces = dict()
    storage_discharging_traces = dict()
    storage_SOC_traces = dict()
    buffer_charging_traces = dict()
    net_demand_traces = dict()
    net_generation_traces = dict()

    demand_NON_colors = dict()
    generation_NON_colors = dict()
    storage_charging_colors = dict()
    storage_discharging_colors = dict()
    storage_SOC_colors = dict()
    buffer_charging_colors = dict()
    # net_demand_colors = dict()
    # net_generation_colors = dict()

    for ems in active_ems:
        barplot = go.Bar(
            x=timeindex,
            y=[
                ems_output_df.loc[(timeperiod, ems), "Net_Demand"]
                for timeperiod in timeindex
            ],
            textposition="auto",
            # hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="black")),
            hovertext="Net_Demand",
            textfont=dict(color="black"),
            name="Net_Demand",
            marker=go.Marker(color="grey", line=dict(color="rgb(8,48,107)", width=1.5)),
            legendgroup=ems,
        )
        net_demand_traces[ems] = barplot

        barplot = go.Bar(
            x=timeindex,
            y=[
                ems_output_df.loc[(timeperiod, ems), "Net_Generation"]
                for timeperiod in timeindex
            ],
            textposition="auto",
            # hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="black")),
            hovertext="Net_Generation",
            textfont=dict(color="black"),
            name="Net_Generation",
            marker=go.Marker(
                color="darkgrey", line=dict(color="rgb(8,48,107)", width=1.5)
            ),
            legendgroup=ems,
        )
        net_generation_traces[ems] = barplot

    for device in enumerate(active_devices):
        demand_NON_colors[device[1]] = blue_colors[device[0]]
        generation_NON_colors[device[1]] = yellow_colors[device[0]]
        storage_charging_colors[device[1]] = dark_green_colors[device[0]]
        storage_discharging_colors[device[1]] = light_green_colors[device[0]]
        storage_SOC_colors[device[1]] = red_colors[device[0]]
        buffer_charging_colors[device[1]] = brown_colors[device[0]]

    for ems in active_ems:
        for device in active_devices:
            if "Load_NON" in device:
                barplot = go.Bar(
                    x=timeindex,
                    y=[
                        device_output_df.loc[(timeperiod, ems, device), "Demand_NON"]
                        for timeperiod in timeindex
                    ],
                    textposition="auto",
                    # hoverinfo="y+text",
                    hoverlabel=dict(font=dict(color="black")),
                    hovertext=("Dem_{}".format(device)),
                    textfont=dict(color="black"),
                    name=device,
                    marker=go.Marker(
                        color=demand_NON_colors[device],
                        line=dict(color="rgb(8,48,107)", width=1.5),
                    ),
                    legendgroup=device,
                )
                demand_NON_traces[device] = barplot

            if "Gen_NON" in device:
                barplot = go.Bar(
                    x=timeindex,
                    y=[
                        device_output_df.loc[
                            (timeperiod, ems, device), "Generation_NON"
                        ]
                        for timeperiod in timeindex
                    ],
                    textposition="auto",
                    # hoverinfo="y+text",
                    hoverlabel=dict(font=dict(color="black")),
                    hovertext=device,
                    textfont=dict(color="black"),
                    name=device,
                    marker=go.Marker(
                        color=generation_NON_colors[device],
                        line=dict(color="rgb(8,48,107)", width=1.5),
                    ),
                    legendgroup=device,
                )
                generation_NON_traces[device] = barplot

            if "Storage" in device:
                barplot = go.Bar(
                    x=timeindex,
                    y=[
                        device_output_df.loc[
                            (timeperiod, ems, device), "Storage_Charging"
                        ]
                        for timeperiod in timeindex
                    ],
                    textposition="auto",
                    # hoverinfo="y+text",
                    hoverlabel=dict(font=dict(color="black")),
                    hovertext=device,
                    textfont=dict(color="black"),
                    name=device,
                    marker=go.Marker(
                        color=storage_charging_colors[device],
                        line=dict(color="rgb(8,48,107)", width=1.5),
                    ),
                    legendgroup=device,
                )
                storage_charging_traces[device] = barplot

                barplot = go.Bar(
                    x=timeindex,
                    y=[
                        device_output_df.loc[
                            (timeperiod, ems, device), "Storage_Discharging"
                        ]
                        for timeperiod in timeindex
                    ],
                    textposition="auto",
                    # hoverinfo="y+text",
                    hoverlabel=dict(font=dict(color="black")),
                    hovertext=device,
                    textfont=dict(color="black"),
                    name=device,
                    marker=go.Marker(
                        color=storage_discharging_colors[device],
                        line=dict(color="rgb(8,48,107)", width=1.5),
                    ),
                    legendgroup=device,
                )
                storage_discharging_traces[device] = barplot

                lineplot = go.Scatter(
                    x=timeindex,
                    y=[
                        device_output_df.loc[(timeperiod, ems, device), "Storage_SOC"]
                        for timeperiod in timeindex
                    ],
                    textposition="auto",
                    # hoverinfo="y+text",
                    hoverlabel=dict(font=dict(color="black")),
                    hovertext=device,
                    textfont=dict(color="black"),
                    name=device,
                    marker=go.Marker(
                        color=storage_SOC_colors[device],
                        line=dict(color="rgb(8,48,107)", width=1.5),
                    ),
                    legendgroup=device,
                )
                storage_SOC_traces[device] = lineplot

            if "Buffer" in device:
                barplot = go.Bar(
                    x=timeindex,
                    y=[
                        device_output_df.loc[
                            (timeperiod, ems, device), "Buffer_Charging"
                        ]
                        for timeperiod in timeindex
                    ],
                    textposition="auto",
                    # hoverinfo="y+text",
                    hoverlabel=dict(font=dict(color="black")),
                    hovertext=device,
                    textfont=dict(color="black"),
                    name=device,
                    marker=go.Marker(
                        color=buffer_charging_colors[device],
                        line=dict(color="rgb(8,48,107)", width=1.5),
                    ),
                    legendgroup=device,
                )
                buffer_charging_traces[device] = barplot

    nonshiftable_profile_data = []
    nonshiftable_profile_data += [
        demand_NON_traces[device] for device in active_devices if "Load_NON" in device
    ]
    nonshiftable_profile_data += [
        generation_NON_traces[device]
        for device in active_devices
        if "Gen_NON" in device
    ]
    storage_profile_data = []
    storage_profile_data += [
        storage_charging_traces[device]
        for device in active_devices
        if "Storage" in device
    ]
    storage_profile_data += [
        storage_discharging_traces[device]
        for device in active_devices
        if "Storage" in device
    ]
    storage_profile_data += [
        storage_SOC_traces[device] for device in active_devices if "Storage" in device
    ]
    buffers_profile_data = []
    buffers_profile_data += [
        buffer_charging_traces[device]
        for device in active_devices
        if "Buffer" in device
    ]
    net_data = []
    net_data += [net_demand_traces[ems] for ems in active_ems]
    net_data += [net_generation_traces[ems] for ems in active_ems]

    layout = go.Layout(
        autosize=True,
        title="Energy Profiles",
        height=550,
        width=1200,
        barmode="relative",
        bargap=5,
        showlegend=True,
        legend=dict(orientation="v"),
        margin=go.Margin(l=60, r=480, b=160, t=50, pad=-50),
        xaxis=dict(
            ticks="outside",
            tick0=0,
            dtick=1,
            ticklen=8,
            tickwidth=4,
            tickcolor="#000",
            showgrid=True,
            gridcolor="#bdbdbd",
            gridwidth=1,
        ),
        yaxis=dict(
            title="kWh",
            autorange=True,
            ticks="outside",
            tick0=0,
            dtick=5,
            ticklen=8,
            tickwidth=4,
            tickcolor="#000",
            hoverformat=".2f",
            showgrid=True,
            gridcolor="#bdbdbd",
            gridwidth=1,
        ),
    )

    fig1 = go.Figure(data=nonshiftable_profile_data, layout=layout)
    fig2 = go.Figure(data=storage_profile_data, layout=layout)
    fig3 = go.Figure(data=buffers_profile_data, layout=layout)
    fig4 = go.Figure(data=net_data, layout=layout)
    fig5 = go.Figure(layout=layout)

    fig5.data.extend(fig1.data)
    fig5.data.extend(fig2.data)
    fig5.data.extend(fig3.data)
    fig5.data.extend(fig4.data)

    py.iplot(fig1)
    py.iplot(fig2)
    py.iplot(fig3)
    py.iplot(fig4)
    py.iplot(fig5)
    return


def print_solver_results(results):
    print(str(results))


def print_solver_data(model):
    model.display()


def save_solver_results(results=None, name=None):
    modelname = name
    working_directory_path = os.path.abspath(os.path.dirname("solver.py"))
    filepath = os.path.join(
        working_directory_path,
        "ComOpt_Loan/comopt/solver/solver_output_data/model_results_"
        + str(modelname)
        + ".txt",
    ).replace("\\", "/")
    with open(filepath, "w") as f:
        f.write(str(results))
        f.close()


def save_solver_model_data(model=None, name=None):
    modelname = name
    working_directory_path = os.path.abspath(os.path.dirname("solver.py"))
    filepath_1 = os.path.join(
        working_directory_path,
        "ComOpt_Loan/comopt/solver/solver_output_data/model_solved_equations_"
        + str(modelname)
        + ".txt",
    )
    filepath_2 = os.path.join(
        working_directory_path,
        "ComOpt_Loan/comopt/solver/solver_output_data/model_declarations_"
        + str(modelname)
        + ".txt",
    )

    with open(filepath_1, "w") as f:
        f.write("Modelname: {}\n".format(name))
        model.display(ostream=f)
        f.close()

    with open(filepath_2, "w") as f:
        f.write("Modelname: {}\n".format(name))
        model.pprint(ostream=f)
        f.close()


def print_solver_file(file=None):
    with open(file, "r") as f:
        output = f.read()
        print(output)
        f.close()


# %% Init
working_directory_path = os.path.abspath(os.path.dirname("solver.py"))
filepath = os.path.join(
    working_directory_path, "ComOpt_Loan/comopt/scenario/testcases.xlsx"
).replace("\\", "/")
data = pd.io.excel.read_excel(filepath, sheet_name="Inputs")


def create_solver_model(name: str, data: DataFrame) -> ConcreteModel:

    # TODO: Add efficiency parameter for storages
    # TODO: Write Docstring
    # TODO: Attach buffer data to data or create on input file for buffer_windows_list and buffer_windows_timeperiods

    # Extract some data from data input
    idx = pd.IndexSlice
    preprocessed_solver_data = preprocess_solver_data(data)
    activated_device_names = preprocessed_solver_data[0]
    activated_device_types = preprocessed_solver_data[1]
    buffer_windows_list = preprocessed_solver_data[2]
    buffer_windows_timeperiods = preprocessed_solver_data[3]

    # Create model
    model = ConcreteModel(name="name")

    # ------------------------  Parameter & Set Rules  ----------------------------- #
    def integral_equal_select(model, timeperiod, ems, device=None):
        # this works because it should be the same value on the ems level
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_integral_equal"])
        else:
            return float(data.loc[(timeperiod, ems, device), "integral_equal"])

    def integral_max_select(model, timeperiod, ems, device=None):
        # this works because it should be the same value on the ems level
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_integral_max"])
        else:
            return float(data.loc[(timeperiod, ems, device), "integral_max"])

    def integral_min_select(model, timeperiod, ems, device=None):
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_integral_min"])
        else:
            return float(data.loc[(timeperiod, ems, device), "integral_min"])

    def derivative_equal_select(model, timeperiod, ems, device=None):
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_derivative_equal"])
        else:
            return float(data.loc[(timeperiod, ems, device), "derivative_equal"])

    def derivative_max_select(model, timeperiod, ems, device=None):
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_derivative_max"])
        else:
            return float(data.loc[(timeperiod, ems, device), "derivative_max"])

    def derivative_min_select(model, timeperiod, ems, device=None):
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_derivative_min"])
        else:
            return float(data.loc[(timeperiod, ems, device), "derivative_min"])

    def SOC_init_select(model, ems, storage):
        return float(data.loc[(model.timeperiods[1], ems, storage), "integral_equal"])

    def SOC_end_select(model, ems, storage):
        return float(data.loc[(model.timeperiods[-1], ems, storage), "integral_equal"])

    def net_generation_price_select(model, timeperiod, ems):
        return float(data.loc[(timeperiod, ems), "feed_in_tariff"].unique())

    def net_demand_price_select(model, timeperiod, ems):
        return float(data.loc[(timeperiod, ems), "market_price"].unique())

    def buffer_window_timeperiods_select(model, buffer_window, ems):
        return buffer_windows_timeperiods[buffer_window]

    # ------------------------------------ # SETS # --------------------------------------- #
    model.timeperiods = Set(
        initialize=data.index.get_level_values(level="time").unique().values.tolist(),
        ordered=True,
        doc="Set of timeperiods",
    )

    model.ems = Set(
        initialize=data.index.get_level_values(level="ems").unique().values.tolist(),
        ordered=True,
        doc="Set of energy management systems",
    )

    model.nonshiftable_loads = Set(
        initialize=[
            device for device in activated_device_names if "_Load_NON" in device
        ],
        ordered=True,
        doc="Set of nonshiftable load devices",
    )

    model.storages = Set(
        initialize=[
            device for device in activated_device_names if "_Storage" in device
        ],
        ordered=True,
        doc="Set of storage devices",
    )

    model.buffers = Set(
        initialize=[device for device in activated_device_names if "_Buffer" in device],
        ordered=True,
        doc="Set of buffer devices by name",
    )

    model.buffers_windows = Set(
        initialize=buffer_windows_list,
        ordered=True,
        doc="Set of buffer shifting windows by name",
    )

    model.buffers_windows_timeperiods = Set(
        model.buffers_windows,
        model.ems,
        initialize=buffer_window_timeperiods_select,
        ordered=True,
        doc="Sets of timeperiods for each buffer window",
    )

    model.nonshiftable_generators = Set(
        initialize=[
            device for device in activated_device_names if "_Gen_NON" in device
        ],
        ordered=True,
        doc="Set of nonshiftable generator devices",
    )

    model.shiftable_generators = Set(
        initialize=[
            device for device in activated_device_names if "_Gen_SHIFT" in device
        ],
        ordered=True,
        doc="Set of shiftable generator devices",
    )

    # ----------------------------------- # parameter DEVICES level # --------------------------------------- #
    # Nonshiftable Load Devices
    if activated_device_types["Loads_NON"] == "Active":
        model.demand_nonshiftables = Param(
            model.timeperiods,
            model.ems,
            model.nonshiftable_loads,
            initialize=derivative_equal_select,
        )

    # Nonshiftable Generator Devices
    if activated_device_types["Gen_NON"] == "Active":
        model.generation_nonshiftables = Param(
            model.timeperiods,
            model.ems,
            model.nonshiftable_generators,
            initialize=derivative_equal_select,
        )

    # Storage Devices
    if activated_device_types["Storages"] == "Active":
        model.storages_max_power_per_step = Param(
            model.timeperiods,
            model.ems,
            model.storages,
            initialize=derivative_max_select,
        )

        model.storages_min_power_per_step = Param(
            model.timeperiods,
            model.ems,
            model.storages,
            initialize=derivative_min_select,
        )

        model.storages_SOC_init = Param(
            model.ems, model.storages, initialize=SOC_init_select
        )

        model.storages_SOC_end = Param(
            model.ems, model.storages, initialize=SOC_end_select
        )

    # Buffer devices
    if activated_device_types["Buffers"] == "Active":
        model.buffers_max_power_per_window = Param(
            model.timeperiods,
            model.ems,
            model.buffers,
            initialize=derivative_max_select,
        )

        model.buffers_min_power_per_window = Param(
            model.timeperiods,
            model.ems,
            model.buffers,
            initialize=derivative_min_select,
        )

    # Shiftable Generator devices
    if activated_device_types["Gen_SHIFT"] == "Active":
        model.shiftable_generator_max_power_per_step = Param(
            model.timeperiods,
            model.ems,
            model.shiftable_generators,
            initialize=derivative_max_select,
        )

        model.shiftable_generator_min_power_per_step = Param(
            model.timeperiods,
            model.ems,
            model.shiftable_generators,
            initialize=derivative_min_select,
        )

    # ---------------------------------------- # parameter EMS level # --------------------------------------------- #
    model.net_generation_max_per_step = Param(
        model.timeperiods, model.ems, initialize=derivative_max_select
    )

    model.net_demand_max_per_step = Param(
        model.timeperiods, model.ems, initialize=derivative_max_select
    )

    model.net_generation_prices = Param(
        model.timeperiods, model.ems, initialize=net_generation_price_select
    )

    model.net_demand_prices = Param(
        model.timeperiods, model.ems, initialize=net_demand_price_select
    )

    # -------------------------------------- # variables STORAGES level # -------------------------------------------- #
    if activated_device_types["Storages"] == "Active":
        model.storages_charging = Var(
            model.timeperiods, model.ems, model.storages, within=NonNegativeReals
        )

        model.storages_discharging = Var(
            model.timeperiods, model.ems, model.storages, within=NonNegativeReals
        )

        model.storages_SOC = Var(
            model.timeperiods, model.ems, model.storages, within=NonNegativeReals
        )

        model.storages_charging_active = Var(
            model.timeperiods, model.ems, model.storages, within=Binary
        )

        model.storages_discharging_active = Var(
            model.timeperiods, model.ems, model.storages, within=Binary
        )

    # ---------------------------------------- # variables BUFFER level # ----------------------------------------------- #
    if activated_device_types["Buffers"] == "Active":
        model.buffers_charging = Var(
            model.timeperiods, model.ems, model.buffers, within=NonNegativeReals
        )

    # ------------------------------------------ # variables EMS level # ------------------------------------------------- #
    model.net_demand = Var(model.timeperiods, model.ems, within=NonNegativeReals)

    model.net_generation = Var(model.timeperiods, model.ems, within=NonNegativeReals)

    model.net_demand_active = Var(model.timeperiods, model.ems, within=Binary)

    model.net_generation_active = Var(model.timeperiods, model.ems, within=Binary)

    # ------------------------------------------- # rules STORAGES level # ----------------------------------------------- #
    def storages_operation_mode_rule(model, timeperiod, ems, storages):
        return (
            model.storages_charging_active[timeperiod, ems, storages]
            + model.storages_discharging_active[timeperiod, ems, storages]
            <= 1
        )

    def storages_min_charging_rule(model, timeperiod, ems, storages):
        return (
            model.storages_charging_active[timeperiod, ems, storages]
            * model.storages_min_power_per_step[timeperiod, ems, storages]
            <= model.storages_charging[timeperiod, ems, storages]
        )

    def storages_max_charging_rule(model, timeperiod, ems, storages):
        return (
            model.storages_charging_active[timeperiod, ems, storages]
            * model.storages_max_power_per_step[timeperiod, ems, storages]
            >= model.storages_charging[timeperiod, ems, storages]
        )

    def storages_min_discharging_rule(model, timeperiod, ems, storages):
        return (
            model.storages_discharging_active[timeperiod, ems, storages]
            * model.storages_min_power_per_step[timeperiod, ems, storages]
            <= model.storages_discharging[timeperiod, ems, storages]
        )

    def storages_max_discharging_rule(model, timeperiod, ems, storages):
        return (
            model.storages_discharging_active[timeperiod, ems, storages]
            * model.storages_max_power_per_step[timeperiod, ems, storages]
            >= model.storages_discharging[timeperiod, ems, storages]
        )

    def storages_state_of_charge_rule(model, timeperiod, ems, storages):
        if timeperiod == model.timeperiods[1]:
            return (
                model.storages_SOC[timeperiod, ems, storages]
                == model.storages_SOC_init[ems, storages]
                + model.storages_charging[timeperiod, ems, storages]
                - model.storages_discharging[timeperiod, ems, storages]
            )

        elif timeperiod == model.timeperiods[-1]:
            return (
                model.storages_SOC_end[ems, storages]
                == model.storages_SOC[timeperiod - 1, ems, storages]
                + model.storages_charging[timeperiod, ems, storages]
                - model.storages_discharging[timeperiod, ems, storages]
            )
        else:
            return (
                model.storages_SOC[timeperiod, ems, storages]
                == model.storages_SOC[timeperiod - 1, ems, storages]
                + model.storages_charging[timeperiod, ems, storages]
                - model.storages_discharging[timeperiod, ems, storages]
            )

    if activated_device_types["Storages"] == "Active":
        model.battery_operation_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_operation_mode_rule,
        )

        model.battery_min_charging_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_min_charging_rule,
        )

        model.battery_max_charging_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_max_charging_rule,
        )

        model.battery_min_discharging_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_min_discharging_rule,
        )

        model.battery_max_discharging_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_max_discharging_rule,
        )

        model.battery_state_of_charge_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_state_of_charge_rule,
        )

    # -------------------------------------------- # rules BUFFERS level # ----------------------------------------------- #
    def buffers_min_charging_rule(model, timeperiod, ems, buffer):
        return (
            model.buffers_min_power_per_window[timeperiod, ems, buffer]
            <= model.buffers_charging[timeperiod, ems, buffer]
        )

    def buffers_max_charging_rule(model, timeperiod, ems, buffer):
        return (
            model.buffers_max_power_per_window[timeperiod, ems, buffer]
            >= model.buffers_charging[timeperiod, ems, buffer]
        )

    def net_balance_buffers_rule(model, ems, buffer_window):
        return sum(
            model.buffers_charging[timeperiod, ems, buffer]
            for buffer in model.buffers
            for timeperiod in model.buffers_windows_timeperiods[buffer_window, ems]
        ) == max(
            data.loc[idx[timeperiod, ems, buffer], "integral_equal"]
            for buffer in model.buffers
            for timeperiod in model.buffers_windows_timeperiods[buffer_window, ems]
        )

    if activated_device_types["Buffers"] == "Active":
        model.buffer_balancing_constraint = Constraint(
            model.ems, model.buffers_windows, rule=net_balance_buffers_rule
        )

        model.buffer_max_charging_constraint = Constraint(
            model.timeperiods, model.ems, model.buffers, rule=buffers_max_charging_rule
        )

        model.buffer_min_charging_constraint = Constraint(
            model.timeperiods, model.ems, model.buffers, rule=buffers_min_charging_rule
        )

    # ---------------------------------------------- # rules EMS level # -------------------------------------------------- #
    def balancing_ems_net_energy_rule(model, timeperiod, ems):
        return (
            sum(
                model.demand_nonshiftables[timeperiod, ems, load]
                for load in model.nonshiftable_loads
                if activated_device_types["Loads_NON"] == "Active"
            )
            + sum(
                model.storages_charging[timeperiod, ems, storage]
                for storage in model.storages
                if activated_device_types["Storages"] == "Active"
            )
            + sum(
                model.buffers_charging[timeperiod, ems, buffer]
                for buffer in model.buffers
                if activated_device_types["Buffers"] == "Active"
            )
            + model.net_generation[timeperiod, ems]
            == sum(
                model.generation_nonshiftables[timeperiod, ems, generator]
                for generator in model.nonshiftable_generators
                if activated_device_types["Gen_NON"] == "Active"
            )
            + sum(
                model.storages_discharging[timeperiod, ems, storage]
                for storage in model.storages
                if activated_device_types["Storages"] == "Active"
            )
            + model.net_demand[timeperiod, ems]
        )

    def market_operation_rule(model, timeperiod, ems):
        return (
            model.net_demand_active[timeperiod, ems]
            + model.net_generation_active[timeperiod, ems]
            <= 1
        )

    def net_demand_max_per_step_rule(model, timeperiod, ems):
        return (
            model.net_demand[timeperiod, ems]
            <= model.net_demand_active[timeperiod, ems]
            * model.net_generation_max_per_step[timeperiod, ems]
        )

    def net_generation_max_per_step_rule(model, timeperiod, ems):
        return (
            model.net_generation[timeperiod, ems]
            <= model.net_generation_active[timeperiod, ems]
            * model.net_generation_max_per_step[timeperiod, ems]
        )

    # ------------------------------------------- # constraints EMS level # ------------------------------------------------- #
    model.balancing_ems_constraint = Constraint(
        model.timeperiods, model.ems, rule=balancing_ems_net_energy_rule
    )

    model.net_demand_maximum_constraint = Constraint(
        model.timeperiods, model.ems, rule=net_demand_max_per_step_rule
    )

    model.net_generation_maximum_constraint = Constraint(
        model.timeperiods, model.ems, rule=net_generation_max_per_step_rule
    )

    # --------------------------------------------- # objective function # ---------------------------------------------------- #
    def objective_function(model):
        return sum(
            model.net_demand[timeperiods, ems]
            * model.net_demand_prices[timeperiods, ems]
            - model.net_generation[timeperiods, ems]
            * model.net_generation_prices[timeperiods, ems]
            for timeperiods in model.timeperiods
            for ems in model.ems
        )

    model.objective_function = Objective(rule=objective_function, sense=minimize)
    # -------------------------------------------- # objective function end # -------------------------------------------------- #
    return model


def solve_schedule(model):
    opt = SolverFactory("glpk")
    return opt.solve(model)


def print_solver_results(results):
    print(str(results))


def print_solver_data(model):
    model.display()


# %%
baseline_model = create_solver_model(name="Baseline", data=data)
results = solve_schedule(baseline_model)
print_solver_results(results)
# print_solver_data(baseline_model)
# save_solver_results(results=results, name="Baseline")
# save_solver_model_data(model=baseline_model, name="Baseline")
# baseline_model.pprint()

# %%
dfx = create_solver_results_dataframes(baseline_model)
device_output_df = dfx[0]
ems_output_df = dfx[1]
plot_solver_results(device_output_df, ems_output_df)
