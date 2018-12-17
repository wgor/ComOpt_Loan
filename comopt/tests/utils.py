from comopt.model.utils import linear, no_noise
from comopt.scenario.ma_policies import buy_at_any_cost
from comopt.scenario.ta_policies import multiply_markup_evenly, choose_action_randomly_using_uniform, sell_at_any_cost

shared_q_parameters = {
        "Gamma": 0.1,  # Reward discount factor
        "Alpha": 0.1,  # Learning rate
        "Epsilon": 0.2,  # Exploration range: 0 = Always random exploration, 1 = Always Argmax(Q-Value)
        "Action function": multiply_markup_evenly,
        # TA EXP FUNCS:# multiply_markup_evenly
        "Exploration function": choose_action_randomly_using_uniform,
        # TA ACT FUNCS: # choose_action_greedily_with_noise
        # choose_action_randomly_using_uniform
        "Step now": 0,
    }

learning_input_data = {
    "Q parameter prognosis": shared_q_parameters,
    "Q parameter flexrequest": shared_q_parameters,
}

MA_negotiation_input_data = {
    "MA prognosis policy": buy_at_any_cost,
    "MA prognosis parameter": {
        "reservation_price": 4,
        "markup": 1,
        "concession": linear,
        "noise": no_noise,
    },
    "MA flexrequest policy": buy_at_any_cost,
    "MA flexrequest parameter": {
        "Sticking factor": 0,
    },
}

TA_negotiation_input_data = {
    "TA prognosis policy": sell_at_any_cost,
    "TA prognosis parameter": {
        "reservation_price": 2,
        "markup": 1,
        "concession": linear,
        "noise": no_noise,
    },
    "TA flexrequest policy": sell_at_any_cost,
    "TA flexrequest parameter": {},
}

negotiation_input_data = {
    "Prognosis rounds": 10,
    "Flexrequest rounds": 10,
    **MA_negotiation_input_data,
    **TA_negotiation_input_data,
}
