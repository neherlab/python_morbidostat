import matplotlib.pyplot as plt
import numpy as np
import sys,os, glob, threading, time


class morbidostat_monitor(object):
    def __init__(self,dir_name):
        if os.path.exists(dir_name):
            self.data_dir = dir_name.rstrip('/')+'/'
            self.read_parameters_file()
            self.OD_fig_name = 'long term OD'
            self.temperature_fig_name = 'temperature'
            self.scan_dt = 10
            self.OD_dir = self.data_dir+'OD/'
            self.lock_file = self.data_dir+'.lock'
            plt.ion()
            self.init_data_plot()
            self.init_temperature_plot()
            self.figure_updater = threading.Thread(target = self.update_cycle)
        else:
            print "data directory not found"
    
    def start(self):
        self.continue_plotting=True
        self.figure_updater.start()

    def stop(self):
        self.continue_plotting=False
        self.figure_updater.join()

    def update_cycle(self):
        while self.continue_plotting:
            self.update_all()
            time.sleep(self.scan_dt)
            

    def update_all(self, xmin=0):
        self.load_cycle_data()
        self.load_OD_data()
        self.update_plot(xmin)
        time.sleep(1)
        self.update_temperature_plot(xmin)

        
    def read_parameters_file(self):
        try:
            with open(self.data_dir+'parameters.dat', 'r') as params_file:
                for line in params_file:
                    entries = line.split()
                    if entries[0]=='vials':
                        self.__setattr__('vials', map(int, entries[1:]))
                        self.n_vials = len(self.vials)
        except:
            print "can't read parameters file"
    
    def load_OD_data(self):
        if not os.path.exists(self.lock_file):
            OD_file_list = glob.glob(self.OD_dir+'OD_cycle*dat')
            if len(OD_file_list):
                tmp = np.loadtxt(OD_file_list[0])
                self.ODs_per_cycle, ncols = tmp.shape
                self.OD = np.zeros((len(OD_file_list)*self.ODs_per_cycle, ncols))
                for fname in OD_file_list:
                    cycle= int(fname.split('_')[-1][:-4])
                    if cycle<len(OD_file_list):
                        self.OD[self.ODs_per_cycle*cycle:self.ODs_per_cycle*(cycle+1),:]=np.loadtxt(fname)
                    else:
                        print "Cycle out of range"
            else:
                print "no OD data"
        else:
            print "data locked"


    def load_cycle_data(self):
        if not os.path.exists(self.lock_file):
            self.drug_concentration = np.loadtxt(self.data_dir+'vials_drug_concentrations.txt')
            self.temperature= np.loadtxt(self.data_dir+'temperature.txt')
            self.growth_rate_estimate = np.loadtxt(self.data_dir+'growth_rate_estimates.txt')
            self.OD_estimate = np.loadtxt(self.data_dir+'cycle_OD_estimate.txt')
        else:
            print "data locked"

    def init_temperature_plot(self):
        plt.figure(self.temperature_fig_name)
        ax = plt.subplot(111)
        plt.xlabel('Time')
        plt.ylabel('Temperature [C]')
        self.temperature_curves = [plt.plot([],[],c='b', label = 'T1')[0], plt.plot([],[],c='r', label = 'T2')[0]]
        plt.legend()
        plt.show()

    def init_data_plot(self):
        '''
        this function sets up the plot of the OD and the antibiotic concentration
        in each of the 
        '''
        print "init figure"
        # there is a subplot for each vial which share axis. hence they are stacked
        n_cols = 3 # subplots are arranged in rows of 3
        n_rows = int(np.ceil(1.0*self.n_vials/n_cols))
        figsize = (n_cols*2, n_rows*2)
        plt.figure(self.OD_fig_name, figsize)
        plt.subplots_adjust(hspace = .001,wspace = .001)
        plt.suptitle('OD long term')
        vi = 0
        self.subplots = {}
        self.plotted_line_objects = {}
        for vi, vial  in enumerate(self.vials):
            self.subplots[vi] = [plt.subplot(n_rows, n_cols, vi+1)]
            self.subplots[vi].append(self.subplots[vi][0].twinx())
            self.plotted_line_objects[vi] = [self.subplots[vi][0].plot([],[], c='b')[0], 
                                             self.subplots[vi][1].plot([],[], c='r', marker='o')[0]]
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
        plt.show()

#    def init_within_cycle_plot(self):
#        '''
#        this function sets up the plot of the OD within a cycle
#        '''
#        print "init within cycle plot figure"
#        # there is a subplot for each vial which share axis. hence they are stacked
#        n_cols = 3 # subplots are arranged in rows of 3
#        n_rows = int(np.ceil(1.0*self.n_vials/n_cols))
#        plt.figure(self.within_cycle_fig_name)
#        plt.subplots_adjust(hspace = .001,wspace = .001)
#        plt.suptitle('OD within cycle')
#        vi = 0
#        self.within_cycle_subplots = {}
#        self.within_plotted_line_objects = {}
#        for vi, vial  in enumerate(self.vials):
#            self.within_cycle_subplots[vi] = [plt.subplot(n_rows, n_cols, vi+1)]
#            self.within_plotted_line_objects[vi] = [self.within_cycle_subplots[vi][0].plot([],[], c='b')[0]]
#            self.within_cycle_subplots[vi][0].text(0.1, 0.9, 'vial '+str(vial+1), transform=self.within_cycle_subplots[vi][0].transAxes)
#            #       self.subplots[vi][0].plot([0,self.experiment_duration], [self.target_OD, self.target_OD], ls='--', c='k')
#
#            # set up the axis such that the only the left most axis shows OD and ticks
#            # and only the rightmost axis shows the antibiotic and ticks
#            if vi%n_cols:
#                self.within_cycle_subplots[vi][0].set_yticklabels([])
#            else:
#                self.within_cycle_subplots[vi][0].set_ylabel('OD')
#
#            # switch off x tick labels in all but the bottom axis
#            if int(np.ceil(1.0*self.n_vials/n_cols))<n_rows:
#                self.within_cycle_subplots[vi][0].set_xticklabels([])
#            else:
#                self.within_cycle_subplots[vi][0].set_xlabel('time')
#

    def update_plot(self, xmin=0):
        '''
        this function is called repeatedly and redraws the plot after adding new data
        the axis are rescaled but kept identical in each subplot
        '''
        plt.figure(self.OD_fig_name)
        n_cycles_to_show = 5
        display_unit = 60
        max_OD = 0
        max_AB = 0
        x_data = self.OD[:,-1]
        x_alt_data = self.drug_concentration[:,-1]
        for vi, vial  in enumerate(self.vials):
            y_data = self.OD[:,vi]
            y_alt_data = self.drug_concentration[:,vi]
            max_OD = max(max_OD, y_data.max())
            max_AB = max(max_AB, y_alt_data.max())
            self.plotted_line_objects[vi][0].set_data(x_data, y_data)
            self.plotted_line_objects[vi][1].set_data(x_alt_data, y_alt_data)

        xmax = x_data.max()
        for vi, vial  in enumerate(self.vials):
            self.subplots[vi][0].set_ylim([0,max_OD*1.2+0.01])
            self.subplots[vi][0].set_xlim([xmin, xmax])
            self.subplots[vi][1].set_ylim([0,max_AB*1.2+0.01])
        plt.draw()
        
    def update_temperature_plot(self, xmin=0):
        zero_indices = np.where(self.temperature[:,-1]==0)[0]
        if len(zero_indices)>1:
            max_index=zero_indices[1]-1
        else:
            max_index = self.temperature.shape[0]
        plt.figure(self.temperature_fig_name)
        self.temperature_curves[0].set_data(self.temperature[:max_index,-1], self.temperature[:max_index,0])
        self.temperature_curves[1].set_data(self.temperature[:max_index,-1], self.temperature[:max_index,1])
        plt.xlim(xmin, self.temperature[:max_index,-1].max())
        plt.ylim(self.temperature[:max_index,:2].flatten().min()-2, self.temperature[:max_index,:2].flatten().max()+2)


#
#    def update_within_cycle_plot(self, dummy):
#        '''
#        this function is called repeatedly and redraws the plot after adding new data
#        the axis are rescaled but kept identical in each subplot
#        '''
#        if not (self.running and self.display_OD):
#            return
#        #plt.ioff()
#        plt.figure(self.within_cycle_fig_name)
#        display_unit = 60
#        mmax = self.OD_measurement_counter
#        max_OD = 0
#        for vi, vial  in enumerate(self.vials):
#            max_OD = max(max_OD, np.max(self.last_OD_measurements[:,vi]))
#            xdata = (self.last_OD_measurements[:mmax,-1]-self.last_OD_measurements[0,-1])/display_unit
#            ydata = self.last_OD_measurements[:mmax,vi]
#            self.within_plotted_line_objects[vi][0].set_data(xdata,ydata)
#        for vi, vial  in enumerate(self.vials):
#            self.within_cycle_subplots[vi][0].set_ylim([0,max_OD*1.2+0.01])
#            self.within_cycle_subplots[vi][0].set_xlim([0, self.cycle_dt/display_unit])
#        plt.draw()
# 


if __name__ == '__main__':
    if len(sys.argv):
        morb_monitor = morbidostat_monitor(sys.argv[1])
        morb_monitor.start()
    else:
        print "name of data directory required"
