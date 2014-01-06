import arduino_interface as morb
import numpy as np
import time
from __future__ import division
import copy

do_nothing = ('',1)
dilute_w_medium = ('medium',2)
dilute_w_drugA = ('drug A', 3)
dilute_w_drugB = ('drug B', 4)

def morbidostat:
    '''
    Running a morbidostat experiment. 
    This class communicates with the morbidostat device through a separate
    interface class and records the optical density of an array of culture vials.
    in response to these OD measurements, the class triggers the addition of 
    either medium or drug solution at different concentrations. 
    '''
    
    def __init__(self, vials = range(15), experiment_duration = 24*60*60, 
                 target_OD = 0.1, diluation_factor = 0.9, bug = '', drug =''
                 drugA_concentration = 0.0, drugB_concentration = 0.0):

        # all times in seconds, define parameter second to speed up for testing
        self.second = 1.0

        # set up the morbidostat
        self.morb = morb.morbidostat()
        self.morbidostat_port = self.morb.connect()
        if not self.morb.morbidostat_OK:
            print("Trouble setting up morbidostat")
        # sync time units
        morb.second = self.second

        # experiment parameters
        self.OD_dt = 60
        self.cycle_dt = 60*10
        self.experiment_duration = experiment_duration

        if (np.max(vials)<15):
            self.vials = copy.copy(vials)
        else:
            print("Morbidostat set-up: all vial numbers must be between 0 and 14")
            self.vials = []

        self.target_OD = target_OD
        self.culture_volume = 10
        self.dilution_factor = 0.9
        self.dilution_volume = self.culture_volume*(1.0-self.dilution_factor)
        self.target_growth_rate = -np.log(self.dilution_factor)/self.dilute_dt
        self.drug = drug
        self.bug = bug
        self.drugA_concentration = drugA_concentration
        self.drugB_concentration = drugB_concentration

        # allocate memory for measurements and culture decisions
        self.ODs_per_cycle = (self.cycle_dt-morb.mixing_time)//self.OD_dt
        self.n_cycles = self.experiment_duration/self.cycle_dt

        self.OD = np.zeros((self.n_cycles, self.ODs_per_cycle, len(self.vials)+1), dtype = float)
        self.decisions = np.zeros((self.n_cycles, len(self.vials)+1), dtype = int)
        self.vial_drug_concentration = np.zeros((self.n_cycles, len(self.vials)+1), dtype = float)
        self.historical_drug_A_concentration = []
        self.historical_drug_B_concentration = []
        self.last_OD_measurements = np.zeros((self.ODs_per_cycle,len(vials+1)))
        self.growth_rate_estimate = np.zeros(len(self.vials))
        self.final_OD_estimate = np.zeros(len(self.vials))

        # counters
        self.OD_measurement_counter = 0
        self.cycle_counter = 0

        # threads handling repeated measurements
        self.cycle_thread = None
        self.OD_thread = None
        
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


    def start_experiment(self):
        self.cycle_thread = threading.Thread(target = self.run_morbidostat)

    def interrupt_experiment(self):
        '''
        finish the current cycle and stop.
        this should stop after the OD measurement and growth rate estimate,
        but before the dilutions (but this is not essential)
        '''
        pass

    def resume_experiment(self):
        '''
        resume the experiment after it having been stopped
        will start with OD measurements for one full cycle and continue as
        if from the beginning
        '''
        pass

    def run_morbidostat(self):
        '''
        loop over cycles, call the 
        '''
        for ci in xrange(self.n_cycles):
            tmp_cycle_start = time.time()
            self.morbidostat_cycle()
            remaining_time = self.cycle_dt-time.time()+tmp_cycle_start
            if remaining_time>0:
                time.sleep(remaining_time)
            else:
                print("run_morbidostat: remaining time is negative"+str(remaining_time))
            self.cycle_counter+=1
            

    def morbidostat_cycle(self):
        self.OD_thread = threading.Thread(target = self.measure_OD_for_cycle)
        # start thread and wait for it to finish
        self.OD_thread.start()
        self.OD_thread.join(timeout=self.OD_dt*1.5*self.second)
        if self.OD_thread.is_alive():
            print("morbidostat_cycle: OD measurement timed out")

        self.estimate_growth_rates()
        self.feedback_on_OD()
        morb.wait_until_mixed()

    def measure_OD_for_cycle():
        for oi in xrange(self.ODs_per_cycle):
            tmp_OD_measurement_start = time.time()
            self.measure_OD()
            remaining_time = self.OD_dt - time.time()+tmp_OD_measurement_start 
            if remaining_time>0:
                time.sleep(remaining_time)
            else:
                print("measure_OD_for_cycle: remaining time is negative"+str(remaining_time))
            self.OD_measurement_counter+=1

    def measure_OD(self):
        '''
        measure OD in all culture vials, add the measurement to the big stack and
        stores it in last_OD_measurement. Increments OD_measurement_counter by 1
        the IR LEDS are switched off at the end.
        '''
        t = time.time()-self.experiment_start
        for vi,vial in enumerate(vials):
            self.last_OD_measurements[self.OD_measurement_counter, vi] = morb.measure_OD(self.ser,vial, self.n_reps, self.rep_dt, False)
        
        self.last_OD_measurements[self.OD_measurement_counter,-1]=t
        morb.switch_light(self.ser, False)

    def estimate_growth_rates(self):
        '''
        estimate the growth rate and final OD in the last dilution period. 
        This function fits a line to the log OD in the last cycle for each vial
        The growth rate is the slope of the linear regression, the final_OD
        is the value of the regression line at the final time point
        '''
        final_time  = self.last_OD_measurements[self.OD_measurement_counter-1,-1]
        tmp_time_array = self.last_OD_measurements[:self.OD_measurement_counter,-1]-final_time
        for vi, vial in enumerate(self.vials):
            tmp_regress = stats.linregress(tmp_time_array,
                                           np.log(self.last_OD_measurements[:self.OD_measurement_counter,vi]))
            self.growth_rate_estimate[vi] = tmp_regress[0]
            self.final_OD_estimate[vi] = np.exp(tmp_regress[1])
            if tmp_regress[2]<0.7:
                print("morbidostat_experiment: bad fit, regression "+str(tmp_regress))
        
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
                if (self.growth_rate_estimate[vi] < self.target_growth_rate ):
                    if self.antibiotic[vi]<self.drugA_concentration:
                        tmp_decision = dilute_w_medium
                    elif:
                        tmp_decision = dilute_w_drugA
                else:
                    if self.antibiotic[vi]<0.5*self.drugA_concentration:
                        tmp_decision = dilute_w_drugA
                    elif:
                        tmp_decision = dilute_w_drugB

            
            if tmp_decision[1]>0:
                morb.inject_volume(tmp_decision[0], vial, self.dilution_volume)
                self.decisions[self.cycle_counter,vial] = tmp_decision[1]

