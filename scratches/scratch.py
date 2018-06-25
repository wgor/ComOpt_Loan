
len(env.active_EMS)













env.TA.flex_req
env.TA.flex_req["req_01"].values['up']
env.EMS[2].costs["Baseline"]
env.TA.flex_req["req"].id
tot_costs = 0
for i,j,k in zip(env.TA.UDI_events["baselines"], env.TA.UDI_events["req"], env.TA.UDI_events["baselines"].keys()):
    if env.TA.UDI_events["baselines"][i].costs > 0:
        diff = env.TA.UDI_events["baselines"][i].costs - env.TA.UDI_events["req"][j].costs
        print("EMS '{}' Costs changed: ".format(k))
        print(diff*-1)
        tot_costs += diff*-1
    elif env.TA.UDI_events["baselines"][i].costs < 0:
        diff = env.TA.UDI_events["baselines"][i].costs - env.TA.UDI_events["req"][j].costs
        print("EMS '{}' Revenues changed: ".format(k))
        print(diff)
        tot_costs += diff*-1
print("Total Costs for Flex-Request: {}".format(tot_costs))

env.TA.UDI_events["baselines"].keys()

env.EMS[0].ts = milp_solver(agents_list=env.EMS, type="solo", flex_req=None)
timeindex = env.EMS[0].ts.index
timeindex
#df1.set_index(['time','ems'])

df1 = env.EMS[0].ts
df2 = env.EMS[2].ts
#df1 = df1.set_index("ems")
#df2 = df2.set_index("ems")
df2
df = pd.concat([df1, df2], axis=0, keys=[1,2,3,4,5,6,7,8,9,10,11,12])
df
 df.set_index(['time','ems'])

df.set_index(["time", "ems"], drop=True )
df = df1.append(df2)
df = df.set_index(["time", "ems"], append=True)

############################
lists = []
times = []
ems = ["a01","a02"]

for time in df1.loc[:,'time']:
    times.append(time)

lists.append(times)
lists.append(ems)

ind = pd.MultiIndex.from_product(lists, names=['time', 'ems'])

ind

df3 = pd.DataFrame(df1,index=ind)
df3["time"][1][0] = 10
df3
df3.drop("time", inplace=True)
df3.loc["time"]






df2 = env.EMS[1].ts
for time,ems in zip(df2.loc[:,'time'], df2.loc[:,'ems']):
    tuples.append((time, ems))

index = pd.MultiIndex.from_tuples(tuples, names=("time","ems"))
index
df3 = pd.DataFrame(np.random.randn(48), index=index)
#df3 = pd.concat([df1,df2], axis=0, ignore_index=False)
df3.sort_values(["ems"])
df3.sort_values(["time", "ems"])
