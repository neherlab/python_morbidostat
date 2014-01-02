import arduino_interface as morb
import numpy as np
import time
from __future__ import division
import copy

def morbidostat:
    '''
    Running a morbidostat experiment. 
    This class communicates with the morbidostat device through the a separate
    interface class and records the optical density of an array of culture vials.
    in response to these OD measurements, the class triggers the addition of 
    either medium or drug solution at different concentrations. 
    '''
    
    def __init__(self, vials = range(15), experiment_duration = 24*60*60, 
                 target_OD = 0.1, diluation_factor = 0.9, bug = '', drug =''
                 drugA_concentration = 0.0, drugB_concentration = 0.0):
        # all times in seconds

        # experiment parameters
        self.OD_dt = 60
        self.dilute_dt = 60*10
        self.experiment_duration = experiment_duration
        if (np.max(vials)<15):
            self.vials = copy.copy(vials)
        else:
            print("Morbidostat set-up: all vial numbers must be between 0 and 14")
            self.vials = []
        self.target_OD = target_OD
        self.dilution_factor = 0.9
        self.target_growth_rate = -np.log(self.dilution_factor)/self.dilute_dt
        self.drug = drug
        self.bug = bug
        self.drugA_concentration = drugA_concentration
        self.drugB_concentration = drugB_concentration

        # allocate memory for measurements and culture decisions
        self.n_OD_measurements = self.experiment_duration/self.OD_dt
        self.n_dilutions = self.experiment_duration/self.dilute_dt

        self.OD = np.zeros((self.n_OD_measurements, len(self.vials)+1), dtype = float)
        self.decisions = np.zeros((self.n_dilutions, len(self.vials)+1), dtype = int)
        self.vial_drug_concentration = np.zeros((self.n_dilutions, np.max(self.vials)+1), dtype = float)
        self.historical_drug_A_concentration = []
        self.historical_drug_B_concentration = []
        self.last_OD_measurement = np.zeros(np.max(vials))
        
        # counters
        self.OD_measurement_counter = 0
        self.dilution_counter = 0
        
        # file names
        self.experiment_start = time.time()
        tmp_time = time.localtime()
        self.base_name = "".join(map(str, [tmp_time.tm_year, 
                                           tmp_time.tm_month, 
                                           tmp_time.tm_day])
                                 ) + '_'.join([self.bug, self.drug])
        self.OD_fname = self.base_name+'_OD.txt'
        self.decisions_fname = self.base_name+'_decisions.txt'
        self.drug_conc_fname = self.base_name+'_vials_drug_concentrations.txt'


    def save_data(self):
        '''
        save the entire arrays to file. note that this will save a LOT of zeroes
        at the beginning of the experiment and generally tends to overwrite files 
        often with the same data -> come up with something more clever
        '''
        np.savetxt(self.OD_fname, self.OD)
        np.savetxt(self.decisions, self.decisions)
        np.savetxt(self.drug_conc_fname, self.vial_drug_concentration)


                                      
    def measure_OD(self):
        '''
        measure OD in all culture vials, add the measurement to the big stack and
        stores it in last_OD_measurement. Increments OD_measurement_counter by 1
        the IR LEDS are switched off at the end.
        '''
        t = time.time()-self.experiment_start
        OD[self.OD_measurement_counter,0]=t
        for vi,vial in enumerate(vials):
            self.last_OD_measurement[vi] = morb.measure_OD(self.ser,vial, self.n_reps, self.rep_dt, False)
        
        OD[self.OD_measurement_counter,1:] = self.last_OD_measurement
        morb.switch_light(self.ser, False)
        self.OD_measurment_counter+=1

    def feedback_on_OD(self):
        '''
        THis function is called every dilute_dt
        it interogates the OD measurements and decides whether to 
        (i) do nothing
        (ii) dilute with medium
        (iii) dilute with drug A
        (iv) dilute with drug B
        the dilution counter is incremented at the end
        '''
        for vi, vial in enumerate(self.vials):
            if self.last_OD_measurement[vi]<self.dilution_threshold:
                tmp_decision = do_nothing
            else:
                if (delta_OD = )
