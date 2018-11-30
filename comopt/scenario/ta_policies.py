from typing import List, Optional, Union, Tuple, Callable
from random import uniform, gauss, seed, randint
from copy import deepcopy
from numpy import abs, sin
from pandas import DataFrame
from comopt.model.utils import root_divided_by_2, linear, cos_root_divided_by_2, no_shape, gauss_1, gauss_2, uniform_1, no_noise
from functools import wraps

"""Policy functions configures the strategy arguments for agents within negotiations"""

#---------------------------------- DECORATORS ----------------------------------------#
# Decorator function for distribution sampling based policies
def get_TA_bid_from_sample(policy_function: Callable) -> Callable:

    @wraps(policy_function)
    # @wraps is a helper function that allows to keep policy functions name when calling e.g. sell_at_any_cost.__name__
    def policy_function_wrapper(rounds_total: int,
                                rounds_left: int,
                                ta_parameter: dict,
                                q_table_df: DataFrame,
                                q_parameter: dict,) -> dict:

        # Get return values from wrapped policy function -> dict()
        ta = policy_function(rounds_total=rounds_total, rounds_left=rounds_left, ta_parameter=ta_parameter,
                             q_table_df=q_table_df, q_parameter=q_parameter)

        # Modify shaped markup based on choosen exploration function
        ta["Markup"] = (ta["Markup"] + ta["Noise"](rounds_total=rounds_total, rounds_left=rounds_left, mean=ta["Markup"])) * ta["Concession"](rounds_total=rounds_total, rounds_left=rounds_left)
        ta["Bid"] = ta["Reservation price"] + ta["Markup"]

        # If TAs bid is lower than his reservation price, use reservation price instead
        if ta["Bid"] < ta["Reservation price"]:
           ta["Bid"] = ta["Reservation price"]

        return {"Bid":ta["Bid"], "Reservation price":ta["Reservation price"], "Markup":ta["Markup"],
                "Q_Table":None, "Q_Parameter":q_parameter, "Action": None}

    return policy_function_wrapper


# Decorator function for learning based policies
def get_TA_bid_from_learning(policy_function: Callable) -> Callable:

    @wraps(policy_function)
    # @wraps allows to keep the object properties of the wrapped functions (e.g. sell_at_any_cost.__name__)
    def policy_function_wrapper(rounds_total: int,
                                rounds_left: int,
                                q_table_df: DataFrame,
                                q_parameter: dict,
                                ta_parameter: dict,) -> dict:

        round_now = rounds_total - rounds_left + 1

        # Get return values from wrapped policy function -> dict()
        ta = policy_function(rounds_total=rounds_total, rounds_left=rounds_left, q_table_df=q_table_df, q_parameter=q_parameter, ta_parameter=ta_parameter)

        # Use an exploration function to choose an action
        action = q_parameter["Exploration function"](q_table_df=q_table_df, q_parameter=q_parameter, round_now=round_now)

        # Modify shaped markup based on choosen action function
        ta["Markup"] = q_parameter["Action function"](action=action,
                                                      markup=(ta["Markup"] * ta["Concession"](rounds_total=rounds_total, rounds_left=rounds_left)),
                                                      show_actions=False)

        # Compute bid based on reservation price and modified markup
        ta["Bid"] = ta["Reservation price"] + ta["Markup"]

        # If TAs bid is lower than his reservation price, use reservation price instead
        if ta["Bid"] < ta["Reservation price"]:
           ta["Bid"] = ta["Reservation price"]

        return {"Bid":ta["Bid"], "Reservation price":ta["Reservation price"] , "Markup":ta["Markup"], "Action": action}

    return policy_function_wrapper


# Decorator for exploration functions
def exploration_function(exploration_function: Callable) -> Callable:

    @wraps(exploration_function)
    def exploration_function_wrapper(q_table_df: DataFrame, q_parameter: dict, round_now: int):
        return exploration_function(q_table_df=q_table_df, q_parameter=q_parameter, round_now=round_now)

    return exploration_function_wrapper


# Decorator for action functions
def action_function(action_function: Callable) -> Callable:

    @wraps(action_function)
    def action_function_wrapper(action: str, markup: float, show_actions: bool):
        #TODO: Test for exceptions
        # show_actions argument allows to return only the actions specified in a given action function, used to e.g. to set up q-table
        if show_actions == True:
            return action_function(action=action, markup=markup, show_actions=show_actions)["Actions"]

        else:
            return action_function(action=action, markup=markup, show_actions=False)["Markup"]

    return action_function_wrapper


#---------------------------------- DECORATED EXPLORATION FUNCTIONS ----------------------------------------#
@exploration_function
# Randomizes existing Q-table with decaying noise (-> 1/environment.step_now). Action then gets chosen based on max Q-values of the randomized table.
def choose_action_greedily_with_noise(q_table_df: DataFrame, q_parameter: dict, round_now: int) -> str:

    # Make copy of Q-Table
    randomized_table = deepcopy(q_table_df)
    # Get number of possible actions
    number_of_actions = len(q_parameter["Action function"](action=None, markup=None, show_actions=True).keys())

    # Randomize Q-value(=value) for each action(=column) in round_now(=index)
    for col in q_table_df.columns:
        randomized_table.loc[round_now,col] = q_table_df.loc[round_now,col] + \
                                              randint(1,number_of_actions) * (1./(q_parameter["Step now"]))

    # Get column name of max Q-value from randomized Q-Table
    action = randomized_table.loc[round_now,:].idxmax(axis=1)

    return action


@exploration_function
# If uniform(0,1) gives a number above q_parameter["Epsilon"], agent uses random action sampling. Otherwise the action with max Q-Value gets selected.
def choose_action_randomly_using_uniform(q_table_df: DataFrame, q_parameter: dict, round_now: int) -> str:

    # Random selection
    if uniform(0,1) > q_parameter["Epsilon"]:
        action = q_table_df.loc[round_now,:].sample(1)
        return action.index.format()[0]

    # Greedy selection
    else:
        action = q_table_df.loc[round_now,:].idxmax()

        return action


#---------------------------------- DECORATED ACTION FUNCTIONS ----------------------------------------#
@action_function
# Action function for learning based policies
def multiply_markup_evenly(action: str, markup: float, show_actions: bool = False) -> float:

    # Describe actions and action values here
    actions = {"+75":1.75, "+50":1.5, "+25":1.25, "0":1, "-25":0.75, "-50":0.5, "-75":0.25}

    # If called only for the action names, make sure you pass markup = None to the action functions arguments.
    if markup is not None:
        markup = markup * actions[action]

    return {"Markup":markup, "Actions": actions}


#------------------------------ DECORATED SAMPLING POLICY FUNCTIONS ------------------------------------#
@get_TA_bid_from_sample
# Selling with a reservation price of +inf
def never_sell(rounds_total_total: int,
               rounds_left: int,
               reservation_price=float("inf"),
               markup: Union[int,float] = 1,
               q_table_df: DataFrame = None,
               q_parameter: dict = None) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {"Bid": 0, "Reservation price":reservation_price, "Markup":markup , "Shape":concession_curve,
            "Q_Table":None, "Q_Parameter":q_parameter, "Action": None}


# TODO: Testing needed. Probably implementing try-functions.
# Selling with a reservation price and markup of 0
@get_TA_bid_from_sample
def sell_at_any_cost(rounds_total: int,
                     rounds_left: int,
                     reservation_price=0,
                     markup: Union[int,float] = 0,
                     concession_curve: Union[root_divided_by_2, linear, no_shape] = linear,
                     q_table_df: DataFrame = None,
                     q_parameter: dict = None) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {"Bid": 0, "Reservation price":reservation_price, "Markup":markup , "Shape":concession_curve,
            "Q_Table":None, "Q_Parameter":q_parameter, "Action": None}


@get_TA_bid_from_sample
# Deterministic markup prices
def sell_with_deterministic_prices(rounds_total: int,
                                   rounds_left: int,
                                   q_table_df: DataFrame,
                                   q_parameter: dict,
                                   reservation_price: Union[int,float] = 2,
                                   markup: Union[int,float] = 0.5,
                                   concession_curve: Union[root_divided_by_2, linear, no_shape] = linear,
                                   ) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {"Bid": 0, "Reservation price":reservation_price, "Markup":markup , "Shape":concession_curve,
            "Q_Table":None, "Q_Parameter":q_parameter, "Action": None}


@get_TA_bid_from_sample
# Samples markup prices from distribution
def sell_with_stochastic_prices(rounds_total: int,
                                rounds_left: int,
                                q_table_df: DataFrame,
                                q_parameter: dict,
                                ta_parameter: dict) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {"Bid": 0, "Reservation price":ta_parameter["Reservation price"], "Markup":ta_parameter["Markup"],
            "Concession":ta_parameter["Concession"], "Noise":ta_parameter["Noise"],
            "Q_Table":None, "Q_Parameter":q_parameter, "Action": None}


#------------------------------ DECORATED LEARNING POLICY FUNCTIONS ------------------------------------#
@get_TA_bid_from_learning
# Gets prices based on q-learning
def Q_learning(rounds_total: int,
               rounds_left: int,
               q_table_df: DataFrame,
               q_parameter: dict,
               ta_parameter: dict) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {"Bid": 0, "Reservation price":ta_parameter["Reservation price"], "Markup":ta_parameter["Markup"],
            "Concession":ta_parameter["Concession"], "Noise":ta_parameter["Noise"],
            "Q_Table":q_table_df, "Q_Parameter":q_parameter, "Action": None}
