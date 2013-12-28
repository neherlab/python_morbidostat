import arduino_interface as morb
import time
import numpy as np
import matplotlib.pyplot as plt


ser = morb.serial_setup()
vial=0
out_file  = '20131220_temp_data1.txt'
dt = 5 # seconds
T = 120*60
voltage_time_course=np.zeros((T/dt, 3))
t0 = time.time()
for ii in xrange(T/dt):
    V =  morb.measure_voltage(ser, vial, 10, 10)
    voltage_time_course[ii,:] = [(time.time()-t0)/60, V[0], V[1]]
    print voltage_time_course[ii,:]
    time.sleep(dt)
    if (ii%50)==0:
        np.savetxt(out_file, voltage_time_course)

plt.plot(voltage_time_course[:,0], voltage_time_course[:,1])
plt.xlabel('time [min]')
plt.ylabel('AD signal')

