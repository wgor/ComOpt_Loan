from ui.utils import data_import
from globals import *
from model.environment import *
from ui.styles import styles
from ui.layout import *
from app import app
# Dash packages
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt
import plotly.graph_objs as go
import pandas as pd
import copy
import json as json
import random
import flask

app.layout = html.Div(style=styles['main'],children=[#app.layout
############################################## TOP ROW ############################################################
html.Div(id="outer-container",className="container-fluid", children=[#className="container-fluid"
    html.Div(id="top-container",className="container-fluid rounded",style=styles['top-container'],children=[#className="container-fluid"
        html.Div(className="row",children=[#TOP ROW
            html.Div(className="col-md-2",style=styles['header'], children=[#HEADER-SLIDER
                "COMOPT USER INTERFACE"
                    ]),#HEADER-SLIDER ENDS
            html.Div(className="col-md-2", style=styles['top-slider'], children=[#SC-SLIDER
                html.Label('Number of Scenarios'),
                dcc.Slider(id="sc-slider",
                    min=1,max=9,
                    marks={i: '{}'.format(i) for i in range(1, 10)},
                    value=1,
                    ),
                ]),#SC-SLIDER ENDS
            html.Div(className="col-md-2", style=styles['top-slider'], children=[#EMS-SLIDER
                html.Label('Activate EM-Systems'),
                dcc.Slider(id="ems-slider",
                    min=1,max=9,
                    marks={i: '{}'.format(i) for i in range(1, 10)},
                    value=1,
                    ),
                ]),#EMS-SLIDER ENDS

            html.Div(className="col-md-2", style=styles['input-name'], children=[ #BUTTONS
                html.Label("Insert Name:"),
                html.Div(
                    dcc.Input(id='input-field', value='Run_01', type='text'),
                    )
                ]),#BUTTONS ENDS

            html.Div(className="col-md-2", style=styles['previous-runs'], children=[ #BUTTONS
                    html.Label("Previous Simulations"),
                    dcc.Dropdown(
                        options=[
                            {'label': i, 'value': i} for i in global_timeseries_dict.keys()
                        ],
                        placeholder="None"
                    )
                ]),#BUTTONS ENDS

            html.Span(className="col-md-2", style=styles['top-button'], children=[#INIT
                    html.Button('Run', id='run-button', n_clicks=0, className="btn btn-outline-primary btn-lg"),
                    html.Button('In', id='input-button', n_clicks=0, className="btn btn-outline-primary btn-lg"),
                    html.Button('Out', id='output-button', n_clicks=0, className="btn btn-outline-primary btn-lg"),
                ]),#INIT ENDS

            ]),#TOP ROW ENDS
        ]),

# ################################################ MAIN ROW  ##################################################################
html.Div(id="main-container",className="container-fluid rounded",
        style=styles['main-container'],
        children=[
        html.Div(id="main-row",className="row",style={'width': '100%', "margin":0},children=[

            html.Div(id="toggle-window", style={'width': '100%'}, children=[#TOGGLE WIND
                        ]),#TOGGLE WINDOW
                        html.Div(style={'display': 'none'},children=[
                        #DUMMY TABLE
                        dt.EditableTable(
                        id='editable-table',
                        dataframe = pd.DataFrame().to_dict()
                        ),
                        ]),
                    ]),#MAIN ROW ENDS
                ]),
#------------------------------------------------# HIDDEN DIVS #------------------------------------------------------------#
        html.Div(className="col-sm-12",id='data-set', style={'display': 'none', 'background': 'lightgreen', "margin":10},children=[html.Div("Dataset")]),
        html.Div(className="col-sm-12",id='parameter-set', style={'display': 'none','background': 'blue'},children=[html.Div("Parameterset")]),
        html.Div(className="col-sm-4",id='init-parameter-set', style={'display': 'none','background': 'white'},children=[html.Div("Init Parameter Set")]),
        html.Div(className="col-sm-4",id='updated-parameter-set', style={'display': 'none','background': 'brown'},children=[html.Div("Intermediate")]),
        html.Div(className="col-sm-12",id='p-bucket', style={'display': 'none','background': 'grey'},children=[html.Div("P-Bucket")]),
        html.Div(className="col-sm-4",id='active-sc', style={'display': 'none','background': 'red'},children=[html.Div("Active SC")]),
        html.Div(className="col-sm-4",id='active-ems', style={'display': 'none','background': 'black'},children=[html.Div("Active EMS")]),
        html.Div(className="col-sm-4",id='selected-sc', style={'display': 'none','background': 'yellow'},children=[html.Div("Selected SC")]),
        html.Div(className="col-sm-4",id='last-clicked', style={'display': 'none','background': 'pink'},children=[html.Div("Selected Agent")]),
        html.Div(className="col-sm-4",id='any-clicks', style={'display': 'none','background': 'blue'},children=[html.Div("Any Clicks")]),
        html.Div(className="col-sm-12",id='flags', style={'display': 'none','background': 'white'},children=[html.Div("Flags")]),
        html.Div(className="col-sm-12",id='run-output', style={'display': 'none','background': 'black'},children=[html.Div("Run")]),
        html.Div(className="col-sm-12",id='save-output', style={'display': 'none','background': 'grey'},children=[html.Div("Save")]),
        html.Div(className="col-sm-12",id='run-name-output', style={'display': 'none','background': 'grey'},children=[html.Div("Run Name")]),
        ]),
])
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ L A Y E R $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
input_layer = html.Div(id="param-row",className="row",style={'width': '100%', "margin-left":5},children=[
                        html.Div(id="tab-bar", style={'width': '100%',"margin-left":5}, children=[]),
                        html.Img(id='image'),
                        html.Div(className="col-6 rounded",id='parameter-div',
                                 style={"height":"762px","width":"100%","padding-top":20, "margin-top":8,
                                        'background': 'white', "border":"thin darkgrey solid", "overflow":"auto"},
                                 children=[

                                 html.Div(id="table-output",
                                        children=[

                                        ]),
                                    ]),
#_________________________________________________Right Column ___________________________________________________________________________
                        html.Div(className="col-6 rounded",id="profile-div",
                                 style={'width': '100%',"padding":0,"margin":0},
                                 children=[

#_________________________________________________Agent-Buttons___________________________________________________________________________
                                html.Div(className="row",style={"width":"80%", "margin-top":0,"margin-left":"100","margin-right":"auto", "padding-left":20},
                                        children=[
                                    html.Div(className="col-md-3 rounded",
                                                 children=[
                                                                html.Div(style=styles["buttons-agents"], children=[
                                                                    html.Button('Press 1st', id='TA-button', n_clicks=0, className="btn-block w-100", n_clicks_timestamp=-1)
                                                                ]),
                                                            ]),
                                    html.Div(className="col-md-3 rounded",
                                                 children=[
                                                                html.Div(style=styles["buttons-agents"], children=[
                                                                    html.Button('Press 2nd', id='MA-button', n_clicks=0, className="btn-block w-1000", n_clicks_timestamp=-1)
                                                                ]),
                                                            ]),

                                    html.Div(className="col-md-3 rounded",
                                                 children=[
                                                                html.Div(style=styles["buttons-agents"], children=[
                                                                    html.Button('Press 3rd', id='EMS-button', n_clicks=0, className="btn-block w-100", n_clicks_timestamp=-1)
                                                                ]),
                                                            ]),
                                    html.Div(className="col-md-3 rounded",
                                                 children=[
                                                                html.Div(style=styles["buttons-agents"], children=[
                                                                    html.Button('Press 4th', id='Prices-button', n_clicks=0, className="btn-block w-100", n_clicks_timestamp=-1)
                                                                ]),
                                                            ]),
                                    ]),
#_________________________________________________1) FLAG-HEADER___________________________________________________________________________
                                html.Div(className="row",style={"width":"100%", "margin-top":0,"padding-left":20, "padding":10},
                                        children=[
                                    html.Div(className="col-md-12 rounded",
                                                 style={"margin-top":5,"margin-right":0,"margin-left":20,
                                                        'background': 'white',"border":"thin darkgrey solid"},
                                                 children=[
                                                 html.Div(className="col-12",style={"padding-left":66, "margin-top":"15"},
                                                         children=[
                                                         html.Div(className="row",style={"width":"100%"},
                                                         children=[
                                                             html.Div(className="col-6",style={"padding-left":10},
                                                             children=[
                                                                 html.Div("Flex-Request-Split",
                                                                 style=styles["flag-header"]
                                                                    ),
                                                                 ]),
                                                              html.Div(className="col-6",
                                                              children=[
                                                                  html.Div("Market Options",
                                                                  style=styles["flag-header"]
                                                                  ),
                                                                  ]),
                                                                 ]),
#_________________________________________________1) FLAG-BOX___________________________________________________________________________
                                                     html.Div(className="row",style={"width":"100%"},
                                                     children=[
                                                         html.Div(className="col-6",style=styles['flag-box'],
                                                         children=[
                                                             dcc.RadioItems(
                                                                id="flex-split-flag",
                                                                options=[
                                                                    {'label': ' equal', 'value': 'equal'},
                                                                    {'label': ' ran-3', 'value': 'ran-3'},
                                                                ],
                                                                value='equal',
                                                                labelStyle={'display': 'inline-block',
                                                                            "margin-left":5,
                                                                            "margin-top":10,
                                                                            #'font-family': 'Jazz LET',
                                                                            'font-size': '20px',
                                                                            "color": "lightblack",
                                                                            "opacity":1}
                                                                            ),
                                                                    ]),
                                                             html.Div(className="col-6",style=styles['flag-box'],
                                                             children=[
                                                                     html.Div(className="col-6",style=styles['flag-box'],
                                                                     children=[
                                                                        dcc.Checklist(id="market-flags",
                                                                            options=[
                                                                                {'label': ' Dayahead', 'value': 'Dayahead'},
                                                                                {'label': ' Intraday', 'value': 'Intraday'},
                                                                                {'label': ' SmartBlocks', 'value': 'SmartBlocks'},
                                                                                {'label': ' Loans', 'value': 'Loans'}
                                                                            ],
                                                                            values=["Dayahead"],
                                                                            labelStyle={'display': 'inline',
                                                                                        #"margin":10,
                                                                                        "margin-left":15,
                                                                                        #'font-family': 'Jazz LET, fantasy',
                                                                                        'font-size': '20px',
                                                                                        "color": "lightblack",
                                                                                        "opacity":1}
                                                                                        ),
                                                                                ]),
                                                                            ]),
                                                                            ]),
#_________________________________________________2) FLAG-HEADER___________________________________________________________________________
                                                         html.Div(className="row",style={"width":"100%"},
                                                         children=[
                                                             html.Div(className="col-6",
                                                             children=[
                                                                 html.Div("Negotiation-Initiator",
                                                                 style=styles["flag-header"]
                                                                 ),
                                                                 ]),
                                                              html.Div(className="col-6",
                                                              children=[
                                                                  html.Div("Negotiation-Strategies",
                                                                  style=styles["flag-header"]
                                                                  ),
                                                                  ]),
                                                                  ]),
#_________________________________________________2) FLAG-BOX__________________________________________________________________________
                                                         html.Div(className="row",style={"width":"100%"},
                                                         children=[

                                                                 html.Div(className="col-6",style=styles['flag-box'],
                                                                 children=[

                                                                      dcc.RadioItems(
                                                                         id="negotiation-init",
                                                                         options=[
                                                                             {'label': ' TA', 'value': 'TA'},
                                                                             {'label': " MA", 'value': 'MA'},
                                                                         ],
                                                                         value='MA',
                                                                         labelStyle={'display': 'inline-block',
                                                                                     "margin":5,
                                                                                     #'font-family': 'Jazz LET, fantasy',
                                                                                     'font-size': '20px',
                                                                                     "color": "lightblack",
                                                                                     "opacity":1}
                                                                                     ),
                                                                        ]),

                                                                html.Div(className="col-6",style=styles['flag-box'],
                                                                children=[
                                                                    #html.Label("Trading Agent:"),
                                                                      dcc.RadioItems(id="ta-strategy",
                                                                         options=[
                                                                             {'label': 'TA 1', 'value': 'TA 1'},
                                                                             {'label': "TA 2", 'value': 'TA 2'},
                                                                             {'label': "TA 3", 'value': 'TA 3'},
                                                                         ],
                                                                         value='cool',
                                                                         labelStyle={'display': 'inline-block',
                                                                                     "margin":5,
                                                                                     #'font-family': 'Jazz LET, fantasy',
                                                                                     'font-size': '18px',
                                                                                     "color": "lightblack",
                                                                                     "opacity":1}
                                                                                     ),

                                                                     dcc.RadioItems(id="ma-strategy",
                                                                        options=[
                                                                            {'label': 'MA 1', 'value': 'MA 1'},
                                                                            {'label': "MA 2", 'value': 'MA 2'},
                                                                            {'label': "MA 3", 'value': 'MA 3'},
                                                                        ],
                                                                        value='random',
                                                                        labelStyle={'display': 'inline-block',
                                                                                    "margin":5,
                                                                                    #'font-family': 'Jazz LET, fantasy',
                                                                                    'font-size': '18px',
                                                                                    "color": "lightblack",
                                                                                    "opacity":1}
                                                                                    ),
                                                                                ]),
                                                                                ]),

#_________________________________________________3) FLAG-HEADER___________________________________________________________________________
                                                         html.Div(className="row",style={"width":"100%"},
                                                         children=[
                                                             html.Div(className="col-6",
                                                             children=[
                                                                 html.Div("Optimization",
                                                                 style=styles["flag-header"]
                                                                ),
                                                                 ]),
                                                              html.Div(className="col-6",
                                                              children=[
                                                                  html.Div("Flexibility-Options",
                                                                  style=styles["flag-header"]
                                                                 ),

                                                                  ]),
                                                                  ]),
#_________________________________________________3) FLAG-BOXES___________________________________________________________________________
                                                         html.Div(className="row",style={"width":"100%"},
                                                         children=[
                                                             html.Div(className="col-6",style={"height":"80"},
                                                             children=[
                                                                 dcc.RadioItems(id="optimization-mode",
                                                                    options=[
                                                                        {'label': ' flex-split', 'value': 'flex-split'},
                                                                        {'label': " central", 'value': 'central'},
                                                                    ],
                                                                    value='flex-split',
                                                                    labelStyle={'display': 'inline-block',
                                                                                "margin":5,
                                                                                #'font-family': 'Jazz LET, fantasy',
                                                                                'font-size': '20px',
                                                                                "color": "lightblack",
                                                                                "opacity":1}
                                                                                ),

                                                                dcc.Checklist(id="internal-balance",
                                                                    options=[
                                                                        {'label': ' Internal-Balance', 'value': 'Internal_Balance'}
                                                                    ],
                                                                    values="",
                                                                    labelStyle={'display': 'inline',
                                                                                "margin":10,
                                                                                "margin-left":0,
                                                                                #'font-family': 'Jazz LET, fantasy',
                                                                                'font-size': '20px',
                                                                                "color": "lightblack",
                                                                                "opacity":1}
                                                                                ),
                                                                        ]),
                                                             html.Div(className="col-6",style=styles['flag-box'],
                                                             children=[
                                                                dcc.Checklist(id="flex-options",
                                                                    options=[
                                                                        {'label': ' Batteries', 'value': 'Batteries'},
                                                                        {'label': ' DSM', 'value': 'DSM'},
                                                                        {'label': ' Curtailment', 'value': 'Curtailment'},
                                                                    ],
                                                                    values=["Batteries"],
                                                                    labelStyle={'display': 'inline',
                                                                                "margin":10,
                                                                                "margin-left":5,
                                                                                #'font-family': 'Jazz LET, fantasy',
                                                                                'font-size': '18px',
                                                                                "color": "lightblack",
                                                                                "opacity":1}
                                                                                ),
                                                            ]),
                                                        ]),
                                                    ]),
                                                ]),
                                            ]),
#_____________________________________________________________________________________________________________________________________________________#
                                html.Div(className="row",style={"height":"190x", "width":"100%", "margin-top":2,"margin-left":20, "margin-bottom":2},
                                      children=[
                                    dcc.Graph(id='profile-graph'),
                                     ]),
                                     html.Div(className="row",style={"width":"80%", "margin-left":"12%"},
                                      children=[
                                      html.Div(className="col",
                                                children=[
                                            dcc.RadioItems(
                                                id="demand-profile-radio",
                                                options=[{'label': dem, 'value': dem} for dem in excel_input_data["Demand"].columns],
                                                value="dem_01",
                                                labelStyle={'display': 'inline-block', "margin":5}
                                                    )
                                                    ]),
                                      html.Div(className="col",#style={"margin-left":70,"margin-right":10},
                                                children=[
                                            dcc.RadioItems(
                                                id="generation-profile-radio",
                                                options=[{'label': gen, 'value': gen} for gen in excel_input_data["Generation"].columns],
                                                value="gen_01",
                                                labelStyle={'display': 'inline-block', "margin":5}
                                                    )
                                                    ]),
                                                ]),
        ]),
    ]),
############################################################################################################################
output_layer = html.Div(id="param-row",className="row",style={'width': '100%', "margin-left":5},children=[# MAIN-LAYER-OUTER
#------------------------------------------------- LEFT COLUMN -------------------------------------------------------------#
         #/////////////////////////////////////// UPPER WINDOW ////////////////////////////////////#
                html.Div(id="upper-window-left",style=styles['upper-window'],className="col-sm-12 rounded",children=[#LS_DIV


                    html.Div(className="row",style={'width': '100%', 'margin':'0px'},children=[#ROW
                        html.Div(className="col",style=styles['dropdown-upper'],children=[
                            dcc.Dropdown(#className="col-md-6 rounded",#className="list-group-item list-group-item-info",# DROPDOWN_01
                                id="dropdown-left-scenarios",
                                options=[
                                        {'label': i, 'value': i} for i in global_sc_names
                                        ],
                                value="SC_1",
                                        )#dropdown close
                                        ]),

                        html.Div(className="col",style=styles['dropdown-upper'],children=[
                            dcc.Dropdown(#className="col-md-6 rounded",#className="list-group-item list-group-item-info",# DROPDOWN_01
                                id="dropdown-left-tabs",
                                options=[
                                        {'label': 'Timeseries', 'value': "Timeseries"},
                                        {'label': 'Costs', 'value': "Costs"},
                                        {'label': 'Messages', 'value': "Messages"},
                                        ],
                                value='Timeseries',
                                        )#dropdown close
                                        ]),
                            ]),#ROW
                         #/////////////////////////////////////// OFFER SLIDER ////////////////////////////////////#
                        html.Div(className="row",style={'width': '100%', 'margin-top':'0px'},children=[#ROW
                            html.Div(className="col-md-5 rounded",style=styles['req-slider'],children=[
                                dcc.Slider(id="offer-slider",
                                min=0,
                                max=5,
                                marks={0: 'BASE', 1: 'OFFER_1', 2: 'OFFER_2', 3: 'OFFER_3', 4: 'OFFER_4', 5: 'OFFER_5'},
                                value=0,
                                ),
                                ]),

                            html.Div(className="col-md-6 rounded",style=styles['checkboxes-output'],children=[
                                dcc.Checklist(id="lower-graph-options",
                                    options=[
                                        {'label': ' Capacity', 'value': 'Capacity'},
                                        {'label': ' Requests', 'value': 'Requests'},
                                        {'label': ' Flexibilities', 'value': 'Flexibilities'},
                                        {'label': ' Starts', 'value': 'Starts'},
                                        {'label': ' Prices', 'value': 'Prices'},
                                    ],
                                    values=["Capacity",'Requests'],
                                    labelStyle={'display': 'inline',
                                                "margin-top":20,
                                                "margin-left":15,
                                                #'font-family': 'Jazz LET, fantasy',
                                                'font-size': '20px',
                                                "color": "lightblack",
                                                "opacity":0.8}
                                                ),
                                ]),
                        ]),

                        ########################################## TOGGLE IN HERE ###################################
                        html.Div(className="row",style={'width': '100%', 'margin-top':'10px', 'margin-left':'2px'},children=[
                            html.Div(id="upper-left-inside",className="col",style=styles['upper-inside'],children=[
                                    ]),#ROW
                        ]),
                        #/////////////////////////////////////// LOWER WINDOWS ////////////////////////////////////#
                        html.Div(className="row",style={'margin-top':'15px'},children=[
                            html.Div(className="col-md-12 rounded",id="lower-window-left-1",style=styles['lower-window'],children=[

                                html.Div(className="row",style={'width': '100%', 'margin-top':'15px', 'margin-left':'2px'},children=[
                                    html.Div(id="lower-left-inside",className="col",style=styles['lower-inside'],children=[
                                            ]),#ROW
                                ]),

                        html.Div(className="row",style={'margin-top':'15px'},children=[
                            html.Div(className="col-md-12 rounded",id="lower-window-left-3",style=styles['lower-window'],children=[

                                html.Div(className="row",style={'width': '100%', 'margin-top':'15px', 'margin-left':'2px'},children=[
                                    html.Div(id="battery-div",className="col",style=styles['lower-inside'],children=[
                                            ]),#ROW
                                ]),
                            ]),
                            ]),

                        html.Div(className="row",style={'margin-top':'10px'},children=[
                            html.Div(className="col-md-12 rounded",id="lower-window-left-2",style=styles['price-window'],children=[

                                html.Div(className="row",style={'width': '100%', 'margin-top':'10px', 'margin-left':'2px'},children=[
                                    html.Div(id="price-div",className="col",style=styles['lower-inside'],children=[
                                            ]),#ROW
                                ]),
                            ]),
                            ]),

                        html.Div(className="row",style={'margin-top':'5px'},children=[
                            html.Div(className="col-md-12 rounded",id="lower-window-left-3",style=styles['stats-window'],children=[

                                html.Div(className="row",style={'width': '100%', 'margin-top':'10px', 'margin-left':'2px'},children=[
                                    html.Div(id="stats-div",className="col",style=styles['lower-inside'],children=[
                                            ]),#ROW
                                ]),
                            ]),
                            ]),

                            ####### LOWER GRAPH ####
                            ])
                        ])
                ])#ROW
                ])
#???+++???+++???+++???+++???+++???+++???+++???+++ C A L L B A C K S +++???+++???+++???+++???+++???+++???+++???+++???+++
