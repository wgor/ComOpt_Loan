# ComOpt_Loan

The Commitment Optimisation package for energy loans demonstrates interactions between different stakeholders trading energy flexibility as part of a smart energy system.
The package supports multi-agent simulations in which each stakeholder is represented as an independent decision-maker (agent) with limited information.
A simulation is executed as a Markov Decision Process from the perspective of one of the agents: the Aggregator.


## Agents

- Prosumer, or Energy Management System (EMS)
- Aggregator (AGR), or trading agent (TA)
- Flexibility Requesting Party (FRP), or market agent (MA)


## Build & Run

### Dependencies:

* Make a virtual environment: `python3.6 -m venv comopt-venv` or use a different tool like `mkvirtualenv`. You can also use
  an [Anaconda distribution](https://conda.io/docs/user-guide/tasks/manage-environments.html) as base, with `conda create -n comopt-venv python=3.6`
* Activate it, e.g.: `source comopt-venv/bin/activate` or, with conda, `activate comopt-venv`.
* Install the `comopt` package and dependencies:

    python setup.py [develop|install]

* Install the `cplex` package and dependencies from `<your cplex path>/python`:

    python setup.py [develop|install]

### Demo instructions

Run `start_sim.py` to start a simulation.
