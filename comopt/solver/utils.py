from pyomo.environ import *
from pyomo.core import *
from pyomo.core import value, ConcreteModel
import pandas as pd
import numpy as np
import cufflinks as cf
import more_itertools as mit
import plotly.offline as py
import plotly.graph_objs as go
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
        # var_output = {'time': timeperiod,
        #               'ems': ems,
        #               }
        for device in model.nonshiftable_loads:
            nonshiftable_loads_output = {
                "time": timeperiod,
                "ems": ems,
                "device": device,
                "Demand_NON": (
                    round(value(model.demand_nonshiftables[timeperiod, ems, device]), 1)
                ),
            }
            # var_output.update(nonshiftable_loads_output)
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
            # var_output.update(nonshiftable_generators_output)
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
