import json as json

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dash_table
import plotly.graph_objs as go
import pandas as pd

from comopt.model.environment import *
from comopt.ui.styles import styles
from comopt.globals import *


##################################### INPUTS #################################################################


##################################### APP ##############################################################
app = dash.Dash()
app.config["suppress_callback_exceptions"] = True
# External CSS
app.css.append_css(
    {
        "external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css"
    }
)
app.css.append_css(
    {
        "external_url": "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css"
    }
)
app.css.append_css({"external_url": "https://rawgit.com/lwileczek/Dash/master/v5.css"})
app.scripts.append_script(
    {"external_url": "http://code.jquery.com/jquery-3.3.1.min.js"}
)
app.scripts.append_script(
    {
        "external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js"
    }
)

app.layout = html.Div(
    style=styles["main"],
    children=[  # app.layout
        ############################################## TOP ROW ############################################################
        html.Div(
            id="outer-container",
            className="container-fluid",
            children=[  # className="container-fluid"
                html.Div(
                    id="top-container",
                    className="container-fluid rounded",
                    style=styles["top-container"],
                    children=[  # className="container-fluid"
                        html.Div(
                            className="row",
                            children=[  # TOP ROW
                                html.Div(
                                    className="col-md-2",
                                    style=styles["header"],
                                    children=["COMOPT USER INTERFACE"],  # HEADER-SLIDER
                                ),  # HEADER-SLIDER ENDS
                                html.Div(
                                    className="col-md-2",
                                    style=styles["top-slider"],
                                    children=[  # SC-SLIDER
                                        html.Label("Number of Scenarios"),
                                        dcc.Slider(
                                            id="sc-slider",
                                            min=1,
                                            max=9,
                                            marks={
                                                i: "{}".format(i) for i in range(1, 10)
                                            },
                                            value=1,
                                        ),
                                    ],
                                ),  # SC-SLIDER ENDS
                                html.Div(
                                    className="col-md-2",
                                    style=styles["top-slider"],
                                    children=[  # EMS-SLIDER
                                        html.Label("Activate EM-Systems"),
                                        dcc.Slider(
                                            id="ems-slider",
                                            min=1,
                                            max=9,
                                            marks={
                                                i: "{}".format(i) for i in range(1, 10)
                                            },
                                            value=1,
                                        ),
                                    ],
                                ),  # EMS-SLIDER ENDS
                                html.Div(
                                    className="col-md-2",
                                    style=styles["input-name"],
                                    children=[  # BUTTONS
                                        html.Label("Insert Name:"),
                                        html.Div(
                                            dcc.Input(
                                                id="input-field",
                                                value="Run_01",
                                                type="text",
                                            )
                                        ),
                                    ],
                                ),  # BUTTONS ENDS
                                html.Div(
                                    className="col-md-2",
                                    style=styles["previous-runs"],
                                    children=[  # BUTTONS
                                        html.Label("Previous Simulations"),
                                        dcc.Dropdown(
                                            options=[
                                                {"label": i, "value": i}
                                                for i in global_timeseries_dict.keys()
                                            ],
                                            placeholder="None",
                                        ),
                                    ],
                                ),  # BUTTONS ENDS
                                html.Span(
                                    className="col-md-2",
                                    style=styles["top-button"],
                                    children=[  # INIT
                                        html.Button(
                                            "Run",
                                            id="run-button",
                                            n_clicks=0,
                                            className="btn btn-outline-primary btn-lg",
                                        ),
                                        html.Button(
                                            "In",
                                            id="input-button",
                                            n_clicks=0,
                                            className="btn btn-outline-primary btn-lg",
                                        ),
                                        html.Button(
                                            "Out",
                                            id="output-button",
                                            n_clicks=0,
                                            className="btn btn-outline-primary btn-lg",
                                        ),
                                    ],
                                ),  # INIT ENDS
                            ],
                        )  # TOP ROW ENDS
                    ],
                ),
                # ################################################ MAIN ROW  ##################################################################
                html.Div(
                    id="main-container",
                    className="container-fluid rounded",
                    style=styles["main-container"],
                    children=[
                        html.Div(
                            id="main-row",
                            className="row",
                            style={"width": "100%", "margin": 0},
                            children=[
                                html.Div(
                                    id="toggle-window",
                                    style={"width": "100%"},
                                    children=[],  # TOGGLE WIND
                                ),  # TOGGLE WINDOW
                                html.Div(
                                    style={"display": "none"},
                                    children=[
                                        # DUMMY TABLE
                                        dash_table.EditableTable(
                                            id="editable-table",
                                            dataframe=pd.DataFrame().to_dict(),
                                        )
                                    ],
                                ),
                            ],
                        )  # MAIN ROW ENDS
                    ],
                ),
                # ------------------------------------------------# HIDDEN DIVS #------------------------------------------------------------#
                html.Div(
                    className="col-sm-12",
                    id="data-set",
                    style={"display": "none", "background": "lightgreen", "margin": 10},
                    children=[html.Div("Dataset")],
                ),
                html.Div(
                    className="col-sm-12",
                    id="parameter-set",
                    style={"display": "none", "background": "blue"},
                    children=[html.Div("Parameterset")],
                ),
                html.Div(
                    className="col-sm-4",
                    id="init-parameter-set",
                    style={"display": "none", "background": "white"},
                    children=[html.Div("Init Parameter Set")],
                ),
                html.Div(
                    className="col-sm-4",
                    id="updated-parameter-set",
                    style={"display": "none", "background": "brown"},
                    children=[html.Div("Intermediate")],
                ),
                html.Div(
                    className="col-sm-12",
                    id="p-bucket",
                    style={"display": "none", "background": "grey"},
                    children=[html.Div("P-Bucket")],
                ),
                html.Div(
                    className="col-sm-4",
                    id="active-sc",
                    style={"display": "none", "background": "red"},
                    children=[html.Div("Active SC")],
                ),
                html.Div(
                    className="col-sm-4",
                    id="active-ems",
                    style={"display": "none", "background": "black"},
                    children=[html.Div("Active EMS")],
                ),
                html.Div(
                    className="col-sm-4",
                    id="selected-sc",
                    style={"display": "none", "background": "yellow"},
                    children=[html.Div("Selected SC")],
                ),
                html.Div(
                    className="col-sm-4",
                    id="last-clicked",
                    style={"display": "none", "background": "pink"},
                    children=[html.Div("Selected Agent")],
                ),
                html.Div(
                    className="col-sm-4",
                    id="any-clicks",
                    style={"display": "none", "background": "blue"},
                    children=[html.Div("Any Clicks")],
                ),
                html.Div(
                    className="col-sm-12",
                    id="flags",
                    style={"display": "none", "background": "white"},
                    children=[html.Div("Flags")],
                ),
                html.Div(
                    className="col-sm-12",
                    id="run-output",
                    style={"display": "none", "background": "black"},
                    children=[html.Div("Run")],
                ),
                html.Div(
                    className="col-sm-12",
                    id="save-output",
                    style={"display": "none", "background": "grey"},
                    children=[html.Div("Save")],
                ),
                html.Div(
                    className="col-sm-12",
                    id="run-name-output",
                    style={"display": "none", "background": "grey"},
                    children=[html.Div("Run Name")],
                ),
            ],
        )
    ],
)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ L A Y E R $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
input_layer = (
    html.Div(
        id="param-row",
        className="row",
        style={"width": "100%", "margin-left": 5},
        children=[
            html.Div(
                id="tab-bar", style={"width": "100%", "margin-left": 5}, children=[]
            ),
            html.Img(id="image"),
            html.Div(
                className="col-6 rounded",
                id="parameter-div",
                style={
                    "height": "762px",
                    "width": "100%",
                    "padding-top": 20,
                    "margin-top": 8,
                    "background": "white",
                    "border": "thin darkgrey solid",
                    "overflow": "auto",
                },
                children=[html.Div(id="table-output", children=[])],
            ),
            # _________________________________________________Right Column ___________________________________________________________________________
            html.Div(
                className="col-6 rounded",
                id="profile-div",
                style={"width": "100%", "padding": 0, "margin": 0},
                children=[
                    # _________________________________________________Agent-Buttons___________________________________________________________________________
                    html.Div(
                        className="row",
                        style={
                            "width": "80%",
                            "margin-top": 0,
                            "margin-left": "100",
                            "margin-right": "auto",
                            "padding-left": 20,
                        },
                        children=[
                            html.Div(
                                className="col-md-3 rounded",
                                children=[
                                    html.Div(
                                        style=styles["buttons-agents"],
                                        children=[
                                            html.Button(
                                                "Press 1st",
                                                id="TA-button",
                                                n_clicks=0,
                                                className="btn-block w-100",
                                                n_clicks_timestamp=-1,
                                            )
                                        ],
                                    )
                                ],
                            ),
                            html.Div(
                                className="col-md-3 rounded",
                                children=[
                                    html.Div(
                                        style=styles["buttons-agents"],
                                        children=[
                                            html.Button(
                                                "Press 2nd",
                                                id="MA-button",
                                                n_clicks=0,
                                                className="btn-block w-1000",
                                                n_clicks_timestamp=-1,
                                            )
                                        ],
                                    )
                                ],
                            ),
                            html.Div(
                                className="col-md-3 rounded",
                                children=[
                                    html.Div(
                                        style=styles["buttons-agents"],
                                        children=[
                                            html.Button(
                                                "Press 3rd",
                                                id="EMS-button",
                                                n_clicks=0,
                                                className="btn-block w-100",
                                                n_clicks_timestamp=-1,
                                            )
                                        ],
                                    )
                                ],
                            ),
                            html.Div(
                                className="col-md-3 rounded",
                                children=[
                                    html.Div(
                                        style=styles["buttons-agents"],
                                        children=[
                                            html.Button(
                                                "Press 4th",
                                                id="Prices-button",
                                                n_clicks=0,
                                                className="btn-block w-100",
                                                n_clicks_timestamp=-1,
                                            )
                                        ],
                                    )
                                ],
                            ),
                        ],
                    ),
                    # _________________________________________________1) FLAG-HEADER___________________________________________________________________________
                    html.Div(
                        className="row",
                        style={
                            "width": "100%",
                            "margin-top": 0,
                            "padding-left": 20,
                            "padding": 10,
                        },
                        children=[
                            html.Div(
                                className="col-md-12 rounded",
                                style={
                                    "margin-top": 5,
                                    "margin-right": 0,
                                    "margin-left": 20,
                                    "background": "white",
                                    "border": "thin darkgrey solid",
                                },
                                children=[
                                    html.Div(
                                        className="col-12",
                                        style={"padding-left": 66, "margin-top": "15"},
                                        children=[
                                            html.Div(
                                                className="row",
                                                style={"width": "100%"},
                                                children=[
                                                    html.Div(
                                                        className="col-6",
                                                        style={"padding-left": 10},
                                                        children=[
                                                            html.Div(
                                                                "Flex-Request-Split",
                                                                style=styles[
                                                                    "flag-header"
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="col-6",
                                                        children=[
                                                            html.Div(
                                                                "Market Options",
                                                                style=styles[
                                                                    "flag-header"
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            # _________________________________________________1) FLAG-BOX___________________________________________________________________________
                                            html.Div(
                                                className="row",
                                                style={"width": "100%"},
                                                children=[
                                                    html.Div(
                                                        className="col-6",
                                                        style=styles["flag-box"],
                                                        children=[
                                                            dcc.RadioItems(
                                                                id="flex-split-flag",
                                                                options=[
                                                                    {
                                                                        "label": " equal",
                                                                        "value": "equal",
                                                                    },
                                                                    {
                                                                        "label": " ran-3",
                                                                        "value": "ran-3",
                                                                    },
                                                                ],
                                                                value="equal",
                                                                labelStyle={
                                                                    "display": "inline-block",
                                                                    "margin-left": 5,
                                                                    "margin-top": 10,
                                                                    # 'font-family': 'Jazz LET',
                                                                    "font-size": "20px",
                                                                    "color": "lightblack",
                                                                    "opacity": 1,
                                                                },
                                                            )
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="col-6",
                                                        style=styles["flag-box"],
                                                        children=[
                                                            html.Div(
                                                                className="col-6",
                                                                style=styles[
                                                                    "flag-box"
                                                                ],
                                                                children=[
                                                                    dcc.Checklist(
                                                                        id="market-flags",
                                                                        options=[
                                                                            {
                                                                                "label": " Dayahead",
                                                                                "value": "Dayahead",
                                                                            },
                                                                            {
                                                                                "label": " Intraday",
                                                                                "value": "Intraday",
                                                                            },
                                                                            {
                                                                                "label": " SmartBlocks",
                                                                                "value": "SmartBlocks",
                                                                            },
                                                                            {
                                                                                "label": " Loans",
                                                                                "value": "Loans",
                                                                            },
                                                                        ],
                                                                        values=[
                                                                            "Dayahead"
                                                                        ],
                                                                        labelStyle={
                                                                            "display": "inline",
                                                                            # "margin":10,
                                                                            "margin-left": 15,
                                                                            # 'font-family': 'Jazz LET, fantasy',
                                                                            "font-size": "20px",
                                                                            "color": "lightblack",
                                                                            "opacity": 1,
                                                                        },
                                                                    )
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            # _________________________________________________2) FLAG-HEADER___________________________________________________________________________
                                            html.Div(
                                                className="row",
                                                style={"width": "100%"},
                                                children=[
                                                    html.Div(
                                                        className="col-6",
                                                        children=[
                                                            html.Div(
                                                                "Negotiation-Initiator",
                                                                style=styles[
                                                                    "flag-header"
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="col-6",
                                                        children=[
                                                            html.Div(
                                                                "Negotiation-Strategies",
                                                                style=styles[
                                                                    "flag-header"
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            # _________________________________________________2) FLAG-BOX__________________________________________________________________________
                                            html.Div(
                                                className="row",
                                                style={"width": "100%"},
                                                children=[
                                                    html.Div(
                                                        className="col-6",
                                                        style=styles["flag-box"],
                                                        children=[
                                                            dcc.RadioItems(
                                                                id="negotiation-init",
                                                                options=[
                                                                    {
                                                                        "label": " TA",
                                                                        "value": "TA",
                                                                    },
                                                                    {
                                                                        "label": " MA",
                                                                        "value": "MA",
                                                                    },
                                                                ],
                                                                value="MA",
                                                                labelStyle={
                                                                    "display": "inline-block",
                                                                    "margin": 5,
                                                                    # 'font-family': 'Jazz LET, fantasy',
                                                                    "font-size": "20px",
                                                                    "color": "lightblack",
                                                                    "opacity": 1,
                                                                },
                                                            )
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="col-6",
                                                        style=styles["flag-box"],
                                                        children=[
                                                            # html.Label("Trading Agent:"),
                                                            dcc.RadioItems(
                                                                id="ta-strategy",
                                                                options=[
                                                                    {
                                                                        "label": "TA 1",
                                                                        "value": "TA 1",
                                                                    },
                                                                    {
                                                                        "label": "TA 2",
                                                                        "value": "TA 2",
                                                                    },
                                                                    {
                                                                        "label": "TA 3",
                                                                        "value": "TA 3",
                                                                    },
                                                                ],
                                                                value="cool",
                                                                labelStyle={
                                                                    "display": "inline-block",
                                                                    "margin": 5,
                                                                    # 'font-family': 'Jazz LET, fantasy',
                                                                    "font-size": "18px",
                                                                    "color": "lightblack",
                                                                    "opacity": 1,
                                                                },
                                                            ),
                                                            dcc.RadioItems(
                                                                id="ma-strategy",
                                                                options=[
                                                                    {
                                                                        "label": "MA 1",
                                                                        "value": "MA 1",
                                                                    },
                                                                    {
                                                                        "label": "MA 2",
                                                                        "value": "MA 2",
                                                                    },
                                                                    {
                                                                        "label": "MA 3",
                                                                        "value": "MA 3",
                                                                    },
                                                                ],
                                                                value="random",
                                                                labelStyle={
                                                                    "display": "inline-block",
                                                                    "margin": 5,
                                                                    # 'font-family': 'Jazz LET, fantasy',
                                                                    "font-size": "18px",
                                                                    "color": "lightblack",
                                                                    "opacity": 1,
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            # _________________________________________________3) FLAG-HEADER___________________________________________________________________________
                                            html.Div(
                                                className="row",
                                                style={"width": "100%"},
                                                children=[
                                                    html.Div(
                                                        className="col-6",
                                                        children=[
                                                            html.Div(
                                                                "Optimization",
                                                                style=styles[
                                                                    "flag-header"
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="col-6",
                                                        children=[
                                                            html.Div(
                                                                "Flexibility-Options",
                                                                style=styles[
                                                                    "flag-header"
                                                                ],
                                                            )
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            # _________________________________________________3) FLAG-BOXES___________________________________________________________________________
                                            html.Div(
                                                className="row",
                                                style={"width": "100%"},
                                                children=[
                                                    html.Div(
                                                        className="col-6",
                                                        style={"height": "80"},
                                                        children=[
                                                            dcc.RadioItems(
                                                                id="optimization-mode",
                                                                options=[
                                                                    {
                                                                        "label": " flex-split",
                                                                        "value": "flex-split",
                                                                    },
                                                                    {
                                                                        "label": " central",
                                                                        "value": "central",
                                                                    },
                                                                ],
                                                                value="flex-split",
                                                                labelStyle={
                                                                    "display": "inline-block",
                                                                    "margin": 5,
                                                                    # 'font-family': 'Jazz LET, fantasy',
                                                                    "font-size": "20px",
                                                                    "color": "lightblack",
                                                                    "opacity": 1,
                                                                },
                                                            ),
                                                            dcc.Checklist(
                                                                id="internal-balance",
                                                                options=[
                                                                    {
                                                                        "label": " Internal-Balance",
                                                                        "value": "Internal_Balance",
                                                                    }
                                                                ],
                                                                values="",
                                                                labelStyle={
                                                                    "display": "inline",
                                                                    "margin": 10,
                                                                    "margin-left": 0,
                                                                    # 'font-family': 'Jazz LET, fantasy',
                                                                    "font-size": "20px",
                                                                    "color": "lightblack",
                                                                    "opacity": 1,
                                                                },
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        className="col-6",
                                                        style=styles["flag-box"],
                                                        children=[
                                                            dcc.Checklist(
                                                                id="flex-options",
                                                                options=[
                                                                    {
                                                                        "label": " Batteries",
                                                                        "value": "Batteries",
                                                                    },
                                                                    {
                                                                        "label": " DSM",
                                                                        "value": "DSM",
                                                                    },
                                                                    {
                                                                        "label": " Curtailment",
                                                                        "value": "Curtailment",
                                                                    },
                                                                ],
                                                                values=["Batteries"],
                                                                labelStyle={
                                                                    "display": "inline",
                                                                    "margin": 10,
                                                                    "margin-left": 5,
                                                                    # 'font-family': 'Jazz LET, fantasy',
                                                                    "font-size": "18px",
                                                                    "color": "lightblack",
                                                                    "opacity": 1,
                                                                },
                                                            )
                                                        ],
                                                    ),
                                                ],
                                            ),
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                    # _____________________________________________________________________________________________________________________________________________________#
                    html.Div(
                        className="row",
                        style={
                            "height": "190x",
                            "width": "100%",
                            "margin-top": 2,
                            "margin-left": 20,
                            "margin-bottom": 2,
                        },
                        children=[dcc.Graph(id="profile-graph")],
                    ),
                    html.Div(
                        className="row",
                        style={"width": "80%", "margin-left": "12%"},
                        children=[
                            html.Div(
                                className="col",
                                children=[
                                    dcc.RadioItems(
                                        id="demand-profile-radio",
                                        options=[
                                            {"label": dem, "value": dem}
                                            for dem in excel_input_data[
                                                "Demand"
                                            ].columns
                                        ],
                                        value="dem_01",
                                        labelStyle={
                                            "display": "inline-block",
                                            "margin": 5,
                                        },
                                    )
                                ],
                            ),
                            html.Div(
                                className="col",  # style={"margin-left":70,"margin-right":10},
                                children=[
                                    dcc.RadioItems(
                                        id="generation-profile-radio",
                                        options=[
                                            {"label": gen, "value": gen}
                                            for gen in excel_input_data[
                                                "Generation"
                                            ].columns
                                        ],
                                        value="gen_01",
                                        labelStyle={
                                            "display": "inline-block",
                                            "margin": 5,
                                        },
                                    )
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
)
############################################################################################################################
output_layer = html.Div(
    id="param-row",
    className="row",
    style={"width": "100%", "margin-left": 5},
    children=[  # MAIN-LAYER-OUTER
        # ------------------------------------------------- LEFT COLUMN -------------------------------------------------------------#
        # /////////////////////////////////////// UPPER WINDOW ////////////////////////////////////#
        html.Div(
            id="upper-window-left",
            style=styles["upper-window"],
            className="col-sm-12 rounded",
            children=[  # LS_DIV
                html.Div(
                    className="row",
                    style={"width": "100%", "margin": "0px"},
                    children=[  # ROW
                        html.Div(
                            className="col",
                            style=styles["dropdown-upper"],
                            children=[
                                dcc.Dropdown(  # className="col-md-6 rounded",#className="list-group-item list-group-item-info",# DROPDOWN_01
                                    id="dropdown-left-scenarios",
                                    options=[
                                        {"label": i, "value": i}
                                        for i in global_sc_names
                                    ],
                                    value="SC_1",
                                )  # dropdown close
                            ],
                        ),
                        html.Div(
                            className="col",
                            style=styles["dropdown-upper"],
                            children=[
                                dcc.Dropdown(  # className="col-md-6 rounded",#className="list-group-item list-group-item-info",# DROPDOWN_01
                                    id="dropdown-left-tabs",
                                    options=[
                                        {"label": "Timeseries", "value": "Timeseries"},
                                        {"label": "Costs", "value": "Costs"},
                                        {"label": "Messages", "value": "Messages"},
                                    ],
                                    value="Timeseries",
                                )  # dropdown close
                            ],
                        ),
                    ],
                ),  # ROW
                # /////////////////////////////////////// OFFER SLIDER ////////////////////////////////////#
                html.Div(
                    className="row",
                    style={"width": "100%", "margin-top": "0px"},
                    children=[  # ROW
                        html.Div(
                            className="col-md-5 rounded",
                            style=styles["req-slider"],
                            children=[
                                dcc.Slider(
                                    id="offer-slider",
                                    min=0,
                                    max=5,
                                    marks={
                                        0: "BASE",
                                        1: "OFFER_1",
                                        2: "OFFER_2",
                                        3: "OFFER_3",
                                        4: "OFFER_4",
                                        5: "OFFER_5",
                                    },
                                    value=0,
                                )
                            ],
                        ),
                        html.Div(
                            className="col-md-6 rounded",
                            style=styles["checkboxes-output"],
                            children=[
                                dcc.Checklist(
                                    id="lower-graph-options",
                                    options=[
                                        {"label": " Capacity", "value": "Capacity"},
                                        {"label": " Requests", "value": "Requests"},
                                        {
                                            "label": " Flexibilities",
                                            "value": "Flexibilities",
                                        },
                                        {"label": " Starts", "value": "Starts"},
                                        {"label": " Prices", "value": "Prices"},
                                    ],
                                    values=["Capacity", "Requests"],
                                    labelStyle={
                                        "display": "inline",
                                        "margin-top": 20,
                                        "margin-left": 15,
                                        # 'font-family': 'Jazz LET, fantasy',
                                        "font-size": "20px",
                                        "color": "lightblack",
                                        "opacity": 0.8,
                                    },
                                )
                            ],
                        ),
                    ],
                ),
                ########################################## TOGGLE IN HERE ###################################
                html.Div(
                    className="row",
                    style={"width": "100%", "margin-top": "10px", "margin-left": "2px"},
                    children=[
                        html.Div(
                            id="upper-left-inside",
                            className="col",
                            style=styles["upper-inside"],
                            children=[],
                        )  # ROW
                    ],
                ),
                # /////////////////////////////////////// LOWER WINDOWS ////////////////////////////////////#
                html.Div(
                    className="row",
                    style={"margin-top": "15px"},
                    children=[
                        html.Div(
                            className="col-md-12 rounded",
                            id="lower-window-left-1",
                            style=styles["lower-window"],
                            children=[
                                html.Div(
                                    className="row",
                                    style={
                                        "width": "100%",
                                        "margin-top": "15px",
                                        "margin-left": "2px",
                                    },
                                    children=[
                                        html.Div(
                                            id="lower-left-inside",
                                            className="col",
                                            style=styles["lower-inside"],
                                            children=[],
                                        )  # ROW
                                    ],
                                ),
                                html.Div(
                                    className="row",
                                    style={"margin-top": "15px"},
                                    children=[
                                        html.Div(
                                            className="col-md-12 rounded",
                                            id="lower-window-left-3",
                                            style=styles["lower-window"],
                                            children=[
                                                html.Div(
                                                    className="row",
                                                    style={
                                                        "width": "100%",
                                                        "margin-top": "15px",
                                                        "margin-left": "2px",
                                                    },
                                                    children=[
                                                        html.Div(
                                                            id="battery-div",
                                                            className="col",
                                                            style=styles[
                                                                "lower-inside"
                                                            ],
                                                            children=[],
                                                        )  # ROW
                                                    ],
                                                )
                                            ],
                                        )
                                    ],
                                ),
                                html.Div(
                                    className="row",
                                    style={"margin-top": "10px"},
                                    children=[
                                        html.Div(
                                            className="col-md-12 rounded",
                                            id="lower-window-left-2",
                                            style=styles["price-window"],
                                            children=[
                                                html.Div(
                                                    className="row",
                                                    style={
                                                        "width": "100%",
                                                        "margin-top": "10px",
                                                        "margin-left": "2px",
                                                    },
                                                    children=[
                                                        html.Div(
                                                            id="price-div",
                                                            className="col",
                                                            style=styles[
                                                                "lower-inside"
                                                            ],
                                                            children=[],
                                                        )  # ROW
                                                    ],
                                                )
                                            ],
                                        )
                                    ],
                                ),
                                html.Div(
                                    className="row",
                                    style={"margin-top": "5px"},
                                    children=[
                                        html.Div(
                                            className="col-md-12 rounded",
                                            id="lower-window-left-3",
                                            style=styles["stats-window"],
                                            children=[
                                                html.Div(
                                                    className="row",
                                                    style={
                                                        "width": "100%",
                                                        "margin-top": "10px",
                                                        "margin-left": "2px",
                                                    },
                                                    children=[
                                                        html.Div(
                                                            id="stats-div",
                                                            className="col",
                                                            style=styles[
                                                                "lower-inside"
                                                            ],
                                                            children=[],
                                                        )  # ROW
                                                    ],
                                                )
                                            ],
                                        )
                                    ],
                                ),
                                ####### LOWER GRAPH ####
                            ],
                        )
                    ],
                ),
            ],
        )  # ROW
    ],
)
# ???+++???+++???+++???+++???+++???+++???+++???+++ C A L L B A C K S +++???+++???+++???+++???+++???+++???+++???+++???+++

######################################################  INIT  ##########################################################

# ---------------------------------------------------checkboxes_profile-----------------------------------------------
@app.callback(
    Output("profile-graph", "figure"),
    [
        Input("demand-profile-radio", "value"),
        Input("generation-profile-radio", "value"),
    ],
)
def profile_switch(demand_profile, generation_profile):
    demand_traces = dict()
    generation_traces = dict()
    for profile in excel_input_data["Generation"].columns:
        barplot = go.Bar(
            x=excel_input_data["Generation"].index,
            y=excel_input_data["Generation"].loc[:, generation_profile],
            name="Generation",
        )
        demand_traces[demand_profile] = barplot

    for profile in excel_input_data["Demand"].columns:
        lineplot = go.Scatter(
            x=excel_input_data["Demand"].index,
            y=excel_input_data["Demand"].loc[:, demand_profile],
            mode="lines+markers",
            marker={"size": 15, "line": {"width": 0.5, "color": "red"}},
            name="Demand",
        )
        generation_traces[generation_profile] = lineplot

    data = [demand_traces[demand_profile], generation_traces[generation_profile]]
    layout = go.Layout(
        width=890,
        height=220,
        showlegend=False,
        margin=go.Margin(l=70, r=10, b=40, t=25, pad=0),
        xaxis=dict(
            title="Timesteps",
            autorange=True,
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
            title="pdf",
            autorange=True,
            ticks="outside",
            tick0=0,
            dtick=5,
            ticklen=8,
            tickwidth=4,
            tickcolor="#000",
        ),
    )
    fig = go.Figure(data=data, layout=layout)
    return fig


# ----------------------------------------------------------any_clicks------------------------------------------
@app.callback(
    Output("any-clicks", "children"),
    [
        Input("TA-button", "n_clicks"),
        Input("MA-button", "n_clicks"),
        Input("EMS-button", "n_clicks"),
        Input("Prices-button", "n_clicks"),
    ],
)
def any_clicks_display(ta_click, ma_click, ems_click, prices_click):
    if ta_click or ma_click or ems_click or prices_click != 0:
        any_clicks = "Yes"
    else:
        any_clicks = "No"
    return json.dumps(any_clicks)


# -----------------------------------------------------toggle_layout-----------------------------------------------------
@app.callback(
    Output("toggle-window", "children"),
    [
        Input("run-button", "n_clicks"),
        Input("input-button", "n_clicks"),
        Input("output-button", "n_clicks"),
        Input("save-output", "children"),
    ],
)
def toggle_layout(run_click, input_click, output_click, save_event):
    global global_layer

    if run_click == 0:
        global_layer = "input_layer"
        return input_layer

    if run_click > 0 and global_layer == "input_layer":
        global_layer = "output_layer"
        return output_layer

    if input_click > 0 and global_layer == "output_layer":
        global_layer = "input_layer"
        return input_layer

    if save_event == True:
        global_layer = "output_layer"
        return output_layer


# ----------------------------------------------------------active-ems------------------------------------------
@app.callback(Output("active-ems", "children"), [Input("ems-slider", "value")])
def active_ems_update(ems_slider_value):
    active_ems = global_ems_names[:ems_slider_value]
    global_active_ems = active_ems
    return json.dumps(active_ems)


# ----------------------------------------------------------active_scenarios------------------------------------------
@app.callback(Output("active-sc", "children"), [Input("sc-slider", "value")])
def active_scenarios_update(sc_slider_value,):
    active_scenarios = global_sc_names[:sc_slider_value]
    global_active_sc = active_scenarios
    return json.dumps(active_scenarios)


# ----------------------------------------------------------run_name------------------------------------------
@app.callback(Output("run-name-output", "children"), [Input("input-field", "value")])
def run_name_update(run_name_update):
    return json.dumps(run_name_update)


# ----------------------------------------------------------scenario_tab_update------------------------------------------
@app.callback(Output("tab-bar", "children"), [Input("active-sc", "children")])
def scenarios_tabs_update(active_sc):
    try:
        active_sc = json.loads(active_sc)
    except TypeError:
        pass

    tabs = (
        dcc.Tabs(
            tabs=[{"label": i, "value": i} for i in active_sc],
            value="SC_1",
            id="sc-tabs",
        ),
    )
    return tabs


# ----------------------------------------------------------last_clicked------------------------------------------
@app.callback(
    Output("last-clicked", "children"),
    [
        Input("TA-button", "n_clicks_timestamp"),
        Input("MA-button", "n_clicks_timestamp"),
        Input("EMS-button", "n_clicks_timestamp"),
        Input("Prices-button", "n_clicks_timestamp"),
        Input("TA-button", "n_clicks"),
        Input("MA-button", "n_clicks"),
        Input("EMS-button", "n_clicks"),
        Input("Prices-button", "n_clicks"),
    ],
)
def last_click_display(
    ta_stamp,
    ma_stamp,
    ems_stamp,
    prices_stamp,
    ta_click,
    ma_click,
    ems_click,
    prices_click,
):
    last_clicked = ""
    d = {"ta": ta_stamp, "ma": ma_stamp, "ems": ems_stamp, "prices": prices_stamp}
    last_clicked = max(d, key=d.get)
    return json.dumps(last_clicked)


# ----------------------------------------------------------selected-sc------------------------------------------
@app.callback(Output("selected-sc", "children"), [Input("sc-tabs", "value")])
def selected_sc_display(tab):
    selected_sc = tab
    return json.dumps(selected_sc)


# ----------------------------------------------------------table_output------------------------------------------
@app.callback(
    Output("table-output", "children"),
    [
        Input("active-ems", "children"),
        Input("active-sc", "children"),
        Input("last-clicked", "children"),
        Input("TA-button", "n_clicks"),
        Input("MA-button", "n_clicks"),
        Input("EMS-button", "n_clicks"),
        Input("Prices-button", "n_clicks"),
        Input("sc-tabs", "value"),
    ],
    [State("selected-sc", "children")]
    # [State('updated-parameter-set', 'children'),]
)
def table_output(
    active_ems,
    active_sc,
    last_clicked,
    ta_click,
    ma_click,
    ems_click,
    prices_click,
    tabchange,
    selected_sc,
):
    global global_clicked_list
    global global_parameter_dict
    global global_timeseries_dict
    global EMS_table
    global TA_table
    global prices_table

    last_clicked = json.loads(last_clicked)
    try:
        selected_sc = json.loads(selected_sc)
        active_sc = json.loads(active_sc)
        active_ems = json.loads(active_ems)
    except:
        return

    tabledata = {}
    old_table = pd.DataFrame(index=parameter_index).to_dict()

    if tabchange == selected_sc:
        print("EQUAL")

    if tabchange != selected_sc:
        print("UNEQUAL")
        selected_sc = tabchange

    if selected_sc in global_agent_clicked_dict.keys():
        print(
            "selected_sc {} is in global_agent_clicked_dict.keys \n".format(selected_sc)
        )
        # pass
    else:
        global_agent_clicked_dict[selected_sc] = dict()

    for sc in active_sc:
        if selected_sc == sc:
            label = last_clicked + selected_sc
            if last_clicked == "ta":
                if label in global_agent_clicked_dict[selected_sc]:
                    tabledata = global_timeseries_dict[selected_sc][last_clicked]
                else:
                    tabledata = TA_table.to_dict()
                    global_agent_clicked_dict[selected_sc].update({label: label})

            elif last_clicked == "ma":
                if label in global_agent_clicked_dict[selected_sc]:
                    tabledata = global_timeseries_dict[selected_sc][last_clicked]
                else:
                    tabledata = MA_table.to_dict()
                    global_agent_clicked_dict[selected_sc].update({label: label})

            elif last_clicked == "prices":
                if label in global_agent_clicked_dict[selected_sc]:
                    tabledata = global_timeseries_dict[selected_sc][last_clicked]
                else:
                    tabledata = prices_table.to_dict()
                    global_agent_clicked_dict[selected_sc].update({label: label})

            elif last_clicked == "ems":
                new_columns = pd.DataFrame(0, columns=active_ems, index=parameter_index)
                for col in enumerate(new_columns):
                    new_columns[col[1]] = parameter_profiles.iloc[:, col[0]]
                new_columns = new_columns.to_dict()

                try:
                    old_table = global_parameter_dict[selected_sc][last_clicked]
                    if len(new_columns) >= len(old_table):
                        tabledata.update(new_columns)
                        tabledata.update(old_table)

                    else:
                        while len(old_table) >= len(new_columns):
                            drop = active_ems[-1]
                            del old_table[drop]
                            tabledata.update(old_table)
                except:
                    tabledata = new_columns
                    global_parameter_dict[selected_sc][last_clicked] = tabledata

    table = (
        dash_table.EditableTable(
            base_styles="numeric",
            id="editable-table",
            editable=True,
            dataframe=tabledata,
        ),
    )
    return table


# ----------------------------------------------------------dump_table_data-----------------------------------------------------
@app.callback(Output("p-bucket", "children"), [Input("editable-table", "dataframe")])
def dump_table_data(dataframe):
    return json.dumps(dataframe)


# ----------------------------------------------------------update_sets-----------------------------------------------------
@app.callback(
    Output("updated-parameter-set", "children"),
    [
        Input("active-sc", "children"),
        Input("last-clicked", "children"),
        Input("any-clicks", "children"),
        Input("selected-sc", "children"),
        Input("p-bucket", "children"),
    ],
)
def update_sets_after_user_input(
    active_sc, last_clicked, any_clicks, selected_sc, changed_table_data
):
    global global_parameter_dict
    global global_timeseries_dict

    any_clicks = json.loads(any_clicks)
    try:
        last_clicked = json.loads(last_clicked)
        selected_sc = json.loads(selected_sc)
    except:
        return

    if any_clicks == "No":
        return

    changed_parameter_data = json.loads(changed_table_data)

    if last_clicked == "ta" or last_clicked == "ma" or last_clicked == "prices":
        if selected_sc in global_timeseries_dict:
            if any_clicks == "Yes":
                global_timeseries_dict[selected_sc][
                    last_clicked
                ] = changed_parameter_data

        else:
            global_timeseries_dict[selected_sc] = dict()
            global_timeseries_dict[selected_sc][last_clicked] = changed_parameter_data

    if last_clicked == "ems":
        if selected_sc in global_parameter_dict:
            if any_clicks == "Yes":
                global_parameter_dict[selected_sc][
                    last_clicked
                ] = changed_parameter_data

        else:
            global_parameter_dict[selected_sc] = dict()
            global_parameter_dict[selected_sc][last_clicked] = changed_parameter_data

    return


# ----------------------------------------------------------write_flags_to_param_set-----------------------------------------------------
@app.callback(
    Output("flags", "children"),
    [Input("selected-sc", "children"), Input("last-clicked", "children")],
    [  # State('selected-sc', 'children'),
        State("input-field", "children"),
        State("active-sc", "children"),
        State("flex-split-flag", "value"),
        State("market-flags", "values"),
        State("negotiation-init", "value"),
        State("ta-strategy", "value"),
        State("ma-strategy", "value"),
        State("optimization-mode", "value"),
        State("internal-balance", "values"),
        State("flex-options", "values"),
    ],
)
def flags_2_parameter_set(
    selected_sc,
    last_clicked,
    run,
    active_sc,
    flex_split_flag,
    market_flags,
    neg_init,
    ta_strategy,
    ma_strategy,
    optimization_mode,
    internal_balance,
    flex_options,
):
    global global_parameter_dict
    try:
        selected_sc = json.loads(selected_sc)
        active_sc = json.loads(active_sc)
    except:
        return

    try:
        global_parameter_dict[selected_sc]
    except:
        global_parameter_dict[selected_sc] = dict()

    scenario_flag_set = pd.DataFrame()
    global_parameter_dict[selected_sc]["flags"] = dict()
    scenario_flag_set.loc["Flex_Request_Split", "TA"] = flex_split_flag
    scenario_flag_set.loc["Initiator", "TA"] = neg_init
    scenario_flag_set.loc["Initiator", "MA"] = neg_init
    scenario_flag_set.loc["Strategy", "TA"] = ta_strategy
    scenario_flag_set.loc["Strategy", "MA"] = ma_strategy
    for flag in market_flags:
        scenario_flag_set.loc[flag, "MA"] = flag
    scenario_flag_set.loc["Optimization", "TA"] = optimization_mode
    scenario_flag_set.loc["Internal_Balance", "TA"] = internal_balance
    for flag in flex_options:
        scenario_flag_set.loc[flag, "EMS"] = flag
    global_parameter_dict[selected_sc]["flags"] = scenario_flag_set

    return


# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$   run_simulation  $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$#
@app.callback(
    Output("run-output", "children"),
    [Input("run-button", "n_clicks")],
    [
        State("active-sc", "children"),
        State("active-ems", "children"),
        # State('input-field', 'value'),
    ],
)
def start_run(run_click, active_scenarios, active_ems):

    if run_click <= 0:
        return

    global global_timeseries_dict
    global global_parameter_dict
    global global_flag_dict
    global global_timeperiods
    generation_curve = None
    demand_curve = None

    try:
        active_scenarios = json.loads(active_scenarios)
        active_ems = json.loads(active_ems)
    except:
        return

    for scenario in active_scenarios:
        ma_dfx = dict()
        ta_dfx = dict()
        for item, request in zip(
            global_timeseries_dict[scenario]["ma"].items(), global_req_names
        ):
            df = pd.Series(item[1])
            df = pd.to_numeric(df)
            df.index.name = "time"
            ma_dfx[request] = df

        for item, request in zip(
            global_timeseries_dict[scenario]["ta"].items(), global_req_names
        ):
            df = pd.Series(item[1])
            df = pd.to_numeric(df)
            df.index.name = "time"
            ta_dfx[request] = df

        multi_ix = pd.MultiIndex.from_product(
            [global_timeperiods, active_ems], names=["time", "ems"]
        )
        multi_ix_df = pd.DataFrame(index=multi_ix, columns=["dem", "gen"])
        global_timeseries_dict[scenario]["costs"] = dict()
        global_timeseries_dict[scenario]["messages"] = dict()
        global_timeseries_dict[scenario]["ems"] = dict()
        global_timeseries_dict[scenario]["stats"] = dict()

        for offer in global_offer_names:
            global_timeseries_dict[scenario]["ta"][offer] = dict()
            global_timeseries_dict[scenario]["ems"][offer] = dict()

        try:
            global_parameter_dict[scenario]["ems"]
        except KeyError:
            break

        for ems in active_ems:
            if global_parameter_dict[scenario]["ems"][ems]["Generation-Profile"] == 1:
                generation_curve = excel_input_data["Generation"].loc[:, "gen_01"]
            elif global_parameter_dict[scenario]["ems"][ems]["Generation-Profile"] == 2:
                generation_curve = excel_input_data["Generation"].loc[:, "gen_02"]
            elif global_parameter_dict[scenario]["ems"][ems]["Generation-Profile"] == 3:
                generation_curve = excel_input_data["Generation"].loc[:, "gen_03"]

            if global_parameter_dict[scenario]["ems"][ems]["Demand-Profile"] == 1:
                demand_curve = excel_input_data["Demand"].loc[:, "dem_01"]
            elif global_parameter_dict[scenario]["ems"][ems]["Demand-Profile"] == 2:
                demand_curve = excel_input_data["Demand"].loc[:, "dem_02"]
            elif global_parameter_dict[scenario]["ems"][ems]["Demand-Profile"] == 3:
                demand_curve = excel_input_data["Demand"].loc[:, "dem_03"]

            ems_df = pd.DataFrame()
            ems_df["dem"] = demand_curve * float(
                global_parameter_dict[scenario]["ems"][ems]["Demand-Total"]
            )
            ems_df["gen"] = generation_curve * float(
                global_parameter_dict[scenario]["ems"][ems]["Generation-Total"]
            )

            for time in global_timeperiods:
                multi_ix_df.at[(time, ems), "dem"] = ems_df.loc[time, "dem"]
                multi_ix_df.at[(time, ems), "gen"] = ems_df.loc[time, "gen"]
                multi_ix_df.at[(time, ems), "mp"] = global_timeseries_dict[scenario][
                    "prices"
                ][("MP_" + ems)][str(time)]
                multi_ix_df.at[(time, ems), "fit"] = global_timeseries_dict[scenario][
                    "prices"
                ][("FIT_" + ems)][str(time)]

        for offer in global_offer_names:
            global_timeseries_dict[scenario]["ems"][offer].update(multi_ix_df)
            global_timeseries_dict[scenario]["costs"][offer] = dict()
            global_timeseries_dict[scenario]["stats"][offer] = dict()

        for item, request in zip(
            global_timeseries_dict[scenario]["ma"].items(), global_req_names
        ):
            global_timeseries_dict[scenario]["ma"][request] = ma_dfx[request]

        for item, request in zip(
            global_timeseries_dict[scenario]["ta"].items(), global_req_names
        ):
            global_timeseries_dict[scenario]["ta"][request] = ta_dfx[request]

        env = Environment(
            timeperiods=global_timeperiods,
            timeseries=global_timeseries_dict[scenario],
            parameter=global_parameter_dict[scenario],
            active_ems=active_ems,
            scenario_name=scenario,
        )
        output = env.step()

        print("OUTSIDE UTILS")

        for offer in global_offer_names:
            global_timeseries_dict[scenario]["ems"][offer] = output[offer]["timeseries"]
            global_timeseries_dict[scenario]["ems"][offer] = (
                global_timeseries_dict[scenario]["ems"][offer]
                .groupby(level="time")
                .reset_index()
            )
            global_timeseries_dict[scenario]["ems"][offer] = global_timeseries_dict[
                scenario
            ]["ems"][offer].shift(1)
            global_timeseries_dict[scenario]["costs"][offer] = output[offer]["costs"]
            global_timeseries_dict[scenario]["stats"][offer] = output[offer]["stats"]
        print("BASE:{}".format(global_timeseries_dict[scenario]["ems"]["BASE"]))
    return


# ______________________________________________________    M A I N   ______________________________________________________#
#####################################################  UPPER WINDOW LEFT ###################################################
@app.callback(
    Output("upper-left-inside", "children"),
    [
        Input("run-button", "n_clicks"),
        Input("offer-slider", "value"),
        Input("dropdown-left-tabs", "value"),
        Input("dropdown-left-scenarios", "value"),
        Input("lower-graph-options", "values"),
    ],
    [State("run-name-output", "children")],
)
def upper_left_inside_update(
    run_button_clicked,
    offer_slider_value,
    tab_name,
    scenario_name,
    checkbox,
    run_name_update,
):
    ems_plot_data = pd.DataFrame()
    costs_data = pd.DataFrame()
    stats_data = pd.DataFrame()
    run_name = json.loads(run_name_update)

    try:
        ems_plot_data = global_timeseries_dict[scenario_name]["ems"]
        pass
    except:
        return

    for sc in global_sc_names:
        if sc == scenario_name:
            print(scenario_name)
            costs_data = global_timeseries_dict[scenario_name]["costs"]
            stats_data = global_timeseries_dict[scenario_name]["stats"]

            for offer in enumerate(ems_plot_data.keys()):
                if offer_slider_value == offer[0]:
                    act_offer = offer[1]
                    ems_plot_data = global_timeseries_dict[scenario_name]["ems"][
                        offer[1]
                    ]
                else:
                    pass

    if tab_name == "Timeseries":

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

        demand_traces = dict()
        demand_colors = dict()
        for ems in enumerate(global_ems_names):
            demand_colors[ems[1]] = blue_colors[ems[0]]

        for ems in ems_plot_data.index.get_level_values("ems").unique():

            barplot = go.Bar(
                x=global_SOC_timeperiods,
                y=[ems_plot_data.loc[(t, ems), "_Demand"] for t in global_timeperiods],
                textposition="auto",
                hoverinfo="y+text",
                hoverlabel=dict(font=dict(color="black")),
                hovertext=("Dem_{}".format(ems)),
                textfont=dict(color="black"),
                name=("Demand_{}".format(ems)),
                marker=go.Marker(
                    color=demand_colors[ems],
                    line=dict(color="rgb(8,48,107)", width=1.5),
                ),
                legendgroup=ems,
            )
            demand_traces[ems] = barplot

        generation_traces = dict()
        generation_colors = dict()
        for ems in enumerate(global_ems_names):
            generation_colors[ems[1]] = yellow_colors[ems[0]]
            # yellow_colors[ems[0]]
        for ems in ems_plot_data.index.get_level_values("ems").unique():

            barplot = go.Bar(
                x=global_SOC_timeperiods,
                y=[
                    ems_plot_data.loc[(t, ems), "_Generation"]
                    for t in global_timeperiods
                ],
                textposition="auto",
                hoverinfo="y+text",
                hoverlabel=dict(font=dict(color="black")),
                hovertext=("Gen_{}".format(ems)),
                textfont=dict(color="black"),
                name=("Generation_{}".format(ems)),
                marker=go.Marker(
                    color=generation_colors[ems],
                    line=dict(color="rgb(8,48,107)", width=1.5),
                ),
                legendgroup=ems,
            )
            generation_traces[ems] = barplot

        buy_traces = dict()
        buy_colors = dict()
        for ems in enumerate(global_ems_names):
            buy_colors[ems[1]] = red_colors[ems[0]]
            # purple_colors[ems[0]]
        for ems in ems_plot_data.index.get_level_values("ems").unique():
            barplot = go.Bar(
                x=global_SOC_timeperiods,
                y=[
                    ems_plot_data.loc[(t, ems), "Net_Demand"]
                    for t in global_timeperiods
                ],
                textposition="auto",
                hoverinfo="y+text",
                hoverlabel=dict(font=dict(color="black")),
                hovertext=("Net_Dem_{}".format(ems)),
                textfont=dict(color="black"),
                name=("Net_Demand_{}".format(ems)),
                marker=go.Marker(
                    color=buy_colors[ems], line=dict(color="rgb(8,48,107)", width=1.5)
                ),
                legendgroup=ems,
            )
            buy_traces[ems] = barplot

        sell_traces = dict()
        sell_colors = dict()
        for ems in enumerate(global_ems_names):
            sell_colors[ems[1]] = cyan_colors[ems[0]]
        for ems in ems_plot_data.index.get_level_values("ems").unique():
            barplot = go.Bar(
                x=global_SOC_timeperiods,
                y=[
                    ems_plot_data.loc[(t, ems), "Net_Generation"]
                    for t in global_timeperiods
                ],
                textposition="auto",
                hoverinfo="y+text",
                hoverlabel=dict(font=dict(color="black")),
                hovertext=("Net_Gen_{}".format(ems)),
                textfont=dict(color="black"),
                name=("Net_Generation_{}".format(ems)),
                marker=go.Marker(
                    color=sell_colors[ems], line=dict(color="rgb(8,48,107)", width=1.5)
                ),
                legendgroup=ems,
            )
            sell_traces[ems] = barplot

        flex_pos_req_trace = dict()
        flex_pos_req_colors = dict()
        for ems in enumerate(global_ems_names):
            flex_pos_req_colors[ems[1]] = "black"
        for ems in ems_plot_data.index.get_level_values("ems").unique():
            barplot = go.Bar(
                x=global_SOC_timeperiods,
                y=[
                    ems_plot_data.loc[(t, ems), "Request_POS"]
                    for t in global_timeperiods
                ],
                textposition="auto",
                hoverinfo="y+text",
                hoverlabel=dict(font=dict(color="white")),
                hovertext=("POS_Req_{}".format(ems)),
                textfont=dict(color="black"),
                name=("Positive_Flex_Request{}".format(ems)),
                marker=go.Marker(
                    color=flex_pos_req_colors[ems],
                    line=dict(color="lightblue", width=2.5),
                ),
                legendgroup="POS_REQ",
            )
            flex_pos_req_trace[ems] = barplot

        flex_neg_req_trace = dict()
        flex_neg_req_colors = dict()
        for ems in enumerate(global_ems_names):
            flex_neg_req_colors[ems[1]] = "black"
        for ems in ems_plot_data.index.get_level_values("ems").unique():
            barplot = go.Bar(
                x=global_SOC_timeperiods,
                y=[
                    ems_plot_data.loc[(t, ems), "Request_NEG"]
                    for t in global_timeperiods
                ],
                textposition="auto",
                hoverinfo="y+text",
                hoverlabel=dict(font=dict(color="white")),
                hovertext=("NEG_Req_{}".format(ems)),
                textfont=dict(color="black"),
                name=("Negative_Flex_Request{}".format(ems)),
                marker=go.Marker(
                    color=flex_neg_req_colors[ems], line=dict(color="yellow", width=2.5)
                ),
                legendgroup="NEG_REQ",
            )
            flex_neg_req_trace[ems] = barplot

        data = []
        data += [
            demand_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]
        data += [
            generation_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]
        data += [
            buy_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]
        data += [
            sell_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]
        data += [
            flex_pos_req_trace[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]
        data += [
            flex_neg_req_trace[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]

        layout = go.Layout(
            title="Energy Profiles",
            height=560,
            barmode="relative",
            bargap=0,
            showlegend=True,
            legend=dict(orientation="h"),
            margin=go.Margin(l=40, r=40, b=40, t=25, pad=0),
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
                dtick=2,
                ticklen=8,
                tickwidth=4,
                tickcolor="#000",
                hoverformat=".2f",
                showgrid=True,
                gridcolor="#bdbdbd",
                gridwidth=1,
            ),
        )
        timeseries_output = (
            dcc.Graph(id="upper-graph", figure=go.Figure(data=data, layout=layout)),
        )
        return timeseries_output

    if tab_name == "Costs":
        costs_traces = dict()
        costs_colors = dict()

        barplot = go.Bar(
            x=[offer for offer in global_offer_names],
            y=[costs_data[offer] for offer in global_offer_names],
            name="Costs/Revenues",
            marker=go.Marker(color="darkslateblue"),
        )
        costs_traces = barplot

        data = []
        data += [costs_traces]

        layout = go.Layout(
            title="Battery Scenario: {scenario_name}".format(),
            height=560,
            barmode="relative",
            showlegend=True,
            legend=dict(orientation="h"),
            margin=go.Margin(l=40, r=40, b=40, t=25, pad=0),
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
                title="Euro",
                autorange=True,
                ticks="outside",
                tick0=0,
                dtick=1,
                ticklen=8,
                tickwidth=4,
                tickcolor="#000",
            ),
        )
        cost_output = (
            dcc.Graph(id="upper-graph", figure=go.Figure(data=data, layout=layout)),
        )
        return cost_output


######################################################  LOWER PLOT LEFT ###################################################
@app.callback(
    Output("lower-left-inside", "children"),
    [
        Input("run-button", "n_clicks"),
        Input("offer-slider", "value"),
        Input("dropdown-left-tabs", "value"),
        Input("dropdown-left-scenarios", "value"),
        Input("lower-graph-options", "values"),
    ],
)
def lower_left_inside_update(
    run_button_clicked, offer_slider_value, tab_name, scenario_name, checkbox
):
    ems_plot_data = pd.DataFrame()
    request_timeseries = pd.Series(0, index=global_timeperiods)

    try:
        ems_plot_data = global_timeseries_dict[scenario_name]["ems"]

        pass
    except:
        return

    for sc in global_sc_names:
        if sc == scenario_name:
            for offer in enumerate(ems_plot_data.keys()):
                if offer_slider_value == offer[0]:
                    act_offer = offer[1]
                    ems_plot_data = global_timeseries_dict[scenario_name]["ems"][
                        offer[1]
                    ]

                    if offer_slider_value != 0:
                        request_nr = offer_slider_value - 1
                        request_timeseries = global_timeseries_dict[scenario_name][
                            "ma"
                        ][global_req_names[request_nr]]
                else:
                    pass

    grey_colors = [
        "lightgray",
        "gray",
        "	lightslategray",
        "silver",
        "dimgray",
        "lightslategray",
        "gainsboro",
        "darkslategray",
        "black",
    ]
    cyan_colors = [
        "aquamarine",
        "darkcyan",
        "aqua",
        "turquoise",
        "teal",
        "darkturquoise",
        "paleturquoise",
        "lightseagreen",
        "cyan",
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
    green_colors = [
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
    red_colors = [
        "lightsalmon",
        "indianred",
        "darkred",
        "salmon",
        "crimson",
        "darkred",
        "darksalmon",
        "red",
        "firebrick",
    ]
    dark_green_colors = [
        "olivedrab",
        "darkgreen",
        "springgreen",
        "darkgreen",
        "lawngreen",
        "limegreen",
        "springgreen",
        "mediumseagreen",
        "seagreen",
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
    purple_colors = [
        "mediumvioletred",
        "blueviolet",
        "indigo",
        "plum",
        "fuchsia",
        "hotpink",
        "deeppink",
        "mediumorchid",
        "mediumpurple",
    ]

    charge_traces = dict()
    charge_colors = dict()
    for ems in enumerate(global_ems_names):
        charge_colors[ems[1]] = dark_green_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        barplot = go.Bar(
            x=global_SOC_timeperiods,
            y=[
                ems_plot_data.loc[(t, ems), "Battery_Charged"]
                for t in global_timeperiods
            ],
            textposition="auto",
            hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="white")),
            hovertext=("Char_{}".format(ems)),
            textfont=dict(color="black"),
            name=("Charging_{}".format(ems)),
            marker=go.Marker(
                color=charge_colors[ems], line=dict(color="rgb(8,48,107)", width=1.5)
            ),
            legendgroup=ems,
        )
        charge_traces[ems] = barplot

    discharge_traces = dict()
    discharge_colors = dict()
    for ems in enumerate(global_ems_names):
        discharge_colors[ems[1]] = orange_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        barplot = go.Bar(
            x=global_SOC_timeperiods,
            y=[
                ems_plot_data.loc[(t, ems), "Battery_Discharged"]
                for t in global_timeperiods
            ],
            textposition="auto",
            hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="white")),
            hovertext=("Dichar_{}".format(ems)),
            textfont=dict(color="black"),
            name=("Discharging_{}".format(ems)),
            marker=go.Marker(
                color=discharge_colors[ems], line=dict(color="rgb(8,48,107)", width=1.5)
            ),
            legendgroup=ems,
        )
        discharge_traces[ems] = barplot

    cap_traces = dict()
    cap_colors = dict()
    for ems in enumerate(global_ems_names):
        cap_colors[ems[1]] = purple_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        lineplot = go.Scatter(
            x=global_SOC_timeperiods,
            y=[ems_plot_data.loc[(t, ems), "Battery_SOC"] for t in global_timeperiods],
            textposition="auto",
            hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="white")),
            hovertext=("Cap_{}".format(ems)),
            textfont=dict(color="black"),
            name=("Capacity_{}".format(ems)),
            marker=go.Marker(color=cap_colors[ems], line=dict(width=3)),
            legendgroup=ems,
            yaxis="y2",
        )
        cap_traces[ems] = lineplot

    batt_switched_on_traces = dict()
    batt_switched_on_colors = dict()
    for ems in enumerate(global_ems_names):
        batt_switched_on_colors[ems[1]] = cyan_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        markerplot = go.Scatter(
            x=global_timeperiods,
            y=[
                ems_plot_data.loc[(t, ems), "Battery_Switched"]
                for t in global_timeperiods
            ],
            name=("{}_b_on".format(ems)),
            mode="markers",
            marker=go.Marker(
                color=batt_switched_on_colors[ems], size=12, line=dict(color="black")
            ),
        )
        batt_switched_on_traces[ems] = markerplot

    batt_flex_charge_traces = dict()
    batt_flex_charge_colors = dict()
    for ems in enumerate(global_ems_names):
        batt_flex_charge_colors[ems[1]] = cyan_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        barplot = go.Bar(
            x=global_SOC_timeperiods,
            y=[
                ems_plot_data.loc[(t, ems), "Battery_Flexibility_POS"]
                for t in global_timeperiods
            ],
            textposition="auto",
            hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="white")),
            hovertext=("Batt_Pos_Flex_{}".format(ems)),
            textfont=dict(color="black"),
            name=("Battery_Pos_Flex_{}".format(ems)),
            marker=go.Marker(
                color=batt_flex_charge_colors[ems],
                line=dict(color="rgb(8,48,107)", width=1.5),
            ),
            legendgroup=ems,
        )
        batt_flex_charge_traces[ems] = barplot

    batt_flex_discharge_traces = dict()
    batt_flex_discharge_colors = dict()
    for ems in enumerate(global_ems_names):
        batt_flex_discharge_colors[ems[1]] = orange_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        barplot = go.Bar(
            x=global_SOC_timeperiods,
            y=[
                ems_plot_data.loc[(t, ems), "Battery_Flexibility_NEG"]
                for t in global_timeperiods
            ],
            textposition="auto",
            hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="white")),
            hovertext=("Batt_Neg_Flex_{}".format(ems)),
            textfont=dict(color="black"),
            name=("Battery_Pos_Flex_{}".format(ems)),
            marker=go.Marker(
                color=batt_flex_discharge_colors[ems],
                line=dict(color="rgb(8,48,107)", width=1.5),
            ),
            legendgroup=ems,
        )
        batt_flex_discharge_traces[ems] = barplot

    requests_traces = dict()
    requests_color = "black"
    flex_request_plot = go.Bar(
        x=global_SOC_timeperiods,
        y=request_timeseries,
        name="Flex-Requests",
        marker=go.Marker(color=requests_color, line=dict(color="red", width=3.5)),
    )

    data = []

    if "Requests" in checkbox:
        data += [flex_request_plot]

    if "Capacity" in checkbox:
        data += [
            cap_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]
        data += [
            charge_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]
        data += [
            discharge_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]

    if "Starts" in checkbox:
        data += [
            batt_switched_on_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]

    if "Flexibilities" in checkbox:
        data += [
            batt_flex_charge_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]
        data += [
            batt_flex_discharge_traces[ems]
            for ems in ems_plot_data.index.get_level_values("ems").unique()
        ]

    layout = go.Layout(
        title="Battery Curves",
        height=350,
        barmode="relative",
        bargap=0,
        showlegend=True,
        legend=dict(orientation="h"),
        margin=go.Margin(l=40, r=40, b=40, t=25, pad=0),
        xaxis=dict(
            ticks="outside",
            tick0=-1,
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
            showgrid=True,
            gridcolor="#bdbdbd",
            gridwidth=1,
        ),
        yaxis2=dict(
            title="kWh",
            autorange=True,
            ticks="outside",
            tick0=0,
            dtick=2,
            ticklen=8,
            tickwidth=4,
            tickcolor="#000",
            overlaying="y",
            side="right",
        ),
    )

    output = (dcc.Graph(id="lower-graph", figure=go.Figure(data=data, layout=layout)),)
    return output


######################################################  BASE BATTERY PLOT LEFT ###################################################
@app.callback(
    Output("battery-div", "children"),
    [
        Input("run-button", "n_clicks"),
        Input("dropdown-left-tabs", "value"),
        Input("dropdown-left-scenarios", "value"),
    ],
)
def base_battery_update(run_button_clicked, tab_name, scenario_name):
    ems_plot_data = pd.DataFrame()
    request_timeseries = pd.Series(0, index=global_timeperiods)
    try:
        ems_plot_data = global_timeseries_dict[scenario_name]["ems"]
        pass
    except:
        return

    for sc in global_sc_names:
        if sc == scenario_name:
            ems_plot_data = global_timeseries_dict[scenario_name]["ems"]["BASE"]

    grey_colors = [
        "lightgray",
        "gray",
        "	lightslategray",
        "silver",
        "dimgray",
        "lightslategray",
        "gainsboro",
        "darkslategray",
        "black",
    ]
    cyan_colors = [
        "aquamarine",
        "darkcyan",
        "aqua",
        "turquoise",
        "teal",
        "darkturquoise",
        "paleturquoise",
        "lightseagreen",
        "cyan",
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
    green_colors = [
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
    red_colors = [
        "lightsalmon",
        "indianred",
        "darkred",
        "salmon",
        "crimson",
        "darkred",
        "darksalmon",
        "red",
        "firebrick",
    ]
    dark_green_colors = [
        "olivedrab",
        "darkgreen",
        "springgreen",
        "darkgreen",
        "lawngreen",
        "limegreen",
        "springgreen",
        "mediumseagreen",
        "seagreen",
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
    purple_colors = [
        "mediumvioletred",
        "blueviolet",
        "indigo",
        "plum",
        "fuchsia",
        "hotpink",
        "deeppink",
        "mediumorchid",
        "mediumpurple",
    ]

    charge_traces = dict()
    charge_colors = dict()
    for ems in enumerate(global_ems_names):
        charge_colors[ems[1]] = green_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        barplot = go.Bar(
            x=global_SOC_timeperiods,
            y=[
                ems_plot_data.loc[(t, ems), "Battery_Charged"]
                for t in global_timeperiods
            ],
            textposition="auto",
            hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="white")),
            hovertext=("Char_{}".format(ems)),
            textfont=dict(color="black"),
            name=("Charging_{}".format(ems)),
            marker=go.Marker(
                color=charge_colors[ems], line=dict(color="rgb(8,48,107)", width=1.5)
            ),
            legendgroup=ems,
        )
        charge_traces[ems] = barplot

    discharge_traces = dict()
    discharge_colors = dict()
    for ems in enumerate(global_ems_names):
        discharge_colors[ems[1]] = brown_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        barplot = go.Bar(
            x=global_SOC_timeperiods,
            y=[
                ems_plot_data.loc[(t, ems), "Battery_Discharged"]
                for t in global_timeperiods
            ],
            textposition="auto",
            hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="white")),
            hovertext=("Dichar_{}".format(ems)),
            textfont=dict(color="black"),
            name=("Discharging_{}".format(ems)),
            marker=go.Marker(
                color=discharge_colors[ems], line=dict(color="rgb(8,48,107)", width=1.5)
            ),
            legendgroup=ems,
        )
        discharge_traces[ems] = barplot

    cap_traces = dict()
    cap_colors = dict()
    for ems in enumerate(global_ems_names):
        cap_colors[ems[1]] = purple_colors[ems[0]]
    for ems in ems_plot_data.index.get_level_values("ems").unique():
        lineplot = go.Scatter(
            x=global_SOC_timeperiods,
            y=[ems_plot_data.loc[(t, ems), "Battery_SOC"] for t in global_timeperiods],
            textposition="auto",
            hoverinfo="y+text",
            hoverlabel=dict(font=dict(color="white")),
            hovertext=("Cap_{}".format(ems)),
            textfont=dict(color="black"),
            name=("Capacity_{}".format(ems)),
            marker=go.Marker(color=cap_colors[ems], line=dict(width=3)),
            legendgroup=ems,
            yaxis="y2",
        )
        cap_traces[ems] = lineplot

    data = []
    data += [
        cap_traces[ems] for ems in ems_plot_data.index.get_level_values("ems").unique()
    ]
    data += [
        charge_traces[ems]
        for ems in ems_plot_data.index.get_level_values("ems").unique()
    ]
    data += [
        discharge_traces[ems]
        for ems in ems_plot_data.index.get_level_values("ems").unique()
    ]

    layout = go.Layout(
        title="Baseline Battery Curves",
        height=350,
        barmode="relative",
        bargap=0,
        showlegend=True,
        legend=dict(orientation="h"),
        margin=go.Margin(l=40, r=40, b=40, t=25, pad=0),
        xaxis=dict(
            ticks="outside",
            tick0=-1,
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
            showgrid=True,
            gridcolor="#bdbdbd",
            gridwidth=1,
        ),
        yaxis2=dict(
            title="kWh",
            autorange=True,
            ticks="outside",
            tick0=0,
            dtick=2,
            ticklen=8,
            tickwidth=4,
            tickcolor="#000",
            overlaying="y",
            side="right",
        ),
    )

    output = (
        dcc.Graph(id="base-battery-graph", figure=go.Figure(data=data, layout=layout)),
    )
    return output


######################################################  PRICE PLOT LEFT ###################################################
@app.callback(
    Output("price-div", "children"),
    [
        Input("run-button", "n_clicks"),
        Input("offer-slider", "value"),
        Input("dropdown-left-tabs", "value"),
        Input("dropdown-left-scenarios", "value"),
        Input("lower-graph-options", "values"),
    ],
)
def price_plots_update(
    run_button_clicked, offer_slider_value, tab_name, scenario_name, checkbox
):
    ems_plot_data = pd.DataFrame()
    request_timeseries = pd.Series(0, index=global_timeperiods)
    try:
        ems_plot_data = global_timeseries_dict[scenario_name]["ems"]
        pass
    except:
        return

    for sc in global_sc_names:
        if sc == scenario_name:
            print(scenario_name)
            for offer in enumerate(ems_plot_data.keys()):
                if offer_slider_value == offer[0]:
                    act_offer = offer[1]
                    ems_plot_data = global_timeseries_dict[scenario_name]["ems"][
                        offer[1]
                    ]
                    if offer_slider_value != 0:
                        request_nr = offer_slider_value - 1
                        request_timeseries = global_timeseries_dict[scenario_name][
                            "ma"
                        ][global_req_names[request_nr]]
                else:
                    pass

    grey_colors = [
        "lightgray",
        "gray",
        "	lightslategray",
        "silver",
        "dimgray",
        "lightslategray",
        "gainsboro",
        "darkslategray",
        "black",
    ]
    cyan_colors = [
        "aquamarine",
        "darkcyan",
        "aqua",
        "turquoise",
        "teal",
        "darkturquoise",
        "paleturquoise",
        "lightseagreen",
        "cyan",
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
    green_colors = [
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
    red_colors = [
        "lightsalmon",
        "indianred",
        "darkred",
        "salmon",
        "crimson",
        "darkred",
        "darksalmon",
        "red",
        "firebrick",
    ]
    dark_green_colors = [
        "olivedrab",
        "darkgreen",
        "springgreen",
        "darkgreen",
        "lawngreen",
        "limegreen",
        "springgreen",
        "mediumseagreen",
        "seagreen",
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

    mp_prices_traces = dict()
    fit_prices_traces = dict()

    mp_prices_colors = dict()
    fit_prices_colors = dict()

    for ems in enumerate(global_ems_names):
        mp_prices_colors[ems[1]] = green_colors[ems[0]]
        fit_prices_colors[ems[1]] = red_colors[ems[0]]

    for ems in ems_plot_data.index.get_level_values("ems").unique():
        mp_lineplot = go.Scatter(
            x=global_SOC_timeperiods,
            y=[ems_plot_data.loc[(t, ems), "Price_Market"] for t in global_timeperiods],
            name=("{}_mp".format(ems)),
            marker=go.Marker(color=mp_prices_colors[ems]),
        )
        mp_prices_traces[ems] = mp_lineplot

        fit_lineplot = go.Scatter(
            x=global_SOC_timeperiods,
            y=[ems_plot_data.loc[(t, ems), "Price_Feedin"] for t in global_timeperiods],
            name=("{}_fit".format(ems)),
            marker=go.Marker(color=fit_prices_colors[ems]),
        )
        fit_prices_traces[ems] = fit_lineplot

    data = []
    data += [
        mp_prices_traces[ems]
        for ems in ems_plot_data.index.get_level_values("ems").unique()
    ]
    data += [
        fit_prices_traces[ems]
        for ems in ems_plot_data.index.get_level_values("ems").unique()
    ]

    layout = go.Layout(
        height=220,
        barmode="relative",
        bargap=0,
        showlegend=True,
        legend=dict(orientation="h"),
        margin=go.Margin(l=40, r=40, b=40, t=5, pad=0),
        xaxis=dict(
            ticks="outside",
            tick0=-1,
            dtick=1,
            ticklen=8,
            tickwidth=4,
            tickcolor="#000",
            showgrid=True,
            gridcolor="#bdbdbd",
            gridwidth=1,
        ),
        yaxis=dict(
            title="Euro/kWh",
            autorange=True,
            ticks="outside",
            tick0=0,
            dtick=5,
            ticklen=8,
            tickwidth=4,
            tickcolor="#000",
            showgrid=True,
            gridcolor="#bdbdbd",
            gridwidth=1,
        ),
    )

    output = (dcc.Graph(id="price-graph", figure=go.Figure(data=data, layout=layout)),)
    return output


###################################################### TABLE DATA PICKLE ################################################
@app.callback(
    Output("stats-div", "children"),
    [
        Input("run-button", "n_clicks"),
        Input("offer-slider", "value"),
        Input("dropdown-left-tabs", "value"),
        Input("dropdown-left-scenarios", "value"),
    ],
)
def generate_table(run_button_clicked, offer_slider_value, tab_name, scenario_name):
    ems_plot_data = pd.DataFrame()
    costs_data = pd.DataFrame()
    stats_data = pd.DataFrame()

    try:
        ems_plot_data = global_timeseries_dict[scenario_name]["ems"]
        pass
    except:
        return

    for sc in global_sc_names:
        if sc == scenario_name:
            costs_data = pd.DataFrame(global_timeseries_dict[scenario_name]["costs"])
            stats_data = global_timeseries_dict[scenario_name]["stats"]
            for offer in enumerate(ems_plot_data.keys()):
                if offer_slider_value == offer[0]:
                    act_offer = offer[1]
                    ems_plot_data = global_timeseries_dict[scenario_name]["ems"][
                        offer[1]
                    ]
                    ems_plot_data.reset_index()

                    if offer_slider_value != 0:
                        request_nr = offer_slider_value - 1
                        request_timeseries = global_timeseries_dict[scenario_name][
                            "ma"
                        ][global_req_names[request_nr]]
                else:
                    pass

    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in ems_plot_data.columns])]
        +
        # Body
        [
            html.Tr(
                [html.Td(ems_plot_data.iloc[i][col]) for col in ems_plot_data.columns]
            )
            for i in range(min(len(ems_plot_data), len(ems_plot_data)))
        ]
    )

    return generate_table(df)


###############################################################################################################################
if __name__ == "__main__":
    app.run_server(debug=False, port=9100)
