# Script based on morbidostat interface by Richard Neher
import time
import threading
import math
import serial,os
import numpy as np

# Import ADCPi
from ADCPi import ADCPi


# Import IOZero32
try:
    from IOZero32 import IOZero32
except ImportError:
    print("Failed to import IOZero32 from python system path")
    print("Importing from parent folder instead")
    try:
        import sys
        sys.path.append("..")
        from IOZero32 import IOZero32
    except ImportError:
        raise ImportError(
            "Failed to import library from parent folder")

#############
# IO Zero I2C board addresses (Have to be changed on the boards)
#############

i2c_IO_board01 = IOZero32(0x20)
i2c_IO_board02 = IOZero32(0x21)
i2c_IO_board03 = IOZero32(0x23)

#############
# ADC Pi I2C board addresses (Have to be changed on the boards)
#############

ADC_1 = ADCPi(0x68, 0x69, 12)
ADC_2 = ADCPi(0x68, 0x69, 12)

#############
# Prevent race conditions = Prevents two threads from accessing shared variables simultaneously
#############

lok=threading.Lock()

#############
# Initialization (before class is called)
#############




#############
# Define morbidostat class that defines command to work with the device
#############

class morbidostat:

        def __init__(self):
            self.connect()
            self.pump_off_threads = {}
            self.temperature_thread = None
            self.light_state = False
            self.mixing_time = 5 # mixing time in seconds


    ### Not done: Atomic serial writer
        def atomic_serial_write(self,msg):
            """
            Converts a message msg into ascii.
            """
            print('Not done yet')

    ### Not done: Atomic serial read line
        def atomic_serial_readline(self,msg):
            """
            Reads from serial port and decodes ascii back into a message
            """
            print('Not done yet')

        ### Not done: Connect to raspberry pi
        def connect(self,msg):
            '''
            Open a serial connection to the raspberry pi. look for it on different
            serial ports. if it is not found on the first ten trials, give
            up and raise error message (to be implemented).
            '''
            try_next = True
            port_number=0

            while try_next:
                try:
                    device_name = '/dev/ttyACM'+str(port_number)
                    self.ser = serial.Serial(device_name, baudrate, timeout = 1.0)
                    #self.ser = serial.Serial('COM2',9600 ,Timeout = 1.0)
                    if self.ser.isOpen():
                        print(f"Serial {device_name} opened")
                        # wait a second to let the serial port get up to speed
                        time.sleep(1)
                        self.morbidostat_OK = True
                        try_next=False
                except:
                    if port_number<10:
                        print(f"Serial {device_name} not available, trying next")
                        try_next=True
                        port_number+=1
                    else:
                        print("Opening serial port failed")
                        try_next=False
                    self.morbidostat_OK = False
            return port_number
            print('Not done yet')

        ### Not done: Atomic serial writer
        def volume_to_time(self,pump_type, pump, volume):

            print('Not done yet')

        ### Not done: Atomic serial writer
        def wait_until_mixed(self):
            print('Not done yet')

        ### Not done: Atomic serial writer
        def disconnect(self,msg):
            """
            Prob. wont be needed anymore
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def pump_to_pin(self, pump_type, pump_number):
            """
            Needs to be changed
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def vial_to_pin(self,vial):
            """
            Needs to change
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def voltage_to_OD(self,vial, mean_val, std_val):
            print('Not done yet')

        ### Not done: Atomic serial writer
        def measure_OD(self, vial, n_measurements=1, dt=10, switch_light_off=True):
            """
            Needs to change

            measure the OD at the specified vial n_measurement times with a time lag
            of dt milli seconds between measurements.
            params:
            ser: open serial port to communicate with the arduino
            vial: number of the vial (or more precisely the A/D it is attached to (<16)
            n_measurments: number of repeated measurements to be taken (<10000)
            dt: time lag between measurements (<10000 ms)
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def measure_voltage(self, vial, n_measurements=1, dt=10, switch_light_off=True):
            """
            Needs to change
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def measure_voltage_pin(self, analog_pin, n_measurements=1, dt=10, switch_light_off=True):
            """
            Needs to change

            Measure the voltage at specified pin n_measurement times with a time lag
            of dt milli seconds between measurements.
            params:
            ser: open serial port to communicate with the arduino
            vial: number of the vial (or more precisely the A/D it is attached to (<16)
            n_measurments: number of repeated measurements to be taken (<10000)
            dt: time lag between measurements (<10000 ms)
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def inject_volume(self, pump_type='pump2', pump_number=0, volume=0.1, conc=None):
            """
            Needs to change

            run a specific pump to inject a given volume
            params:
            pump_type: one of "pump1", "pump2" and "pump3"
            pump_number: number of the pump to be switched on (0-15)
            volume: volume to be added in ml
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def remove_waste(self,msg):
            """
            Needs to change

            run the waste pump to remove the specified volume of waste
            params:
            volume: volume to be removed in ml
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def run_pump(self,pump_type='pump2', pump_number=0, run_time=0.1):
            """
            Needs to change

            Run a specific pump for a given amount of time
            params:
            pump_type: one of "medium", "pump1" and "pump3"
            pump_number: number of the pump to be switched on (0-15)
            time: time to run the pump in seconds
            """
            print('Not done yet')

        ### Not done: Atomic serial writer
        def atomic_serial_write(self,msg):
            print('Not done yet')

        ### Not done: Atomic serial writer
        def atomic_serial_write(self,msg):
            print('Not done yet')

        ### Not done: Atomic serial writer
        def atomic_serial_write(self,msg):
            print('Not done yet')

        ### Not done: Atomic serial writer
        def atomic_serial_write(self,msg):
            print('Not done yet')

        ### Not done: Atomic serial writer
        def atomic_serial_write(self,msg):
            print('Not done yet')

        ### Not done: Atomic serial writer
        def atomic_serial_write(self,msg):
            print('Not done yet')