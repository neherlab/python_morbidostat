from morbidostat_experiment import *
import Tkinter
import threading


class set_up_dialog(Tkinter.Frame):
    '''
    defines a class that prompts the user for parameters of the morbidostat
    and scheduling intervals. It uses the Tkinter library to display windows
    and read user input
    '''


    def __init__(self, morb):
        '''
        requires a morbidostat instance as argument. will set the morbidostat
        parameters as they are read from the dialog
        '''
        self.top= Tkinter.Toplevel()
        self.top.title('Morbidostat Parameters and Set-Up')
        self.morb = morb
        # instantiate a dialog for vial selection. is displayed only upon click
        self.vial_selector = vial_selection_dialog(self.morb)

        # scheduling variables
        self.time_variable_names = [('experiment_duration', 'Experiment duration [s]'),
                                    ('cycle_dt', 'Length of cycle [s]'),
                                    ('OD_dt', 'Measurment interval [s]')]
        # bookkeeping and annotation
        self.string_variable_names = [('experiment_name', 'Experiment name '),
                                    ('bug', 'Organism'),
                                    ('drugA', 'Drug A'),('drugB', 'Drug B')]
        # floating point variables that define the feedback properties and concentrations
        self.concentration_variable_names = [('target_OD', 'Target OD'),
                                    ('dilution_threshold', 'Dilution Threshold'),
                                    ('dilution_factor', 'Dilution Factor'),
                                    ('drugA_concentration', 'Drug A concentration'),
                                    ('drugB_concentration', 'Drug B concentration')]

        self.variables = {}
        for ttype,var_name in self.time_variable_names +\
                              self.string_variable_names +\
                              self.concentration_variable_names:
            self.variables[ttype] = Tkinter.StringVar()
            self.variables[ttype].set(str(self.morb.__getattribute__(ttype)))
        self.open_dialog()
        

    def open_dialog(self):
        '''
        open a dialog window and add all the entries required
        '''
        self.frame= Tkinter.Frame(self.top)
        self.frame.pack()

        grid_counter = 0  # keeps track of the number of fields for arrangment on a grid
        self.fields= {}
        # names and annotations
        for ti,(ttype, var_name) in enumerate(self.string_variable_names):
            Tkinter.Label(self.frame, text=var_name).grid(row=ti,column = 0, 
                                                          sticky=Tkinter.W)
            self.fields[ttype] = Tkinter.Entry(self.frame, textvariable = 
                                               str(self.variables[ttype]))
            self.fields[ttype].grid(row=ti+grid_counter, column=1)

        # concentrations and feed back variables
        grid_counter+=ti+2 # produce gap (but it doesn't make a difference)
        for ti,(ttype, var_name) in enumerate(self.concentration_variable_names):
            Tkinter.Label(self.frame, text=var_name).grid(row=ti+grid_counter,column = 0, 
                                                          sticky=Tkinter.W)
            self.fields[ttype] = Tkinter.Entry(self.frame, textvariable = 
                                               str(self.variables[ttype]))
            self.fields[ttype].grid(row=ti+grid_counter, column=1)

        # scheduling variables
        grid_counter+=ti+2
        for ti,(ttype, var_name) in enumerate(self.time_variable_names):
            Tkinter.Label(self.frame, text=var_name).grid(row=ti+grid_counter,column = 0, 
                                                          sticky=Tkinter.W)
            self.fields[ttype] = Tkinter.Entry(self.frame, textvariable = 
                                               str(self.variables[ttype]))
            self.fields[ttype].grid(row=ti+grid_counter, column=1)

        # add buttons to select vials or return to main dialog
        grid_counter+=ti+2
        done_button = Tkinter.Button(self.frame, text="Done", command = self.read_dialog)
        done_button.grid(row=grid_counter,column=1)
        vial_selector_button = Tkinter.Button(self.frame, text="Select vials", fg="black", 
                        command=self.vial_selector.open_dialog)
        vial_selector_button.grid(row=grid_counter,column=0)
        

    def read_dialog(self):
        '''
        read the user input and assign to morbidostat instance
        this is called by the "Done" button, hence destroy the window
        '''
        if not self.morb.running:
            # scheduling variables all integers interpreted as seconds
            for ttype, var_name in self.time_variable_names:
                self.morb.__setattr__(ttype, int(self.variables[ttype].get()))

            # annotiations and names, interpret as strings
            for ttype, var_name in self.string_variable_names:
                self.morb.__setattr__(ttype, self.variables[ttype].get())

            # concentrations and feed back variables, interpret as float
            for ttype, var_name in self.concentration_variable_names:
                self.morb.__setattr__(ttype, float(self.variables[ttype].get()))

            # set active vials -> make a list of checked buttons
            self.morb.vials = [vi for vi in range(15) if 
                               self.vial_selector.vial_selector_variables[vi].get()]
        elif self.morb.interrupted:
            # update some parameters:
            print "update parameters at time ", self.morb.experiment_time()
            new_experiment_length  = int(self.variables['experiment_duration'].get())
            if new_experiment_length>self.morb.experiment_duration:
                cycles_to_add = (new_experiment_length-self.morb.experiment_duration)//self.morb.cycle_dt
                if cycles_to_add>0:
                    self.morb.experiment_duration = new_experiment_length
                    print "added", cycles_to_add, 'cycles. New experiment duration', self.morb.experiment_duration
                    self.morb.add_cycles_to_data_arrays(cycles_to_add)
            new_drug_conc = (float(self.variables['drugA_concentration'].get()),
                             float(self.variables['drugB_concentration'].get()))
            self.morb.change_drug_concentrations(new_drug_conc[0], new_drug_conc[1])
            self.morb.target_OD = float(self.variables['target_OD'].get())
            self.morb.dilution_factor = float(self.variables['dilution_factor'].get())
            self.morb.dilution_threshold = float(self.variables['dilution_threshold'].get())
            self.morb.calculate_derived_values()

        self.top.destroy()
        

class vial_selection_dialog(Tkinter.Frame):
    '''
    defines a window that displays the vial layout with checkboxes
    '''
    def __init__(self,morb):
        ''' 
        requires a morbidostat instance as input to set the active vials
        '''
        self.morb = morb
        self.vial_selector_variables = []
        # make a list of Tkinter.IntVar and set them with the current active vials 
        for xi in xrange(5):
            for yi in xrange(3):
                vi= xi*3+yi
                self.vial_selector_variables.append(Tkinter.IntVar())
                self.vial_selector_variables[-1].set(int(vi in self.morb.vials))

    def open_dialog(self):
        '''
        make a dialog consisting of a 5x3 array of checkboxes annd a done button
        '''
        top = Tkinter.Toplevel()
        top.title('Active vials')
        vial_selector_frame = Tkinter.Frame(top)
        vial_selector_frame.pack()

        vial_selector_buttons = []
        for xi in xrange(5):
            for yi in xrange(3):
                vi= xi*3+yi
                vial_selector_buttons.append(Tkinter.Checkbutton
                                                  (vial_selector_frame, text = str(vi+1),
                                                   var=self.vial_selector_variables[vi]))
                vial_selector_buttons[-1].grid(row=xi,column=yi)
        # add button, destroy window upon pressing, result is read out by parent
        done_button = Tkinter.Button(vial_selector_frame, text="Done", 
                                     command = top.destroy)        
        done_button.grid(row=5,column=1)


class experiment_selector(Tkinter.Frame):
    '''
    window that opens in the very beginning and prompts the user for the 
    type of experiment he/she wants to run. as of know there are three choices. 
    '''
    def __init__(self, morb):
        self.top = Tkinter.Toplevel()
        self.top.title("select experiment type")
        self.morb = morb

        self.experiment_types = [("Morbidostat", MORBIDOSTAT_EXPERIMENT),
                            ("Fixed OD", FIXED_OD_EXPERIMENT),
                            ("Growth curve", GROWTH_RATE_EXPERIMENT)]
        self.v = Tkinter.IntVar()
        self.v.set(0) # initialize default choice

        self.selector_window()

    
    def selector_window(self):
        '''
        upon window, add radiobuttons
        '''
        self.selector_frame = Tkinter.Frame(self.top)
        self.selector_frame.pack()
        for mode, text in enumerate(self.experiment_types):
            b = Tkinter.Radiobutton(self.selector_frame, text=text[0],
                                    variable=self.v, value = mode)
            b.pack(anchor=Tkinter.W)

        # add button. upon pressing it, the result is read, set and the window closed
        done_button = Tkinter.Button(self.selector_frame, text="Done", 
                                     command = self.read_type_and_set)        
        done_button.pack(anchor=Tkinter.E)

    def read_type_and_set(self):
        '''
        read the button group, set the result in self.morb and destroy window
        '''
        mode_index = self.v.get()
        self.morb.experiment_type = self.experiment_types[mode_index][1]
        self.top.destroy()
        

class morbidostat_interface(Tkinter.Frame):
    '''
    control panel of the morbidostat
    '''

    def __init__(self, master, morb):
        '''
        required input
        -- Tkinter master
        -- a morbidostat instance
        '''
        self.master = master        
        self.morb = morb
        self.all_good=True
        #self.update_status_thread = threading.Thread(target = self.update_status_strings)
        self.run_time_window()

    def call_set_up(self):
        '''
        called upon parameters button press. opens dialog 
        '''
        if morb.running==False or morb.interrupted:
            set_up_dialog_window = set_up_dialog(self.morb)
            self.master.wait_window(set_up_dialog_window.top)
        else:
            print "cannot update parameters while running"

    def open_experiment_type_selector(self):
        '''
        called in the very beginning
        '''
        if not morb.running:
            experiment_selector_dialog = experiment_selector(self.morb)
            self.master.wait_window(experiment_selector_dialog.top)
        else:
            print "cannot update parameters while running"


    def quit(self):
        '''
        called by quit button
        '''
        self.all_good=False
        self.morb.stop_experiment()
        self.run_time_frame.quit()

    def start(self):
        '''
        called by start button
        '''
        self.all_good=True
        self.morb.start_experiment()
        self.update_status_strings()

    def interrupt(self):
        '''
        called by interrupt button
        '''
        self.all_good=True
        self.morb.interrupt_experiment()
        self.update_status_strings()

    def resume(self):
        '''
        called by resume button
        '''
        self.all_good=True
        self.morb.resume_experiment()
        self.update_status_strings()


    def status_str(self):
        '''
        translates the status of the morbidostat into a human readabe string
        '''
        if self.morb.running and not self.morb.interrupted:
            return "running"
        elif self.morb.interrupted:
            return "interrupted"
        elif self.morb.stopped:
            return "stopped"
        else:
            return "undefined"

    def remaining_time_str(self):
        '''
        returns a formated string of the time remaining the experiment
        '''
        remaining_time = (self.morb.n_cycles-self.morb.cycle_counter)*self.morb.cycle_dt
        return self.seconds_to_time_str(remaining_time)
            
    def elapsed_time_str(self):
        '''
        returns a formated string of the duration of the experiment so far
        '''        
        remaining_time = (self.morb.cycle_counter)*self.morb.cycle_dt
        return self.seconds_to_time_str(remaining_time)

    def remaining_cycle_time_str(self):
        '''
        returns a formated string of the time remaining in the current cycle
        '''                
        remaining_time = (self.morb.ODs_per_cycle-self.morb.OD_measurement_counter)*self.morb.OD_dt
        return self.seconds_to_time_str(remaining_time)

    def seconds_to_time_str(self,nsec):
        '''
        format seconds into a human readable string
        '''
        hours = nsec//3600
        minutes = nsec//60 - hours*60
        seconds = nsec-60*minutes-hours*3600
        return str(hours)+'h:'+format(minutes,'02d')+'m:'+format(seconds,'02d')+'s'        
        

    def run_time_window(self):
        '''
        set up the window displaying status, time, and experiment type
        '''
        self.run_time_frame = Tkinter.Frame(self.master)
        self.master.title("Morbidostat control")
        self.run_time_frame.pack()
        label_font= 'Helvetica'
        var_font = 'Courier'
        fsize = 16
    
        # define the annotations of the displayed info
        self.experiment_type_label = Tkinter.Label(self.run_time_frame, text='Experiment type: ', 
             fg="black", anchor=Tkinter.W, height = 2, width= 20, font=(label_font, fsize))
        self.status_label = Tkinter.Label(self.run_time_frame, text='Status: ', 
             fg="black", anchor=Tkinter.W, height = 2, width= 20, font=(label_font, fsize))
        self.elapsed_time = Tkinter.Label(self.run_time_frame, text  = 'Elapsed time:', 
             fg="black", anchor=Tkinter.W, height = 2, width= 20, font=(label_font, fsize))
        self.remaining_time = Tkinter.Label(self.run_time_frame, text  = 'Remaining time:',
             fg="black", anchor=Tkinter.W, height = 2, width= 20, font=(label_font, fsize))
        self.remaining_cycle_time = Tkinter.Label(self.run_time_frame, text  = 'Remaining in cycle: ', 
             fg="black", anchor=Tkinter.W, height = 2, width= 20, font=(label_font, fsize))

        # define fields for the displayed info
        self.experiment_type_label_val = Tkinter.Label(self.run_time_frame, 
             text=self.morb.experiment_type, fg="black", anchor=Tkinter.W, height = 2, 
             width= 15, font=(var_font, fsize))
        self.status_label_val = Tkinter.Label(self.run_time_frame, 
             text=self.status_str(), fg="black", anchor=Tkinter.W, height = 2, 
             width= 15, font=(var_font, fsize))
        self.elapsed_time_val = Tkinter.Label(self.run_time_frame, 
             text  = self.elapsed_time_str(), fg="black", anchor=Tkinter.W, height = 2, 
             width= 15, font=(var_font, fsize))
        self.remaining_time_val = Tkinter.Label(self.run_time_frame, 
             text  = self.remaining_time_str(), fg="black", anchor=Tkinter.W, height = 2, 
             width= 15, font=(var_font, fsize))
        self.remaining_cycle_time_val = Tkinter.Label(self.run_time_frame, 
             text  = self.remaining_cycle_time_str(), fg="black", anchor=Tkinter.W, 
             height = 2, width= 15, font=(var_font, fsize))

        # define the buttons
        self.set_up_button = Tkinter.Button(self.run_time_frame, text="PARAMETERS", fg="black", 
                                   command=self.call_set_up, height = 2)
        self.refresh_button = Tkinter.Button(self.run_time_frame, text="REFRESH", fg="black", 
                                   command=self.update_status_strings, height = 2)
        self.start_button = Tkinter.Button(self.run_time_frame, text="START", fg="black", 
                                   command=self.start, height = 2)
        self.interrupt_button =Tkinter.Button(self.run_time_frame, text="INTERRUPT", fg="red", 
                                  command=self.interrupt, height = 2)
        self.resume_button = Tkinter.Button(self.run_time_frame, text="RESUME", fg="black", 
                                    command=self.resume, height = 2)
        self.quit_button = Tkinter.Button(self.run_time_frame, text="QUIT", fg="black", 
                                          command=self.quit, height = 2)

        # arrange the labels in column 0
        self.experiment_type_label.grid(row=0, column=0, columnspan=2)
        self.status_label.grid(row=1, column=0, columnspan=2)
        self.elapsed_time.grid(row=2, column=0, columnspan=2)
        self.remaining_time.grid(row=3, column=0, columnspan=2)
        self.remaining_cycle_time.grid(row=4, column=0, columnspan=2)

        # arrange the information in column 1 
        self.experiment_type_label_val.grid(row=0, column=2, columnspan=3)
        self.status_label_val.grid(row=1, column=2, columnspan=3)
        self.elapsed_time_val.grid(row=2, column=2, columnspan=3)
        self.remaining_time_val.grid(row=3, column=2, columnspan=3)
        self.remaining_cycle_time_val.grid(row=4, column=2, columnspan=3)

        # arrange the buttons in one row at the bottom
        self.set_up_button.grid(row= 6, column = 0)
        self.refresh_button.grid(row= 6, column = 1)
        self.start_button.grid(row= 6, column = 2)
        self.interrupt_button.grid(row= 6, column = 3)
        self.resume_button.grid(row= 6, column = 4)
        self.quit_button.grid(row= 6, column = 5)

        # prompt the user for the experiment type
        self.open_experiment_type_selector()
        # make sure all strings are uptodate
        self.update_status_strings()
    
    def update_status_strings(self):
        '''
        rewrite all displayed information such that it is up-to-date
        '''
        self.experiment_type_label_val.configure(text = self.morb.experiment_type)
        self.status_label_val.configure(text=self.status_str())
        self.elapsed_time_val.configure(text  = self.elapsed_time_str())
        self.remaining_time_val.configure(text  = self.remaining_time_str())
        self.remaining_cycle_time_val.configure(text  = self.remaining_cycle_time_str())


def run_GUI(morb):
    '''
    open the gui
    '''
    root = Tkinter.Tk()
    app=morbidostat_interface(root, morb)
    root.mainloop()
    root.destroy()

if __name__ == '__main__':
    morb = morbidostat()
    gui_thread = threading.Thread(target = run_GUI, args = (morb,))
    gui_thread.start()
    

