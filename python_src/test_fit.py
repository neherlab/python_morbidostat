dt=10
vi=1
n=morb_monitor.OD.shape[0]
OD = morb_monitor.OD
plt.figure()
for ti in range(0,n-dt,dt):
    final_time  = OD[ti+dt-1,-1]
    tmp_time_array = OD[ti:ti+dt,-1]-final_time
    tmp_regress = stats.linregress(tmp_time_array,
                                   np.log(OD[ti:ti+dt,vi]))
    print tmp_regress[0], exp(tmp_regress[1])
    plt.plot(tmp_time_array+final_time, np.exp(tmp_regress[1]+tmp_time_array*tmp_regress[0]))
    plt.plot(tmp_time_array+final_time, OD[ti:ti+dt,vi])
