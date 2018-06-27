import pickle

from comopt.model import Environment


if __name__ == '__main__':
    inputs = pickle.load(open("inputs.pickle", "rb"))
    env = Environment(data=inputs)
    env.step()
