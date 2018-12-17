from datetime import datetime, timedelta

from comopt.model.environment import Environment
from comopt.scenario.balancing_opportunities import (
    single_curtailment_each_day_from_hours_a_to_b
)
from comopt.tests.utils import learning_input_data, negotiation_input_data

# Set simulation period
start = datetime(year=2018, month=6, day=1, hour=12)
end = datetime(year=2018, month=6, day=1, hour=16)
resolution = timedelta(minutes=15)

input_data = {
    "TA horizon": timedelta(hours=4),
    "MA horizon": timedelta(hours=2),
    "EMS constraints": [],
    "Balancing opportunities": single_curtailment_each_day_from_hours_a_to_b(start, end, resolution, a=12, b=14),
    "MA deviation prices": [],
    "MA deviation multiplicator": 1,
    "MA imbalance market costs": {},
    "Central optimization": False,
}
input_data = {**input_data, **learning_input_data, **negotiation_input_data}

# Set up simulation environment
env = Environment(
    name="Baseline scenario without any FlexRequests.",
    start=start,
    end=end,
    resolution=resolution,
    input_data=input_data,
)

# Run simulation model
# env.run_model()
