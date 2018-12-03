from __future__ import division
import time
import math
import threading
import numpy as np

#morb_path = '/ebio/ag-neher/share/users/bregenbogen/morbidostat/python_arduino/'
morb_path =  './'
pump_calibration_file_base = morb_path+'python_src/pump_calibration'
OD_calibration_file_name = morb_path+'python_src/OD_calibration.dat'

debug = False
# dictionary mapping pumps to pins
pumps = {'pump2': range(7,7+15),
         'pump1': range(22,22+15),
         'pump3': range(38,38+15), 'waste':3}


class morbidostat:
    def __init__(self):
        self.n_cultures= 15
        self.OD = np.zeros(self.n_cultures)
        self.IC50 = np.zeros(self.n_cultures)
        self.antibiotic = np.zeros(self.n_cultures)
        self.max_growth_rate = np.zeros(self.n_cultures)
        self.mixing_time = 1
        self.time = 0
        self.dt = 10.0
        self.concA = 0.3
        self.concB = 2.0
        self.volume = 10.0
        self.second = 1.0
        self.temperatures = (37,37)

    def wait_until_mixed(self):
        '''
        function not needed in a simulator, included for compatibility
        '''
        return

    def volume_to_time(self, pump_type, pump, volume):
        return 0


    def measure_temperature(self,switch_light_off=True):
        pass

    def connect(self):
        self.morbidostat_OK=True
        self.set_up_and_start()
        return 0

    def disconnect(self):
        self.morbidostat_OK=False
        return 0


    def growth_rate(self):
        '''
        convert IC50 amd antibiotic conc into a growth rate
        '''
        return self.max_growth_rate/(1+(self.antibiotic/self.IC50)**2)

    def set_up_and_start(self, OD_init=0.05, IC50_init=550, antibiotic_init=0, max_growth_rate_init=0.0003, final_time = 24*60*60):
        '''
        copies initial conditions into the local arrays, sets the duration of the
        experiments and starts it
        '''
        self.OD[:] = OD_init
        self.IC50[:] = IC50_init
        self.antibiotic[:] = antibiotic_init
        self.max_growth_rate[:] = max_growth_rate_init
        self.final_time = final_time

        self.evolve_thread=threading.Thread(target = self.evolve)
        self.evolve_thread.start()

    def evolve(self):
        '''
        called by the evolve_thread, this function iterates until the final
        time is reached. it update OD via a geometric increments and changes
        the IC50 by random additive increments (this is the evolution part)
        '''
        while self.time<self.final_time and self.morbidostat_OK:
            self.OD+=self.dt*self.growth_rate()*self.OD*(1+0.1*np.random.randn(self.n_cultures))
            self.IC50+=0.1*(np.random.random(self.n_cultures)<0.02/(1+np.exp((self.IC50-self.antibiotic)*100))
                            )*np.random.standard_exponential(self.n_cultures)*(1-self.IC50)
            time.sleep(1.0*self.dt*self.second)
            self.time+=self.dt


    def measure_OD(self, vial, n_measurements=1, dt=10, switch_light_off=True):
        '''
        return the simulated OD values
        '''
        return max(0.004,self.OD[vial]+0.001*np.random.randn()), 0

    def measure_voltage(self, vial, n_measurements=1, dt=10, switch_light_off=True):
        '''
        return the simulated OD values
        '''
        return max(0.004,self.OD[vial]+0.001*np.random.randn()), 0

    def switch_light(self, state):
        pass
    def remove_waste(self,volume):
        pass

    def inject_volume(self, pump_type='pump1', pump_number=0, volume=0.1, conc=0.0):
        '''
        mimick the running of the pumps by diluting the OD and
        changing the antibiotic concentration as appropriate
        '''
        self.antibiotic[pump_number]*=(1 - volume/self.volume)
        self.antibiotic[pump_number]+= conc*volume/self.volume
        self.OD[pump_number]*=(1 - volume/self.volume)
