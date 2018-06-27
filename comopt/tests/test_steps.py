from comopt.model import Environment


def test_step_ends(simulation_environment: Environment):
    assert simulation_environment.step() == "Step Completed"


def test_this():
    assert 1 == 2
