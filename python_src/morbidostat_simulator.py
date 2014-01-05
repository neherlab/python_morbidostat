import time
import math
import threading
import numpy as np

debug = False
# dictionary mapping pumps to pins
pumps = {'medium': range(7,7+15), 
         'drug A': range(22,22+15),
         'drug B': range(38,38+15)}


class morbidostat:
    def __init__(self):
        self.n_cultures= 15
        self.OD = np.zeros(self.n_cultures)
        self.IC50 = np.zeros(self.n_cultures)
        self.antibiotic = np.zeros(self.n_cultures)
        self.max_growth_rate = np.zeros(self.n_cultures)
        self.time = 0
        self.dt = 10.0
        self.concA = 1.0
        self.concB = 5.0
        self.volume = 10.0
        self.speed_up = 100

    def growth_rate(self):
        return self.max_growth_rate/(1+(self.antibiotic/self.IC50)**2)

    def set_up_and_start(self, OD_init=0.01, IC50_init=0.1, antibiotic_init=0, max_growth_rate_init=0.02):
        self.OD[:] = OD_init
        self.IC50[:] = IC50_init
        self.antibiotic[:] = antibiotic_init
        self.max_growth_rate[:] = max_growth_rate_init

        self.evolve_thread=threading.Thread(target = self.evolve)
        self.evolve_thread.start()

    def evolve(self):
        while self.time<100*self.dt:
            self.OD+=self.dt*self.growth_rate()*self.OD*(1+0.1*np.random.randn(self.n_cultures))
            self.IC50+=0.1*(np.random.random(self.n_cultures)<0.1/(1+np.exp((self.IC50-self.antibiotic)*100))
                            )*np.random.standard_exponential(self.n_cultures)
            time.sleep(1.0*self.dt/self.speed_up)
            self.time+=self.dt


    def measure_OD(self, vial, n_measurements=1, dt=10, switch_light_off=True):
        return self.OD[vial]+0.01*np.random.randn()


    def inject_volume(self, pump_type='medium', pump_number=0, volume=0.1):
        # run the pump for calculated time
        if pump_type=='medium':
            self.antibiotic[pump_number]*=(1 - volume/self.volume)
        elif pump_type=='drug A':
            self.antibiotic[pump_number]*=(1 - volume/self.volume)
            self.antibiotic[pump_number]+=self.concA*volume/self.volume
        elif pump_type=='drug B':
            self.antibiotic[pump_number]*=(1 - volume/self.volume)
            self.antibiotic[pump_number]+=self.concB*volume/self.volume
