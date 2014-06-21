from __future__ import division
#import arduino_interface as morb
import morbidostat_simulator as morb
import numpy as np
from scipy.stats import linregress
import time,copy,threading,os
import matplotlib.pyplot as plt
from matplotlib import animation

from scipy import stats
#plt.ion()
debug = False

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
    if vials is None:
        vials = range(15)
    calibration_morb = morb.morbidostat()
    no_valid_standard=True
    ODs = []
    voltages = []
    while True:
        while no_valid_standard:
            s = raw_input("Enter OD of standard [q to quit]: ")
            if s==q:
                print("Aborting calibration")
                return
            try:
                cur_OD = float(s)
                no_valid_standard=False
            except:
                print("invalid entry")
        
        ODs.append(cur_OD)
        voltages.append(np.zeros(len(vials)))
        for vi,vial in enumerate(vials):
            OKstr = raw_input("Place OD standard in receptible "+str(vial+1)+", press enter when done")
            voltages[-1][vi] = calibration_morb.measure_voltage(calibration_morb.vial_to_pin(vial), 
                                                                switch_light_off=True)

    if len(ODs)>1:
        print("Collected "+str(len(ODs))+" OD voltage pairs, calculating voltage -> OD conversion")
        ODs = np.array(ODs)
        voltages = np.array(voltages).T
        fit_parameters = np.zeros((len(vials), 2))
        for vi,vial in enumerate(vials):
            slope, intercept, r,p,stderr = linregress(ODs, voltages[vi,:])
            fit_parameters[vi,:] = [1.0/slope,  -intercept/slope]
        np.savetxt(morb.OD_calibration_file_name, fit_parameters)
    else:
        print("need measurements for at least two OD standards") 

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
        self.second = 0.01

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
        self.ODs_per_cycle = (self.cycle_dt-self.morb.mixing_time)//self.OD_dt
        self.n_cycles = self.experiment_duration//self.cycle_dt

        if (np.max(vials)<15):
            self.vials = copy.copy(vials)
            self.n_vials = len(vials)
        else:
            print("Morbidostat set-up: all vial numbers must be between 0 and 14")
            self.vials = []

        self.target_OD = target_OD
        self.culture_volume = 10
        self.dilution_factor = 0.9
        self.dilution_volume = self.culture_volume*(1.0-self.dilution_factor)
        self.dilution_threshold = 0.03
        self.target_growth_rate = -np.log(self.dilution_factor)/self.cycle_dt
        self.drugA = drugA
        self.drugB = drugB
        self.experiment_name = ''
        self.bug = bug
        self.drugA_concentration = drugA_concentration
        self.drugB_concentration = drugB_concentration
        # data acqusition specifics
        self.n_reps=1
        self.rep_dt = 0.001
        # counters
        self.OD_measurement_counter = 0
        self.cycle_counter = 0

        # diagnostic variables
        self.display_OD = True
        self.stopped=True
        self.interrupted =False
        self.running = False
        self.cycle_counter=0

    def set_up(self):
        # allocate memory for measurements and culture decisions
        self.ODs_per_cycle = (self.cycle_dt-self.morb.mixing_time)//self.OD_dt
        self.n_cycles = self.experiment_duration//self.cycle_dt

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
        self.base_name = '../data/'+"".join(map(str, [tmp_time.tm_year, 
                                           tmp_time.tm_mon, 
                                           tmp_time.tm_mday])
                                 ) + '_'.join(['',self.experiment_name,self.bug, self.drugA,self.drugB, self.experiment_type])+'/'
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

    def experiment_time(self):
        return (time.time()-self.experiment_start)/self.second

    def save_data(self):
        '''
        save the entire arrays to file. note that this will save a LOT of zeroes
        at the beginning of the experiment and generally tends to overwrite files 
        often with the same data. Only OD is saved cycle wise
        '''
        np.savetxt(self.OD_fname+'_cycle_'+str(self.cycle_counter)+'.dat', self.OD[self.cycle_counter], fmt='%2.3f')
        np.savetxt(self.decisions_fname, self.decisions, fmt='%2.3f')
        np.savetxt(self.drug_conc_fname, self.vial_drug_concentration,fmt='%2.6f')
        np.savetxt(self.temperature_fname, self.temperatures, fmt='%2.1f')
        np.savetxt(self.growth_rate_fname, self.growth_rate_estimate,fmt='%2.6f')
        np.savetxt(self.cycle_OD_fname, self.final_OD_estimate,fmt='%2.3f')


    def start_experiment(self):
        '''
        start the thread measuring and feedbacking the cultures
        start the OD animation if self.display_OD is True
        '''
        if self.running==False:
            self.set_up()
            self.cycle_thread = threading.Thread(target = self.run_morbidostat)
            if self.display_OD:
                self.figure_thread = threading.Thread(target = self.cycle_figure)
                n_cols = 3
                n_rows = int(np.ceil(1.0*self.n_vials/n_cols))
                plt.ion()
                self.data_figure = plt.figure(figsize = (n_cols*3, min(12,n_rows*3)))
                self.init_data_plot()
                plt.show()
#                self.OD_animation = animation.FuncAnimation(self.data_figure, self.update_plot, 
#                                                            init_func=self.init_data_plot,
#                                                            interval = self.cycle_dt*self.second*1000)
                self.figure_thread.start()
                plt.draw()

            self.experiment_start = time.time()
            self.cycle_thread.start()
            self.running = True
            self.stopped = False
            self.interrupted=False
        else:
            print "experiment already running"

    def cycle_figure(self, ):
        while not self.stopped:
            self.update_plot(0)
            time.sleep(self.cycle_dt*self.second*0.5)
    

    def stop_experiment(self):
        '''
        set the stop signal and wait for threads to finish
        '''
        self.stopped = True
        if self.running and self.cycle_counter<self.n_cycles:
            print "Stopping the cycle thread, waiting for cycle to finish"
            self.cycle_thread.join()

        if self.display_OD:
            try:
                self.figure_thread.join()
                #self.OD_animation.repeat=False
                #self.OD_animation._stop()
                #plt.close(self.data_figure)
            except:
                pass
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
                if self.display_OD:
                    pass
                    #self.OD_animation.repeat=False
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
            if self.display_OD:
                pass
                #self.OD_animation.repeat=True
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
            remaining_time = self.cycle_dt-(time.time()-tmp_cycle_start)/self.second
            if remaining_time>0:
                time.sleep(remaining_time*self.second)
                if debug:
                    print "run_morbidostat: remaining time", remaining_time
            else:
                print("run_morbidostat: remaining time is negative"+str(remaining_time))
            self.cycle_counter+=1
            if self.stopped or self.interrupted:
                break
        if self.cycle_counter==self.n_cycles:
            self.stop_experiment()


    def morbidostat_cycle(self):
        t = self.experiment_time()
        self.morb.measure_temperature()
        self.OD_measurement_counter=0
        self.OD_thread = threading.Thread(target = self.measure_OD_for_cycle)
        # start thread and wait for it to finish
        self.OD_thread.start()
        self.OD_thread.join(timeout=self.OD_dt*(self.ODs_per_cycle+5)*self.second)
        if self.OD_thread.is_alive():
            print("morbidostat_cycle: OD measurement timed out")

        self.estimate_growth_rates()
        if  self.experiment_type==MORBIDOSTAT_EXPERIMENT:
            self.feedback_on_OD()
        elif self.experiment_type ==FIXED_OD_EXPERIMENT:
            self.dilute_to_OD()
        elif self.experiment_type==GROWTH_RATE_EXPERIMENT:
            pass
        else:
            print "unknown experiment type:", self.experiment_type
        self.morb.wait_until_mixed()
        
        self.temperatures[self.cycle_counter,-1] = t
        self.temperatures[self.cycle_counter,:2] = self.morb.temperatures


    def measure_OD_for_cycle(self):
        for oi in xrange(self.ODs_per_cycle):
            if debug:
                print "OD measurement:",self.OD_measurement_counter
            tmp_OD_measurement_start = time.time()
            self.measure_OD()
            remaining_time = self.OD_dt - (time.time()-tmp_OD_measurement_start)/self.second 
            if remaining_time>0:
                time.sleep(remaining_time*self.second)
            else:
                print("measure_OD_for_cycle: remaining time is negative"+str(remaining_time))
            self.OD_measurement_counter+=1
        self.OD[self.cycle_counter,:,:]=self.last_OD_measurements

    def measure_OD(self):
        '''
        measure OD in all culture vials, add the measurement to the big stack and
        stores it in last_OD_measurement. Increments OD_measurement_counter by 1
        the IR LEDS are switched off at the end.
        '''
        t = self.experiment_time()
        if debug:
            print "OD",
        self.last_OD_measurements[self.OD_measurement_counter, :] = 0
        for rep in xrange(self.n_reps):
            for vi,vial in enumerate(self.vials):
                self.last_OD_measurements[self.OD_measurement_counter, vi] += self.morb.measure_OD(vial, 1, 0, False)
                if debug:
                     print np.round(self.last_OD_measurements[self.OD_measurement_counter, vi],4),
            
        self.last_OD_measurements[self.OD_measurement_counter, :] /= self.n_reps
        if debug:
            print 
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
            if self.final_OD_estimate[self.cycle_counter,vi]<self.dilution_threshold:
                tmp_decision = do_nothing
                vol_mod=0
            else:
                if (self.target_growth_rate-self.growth_rate_estimate[self.cycle_counter,vi])*self.OD_dt \
                        + (self.target_OD-self.final_OD_estimate[self.cycle_counter,vi])/3>0:
                    if self.vial_drug_concentration[self.cycle_counter,vi]<self.drugA_concentration:
                        tmp_decision, vol_mod = dilute_w_medium, max(0,
                              min(2,1-(self.target_OD-self.final_OD_estimate[self.cycle_counter,vi])/self.target_OD))
                    else:
                        tmp_decision, vol_mod = dilute_w_drugA,max(0, 
                              min(2,1-(self.target_OD-self.final_OD_estimate[self.cycle_counter,vi])/self.target_OD))
                else:
                    if self.vial_drug_concentration[self.cycle_counter, vi]<0.5*self.drugA_concentration:
                        tmp_decision, vol_mod = dilute_w_drugA, max(0,
                              min(2, 1+(self.target_OD-self.final_OD_estimate[self.cycle_counter,vi])/self.target_OD))
                    else:
                        tmp_decision, vol_mod = dilute_w_drugB, max(0,
                              min(2,1+(self.target_OD-self.final_OD_estimate[self.cycle_counter,vi])/self.target_OD))

            
            if tmp_decision[1]>0:
                self.morb.inject_volume(tmp_decision[0], vial, self.dilution_volume)
                self.vial_drug_concentration[self.cycle_counter+1,vi] = \
                    self.vial_drug_concentration[self.cycle_counter,vi]*self.dilution_factor
                if tmp_decision==dilute_w_drugA:
                    self.vial_drug_concentration[self.cycle_counter+1,vi]+= \
                        self.drugA_concentration*(1-self.dilution_factor)
                elif tmp_decision==dilute_w_drugB:
                    self.vial_drug_concentration[self.cycle_counter+1,vi]+=\
                        self.drugB_concentration*(1-self.dilution_factor)

                self.decisions[self.cycle_counter,vi] = tmp_decision[1]
            else:
                self.vial_drug_concentration[self.cycle_counter+1,vi] = \
                    self.vial_drug_concentration[self.cycle_counter,vi]
            self.vial_drug_concentration[self.cycle_counter,-1]=self.experiment_time()

                
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
        does nothing if OD is below target OD, dilutes as necessary (within limits) if OD is high
        '''
        for vi, vial in enumerate(self.vials):
            if self.final_OD_estimate[self.cycle_counter,vi]<self.target_OD:
                tmp_decision = do_nothing
                volume_to_add=0
            else:
                volume_to_add = min(5,(self.final_OD_estimate[self.cycle_counter,vi]-self.target_OD)*self.culture_volume/self.target_OD)
                self.morb.inject_volume(dilute_w_medium[0], vial, volume_to_add)
            print "dilute vial ",vial,'with', np.round(volume_to_add,3), 'previous OD', np.round(self.final_OD_estimate[self.cycle_counter,vi],3)
            self.decisions[self.cycle_counter,vi] = volume_to_add

    def init_data_plot(self):
        '''
        this function sets up the plot of the OD and the antibiotic concentration
        in each of the 
        '''
        print "init figure"
        # there is a subplot for each vial which share axis. hence they are stacked
        n_cols = 3 # supplots are arranged in rows of 3
        n_rows = int(np.ceil(1.0*self.n_vials/n_cols))
        plt.subplots_adjust(hspace = .001,wspace = .001)
        
        vi = 0
        self.subplots = {}
        self.plotted_line_objects = {}
        for vi, vial  in enumerate(self.vials):
            self.subplots[vi] = [plt.subplot(n_rows, n_cols, vi+1)]
            self.subplots[vi].append(self.subplots[vi][0].twinx())
            self.plotted_line_objects[vi] = [self.subplots[vi][0].plot([],[], c='b')[0], 
                                             self.subplots[vi][1].plot([],[], c='r')[0]]
            self.subplots[vi][0].text(0.1, 0.9, 'vial '+str(vial+1), transform=self.subplots[vi][0].transAxes)
            #       self.subplots[vi][0].plot([0,self.experiment_duration], [self.target_OD, self.target_OD], ls='--', c='k')

            # set up the axis such that the only the left most axis shows OD and ticks
            # and only the rightmost axis shows the antibiotic and ticks
            if vi%n_cols:
                self.subplots[vi][0].set_yticklabels([])
            else:
                self.subplots[vi][0].set_ylabel('OD')
            if vi%n_cols<n_cols-1:
                self.subplots[vi][1].set_yticklabels([])
            else:
                self.subplots[vi][1].set_ylabel('antibiotic')

            # switch off x tick labels in all but the bottom axis
            if int(np.ceil(1.0*self.n_vials/n_cols))<n_rows:
                self.subplots[vi][0].set_xticklabels([])
            else:
                self.subplots[vi][0].set_xlabel('time')


    def update_plot(self, dummy):
        '''
        this function is called repeatedly and redraws the plot after adding new data
        the axis are rescaled but kept identical in each subplot
        '''
        if not (self.running and self.display_OD):
            return
        
        n_cycles_to_show = 5
        display_unit = 60
        first_plot_cycle = max(0,self.cycle_counter-n_cycles_to_show)
        last_plot_cycle = first_plot_cycle+n_cycles_to_show
        #print "updating plot"
        max_OD = 0
        max_AB = 0
        for vi, vial  in enumerate(self.vials):
            x_data = np.zeros(n_cycles_to_show*self.ODs_per_cycle)
            y_data = np.zeros(n_cycles_to_show*self.ODs_per_cycle)
            y_alt_data = np.zeros(n_cycles_to_show*self.ODs_per_cycle)
            for cii, ci in enumerate(range(first_plot_cycle, last_plot_cycle)):
                if ci<self.cycle_counter:
                    x_data[cii*self.ODs_per_cycle:(cii+1)*self.ODs_per_cycle] = self.OD[ci][:,-1]/display_unit
                    y_data[cii*self.ODs_per_cycle:(cii+1)*self.ODs_per_cycle] = self.OD[ci][:,vi]
                    y_alt_data[cii*self.ODs_per_cycle:(cii+1)*self.ODs_per_cycle] = self.vial_drug_concentration[ci,vi]
                else:
                    x_data[cii*self.ODs_per_cycle:(cii+1)*self.ODs_per_cycle] =np.nan
                    y_data[cii*self.ODs_per_cycle:(cii+1)*self.ODs_per_cycle]=np.nan
                    y_alt_data[cii*self.ODs_per_cycle:(cii+1)*self.ODs_per_cycle] =np.nan

            max_OD = max(max_OD, np.max(np.ma.masked_invalid(y_data)))
            max_AB = max(max_AB, np.max(np.ma.masked_invalid(y_alt_data)))
            self.plotted_line_objects[vi][0].set_data(x_data, y_data)
            self.plotted_line_objects[vi][1].set_data(x_data, y_alt_data)

        for vi, vial  in enumerate(self.vials):
            self.subplots[vi][0].set_ylim([0,max_OD*1.2+0.01])
            self.subplots[vi][0].set_xlim([np.min(np.ma.masked_invalid(x_data)),
                                           np.max(np.ma.masked_invalid(x_data))+self.OD_dt/display_unit])
            self.subplots[vi][1].set_ylim([0,max_AB*1.2+0.01])
        plt.draw()

