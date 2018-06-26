# ComOpt_Loan

The Commitment Optimisation package for energy loans demonstrates interactions between different stakeholders trading energy flexibility as part of a smart energy system.
The package supports multi-agent simulations in which each stakeholder is represented as an independent decision-maker (agent) with limited information.
A simulation is executed as a Markov Decision Process from the perspective of one of the agents: the Aggregator.


## Agents

- Prosumer, or Energy Management System (EMS)
- Aggregator (AGR), or trading agent (TA)
- Flexibility Requesting Party (FRP)


## Build & Run

### Dependencies:

* Make a virtual environment: `python3.6 -m venv comopt-venv` or use a different tool like `mkvirtualenv`. You can also use
  an [Anaconda distribution](https://conda.io/docs/user-guide/tasks/manage-environments.html) as base.
* Activate it, e.g.: `source comopt-venv/bin/activate`
* Install the `comopt` package and dependencies:

      python setup.py [develop|install]
      
### Demo instructions

1) Open Excel, click on "Clear Results"-Button.
2) Run run_opt.py from folder.
3) Click on "Agent 01","Agent 02","Agent 03"-Buttons to see Plots for the results.

