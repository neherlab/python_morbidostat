from morbidostat_experiment import *
import Tkinter

class set_up_dialog(Tkinter.Frame):
    def __init__(self, morb):
        self.top= Tkinter.Toplevel()
        self.top.title('Morbidostat Parameters and Set-Up')
        self.morb = morb
        self.vial_selector = vial_selection_dialog(self.morb)

        # scheduling variables
        self.time_variable_names = [('experiment_duration', 'Experiment duration [s]'),
                                    ('cycle_dt', 'Length of cycle [s]'),
                                    ('OD_dt', 'Measurment interval [s]')]
        self.string_variable_names = [('experiment_name', 'Experiment name '),
                                    ('bug', 'Organism'),
                                    ('drugA', 'Drug A'),('drugB', 'Drug B')]

        self.concentration_variable_names = [('target_OD', 'Target OD'),
                                    ('dilution_threshold', 'Dilution Threshold'),
                                    ('dilution_factor', 'Dilution Factor'),
                                    ('drugA_concentration', 'Drug A concentration'),
                                    ('drugB_concentration', 'Drug B concentration')]

        self.variables = {}
        for ttype,var_name in self.time_variable_names + self.string_variable_names + self.concentration_variable_names:
            self.variables[ttype] = Tkinter.StringVar()
            self.variables[ttype].set(str(self.morb.__getattribute__(ttype)))
        self.open_dialog()
        

    def open_dialog(self):
        self.frame= Tkinter.Frame(self.top)
        self.frame.pack()

        grid_counter = 0
        self.fields= {}
        for ti,(ttype, var_name) in enumerate(self.string_variable_names):
            Tkinter.Label(self.frame, text=var_name).grid(row=ti,column = 0, sticky=Tkinter.W)
            self.fields[ttype] = Tkinter.Entry(self.frame, textvariable = str(self.variables[ttype]))
            self.fields[ttype].grid(row=ti+grid_counter, column=1)
        grid_counter+=ti+2

        for ti,(ttype, var_name) in enumerate(self.concentration_variable_names):
            Tkinter.Label(self.frame, text=var_name).grid(row=ti+grid_counter,column = 0, sticky=Tkinter.W)
            self.fields[ttype] = Tkinter.Entry(self.frame, textvariable = str(self.variables[ttype]))
            self.fields[ttype].grid(row=ti+grid_counter, column=1)

        grid_counter+=ti+2
        for ti,(ttype, var_name) in enumerate(self.time_variable_names):
            Tkinter.Label(self.frame, text=var_name).grid(row=ti+grid_counter,column = 0, sticky=Tkinter.W)
            self.fields[ttype] = Tkinter.Entry(self.frame, textvariable = str(self.variables[ttype]))
            self.fields[ttype].grid(row=ti+grid_counter, column=1)

        grid_counter+=ti+2
        done_button = Tkinter.Button(self.frame, text="Done", command = self.read_dialog)        
        done_button.grid(row=grid_counter,column=1)
        vial_selector_button = Tkinter.Button(self.frame, text="Select vials", fg="black", 
                        command=self.vial_selector.open_dialog)
        vial_selector_button.grid(row=grid_counter,column=0)
        

    def read_dialog(self):
        for ttype, var_name in self.time_variable_names:
            self.morb.__setattr__(ttype, int(self.variables[ttype].get()))
        
        for ttype, var_name in self.string_variable_names:
            self.morb.__setattr__(ttype, self.variables[ttype].get())

        for ttype, var_name in self.concentration_variable_names:
            self.morb.__setattr__(ttype, float(self.variables[ttype].get()))

        self.morb.vials = [vi for vi in range(15) if self.vial_selector.vial_selector_variables[vi].get()]
        self.top.destroy()
        

class vial_selection_dialog(Tkinter.Frame):

    def __init__(self,morb):
        # active vials
        self.morb = morb
        self.vial_selector_variables = []
        for xi in xrange(5):
            for yi in xrange(3):
                vi= xi*3+yi
                self.vial_selector_variables.append(Tkinter.IntVar())
                self.vial_selector_variables[-1].set(int(vi in self.morb.vials))

    def open_dialog(self):            
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
        done_button = Tkinter.Button(vial_selector_frame, text="Done", command = top.destroy)        
        done_button.grid(row=5,column=1)


class morbidostat_interface(Tkinter.Frame):
    def __init__(self, master):
        self.master = master        
        self.morb = morbidostat()
        self.run_time_window()

    def call_set_up(self):
        set_up_dialog_window = set_up_dialog(self.morb)
        self.master.wait_window(set_up_dialog_window.top)
    

    def quit(self):
        self.morb.stop_experiment()
        self.run_time_frame.quit()

    def run_time_window(self):
        self.run_time_frame = Tkinter.Frame(self.master)
        self.master.title("Morbidostat control")
        self.run_time_frame.pack()

        self.set_up_button = Tkinter.Button(self.run_time_frame, text="PARAMETERS", fg="black", 
                                   command=self.call_set_up)
        self.start_button = Tkinter.Button(self.run_time_frame, text="START", fg="black", 
                                   command=self.morb.start_experiment)
        self.interrupt_button =Tkinter.Button(self.run_time_frame, text="INTERRUPT", fg="red", 
                                  command=self.morb.interrupt_experiment)
        self.resume_button = Tkinter.Button(self.run_time_frame, text="RESUME", fg="black", 
                                    command=self.morb.resume_experiment)
        self.quit_button = Tkinter.Button(self.run_time_frame, text="QUIT", fg="black", 
                                          command=self.quit)

        self.set_up_button.grid(row= 5, column = 0)
        self.start_button.grid(row= 5, column = 1)
        self.interrupt_button.grid(row= 5, column = 2)
        self.resume_button.grid(row= 5, column = 3)
        self.quit_button.grid(row= 5, column = 4)





if __name__ == '__main__':
    root = Tkinter.Tk()
    app=morbidostat_interface(root)
    root.mainloop()
    root.destroy()


