from morbidostat_experiment import *
import Tkinter

class morbidostat_interface(Tkinter.Frame):
    def __init__(self, master):
        self.master = master        
        self.morb = morbidostat()
        self.set_defaults()
        
        self.set_up_window()

    def quit(self):
        self.morb.stop_experiment()
        self.run_time_frame.quit()


    def run_time_window(self):
        self.run_time_frame = Tkinter.Frame(self.master)
        self.master.title("Morbidostat control")
        self.run_time_frame.pack()

        self.start_button = Tkinter.Button(self.run_time_frame, text="START", fg="green", 
                                   command=self.morb.start_experiment)
        self.interrupt_button =Tkinter.Button(self.run_time_frame, text="INTERRUPT", fg="red", 
                                  command=self.morb.interrupt_experiment)
        self.resume_button = Tkinter.Button(self.run_time_frame, text="RESUME", fg="yellow", 
                                    command=self.morb.resume_experiment)
        self.quit_button = Tkinter.Button(self.run_time_frame, text="QUIT", fg="black", 
                                          command=self.quit)

        self.start_button.grid(row= 5, column = 0)
        self.interrupt_button.grid(row= 5, column = 1)
        self.resume_button.grid(row= 5, column = 2)
        self.quit_button.grid(row= 5, column = 7)

#        self.start_button.pack(side=Tkinter.LEFT)
#        self.interrupt_button.pack(side=Tkinter.LEFT)
#        self.resume_button.pack(side=Tkinter.LEFT)
#        self.quit_button.pack(side=Tkinter.LEFT)
#


    def set_up_window(self):
        self.set_up_top = Tkinter.Toplevel()
        self.set_up_frame = Tkinter.Frame(self.set_up_top)
        self.set_up_top.title("Morbidostat set-up")
        self.set_up_frame.pack()

        # variables that         
        self.vial_selector_button = Tkinter.Button(self.set_up_frame, text="Select vials", fg="black", 
                                   command=self.select_vials)
        self.scheduling_button = Tkinter.Button(self.set_up_frame, text="Scheduling", fg="black", 
                                  command=self.proceed_to_run_time)
        self.control_button= Tkinter.Button(self.set_up_frame, text="Control", fg="black", 
                                    command=self.proceed_to_run_time)
        self.next_button= Tkinter.Button(self.set_up_frame, text="Next", fg="black", 
                                          command=self.proceed_to_run_time)

        self.vial_selector_button.grid(row= 0, column = 0, padx = 10, pady=10)
        self.scheduling_button.grid(row= 0, column = 1, padx = 10, pady=10)
        self.control_button.grid(row= 0, column = 2, padx = 10, pady=10)
        self.next_button.grid(row= 0, column = 3, padx = 10, pady=10)

    def proceed_to_run_time(self):
        self.set_up_top.destroy()
        self.run_time_window()

    def set_defaults(self, ):
        # active vials
        self.vial_selector_variables = []
        for xi in xrange(3):
            for yi in xrange(5):
                self.vial_selector_variables.append(Tkinter.IntVar())
                self.vial_selector_variables[-1].set(1)

        # scheduling variables
        self.time_variable_names = ['experiment_duration', 'cycle_dt', 'OD_dt']
        self.times = {}
        for ttype in self.time_variable_names:
            self.times[ttype] = Tkinter.IntVar()
            self.times[ttype].set(self.morb.__getattribute__(ttype))

        # text and protocol variables
        self.text_attribute_names = ['experiment_name', 'bug','drug']
        self.text_attributes = {}
        for ttype in ['experiment_name', 'bug','drug']:
            self.text_attributes[ttype] = Tkinter.StringVar()
            self.text_attributes[ttype].set(self.morb.__getattribute__(ttype))
        
        # feed back attributes
        self.feed_back_parameter_names = ['dilution_factor', 'target_OD', 'dilution_threshold',
                                          'drugA_concentration','drugB_concentration']         
        
        self.feed_back_parameters = {}
        for ftype in self.feed_back_parameter_names:
            self.feed_back_parameters[ftype]=Tkinter.StringVar()
            self.feed_back_parameters[ftype].set(str(self.morb.__getattribute__(ftype)))        


    def select_vials(self):
        top = Tkinter.Toplevel()
        top.title('Active vials')
        vial_selector_frame = Tkinter.Frame(top)
        vial_selector_frame.pack()

        vial_selector_buttons = []
        for xi in xrange(3):
            for yi in xrange(5):
                vi= xi*5+yi
                vial_selector_buttons.append(Tkinter.Checkbutton
                                                  (vial_selector_frame, text = str(vi+1),
                                                   var=self.vial_selector_variables[vi]))
                vial_selector_buttons[-1].grid(row=yi,column=xi)
        done_button = Tkinter.Button(vial_selector_frame, text="Done", command = top.destroy)        
        done_button.grid(row=5,column=1)


    def  set_scheduling(self):
        self.scheduling_top = Tkinter.Toplevel()
        self.scheduling_top.title('Scheduling variables')
        scheduling_frame= Tkinter.Frame(self.scheduling_top)
        scheduling_frame.pack()

        entries = {}
        for ti,ttype in enumerate(self.time_variable_names):
            Label(master, text=ttype).grid(row=ti,column = 0, sticky=W)
            entries[ttype] = Tkinter.Entry(scheduling_frame)
            entries[ttype].grid(row=ti, column=1)

        done_button = Tkinter.Button(scheduling_frame, text="Done", command = self.read_scheduling_dialog)        
        done_button.grid(row=len(self.time_variable_names),column=1)

    def read_scheduling_dialog(self):
        for ti,ttype in enumerate(self.time_variable_names):
            Label(master, text=ttype).grid(row=ti,column = 0, sticky=W)
            entries[ttype] = Tkinter.Entry(scheduling_frame)
            entries[ttype].grid(row=ti, column=1)
        

if __name__ == '__main__':
    root = Tkinter.Tk()
    app=morbidostat_interface(root)
    root.mainloop()
    root.destroy()


