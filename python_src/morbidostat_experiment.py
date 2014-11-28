from __future__ import division
import arduino_interface as morb
#import morbidostat_simulator as morb
import numpy as np
from scipy.stats import linregress
import time,copy,threading,os

from scipy import stats
#plt.ion()
debug = True

do_nothing = ('as is',1)
dilute_w_medium = ('medium',2)
dilute_w_drugA = ('drugA', 3)
dilute_w_drugB = ('drugB', 4)

MORBIDOSTAT_EXPERIMENT = 'morbidostat'
GROWTH_RATE_EXPERIMENT = 'growth_rate'
FIXED_OD_EXPERIMENT = 'fixed_OD'

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
        print("Collected "+str(len(ODs))+" OD voltage pairs, calculating voltage -> OD conversion")
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

def calibrate_pumps(pump_type, vials = None, dt = 10):
    '''
    Routine that runs all pumps sequentially assuming the outlet is sitting on 
    on a balance. after running a pump for dt seconds, the user is prompted for the weight
    until all 15 pumps have been run
    '''
    if vials is None:
        vials = range(15)
    calibration_morb = morb.morbidostat()
    print("Upon pressing enter, each pump will be run for "+str(dt)+" seconds.")
    print("Before each pump, you will be prompted for the weight of the current set-up.")
    s = raw_input("press enter to start, q to stop: ")
    if len(s)>0:
        print("Aborting calibration")
        return

    # loop over vials, prompt for weight
    weight  = np.zeros(len(vials)+1)   
    for vi,vial in enumerate(vials):
        no_weight = True
        while no_weight:
            s = raw_input('current weight: ')
            try:
                weight[vi] =float(s)
                no_weight = False
            except:
                print("invalid weight")
        calibration_morb.run_pump(pump_type, vial,run_time=dt)

    # get final weight
    no_weight = True
    while no_weight:
        s = raw_input('final weight: ')
        try:
            weight[-1] =float(s)
            no_weight = False
        except:
            print("invalid weight")

    # calculate pump_rate and save to file
    pump_rate = np.diff(weight)/dt
    np.savetxt(morb.pump_calibration_file_base+'_'+pump_type+'.dat', pump_rate)

def calibrate_pumps_parallel(pump_type, vials = None, dt = 10):
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
    weight  = np.zeros(len(vials))   
    for vi,vial in enumerate(vials):
        no_weight = True
        while no_weight:
            s = raw_input('weight of vial '+str(vial+1)+': ')
            try:
                weight[vi] =float(s)
                no_weight = False
            except:
                print("invalid weight")


    # calculate pump_rate and save to file
    pump_rate = weight/dt
    np.savetxt(morb.pump_calibration_file_base+'_'+pump_type+'.dat', pump_rate)
    
def wash_tubing(pumps=None, bleach_runtime=None, vials=None):
    '''
    Washing routine to sterilize all tubing. Valid arguments are pumps as an array and 
    bleach_time in seconds. Without arguments standard is used. 
    - pumps: medium, drugA and drugB
    - bleach_runtime: 300 (= 5 min)
    '''
    
    # standard
    if pumps is None:
        pumps = ['drugB', 'medium', 'drugA']
    elif bleach_runtime is None:
        bleach_runtime = 300

    if vials is None:
        vials=range(15)

    wash_time = 300
    wait_time = 300
    wash_morb = morbidostat(vials=vials)
    print("Starting sterilization of tubing...")
    
    # washing cycle
    for pump in pumps:
        # bleach
        print("Connect bleach reservoir to " +str(pump) 
              + " pumps and spray ethanol on all Luer connectors.")
        s = raw_input("Press enter to run pumps for " + str(bleach_runtime) + " seconds.")
        wash_morb.run_all_pumps(pump, bleach_runtime)
        print("Wait until pumping is finished...")
        time.sleep(bleach_runtime)
        # wait
        print("Wait for 5 min.")
        time.sleep(wait_time)
        # sterile water
        print("Swap bleach reservoir with steril water reservoir: " +str(pump))
        s = raw_input("Press enter to run pumps for 5 min.")
        wash_morb.run_all_pumps(pump, wash_time)
        wash_morb.morb.run_waste_pump(bleach_runtime + wash_time)
        #time.sleep(wash_time)

    print("Wait for waste pump to finish.")
          
    for pump in pumps:
        # ethanol
        print("Swap steril water reservoir with ethanol reservoir: " +str(pump))
        s = raw_input("Press enter to run pumps for 5 min.")
        wash_morb.run_all_pumps(pump, wash_time)
        wash_morb.morb.run_waste_pump(wash_time)

    print("Wait for pumps to finish (15 min incubation of EtOH).")        
    # wait
    #print("Wait for 15 min.")
    #time.sleep(wait_time*3)
     
    for pumps in pumps:
        # sterile water
        print("Swap ethanol reservoir with steril water reservoir: " +str(pump))
        s = raw_input("Press enter to run pumps for 5 min.")
        wash_morb.run_all_pumps(pump, wash_time)
        wash_morb.morb.run_waste_pump(wash_time)
    
    time.sleep(wash_time)    
    print("Washing cycle finished.")

def pump_solutions(pumps=None, vials=None):
    ''' 
    Function to flush tubing with sterile solutions
    standard: all vials, all pumps
    '''    
    if pumps is None:
        pumps = ['drugB', 'medium', 'drugA']
    elif vials is None:
        vials=range(15)
    
    run_time = 100
    wash_morb = morbidostat(vials=vials)

    print("Connect solutions to pumps.")
    s = raw_input("Press enter to run pumps.")

    for pump in pumps:
        wash_morb.run_all_pumps(pump, run_time)
        wash_morb.morb.run_waste_pump(run_time)
        time.sleep(run_time)

    print("Morbidostat is ready to use.")    
    
class morbidostat(object):
    '''
    Running a morbidostat experiment. 
    This class communicates with the morbidostat device through a separate
    interface class and records the optical density of an array of culture vials.
    in response to these OD measurements, the class triggers the addition of 
    either medium or drug solution at different concentrations. 
    '''
    
    def __init__(self, vials = range(15), experiment_duration = 2*60*60, 
                 target_OD = 0.1, diluation_factor = 0.9, bug = '', drugA ='',drugB ='',
                 drugA_concentration = 0.3, drugB_concentration = 2.0, OD_dt = 30, cycle_dt = 600):
        # the default experiment is a morbidostat measurement
        self.experiment_type = MORBIDOSTAT_EXPERIMENT

        # all times in seconds, define parameter second to speed up for testing
        self.second = 1.0

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
        self.dilution_factor = 0.9
        self.dilution_threshold = 0.03
        self.extra_suction  = 2 # extra volume that is being sucked out of the vials [ml]
        self.drugA = drugA
        self.drugB = drugB
        self.experiment_name = ''
        self.bug = bug
        self.drugA_concentration = drugA_concentration
        self.drugB_concentration = drugB_concentration
        # data acqusition specifics
        self.n_reps=8
        self.buffer_time = 10
        # counters
        self.OD_measurement_counter = 0
        self.cycle_counter = 0
        #feedback parameters
        self.max_growth_fraction = 0.2  # increase antibiotics with 20% OD increase per cycle
        self.max_OD_deviation = 0.2     # increase antibiotic if 20% above target OD
        self.AB_switch_conc = 0.3       # use high concentration if culture conc is 30% of drug A
        #self.rescue_threshold = -0.1    # dilute culture with medium only if growth rate is 10\% below target.
        # diagnostic variables
        self.stopped = True
        self.interrupted = False
        self.running = False
        self.calculate_derived_values()
        self.override = False


    def calculate_derived_values(self):
        '''
        values calculated after other parameters are set. 
        '''
        self.n_cycles = self.experiment_duration//self.cycle_dt
        self.dilution_volume = self.culture_volume*(1.0/np.max((0.5, self.dilution_factor))-1.0)
        self.target_growth_rate = -np.log(self.dilution_factor)/self.cycle_dt
        self.pump_time = np.max([self.morb.volume_to_time('medium',vi,self.dilution_volume) for vi in self.vials])
        self.ODs_per_cycle = int(self.cycle_dt-self.morb.mixing_time-self.pump_time - self.buffer_time)//self.OD_dt
        self.n_vials = len(self.vials)


    def set_up(self):
        '''
        this allocate memory for measurements and culture decisions
        note that this only works for fixed experiment length. 
        the duration of the experiment cannot be changed after this function is called
        '''
        self.calculate_derived_values()

        self.OD = np.zeros((self.n_cycles, self.ODs_per_cycle, self.n_vials+1), dtype = float)
        self.temperatures = np.zeros((self.n_cycles, 3))
        self.decisions = np.zeros((self.n_cycles, self.n_vials+1), dtype = float)
        self.vial_drug_concentration = np.zeros((self.n_cycles+1, self.n_vials+1), dtype = float)
        self.vial_drug_concentration[:,-1]=np.arange(self.n_cycles+1)*self.cycle_dt

        self.historical_drug_A_concentration = []
        self.historical_drug_B_concentration = []
        self.last_OD_measurements = np.zeros((self.ODs_per_cycle,self.n_vials+1))
        self.growth_rate_estimate = np.zeros((self.n_cycles,self.n_vials+1))
        self.final_OD_estimate = np.zeros((self.n_cycles,self.n_vials+1))

        # threads handling repeated measurements
        self.cycle_thread = None
        self.OD_thread = None
        
        # file names
        tmp_time = time.localtime()
        self.base_name = morb.morb_path+'data/'+"".join([format(v,'02d') for v in
                                             [tmp_time.tm_year, tmp_time.tm_mon, tmp_time.tm_mday]])\
                                  + '_'.join(['',self.experiment_name,self.bug, self.drugA,self.drugB, self.experiment_type])+'/'
        if os.path.exists(self.base_name):
            print self.base_name+"directory already exists"
        else:
            os.mkdir(self.base_name)
        if not os.path.exists(self.base_name+'/OD'):
            os.mkdir(self.base_name+'OD/')
            
        self.OD_fname = self.base_name+'OD/OD'
        self.decisions_fname = self.base_name+'decisions.txt'
        self.drug_conc_fname = self.base_name+'vials_drug_concentrations.txt'
        self.temperature_fname = self.base_name+'temperature.txt'
        self.cycle_OD_fname = self.base_name+'cycle_OD_estimate.txt'
        self.growth_rate_fname = self.base_name+'growth_rate_estimates.txt'
        self.last_cycle_fname = self.base_name+'OD/'+'current_cycle.dat'

    def add_cycles_to_data_arrays(self, cycles_to_add):
        '''
        provides the possibility to extend a running experiment by providing more space
        in the arrays used to store the data. 
        '''
        self.OD = np.concatenate((self.OD, np.zeros((cycles_to_add, self.ODs_per_cycle, self.n_vials+1), dtype = float)))
        self.temperatures = np.concatenate((self.temperatures, np.zeros((cycles_to_add, 3), dtype = float)))
        self.decisions = np.concatenate((self.decisions, np.zeros((cycles_to_add, self.n_vials+1), dtype = float)))
        self.vial_drug_concentration = np.concatenate((self.vial_drug_concentration, np.zeros((cycles_to_add+1, self.n_vials+1), dtype = float)))
        self.vial_drug_concentration[-cycles_to_add:,-1]=np.arange(self.vial_drug_concentration.shape[0]-cycles_to_add, 
                                                     self.vial_drug_concentration.shape[0])*self.cycle_dt

        self.growth_rate_estimate = np.concatenate((self.growth_rate_estimate, np.zeros((cycles_to_add,self.n_vials+1))))
        self.final_OD_estimate = np.concatenate((self.final_OD_estimate, np.zeros((cycles_to_add,self.n_vials+1))))
        

    def experiment_time(self):
        return (time.time()-self.experiment_start)/self.second

    def write_parameters_file(self, ):
        with open(self.base_name+'/parameters.dat', 'w') as params_file:
            params_file.write('vials\t'+'\t'.join(map(str,self.vials))+'\n')
            params_file.write('Experiment:\t'+self.experiment_name+' type: '+self.experiment_type+'\n')
            params_file.write('Strain:\t'+self.bug+'\n')
            params_file.write('Drugs:\t'+self.drugA+'\t'+self.drugB+'\n')
            params_file.write('cycle duration:\t'+str(self.cycle_dt)+'\n')
            params_file.write('measurments/cycle:\t'+str(self.ODs_per_cycle)+'\n')
            params_file.write('experiment start:\t'+str(self.experiment_start))

    def change_drug_concentrations(self, Aconc, Bconc):
        '''
        change drug concentrations during run time
        '''
        self.historical_drug_A_concentration.append((self.experiment_time(), self.drugA_concentration))
        self.drugA_concentration = Aconc
        self.historical_drug_B_concentration.append((self.experiment_time(), self.drugB_concentration))
        self.drugB_concentration = Bconc


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
        np.savetxt(self.drug_conc_fname, self.vial_drug_concentration,fmt='%2.6f')
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

    def run_all_pumps(self,pump_type, run_time):
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
            if debug:
                print "#####################\n# Cycle",ci,"\n##################"
            tmp_cycle_start = time.time()
            self.morbidostat_cycle()
            self.save_data()
            self.cycle_counter+=1
            remaining_time = self.cycle_dt-(time.time()-tmp_cycle_start)/self.second
            if remaining_time>0:
                time.sleep(remaining_time*self.second)
                if debug:
                    print "run_morbidostat: remaining time", remaining_time
            else:
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
        if  self.experiment_type==MORBIDOSTAT_EXPERIMENT:
            self.feedback_on_OD()
        elif self.experiment_type ==FIXED_OD_EXPERIMENT:
            self.dilute_to_OD()
        elif self.experiment_type==GROWTH_RATE_EXPERIMENT:
            pass
        else:
            print "unknown experiment type:", self.experiment_type
        self.morb.wait_until_mixed()
        # remove the max of the added volumes plus some safety margin. 
        # this will suck air in some vials. 
        run_time = self.morb.remove_waste(max(self.added_volumes) + self.extra_suction)
        self.morb.pump_off_threads[('waste pump',0)].join()
        self.temperatures[self.cycle_counter,-1] = t
        self.temperatures[self.cycle_counter,:2] = self.morb.temperatures


    def measure_OD_for_cycle(self):
        '''
        acquires all measurents for a given OD counter is incremented in parent
        '''
        self.last_OD_measurements[:] = 0
        for oi in xrange(self.ODs_per_cycle):
            if debug:
                print "OD measurement:",self.OD_measurement_counter
            tmp_OD_measurement_start = time.time()
            self.measure_OD()
            self.OD_measurement_counter+=1
            self.save_within_cycle_data()
            remaining_time = self.OD_dt - (time.time()-tmp_OD_measurement_start)/self.second 
            if remaining_time>0:
                time.sleep(remaining_time*self.second)
            else:
                print("measure_OD_for_cycle: remaining time is negative"
                      +str(remaining_time))
        self.OD[self.cycle_counter,:,:]=self.last_OD_measurements

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
        for rep in xrange(self.n_reps):
            if debug:
                print "OD rep",rep,
            for vi,vial in index_vial_pairs[::(1-2*(rep%2))]:
                self.last_OD_measurements[self.OD_measurement_counter, vi] += self.morb.measure_OD(vial, 1, 0, False)[0]
                if debug:
                     print format(np.round(self.last_OD_measurements[self.OD_measurement_counter, vi],4)/(rep+1.0), '0.3f'),
            
            if debug:
	            print 
        self.last_OD_measurements[self.OD_measurement_counter, :] /= self.n_reps
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
                if debug:
                    print "growth vial",vial, tmp_regress[0], tmp_regress[1]
                if tmp_regress[2]<0.5:
                    print "morbidostat_experiment: bad fit, regression:"
                    for q,x in zip(['slope', 'intercept', 'r-val','p-val'], np.round(tmp_regress[:4],4)): 
                        print q,'\t',x
                    print
            self.growth_rate_estimate[self.cycle_counter,-1]=self.experiment_time()
            self.final_OD_estimate[self.cycle_counter,-1]=self.experiment_time()
            
        else:
            print("morbidostat_experiment: no data")


    def standard_feedback(self, vial):
        '''
        threshold on excess growth rate
        '''
        vi = self.vials.index(vial)
        # calculate the expected OD increase per cycle
        expected_growth = (self.growth_rate_estimate[self.cycle_counter,vi]-self.target_growth_rate)*self.cycle_dt\
                            *self.final_OD_estimate[self.cycle_counter,vi]
        # calculate the amount by which OD exceeds the target
        excess_OD = (self.final_OD_estimate[self.cycle_counter,vi]-self.target_OD)
        # if neither OD nor growth are above thresholds, dilute with happy fluid

        print "vial",vial
        print expected_growth, self.target_OD*self.max_growth_fraction
        print excess_OD, self.max_OD_deviation*self.target_OD

        if expected_growth<self.target_OD*self.max_growth_fraction or excess_OD<self.max_OD_deviation*self.target_OD:
            # if drug conc in vial is low or expected growth too negative, dilute with medium 
            tmp_decision = dilute_w_medium
        else: # if feedback with drugs is required, dilute with one or the other drug depending on preex conc
            if self.cycle_counter==0 or self.decisions[self.cycle_counter-1,vi]<=2:
                if self.vial_drug_concentration[self.cycle_counter, vi]<self.AB_switch_conc*self.drugA_concentration:
                    tmp_decision = dilute_w_drugA
                else:
                    tmp_decision = dilute_w_drugB
            else:
                tmp_decision = dilute_w_medium
        return tmp_decision

    def feedback_on_OD(self):
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
        for vi, vial in enumerate(self.vials):
            # check manual override of decision
            if self.override:
                print 'Specify decision:\n(1) do nothing\n(2) dilute with medium\n(3) dilute with drug A\n(4) dilute with drug B'
                s = input('Input: ')
                if s==1:
                    tmp_decision = do_nothing
                elif s==2:
                    tmp_decision = dilute_w_medium
                elif s==3:
                    tmp_decision = dilute_w_drugA 
                elif s==4:
                    tmp_decision = dilute_w_drugB   
            # check dilution threshold            
            elif self.final_OD_estimate[self.cycle_counter,vi]<self.dilution_threshold:
                tmp_decision = do_nothing
                vol_mod=0
            # start feedback
            else:
                tmp_decision = self.standard_feedback(vial)

            # check decision
            if tmp_decision[1]>1:
                # save volumes
                self.added_volumes[vi]=self.dilution_volume
                # dilute according to decision
                self.morb.inject_volume(tmp_decision[0], vial, self.dilution_volume)
                # save current drug concentration
                self.vial_drug_concentration[self.cycle_counter+1,vi] = \
                    self.vial_drug_concentration[self.cycle_counter,vi]*self.dilution_factor
                # save drugA concentration
                if tmp_decision==dilute_w_drugA:
                    self.vial_drug_concentration[self.cycle_counter+1,vi]+= \
                        self.drugA_concentration*(1-self.dilution_factor)
                # save drugB concentration
                elif tmp_decision==dilute_w_drugB:
                    self.vial_drug_concentration[self.cycle_counter+1,vi]+=\
                        self.drugB_concentration*(1-self.dilution_factor)
                # save decision
                self.decisions[self.cycle_counter,vi] = tmp_decision[1]
            # do nothing
            else:
                # save current drug concentration
                self.vial_drug_concentration[self.cycle_counter+1,vi] = \
                    self.vial_drug_concentration[self.cycle_counter,vi]
            # save time of dilution
            self.vial_drug_concentration[self.cycle_counter+1,-1]=self.experiment_time()
                
        print 'Cycle:',self.cycle_counter, self.experiment_time()
        print 'Growth rate (rel to target):',
        for x in self.growth_rate_estimate[self.cycle_counter,:-1]: print '\t',np.round(x/self.target_growth_rate,2),
        print '\nOD (rel to target):\t',
        for x in self.final_OD_estimate[self.cycle_counter,:-1]: print '\t',np.round(x/self.target_OD,2),
        print '\nDecision:\t\t',
        for x in self.decisions[self.cycle_counter,:-1]: print '\t',x,
        print '\n'

    def dilute_to_OD(self):
        '''
        does nothing if OD is below target OD, dilutes as necessary (within limits) 
        if OD is high. 
        '''
        for vi, vial in enumerate(self.vials):
            if self.final_OD_estimate[self.cycle_counter,vi]<self.target_OD:
                tmp_decision = do_nothing
                volume_to_add=0
            else:
                volume_to_add = min(5,(self.final_OD_estimate[self.cycle_counter,vi]-
                                       self.target_OD)*self.culture_volume/self.target_OD)
                self.added_volumes[vi]=volume_to_add
                self.morb.inject_volume(dilute_w_medium[0], vial, volume_to_add)
            print "dilute vial ",vial,'with', np.round(volume_to_add,3), \
                'previous OD', np.round(self.final_OD_estimate[self.cycle_counter,vi],3)
            self.decisions[self.cycle_counter,vi] = volume_to_add


