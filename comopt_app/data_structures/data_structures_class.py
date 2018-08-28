import numpy as np
import matplotlib.pyplot as plt


class deviation_cost_curve:
    '''
    function_type:
        Argument could be one of the following: "Zero","Rectangle","Linear","Power"
    excess_type:
        Indicates either excess consumption or excess surplus.
        Argument could be one of the following: "Supply" or "Demand"
    origin:
        Determines the root for a rectangle cost function.
    epsilon:
        Determines a null cost interval for a rectangle cost function.
    cost_step:
        Determines the value of a "price jump" for a rectangle cost function.
    gradient:
        Determines the gradient of the linear cost curve for a linear cost function.
    power:
        Determines the power of a ... cost function.
    '''
    def __init__(self,
                function_type=None,
                excess_type=None,
                origin=0,
                epsilon=None,
                cost_step=None,
                gradient=None,
                power=None,
                ):

        if function_type == "Rectangle":
            assert epsilon != None, "No EPSILON VALUE - Please pass one!"
            assert cost_step != None, "No COST_STEP VALUE - Please pass one!"

        if function_type == "Linear":
            assert gradient != None, "No GRADIENT VALUE - Please pass one!"

        if function_type == "Power":
            assert power != None, "No POWER VALUE - Please pass one!"

        self.function_type = function_type
        self.excess = excess_type
        self.origin = origin
        self.epsilon = epsilon
        self.cost_step = cost_step
        self.gradient = gradient
        self.power = power
        return

    def get_costs(self,quantity):
        self.x_values = np.linspace(-quantity-self.origin,quantity+self.origin,1000)+self.origin

        if self.function_type == "Zero":
            self.y_values = [0 for value in range(len(self.x_values))]
            self.y_costs = 0
            self.x_costs = quantity

        if self.function_type == "Rectangle":
            self.y_values = [self.cost_step if value<=self.origin-self.epsilon or value>=self.origin+self.epsilon
                             else 0 for value in self.x_values]
            self.y_costs = [self.cost_step if quantity<=self.origin-self.epsilon or quantity>=self.origin+self.epsilon
                            else 0]
            self.x_costs = quantity

        if self.function_type == "Linear":
            self.y_values = [np.abs(value*self.gradient) for value in self.x_values]
            self.x_values = [x+self.origin if quantity > 0 else self.origin+x for x in self.x_values]
            self.y_costs = [np.abs(quantity*self.gradient)]
            self.x_costs = quantity+self.origin

        if self.function_type == "Power":
            self.y_values = [np.abs(value**self.power) for value in self.x_values]
            self.x_values = [x+self.origin if quantity > 0 else self.origin+x for x in self.x_values]
            self.y_costs = [np.abs(quantity**self.power)]
            self.x_costs = quantity+self.origin

        plt.title("Penalty-Function-Type: {}\n Excess-Type: {}\n Quantity:{}\n Costs:{}".format(self.function_type,
                                                                                                self.excess, quantity,
                                                                                                self.y_costs))
        plt.plot(self.x_costs,self.y_costs, '-o', label="costs")
        plt.plot(self.x_values,self.y_values)
        plt.xlabel("kWh")
        plt.ylabel("Euro/kWh")
        plt.legend(loc=3)
        plt.show()

        return self.y_costs, self.x_costs

zero_curve = deviation_cost_curve(function_type="Zero", excess_type="Supply")
zero_curve.get_costs(10)

rect_curve = deviation_cost_curve(function_type="Rectangle", excess_type="Supply", epsilon=100, cost_step=50, origin=100)
rect_curve.get_costs(300)
#rect_curve.show()

linear_curve = deviation_cost_curve(function_type="Linear", excess_type="Supply", constant=1.5, origin=0)
linear_curve.get_costs(10)
#linear_curve.show()

power_curve = deviation_cost_curve(function_type="Power", excess_type="Supply", power=2, origin=150)
power_curve.get_costs(100)
#power_curve.show()

x = np.arange(1, 7, 0.4)
x
y0 = np.sin(x)

#    print("working: {}, {}".format(type, excess))
#    return type, excess
# sh = 50

x = np.arange(1, 10, 1)
y=[2,2,4,6,10,2,3,9,5]
plt.plot(x,y,drawstyle="steps", label="commited profile")
plt.fill_between(x,y, step="pre",facecolor='green', alpha=0.4)
plt.xlabel("timestamp")
plt.ylabel("kWh")
plt.legend(loc=3)
plt.show()

x = np.arange(1, 10, 1)
y=[2,2,4,6,10,2,3,9,5]
plt.plot(x,y,drawstyle="steps", label="commited profile")
#plt.fill_between(x,y, step="pre", alpha=0.4, facecolor='green')
y2=[2,2,4,6,8,2,3,9,5]
plt.plot(x,y2,drawstyle="steps", color="green")
y3=[2,2,4,6,8,4,3,9,5]
plt.fill_between(x,y3,step="pre", alpha=0.4, facecolor='green')
y4=[2,2,4,6,10,4,3,9,5]
plt.fill_between(x,y4, step="pre", alpha=0.4, facecolor='lightblue')
#plt.plot(x,y4,drawstyle="steps")

plt.xlabel("timestamp")
plt.ylabel("kWh")
plt.legend(loc=3)
plt.show()

#plt.fill_between(x,y2, step="pre", alpha=0, color="black")
plt.errorbar(x, y2, yerr=([0,0]), fmt='o')
plt.plot(x,y, drawstyle="steps")
plt.step(x,y3)
#plt.plot(x,y2, drawstyle="steps")

# # x2 = np.linspace(-10+sh, 10+sh, 11)
# x
# y = np.array([1 if np.abs(val)<=50-5 or np.abs(val)>=50+5 else 0 for val in x])
# y
# def re(x):
#     y = [x+50 for x in x]
#     return y
# re(x)
#
# plt.plot(x+50,y)
# plt.show()
# x_vals = np.linspace(-30,30,101)
# x_vals
# def linear_func(x_vals):
#     #y = [x*10 if x >= 0 else x*-10 for x in x_val]
#     y = [np.abs(x*10) for x in x_vals]
#     return y
#
# ys = linear_func([-10])
# ys
# plt.plot(x_val+30,ys)
# plt.show()
#

# x_values
# eps = 10
# l = lambda q: np.clip(q,-10,0)+np.clip(q,0,10)
# l(x_values)
#
# clp = np.clip(x_values, -10, 10)
# clp
