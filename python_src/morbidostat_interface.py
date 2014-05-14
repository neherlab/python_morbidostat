from morbidostat_experiment import *
import Tkinter

class morbidostat_interface(Tkinter.Frame):
    def __init__(self, master):
        frame = Tkinter.Frame(master)
        frame.pack()
        self.morb = morbidostat()

        self.vial_selector_frame = Tkinter.LabelFrame(frame, text = "Active vials")
        self.vial_selector_frame.grid(row=0, column=0, columnspan=3, rowspan=5,
                                      padx=5, pady=5, ipadx=5, ipady=5)
        self.vial_selector_variables = []
        self.vial_selector_buttons = []
        for xi in xrange(3):
            for yi in xrange(5):
                self.vial_selector_variables.append(Tkinter.IntVar())
                self.vial_selector_variables[-1].set(1)
                self.vial_selector_buttons.append(Tkinter.Checkbutton
                                                  (self.vial_selector_frame, text = str(xi*5+yi+1),
                                                   var=self.vial_selector_variables[-1]))
                self.vial_selector_buttons[-1].grid(row=yi,column=xi)


        self.start_button = Tkinter.Button(frame, text="START", fg="green", 
                                   command=self.morb.start_experiment)
        self.interrupt_button =Tkinter.Button(frame, text="INTERRUPT", fg="red", 
                                  command=self.morb.interrupt_experiment)
        self.resume_button = Tkinter.Button(frame, text="RESUME", fg="yellow", 
                                    command=self.morb.resume_experiment)
        self.quit_button = Tkinter.Button(frame, text="QUIT", fg="black", 
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
    def quit(self):
        self.morb.stop_experiment()
        frame.quit()

if __name__ == '__main__':
    root = Tkinter.Tk()
    app=morbidostat_interface(root)
    root.mainloop()
    root.destroy()


