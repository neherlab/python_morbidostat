from __future__ import division
import numpy as np
from scipy.stats import linregress
import time,copy,threading,os,sys
from scipy import stats
import glob
import csv

 
simulator = False
if simulator:
    import morbidostat_simulator as morb
else:
    import arduino_interface as morb


MORBIDOSTAT_EXPERIMENT = 'M'
CONTINUOUS_MORBIDOSTAT = 'C'
GROWTH_RATE_EXPERIMENT = 'G'
FIXED_OD_EXPERIMENT = 'OD'

do_nothing = ("none", -1)


def calibrate_OD(vials = None):
    '''
    measure OD of OD standard, calculate regression coefficients
    '''
    import matplotlib.pyplot as plt
    if vials is None:
        vials = range(15)
    calibration_morb = morb.morbidostat()
    no_valid_standard=True
    ODs = []
    voltages = []
    all_cycles_measured = False
    while all_cycles_measured==False:
        while no_valid_standard:
            s = raw_input("Enter OD of standard [q to quit]: ")
            if s=='q':
                print("Aborting calibration")
		all_cycles_measured = True
		break
            try:
                cur_OD = float(s)
                no_valid_standard=False
            except:
                print("invalid entry")

        if not all_cycles_measured: # prompt user for 15 measurements while q is not pressed
            ODs.append(cur_OD)
            voltages.append(np.zeros(len(vials)))
            for vi,vial in enumerate(vials):
                OKstr = raw_input("Place OD standard in receptible "+str(vial+1)+
                                  ", press enter when done")
                time.sleep(0.001)  #delay for 1 second to allow for heating of the diode
                voltages[-1][vi] = calibration_morb.measure_voltage(vial, switch_light_off=True)[0]
                print vial, "measurement ", voltages[-1][vi]
            no_valid_standard=True

    if len(ODs)>1:
        print("Collected "+str(len(ODs))+" OD voltage pairs, calculating voltage -> OD  conversion")
        ODs = np.array(ODs)
        voltages = np.array(voltages).T
        fit_parameters = np.zeros((len(vials), 2))
        for vi,vial in enumerate(vials):
            good_measurements = voltages[vi,:]<900
            if good_measurements.sum()>1:
                slope, intercept, r,p,stderr = linregress(ODs[good_measurements], voltages[vi,good_measurements])
            else:
                print("less than 2 good measurements, also using saturated measurements for vial"+str(vial))
                slope, intercept, r,p,stderr = linregress(ODs, voltages[vi,:])
            fit_parameters[vi,:] = [1.0/slope,  -intercept/slope]
        np.savetxt(morb.OD_calibration_file_name, fit_parameters)
        tmp_time = time.localtime()

        # make figure showing calibration
        plt.plot(ODs, voltages.T, 'o', ls='-')
        plt.xlabel('OD standard')
        plt.ylabel('measured signal (0-1023)')

        # save calibration measurements
        date_string = "".join([format(v,'02d') for v in
                               [tmp_time.tm_year, tmp_time.tm_mon, tmp_time.tm_mday]])
        with open(morb.morb_path+'data/voltage_measurements_'+date_string+'.txt', 'w') as volt_file:
            for oi in range(len(ODs)):
                volt_file.write(str(ODs[oi]))
                for vi in range(len(vials)):
                    volt_file.write('\t'+str(voltages[vi,oi]))
                volt_file.write('\n')

    else:
        print("need measurements for at least two OD standards")
    return fit_parameters, ODs, voltages

def calibrate_pumps(mymorb, pump_type, vials = None, dt = 100):
    '''
    Routine that runs all pumps sequentially assuming the outlet is sitting on
    on a balance. after running a pump for dt seconds, the user is prompted for the weight
    until all 15 pumps have been run
    '''
    if vials is None:
        vials = range(15)
    s = raw_input("press enter to start, q to stop: ")
    if len(s)>0:
        print("Aborting calibration")
        return

    # loop over vials, prompt for weight
    weight  = np.zeros((2,len(vials)))
    print("Put in weight of vials before pumping")
    for vi,vial in enumerate(vials):
        no_weight = True
        while no_weight:
            s = raw_input('weight of vial '+str(vial+1)+': ')
            try:
                weight[0][vi] =float(s)
                no_weight = False
            except:
                print("invalid weight")

    mymorb.run_all_pumps(pump_type, dt)
    print("Put in weight of vials after pumping")
    for vi,vial in enumerate(vials):
        no_weight = True
        while no_weight:
            s = raw_input('weight of vial '+str(vial+1)+': ')
            try:
                weight[1][vi] =float(s)
                no_weight = False
            except:
                print("invalid weight")


    # calculate pump_rate and save to file
    pump_rate = (weight[1]-weight[0])/dt
    np.savetxt(morb.pump_calibration_file_base+'_'+pump_type+'.dat', pump_rate)

class morbidostat(object):
    '''
    Running a morbidostat experiment.
    This class communicates with the morbidostat device through a separate
    interface class and records the optical density of an array of culture vials.
    in response to these OD measurements, the class triggers the addition of
    either medium or drug solution at different concentrations.
    '''
    def __init__(self, vials = range(15), experiment_duration = 2*60*60,
                 target_OD = 1, dilution_factor = 0.9, bug = 'tbd', drugs =[], mics=[],
                 bottles = [], OD_dt = 30, cycle_dt = 600, experiment_name="tbd", verbose=1):
        # the default experiment is a morbidostat measurement
        self.experiment_type = MORBIDOSTAT_EXPERIMENT

        # all times in seconds, define parameter second to speed up for testing
        if simulator:
            self.second = .001
        else:
            self.second = 1.0
        self.verbose = verbose
        # set up the morbidostat
        self.morb = morb.morbidostat()
        self.morbidostat_port = self.morb.connect()
        if not self.morb.morbidostat_OK:
            print("Trouble setting up morbidostat")
        # sync time units
        self.morb.second = self.second

        # experiment parameters
        self.OD_dt = OD_dt
        self.cycle_dt = cycle_dt
        self.experiment_duration = experiment_duration

        if (np.max(vials)<15):
            self.vials = copy.copy(vials)
        else:
            print("Morbidostat set-up: all vial numbers must be between 0 and 14")
            self.vials = []

        self.target_OD = target_OD
        self.culture_volume = 18 # target volume in milliliters
        self.dilution_factor = dilution_factor
        self.drug_injection_count = [0]*len(vials)
        self.dilution_threshold = 0.09
        self.extra_suction  = 2 # extra volume that is being sucked out of the vials [ml]
        self.drugs = drugs
        self.mics = mics
        self.ndrugs = len(drugs)
        self.nbottles = len(bottles)
        self.bottles = bottles
        self.experiment_name = experiment_name
        self.bug = bug
        self.drug_concentrations = np.zeros((self.nbottles, self.ndrugs))
        self.historical_drug_concentrations = []
        self.experiment_start = 0.0
        # data acqusition specifics
        self.n_reps=8
        self.buffer_time = 10
        # counters
        self.OD_measurement_counter = 0
        self.cycle_counter = 0
        self.restart_from_file=None # if a directory name, resume from there.
        #feedback parameters
        self.max_growth_fraction = 0.012     # increase antibiotics with 1.5% OD increase per cycle
        self.AB_switch_conc = 0.3          # use high concentration if culture conc is 30% of drug A
        self.feedback_time_scale =  12       # compare antibiotic concentration to that x cycles ago
        self.saturation_threshold = 0.4   # threshold beyond which OD can't be reliable measured
        self.anticipation_threshold = 0.95  # fraction of target_OD, at which increasing antibiotics is first considered
        # diagnostic variables
        self.max_AB_fold_increase = 1.1    # maximum amount by which the antibiotic concentration is allowed to increase within the feed back time scale
        self.mic_kd = 0.25   # fraction of the mic to which is added to low drug concentrations when calculating the AB_fold_increase
        self.stopped = True
        self.interrupted = False
        self.running = False
        self.override = False
        self.tmp_conc = 5

        self.n_cycles = self.experiment_duration//self.cycle_dt
        self.n_vials = len(self.vials)
        self.calculate_derived_values()
        self.ODs_per_cycle = int(self.cycle_dt-self.morb.mixing_time-self.pump_time - self.buffer_time)//self.OD_dt
        self.prefactor_conc_start = 0.1
        self.prefactor_conc_multiplication = 3
        self.prefactor_conc_anticipation = 0.025
        self.prefactor_start_conc_comparison = 1
        self.max_rel_increase = 0.6 
        self.delta_OD_time_scale = 6
        self.conc_diff_time_scale = 8 
        self.prefactor_critical_conc = 0.5
        self.store_critical_conc = [500]*len(vials)
        self.load_from_file_limit = True
        self.old_experiment_duration = 0


    def set_vial_properties(self, vial_dict):
        self.vial_props = vial_dict

    def calculate_derived_values(self):
        '''
        values calculated after other parameters are set.
        '''
        self.dilution_volume = self.culture_volume*(1.0/np.max((0.5, self.dilution_factor))-1.0)
        self.target_growth_rate = -np.log(self.dilution_factor)/self.cycle_dt
        self.pump_time = np.max([self.morb.volume_to_time('pump2',vi,self.dilution_volume) for vi in self.vials])


    def set_up(self):
        '''
        this allocate memory for measurements and culture decisions
        note that this only works for fixed experiment length.
        the duration of the experiment cannot be changed after this function is called
        '''
        self.n_cycles = self.experiment_duration//self.cycle_dt
        self.n_vials = len(self.vials)
        self.calculate_derived_values()
        self.ODs_per_cycle = int(self.cycle_dt-self.morb.mixing_time-self.pump_time - self.buffer_time)//self.OD_dt

        self.OD = np.zeros((self.n_cycles, self.ODs_per_cycle, self.n_vials+1), dtype = float)
        self.temperatures = np.zeros((self.n_cycles, 3))
        self.decisions = np.zeros((self.n_cycles, self.n_vials+1), dtype = float)
        self.dilution_concentration = np.zeros((self.n_cycles+1, self.n_vials+1), dtype = float)
        self.vial_drug_concentration = np.zeros((self.n_cycles+1, self.n_vials+1, self.ndrugs), dtype = float)
        self.vial_drug_concentration[:,-1:, ]=np.nan

        self.last_OD_measurements = np.zeros((self.ODs_per_cycle,self.n_vials+1))
        self.growth_rate_estimate = np.zeros((self.n_cycles,self.n_vials+1))
        self.final_OD_estimate = np.zeros((self.n_cycles,self.n_vials+1))

        # threads handling repeated measurements
        self.cycle_thread = None
        self.OD_thread = None

        # file names
        from datetime import date
        today =date.today()
        if self.restart_from_file is None or os.path.exists(self.restart_from_file)==False:
            base_name = morb.morb_path+'data/'\
                 + '_'.join([today.strftime("%Y-%m-%d"), self.experiment_name, self.bug])+'/'
            self.base_name = base_name.replace(" ", "_")
            if os.path.exists(self.base_name):
                print self.base_name+"directory already exists"
            else:
                os.mkdir(self.base_name)
            if not os.path.exists(self.base_name+'/OD'):
                os.mkdir(self.base_name+'OD/')
        else:
            self.base_name = self.restart_from_file.rstrip('/')+'/'

        self.OD_fname = self.base_name+'OD/OD'
        self.decisions_fname = self.base_name+'decisions.txt'
        self.drug_conc_fname = {}
        for drug in self.drugs:
            self.drug_conc_fname[drug] = self.base_name+'vials_%s_concentrations.txt'%drug
        self.temperature_fname = self.base_name+'temperature.txt'
        self.cycle_OD_fname = self.base_name+'cycle_OD_estimate.txt'
        self.growth_rate_fname = self.base_name+'growth_rate_estimates.txt'
        self.last_cycle_fname = self.base_name+'OD/'+'current_cycle.dat'

        if self.restart_from_file:
            self.load_data_from_file()

    def load_data_from_file(self):
        print('coutner',self.cycle_counter)
        self.base_name = self.restart_from_file
        self.OD_fname = self.base_name+'OD/OD'
        self.decisions_fname = self.base_name+'decisions.txt'
        self.drug_conc_fname = {}
        for drug in self.drugs:
            self.drug_conc_fname[drug] = self.base_name+'vials_%s_concentrations.txt'%drug
        self.temperature_fname = self.base_name+'temperature.txt'
        self.cycle_OD_fname = self.base_name+'cycle_OD_estimate.txt'
        self.growth_rate_fname = self.base_name+'growth_rate_estimates.txt'
        self.last_cycle_fname = self.base_name+'OD/'+'current_cycle.dat'

        # find cycle counter from previous run
        # find last epxeriment time from last cycle


        parameter_file = glob.glob(self.base_name+'/para*')
        if self.load_from_file_limit:
            self.load_from_file_limit = False
            last_cycle = sorted(os.listdir(self.base_name+'OD'))[-2]
            self.cycle_counter = int(last_cycle[-8:-4])
            with open(parameter_file[0],'r') as myfile:
                read_parameter = csv.reader(myfile,delimiter='\t')
                for row in read_parameter:
                    if row[0] == 'experiment_start:':
                        old_experiment_time = row[1]
                    if row[0] == 'experiment_duration:':
                        self.old_experiment_duration = float(row[1])
                        print('exp duration',self.old_experiment_duration)
        #print(old_experiment_duration,old_experiment_time)


        


    def add_cycles_to_data_arrays(self, cycles_to_add):
        '''
        provides the possibility to extend a running experiment by providing more space
        in the arrays used to store the data.
        '''
        self.OD = np.concatenate((self.OD, np.zeros((cycles_to_add, self.ODs_per_cycle, self.n_vials+1), dtype = float)))
        self.temperatures = np.concatenate((self.temperatures, np.zeros((cycles_to_add, 3), dtype = float)))
        self.decisions = np.concatenate((self.decisions, np.zeros((cycles_to_add, self.n_vials+1), dtype = float)))
        self.vial_drug_concentration = np.concatenate((self.vial_drug_concentration,
                            np.zeros((cycles_to_add+1, self.n_vials+1, self.ndrugs), dtype = float)))
        self.vial_drug_concentration[-cycles_to_add:,-1,0]=np.arange(self.vial_drug_concentration.shape[0]-cycles_to_add,
                                                     self.vial_drug_concentration.shape[0])*self.cycle_dt

        self.growth_rate_estimate = np.concatenate((self.growth_rate_estimate, np.zeros((cycles_to_add,self.n_vials+1))))
        self.final_OD_estimate = np.concatenate((self.final_OD_estimate, np.zeros((cycles_to_add,self.n_vials+1))))


    def experiment_time(self):
        if self.restart_from_file is not None:
            #print(time.time()+self.old_experiment_duration-self.experiment_start/self.second)
            #print(self.old_experiment_duration)
            return (time.time()-self.experiment_start+self.experiment_duration)/self.second
        else:
            return (time.time()-self.experiment_start)/self.second

    def write_parameters_file(self, ):
        with open(self.base_name+'/parameters_%s.dat'%time.strftime('%Y-%m-%d_%H_%M_%S'), 'w') as params_file:
            params_file.write('vials\t'+'\t'.join(map(str,self.vials))+'\n')
            params_file.write('Experiment:\t'+self.experiment_name+'\n')
            params_file.write('Strain:\t'+self.bug+'\n')
            params_file.write('Drugs:\t'+'\t'.join(self.drugs)+'\n')
            params_file.write('Bottles:\t'+'\t'.join(self.bottles)+'\n')
            params_file.write('drug_concentrations:\t'+'\t'.join(map(str, self.drug_concentrations))+'\n')
            params_file.write('cycle_duration:\t'+str(self.cycle_dt)+'\n')
            params_file.write('measurements/cycle:\t'+str(self.ODs_per_cycle)+'\n')
            params_file.write('OD_dt:\t'+str(self.OD_dt)+'\n')
            params_file.write('experiment_start:\t'+str(self.experiment_start)+'\n')
            params_file.write('experiment_duration:\t'+str(self.experiment_duration)+'\n')
            params_file.write('AB_switch_conc:\t'+str(self.AB_switch_conc)+'\n')
            params_file.write('max_AB_fold_increase:\t'+str(self.max_AB_fold_increase)+'\n')
            params_file.write('feedback_time_scale:\t'+str(self.feedback_time_scale)+'\n')
            params_file.write('anticipation_threshold:\t'+str(self.anticipation_threshold)+'\n')
            params_file.write('saturation_threshold:\t'+str(self.saturation_threshold)+'\n')
            params_file.write('dilution_threshold:\t'+str(self.dilution_threshold)+'\n')
            params_file.write('dilution_factor:\t'+str(self.dilution_factor))

    def load_parameters_file(self, fname):
        try:
            with open(fname, 'r') as params_file:
                for line in params_file:
                    entries = line.split()
                    try:
                        if entries[0]=='vials':
                            self.__setattr__('vials', map(int, entries[1:]))
                            self.n_vials = len(self.vials)
                        elif entries[0]=='Experiment:':
                            self.__setattr__('experiment_name', entries[1])
                        elif entries[0]=='Strain:':
                            self.__setattr__('bug', entries[-1])
                        elif entries[0]=='drugs:':
                            self.__setattr__('drugs', entries[1:])
                        elif entries[0]=='drug_concentrations:':
                            self.__setattr__('drug_concentrations', np.array(map(float(entries[1:]))))
                        elif entries[0]=='cycle_duration:':
                            self.__setattr__('cycle_dt', int(entries[-1]))
                        elif entries[0]=='measurements/cycle:':
                            self.__setattr__('ODs_per_cycle', int(entries[-1]))
                        elif entries[0]=='OD_dt:':
                            self.__setattr__('OD_dt', int(entries[-1]))
                        elif entries[0]=='experiment_start:':
                            self.__setattr__('experiment_start', float(entries[-1]))
                        elif entries[0]=='experiment_duration:':
                            self.__setattr__('experiment_duration', int(entries[-1]))
                        elif entries[0]=='dilution_factor:':
                            self.__setattr__('dilution_factor', float(entries[-1]))
                        elif entries[0]=='AB_switch_conc:':
                            self.__setattr__('AB_switch_conc', float(entries[-1]))
                        elif entries[0]=='max_AB_fold_increase:':
                            self.__setattr__('max_AB_fold_increase', int(entries[-1]))
                        elif entries[0]=='feedback_time_scale:':
                            self.__setattr__('feedback_time_scale', float(entries[-1]))
                        elif entries[0]=='anticipation_threshold:':
                            self.__setattr__('anticipation_threshold', float(entries[-1]))
                        elif entries[0]=='saturation_threshold:':
                            self.__setattr__('saturation_threshold', float(entries[-1]))
                        elif entries[0]=='dilution_threshold:':
                            self.__setattr__('dilution_threshold', float(entries[-1]))
                        else:
                            print "unrecognized parameter entry:",line, entries
                    except:
                        print "can't parse:", line, entries
        except:
            print "can't read parameters file"


    def set_drug_concentrations(self, bottle, conc, initial=False):
        '''
        change drug concentrations during run time
        '''
        if bottle in self.bottles:
            bottle_ii = self.bottles.index(bottle)
            if not initial:
                self.historical_drug_concentrations.append((self.experiment_time(),
                        np.copy(self.drug_concentrations)))
            self.drug_concentrations[bottle_ii]=conc
        else:
            print("not a valid bottle, has to be one of ", self.bottles)


    def save_data(self):
        '''
        save the entire arrays to file. note that this will save a LOT of zeroes
        at the beginning of the experiment and generally tends to overwrite files
        often with the same data. Only OD is saved cycle wise
        '''
        lockfname = self.base_name+'/.lock'   # write a file that contains the date to lock
        with open(lockfname, 'w') as lockfile:
            lockfile.write(time.strftime('%x %X'))

        # save OD data from individual cycle
        np.savetxt(self.OD_fname+'_cycle_'+format(self.cycle_counter, '05d')+'.dat', self.OD[self.cycle_counter], fmt='%2.3f')
        # overwrite all remaining files
        np.savetxt(self.decisions_fname, self.decisions, fmt='%2.3f')
        for di, drug in enumerate(self.drugs):
            np.savetxt(self.drug_conc_fname[drug], self.vial_drug_concentration[:,:,di],fmt='%2.6f')
        np.savetxt(self.temperature_fname, self.temperatures, fmt='%2.1f')
        np.savetxt(self.growth_rate_fname, self.growth_rate_estimate,fmt='%2.6f')
        np.savetxt(self.cycle_OD_fname, self.final_OD_estimate,fmt='%2.3f')
        os.remove(lockfname)

    def save_within_cycle_data(self):
        '''
        save only OD of the current cycle
        '''
        lockfname = self.base_name+'/.lock'
        with open(lockfname, 'w') as lockfile:
            lockfile.write(time.strftime('%x %X'))
        np.savetxt(self.last_cycle_fname, self.last_OD_measurements[:self.OD_measurement_counter,:],fmt='%2.3f')
        os.remove(lockfname)


    def start_experiment(self):
        '''
        start the thread measuring and feedbacking the cultures
        '''
        if self.running==False:
            self.set_up()
            self.cycle_thread = threading.Thread(target = self.run_morbidostat)
            self.experiment_start = time.time()
            self.cycle_thread.start()
            self.running = True
            self.stopped = False
            self.interrupted=False
            self.write_parameters_file()
        else:
            print "experiment already running"

    def stop_experiment(self):
        '''
        set the stop signal and wait for threads to finish
        '''
        self.stopped = True
        if self.running and self.cycle_counter<self.n_cycles:
            print "Stopping the cycle thread, waiting for cycle to finish"
            self.cycle_thread.join()

        print "experiment has finished. disconnecting the morbidostat"
        self.morb.disconnect()
        self.running=False
    se = stop_experiment

    def interrupt_experiment(self):
        '''
        finish the current cycle and stop.
        this should stop after the OD measurement and growth rate estimate,
        but before the dilutions (but this is not essential)
        '''
        if self.running:
            self.interrupted = True
            if self.cycle_counter<self.n_cycles and self.running:
                print "Stopping the cycle thread, waiting for cycle to finish"
                self.cycle_thread.join()
            print "recording stopped, safe to disconnect"
        else:
            print "experiment not running"
    ie = interrupt_experiment

    def reset_concentrations(self):
        '''
        reset vial concentrations to zero, e.g. after sample taking,
        experiment has to be interrupted
        '''
        if self.interrupted:
            self.vial_drug_concentration[self.cycle_counter,:-1]=0
            print "vial concentrations set to zero"
        else:
            print "experiment has to be interrupted to reset vial concentrations"

    def resume_experiment(self):
        '''
        resume the experiment after it having been stopped
        will start with OD measurements for one full cycle and continue as
        if from the beginning
        '''
        if self.interrupted:
            self.cycle_thread = threading.Thread(target = self.run_morbidostat)
            self.interrupted=False
            self.running = True
            self.cycle_thread.start()
            print "morbidostat restarted in cycle", self.cycle_counter
        else:
            print "experiment is not interrupted"
    re = resume_experiment

    def run_all_pumps(self, pump_type, run_time):
        '''
        run all pumps of a specified type, for example for cleaning purposes
        '''
        for vi,vial in enumerate(self.vials):
            self.morb.run_pump(pump_type=pump_type, pump_number = vial, run_time = run_time)

    def run_morbidostat(self):
        '''
        loop over cycles, call the morbidostat cycle function
        '''
        initial_cycle_count = self.cycle_counter
        for ci in xrange(initial_cycle_count, self.n_cycles):
            if self.verbose>0:
                print "#####################\n# Cycle",ci,"\n#####################"
            tmp_cycle_start = time.time()
            self.morbidostat_cycle()
            self.save_data()
            self.cycle_counter+=1
            remaining_time = self.cycle_dt-(time.time()-tmp_cycle_start)/self.second
            if remaining_time>0:
                time.sleep(remaining_time*self.second)
                if self.verbose>2:
                    print "run_morbidostat: remaining time", remaining_time
            else:
                if self.verbose>2:
                    print("run_morbidostat: remaining time is negative"+str(remaining_time))
            if self.stopped or self.interrupted:
                break
        if self.cycle_counter==self.n_cycles:
            self.stop_experiment()


    def morbidostat_cycle(self):
        t = self.experiment_time()
        self.morb.measure_temperature(switch_light_off=True)
        time.sleep(2.0*self.second)  # delay to allow for temperature conversion
        self.OD_measurement_counter=0
        self.OD_thread = threading.Thread(target = self.measure_OD_for_cycle)
        # start thread and wait for it to finish
        self.OD_thread.start()
        self.OD_thread.join(timeout=(self.OD_dt+5)*self.ODs_per_cycle*self.second)
        if self.OD_thread.is_alive():
            print("morbidostat_cycle: OD measurement timed out")

        self.estimate_growth_rates()
        # keep track of volumes that are added to gauge waste removal
        self.added_volumes = np.zeros(len(self.vials))
        for vi,vial in enumerate(self.vials):
            if  self.vial_props[vial]["feedback"] == MORBIDOSTAT_EXPERIMENT:
                self.feedback_on_OD(vial)
            elif self.vial_props[vial]["feedback"] == FIXED_OD_EXPERIMENT:
                self.dilute_to_OD(vial)
            elif self.vial_props[vial]["feedback"] == GROWTH_RATE_EXPERIMENT:
                pass
            elif self.vial_props[vial]["feedback"] == CONTINUOUS_MORBIDOSTAT:
                self.continuous_feedback(vial)
            else:
                print "unknown experiment type:", self.experiment_type[vi]
        self.vial_drug_concentration[self.cycle_counter, -1, :] = self.experiment_time()
        self.morb.wait_until_mixed()
        # remove the max of the added volumes plus some safety margin.
        # this will suck air in some vials.
        run_time = self.morb.remove_waste(max(self.added_volumes) + self.extra_suction)
        if not simulator:
            self.morb.pump_off_threads[('waste pump',0)].join()
        self.temperatures[self.cycle_counter,-1] = t
        self.temperatures[self.cycle_counter,:2] = self.morb.temperatures


    def measure_OD_for_cycle(self):
        '''
        acquires all measurents for a given OD counter is incremented in parent
        '''
        self.last_OD_measurements[:] = 0
        for oi in xrange(self.ODs_per_cycle):
            if self.verbose>3:
                print "OD measurement:",self.OD_measurement_counter
            tmp_OD_measurement_start = time.time()
            self.measure_OD()
            self.OD_measurement_counter+=1
            self.save_within_cycle_data()
            if self.verbose==1:
                print "OD measurement %d out of %d            \r"%(oi+1, self.ODs_per_cycle),
                sys.stdout.flush()
            remaining_time = self.OD_dt - (time.time()-tmp_OD_measurement_start)/self.second
            if remaining_time>0:
                time.sleep(remaining_time*self.second)
            else:
                if self.verbose>2:
                    print("measure_OD_for_cycle: remaining time is negative"
                      +str(remaining_time))
        self.OD[self.cycle_counter,:,:]=self.last_OD_measurements
        if self.verbose==1:
            print("vial:"+ ", ".join(map(lambda x:"  v%02d"%(x+1), self.vials)))
            print("OD:  "+ ", ".join(map(lambda x:"%1.3f"%x, self.last_OD_measurements[-1,:-1]))+'\n')

    def measure_OD(self):
        '''
        measure OD in all culture vials, add the measurement to the big stack and
        stores it in last_OD_measurement. Increments OD_measurement_counter by 1
        the IR LEDS are switched off at the end.
        '''
        t = self.experiment_time()
        self.last_OD_measurements[self.OD_measurement_counter, :] = 0
        self.morb.switch_light(True) # switch light on
        time.sleep(1.0*self.second)  # sleep for one second to allow for heating of LEDs

        index_vial_pairs = zip(range(len(self.vials)), self.vials)
        tmp_OD_measurements = np.zeros((self.n_reps, len(self.vials)))
        for rep in xrange(self.n_reps):
            if self.verbose>4:
                print "OD rep",rep,
            for vi,vial in index_vial_pairs[::(1-2*(rep%2))]:
                tmp_OD_measurements[rep, vi] = self.morb.measure_OD(vial, 1, 0, False)[0]
                if self.verbose>4:
                     print format(tmp_OD_measurements[rep, vi], '0.3f'),
            if self.verbose>4:
	            print
        self.last_OD_measurements[self.OD_measurement_counter, :-1] = np.median(tmp_OD_measurements, axis=0)
        if self.verbose>2:
            print "OD:", ' '.join(map(str,np.round(self.last_OD_measurements[self.OD_measurement_counter, :],3)))
        self.last_OD_measurements[self.OD_measurement_counter,-1]=t
        self.morb.switch_light(False)

    def estimate_growth_rates(self):
        '''
        estimate the growth rate and final OD in the last dilution period.
        This function fits a line to the log OD in the last cycle for each vial
        The growth rate is the slope of the linear regression, the final_OD
        is the value of the regression line at the final time point
        '''
        if self.OD_measurement_counter>2:
            final_time  = self.last_OD_measurements[self.OD_measurement_counter-1,-1]
            tmp_time_array = self.last_OD_measurements[:self.OD_measurement_counter,-1]-final_time
            for vi, vial in enumerate(self.vials):
                tmp_regress = stats.linregress(tmp_time_array,
                                               np.log(self.last_OD_measurements[:self.OD_measurement_counter,vi]))
                self.growth_rate_estimate[self.cycle_counter,vi] = tmp_regress[0]
                self.final_OD_estimate[self.cycle_counter,vi] = np.exp(tmp_regress[1])
                if self.verbose>3:
                    print "growth vial",vial, tmp_regress[0], tmp_regress[1]
                if tmp_regress[2]<0.5:
                    if self.verbose>3:
                        print "morbidostat_experiment: bad fit, regression:"
                        for q,x in zip(['slope', 'intercept', 'r-val','p-val'], np.round(tmp_regress[:4],4)):
                            print q,'\t',x
                        print
            self.growth_rate_estimate[self.cycle_counter,-1]=self.experiment_time()
            self.final_OD_estimate[self.cycle_counter,-1]=self.experiment_time()

        else:
            print("morbidostat_experiment: no data")

    def mix_concentration(self, vial, conc, fi):
        '''
        for now, we only want to run two pumps per vial at most. In this case, we
        can simply try all three pairs and choose the one with the most even distribution
        of volumes
        '''
        pairs = [[0,1],[0,2],[1,2]]
        bottle_conc, conc_order = self.get_vial_bottle_concentrations(vial, fi)
        fractions = np.array([(conc-bottle_conc[j])/(bottle_conc[i]-bottle_conc[j])
                      for (i,j) in pairs])
        best_choice = np.argmin(np.abs(fractions-0.5))
        best_pair = pairs[best_choice]
        mix = np.array([fractions[best_choice],1-fractions[best_choice]])
        if np.any(mix<0):
            if self.verbose>3:
                print("concentration can't be achieved, will do the best approximation")
            mix[mix<0.0] = 0.0
            mix[mix>1.0] = 1.0
        if self.verbose>4:
            print("desired concentration %f, will inject %f of conc %f and %f of conc %f"%(conc, mix[0], bottle_conc[best_pair[0]], mix[1], bottle_conc[best_pair[1]]))
        actual_concentration = (mix[0]*bottle_conc[best_pair[0]]+mix[1]*bottle_conc[best_pair[1]])
        fractions = {'pump%d'%(p+1): frac for p, frac in zip(best_pair,mix)}
        return fractions, actual_concentration


    def inject_concentration(self, vial, volume=1.0, conc=0.0, fi=0):
        fractions, actual_concentration = self.mix_concentration(vial, conc, fi)
        vi = self.vials.index(vial)
        if self.verbose>2:
            print("inject_concentration: vial %d"%(vial), fractions)
        for pump, frac in fractions.iteritems():
            if frac>0.05:
                if self.verbose>2:
                    print("injecting %f1.4ml from %s into vial %d"%(volume*frac, pump, vial))
                self.morb.inject_volume(pump, vial, volume*frac, conc=conc)

        self.added_volumes[vi]=np.sum(fractions.values())*volume
        return fractions
 


    def adjust_dilution_concentration(self, vial):

        vi, fi = self.get_vial_and_drug_index(vial)
        # calculate the expected OD increase per cycle and by how much the expectect OD is over the target OD
        final_OD = self.final_OD_estimate[self.cycle_counter,vi]
        delta_OD = (self.final_OD_estimate[self.cycle_counter,vi] -
                   self.final_OD_estimate[max(self.cycle_counter-self.delta_OD_time_scale,0),vi])/self.delta_OD_time_scale
        delta_OD_previous_cycle = (self.final_OD_estimate[self.cycle_counter-1,vi] -
                   self.final_OD_estimate[max(self.cycle_counter-self.delta_OD_time_scale-1,0),vi])/self.delta_OD_time_scale           
        conc_diff = self.vial_drug_concentration[self.cycle_counter,vi]-\
                    self.vial_drug_concentration[self.cycle_counter-self.conc_diff_time_scale,vi]
        # feedback is based on the current drug concentration in the vial
        vial_conc = np.copy(self.vial_drug_concentration[self.cycle_counter, vi])
        ignore_dilution_threshold = False # necessary in order that diluting high drug concentration works below dilution threshold

        # start of the feedback
        # calculating of drug concentration only above the dilution threshold
        # but also makes sure that dilution of high drug concentration works
        if final_OD<self.dilution_threshold:
            if delta_OD<0 and self.vial_drug_concentration[self.cycle_counter, vi]>self.prefactor_critical_conc*self.store_critical_conc[vi]:
                vial_conc = 0
                ignore_dilution_threshold = True
                

        # calculates drug concentration when bacteria are growing and OD is above dilution threshold
        
        elif delta_OD>0:
            print(conc_diff, self.mics[fi],self.max_rel_increase*(vial_conc-conc_diff))
            if conc_diff>max(self.mics[fi],self.max_rel_increase*(vial_conc-conc_diff)):
                pass
            else:
                # calculation of start concentration =
                previous_concentrations = self.vial_drug_concentration[self.cycle_counter,vi]
                if previous_concentrations<self.prefactor_start_conc_comparison*self.mics[fi]:
                    vial_conc += self.prefactor_conc_start*self.mics[fi]
                # caclulation of drug concentration accodring to the growth
                vial_conc *= 1.0 +self.prefactor_conc_multiplication*delta_OD/self.target_OD

                # when they are still growing and exceed the anticipation threshold 10% of the drug vial_concentratio gets added            
                if final_OD>self.target_OD*self.anticipation_threshold:
                    vial_conc += self.prefactor_conc_anticipation*self.mics[fi]

        # when they are dieing media gets added
        else:
            if delta_OD_previous_cycle>0 and delta_OD<0:
                self.store_critical_conc[vi] = self.vial_drug_concentration[self.cycle_counter,vi]
            if self.vial_drug_concentration[self.cycle_counter,vi]>self.store_critical_conc[vi]:
                vial_conc = 0
            else:
                pass 

        self.vial_to_inject_concentration(vial,vial_conc,vi)
        print('vial_conc',vial_conc)
        return ignore_dilution_threshold  

        
    def vial_to_inject_concentration(self,vial,vial_conc,vi):
        # current concentration in vial
        old_vial_conc = np.copy(self.vial_drug_concentration[self.cycle_counter, vi])
        # difference of calculated concentration in adjust_concentration and the current vial concentration
        conc_difference = vial_conc - old_vial_conc
        # calculating how much drug needs to be added in order to achieve the cacluated concentration
        self.dilution_concentration[self.cycle_counter+1,vi] = conc_difference*self.culture_volume/self.dilution_volume + old_vial_conc
        

    def update_vial_concentration(self, vial, dilution, conc):
        vi,fi = self.get_vial_and_drug_index(vial)
        self.vial_drug_concentration[self.cycle_counter+1,vi] = self.vial_drug_concentration[self.cycle_counter,vi]*dilution +((1.0-dilution)*conc)
        
        
    def continuous_feedback(self, vial):
        # enumerate all vials
        vi, fi = self.get_vial_and_drug_index(vial)
        ignore_dilution_threshold = self.adjust_dilution_concentration(vial)
        if self.final_OD_estimate[self.cycle_counter,vi]>self.dilution_threshold or ignore_dilution_threshold:
            conc = self.dilution_concentration[self.cycle_counter+1,vi]
            fractions = self.inject_concentration(vial, conc = conc,
                                    volume = self.dilution_volume, fi=fi)
            _, actual_concentration = self.mix_concentration(vial, conc, fi)
            self.update_vial_concentration(vial, self.dilution_factor, actual_concentration)
            self.decisions[self.cycle_counter,vi] = actual_concentration
        else:
            self.update_vial_concentration(vial, 1.0, np.zeros(len(self.drugs)))
            self.decisions[self.cycle_counter,vi] = -1.0
            


    def get_vial_bottle_concentrations(self, vial, fi):
        conc = [self.get_bottle_concentration(bottle)[fi]
                  for bottle in self.vial_props[vial]["bottles"]]
        return conc, np.argsort(conc)

    def get_bottle_concentration(self, bottle):
        return self.drug_concentrations[self.bottles.index(bottle)]

    def get_vial_and_drug_index(self, vial):
        vi = self.vials.index(vial)
        fi = self.drugs.index(self.vial_props[vial]['feedback_drug'])
        return (vi,fi)

    def lowest_concentration(self, vial,fi):
        '''
        return the pump that pumps the "recovery" medium, i.e. the one with least drug
        '''
        conc, arg_conc = self.get_vial_bottle_concentrations(vial,fi)
        pump = arg_conc[0]
        return ("pump%d"%(pump+1), pump, conc[pump])


    def which_drug(self, current_conc, prev_conc, bottle_conc, pumps, mic=1):
        medium_conc = bottle_conc[pumps[1]]
        high_conc = bottle_conc[pumps[-1]]
        if current_conc<self.AB_switch_conc*medium_conc:
            tmp_decision = ("pump%s"%(1+pumps[1]), pumps[1], medium_conc)
        else:
            tmp_decision = ("pump%s"%(1+pumps[2]), pumps[2], high_conc)

        return tmp_decision


    def standard_feedback(self, vial):
        '''
        threshold on excess growth rate
        '''
        vi, fi = self.get_vial_and_drug_index(vial)
        # calculate the average drug conc over last couple of cycles
        first, last = max(self.cycle_counter-self.feedback_time_scale, 0), (self.cycle_counter+1)
        prevAB = np.mean(self.vial_drug_concentration[first:last,vi, fi], axis=0)
        current_conc = self.vial_drug_concentration[self.cycle_counter, vi, fi]
        # calculate the expected OD increase per cycle
        finalOD = self.final_OD_estimate[self.cycle_counter,vi]
        deltaOD = (self.final_OD_estimate[self.cycle_counter,vi] - self.final_OD_estimate[max(self.cycle_counter-2,0),vi])/2
        growth_rate = self.growth_rate_estimate[self.cycle_counter,vi]
        expected_growth = (growth_rate-self.target_growth_rate)*self.cycle_dt*finalOD
        # get the bottle concentrations of the relevant drug
        conc, pumps = self.get_vial_bottle_concentrations(vial, fi)
        inhibit_decision = self.which_drug(current_conc, prevAB, conc, pumps, mic=1)
        dilute_decision = self.lowest_concentration(vial,fi)
        # calculate the amount by which OD exceeds the target
        excess_OD = (finalOD-self.target_OD)
        # if neither OD nor growth are above thresholds, dilute with happy fluid

        if finalOD<self.dilution_threshold:  # below the low threshold: let them grow, do nothing
            tmp_decision = do_nothing
        elif finalOD<self.target_OD*self.anticipation_threshold:  # intermediate OD: let them grow, but dilute with medium
            tmp_decision = dilute_decision
        elif finalOD<self.target_OD: # approaching the target OD: increase antibiotics if they grow too fast
            if deltaOD<self.target_OD*self.max_growth_fraction:
                tmp_decision = dilute_decision
            else:
                tmp_decision = inhibit_decision
        elif finalOD<self.saturation_threshold: # beyond target OD: give them antibiotics if they still grow
            if deltaOD<0:
                tmp_decision = dilute_decision
            else:
                tmp_decision = inhibit_decision
        else:  # above saturation: deltaOD can't be reliably measured. give them antibiotics
            tmp_decision = inhibit_decision

        if self.verbose>3:
            print("dilute vial %d with %s. current: %1.3f, previous: %1.3f"%(vial, tmp_decision[0], current_conc, dilute_to_OD))

        return tmp_decision

    def feedback_on_OD(self, vial):
        '''
        This function is called every dilute_dt
        it interogates the OD measurements and decides whether to
        (i) do nothing
        (ii) dilute with medium
        (iii) dilute with drug A
        (iv) dilute with drug B
        the dilution counter is incremented at the end
        '''
        # enumerate all vials
        vi, fi = self.get_vial_and_drug_index(vial)
        # check manual override of decision
        if self.override:
            print 'Specify decision:\n(1) do nothing\n(2) dilute with medium\n(3) dilute with drug A\n(4) dilute with drug B'
            s = input('Input: ')
            if s==1:
                tmp_decision = do_nothing
            elif s==2:
                tmp_decision = ("pump1",0, 0)
            elif s==3:
                tmp_decision = ("pump2",1, 0)
            elif s==4:
                tmp_decision = ("pump3",2, 0)
        # check dilution threshold
        elif self.final_OD_estimate[self.cycle_counter,vi]<self.dilution_threshold:
            tmp_decision = do_nothing
            vol_mod=0
        # start feedback
        else:
            tmp_decision = self.standard_feedback(vial)

        # check decision
        if tmp_decision[1]>=0:
            pump = tmp_decision[0]
            pump_ii = tmp_decision[1]
            bottle = self.vial_props[vial]["bottles"][pump_ii]
            bottle_ii = self.bottles.index(bottle)
            # save volumes
            self.added_volumes[vi]=self.dilution_volume
            # dilute according to decision
            self.morb.inject_volume(pump, vial, self.dilution_volume,
                conc=self.drug_concentrations[bottle_ii][fi])
            # copy the current drug concentration and dilute it
            self.update_vial_concentration(vial, self.dilution_factor, self.drug_concentrations[bottle_ii])
            # save decision
            self.decisions[self.cycle_counter,vi] = tmp_decision[2]
        # do nothing
        else:
            # save current drug concentration
            self.update_vial_concentration(vial, 1.0, np.zeros(len(self.drugs)))
            self.decisions[self.cycle_counter,vi] = -1.0


    def dilute_to_OD(self, vial):
        '''
        does nothing if OD is below target OD, dilutes as necessary (within limits)
        if OD is high.
        '''
        vi, fi = self.get_vial_and_drug_index(vial)
        # get the bottle concentrations of the relevant drug
        dilute_decision = self.lowest_concentration(vial,fi)
        if self.final_OD_estimate[self.cycle_counter,vi]<self.target_OD:
            tmp_decision = do_nothing
            volume_to_add=0
        else:
            volume_to_add = min(10.0,(self.final_OD_estimate[self.cycle_counter,vi]-
                                   self.target_OD)*self.culture_volume/self.target_OD)
            self.added_volumes[vi]=volume_to_add
            self.morb.inject_volume(dilute_decision[0], vial, volume_to_add, conc=0.0)
        if self.verbose>3:
            print("dilute vial %d with %1.4fml, previous OD: %1.4f"%(vial, volume_to_add, self.final_OD_estimate[self.cycle_counter,vi]))
        self.decisions[self.cycle_counter,vi] = volume_to_add
