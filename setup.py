from setuptools import setup

setup(
    name="comopt",
    description="Commitment Optimisation package.",
    keywords=["smart grid", "renewables", "balancing", "energy loans"],
    version="0.1",
    install_requires=[
        "pandas",
        "numpy>=1.15.4",
        "pyomo",
        "cplex",
        "enlopy",
        "matplotlib==2.2.2",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    packages=["comopt"],
    include_package_data=True,
    # license="Apache",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
    ],
    long_description="""\
The Commitment Optimisation package for energy loans demonstrates interactions between different stakeholders trading energy flexibility as part of a smart energy system.
The package supports multi-agent simulations in which each stakeholder is represented as an independent decision-maker (agent) with limited information.
A simulation is executed as a Markov Decision Process from the perspective of one of the agents: the Aggregator.
""",
)
