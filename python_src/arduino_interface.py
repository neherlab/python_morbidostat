import time
import threading
import math
import serial,os
import numpy as np

lok=threading.Lock()

debug = False
baudrate = 9600
# arduino pin controlling the IR LEDs via a relais
<<<<<<< HEAD
light_switch = 22
thermometer_pin = 4
suction_pump = 3
reset_pin = 52
# dictionary mapping pumps to pins
pumps = {'pump1': [22, 23, 24, 25, 26,  # 1.1 - 1.5
                   27, 28, 29, 30, 31,  # 2.1 - 2.5
                   32, 33, 34, 35, 36], # 3.1 - 3.5
         'pump2': [37, 38, 39, 40, 41,  # 4.1 - 4.5
                   42, 43, 44, 45, 46,  # 5.1 - 5.5
                   47, 48, 49, 50, 51], # 6.1 - 6.5
         'pump3': [14, 0, 1, 2, 3,      # 7.1 - 7.5
                   4, 5, 6, 7, 8,       # 8.1 - 8.5
                   9, 10, 11, 12, 13],  # 9.1 - 9.5
=======
reset_pin =53
light_switch = 52
thermometer_pin = 17
suction_pump = 53 #waste pump
pumps = {'pump1': [22, 23, 24, 25, 26,  # 1.1 - 1.5 plug 1
                   27, 28, 29, 30, 31,  # 2.1 - 2.5 plug 2
                   32, 33, 34, 35, 36], # 3.1 - 3.5 plug 3
         'pump2': [37, 38, 39, 40, 41,  # 4.1 - 4.5 plug 4 (pump 2 didn't switch)
                   42, 43, 44, 45, 46,  # 5.1 - 5.5 plug 5 
                   47, 48, 49, 50, 51], # 6.1 - 6.5 plug 6 
         'pump3': [14, 15, 16, 2, 3,      # 7.1 - 7.5 plug 7 (pin 0,1 seem to be always high)
                   4, 5, 6, 7, 8,       # 8.1 - 8.5 plug 8
                   9, 10, 11, 12, 13],  # 9.1 - 9.5 plug 7
>>>>>>> 8bbbe3359dbe0cb99be706dea07b6e9ed8d42853
         'waste': suction_pump}


#vials_to_pins_assignment = [10,5,0, 11,6,1,12,7,2,13,8,3,14,9,4]
#vials_to_pins_assignment = [0,5,10,1,6,11,2,7,12,3,8,13,4,9,14]
vials_to_pins_assignment = [10, 11, 12, 13, 14, #row 1
                            5, 6, 7, 8, 9,      #row 2
                            0, 1, 2, 3, 4]      #row 3


####
<<<<<<< HEAD
morb_path = '/mnt/c/Users/Eric/Documents/Master/Masterarbeit/python_morbidostat/'
=======
morb_path = '/'.join(os.path.realpath(__file__).split('/')[:-2])+'/'
print(morb_path)
#morb_path = '/home/morbidostat/python_arduino/'
>>>>>>> 8bbbe3359dbe0cb99be706dea07b6e9ed8d42853

############
# load calibration parameters
############
pump_calibration_file_base = morb_path+'python_src/pump_calibration'
OD_calibration_file_name = morb_path+'python_src/OD_calibration.dat'
pump_calibration_params = {}
for pump_type in pumps:
    fname = pump_calibration_file_base+'_'+pump_type+'.dat'
    if pump_type!='waste':
        if os.path.isfile(fname):
            try:
                pump_calibration_params[pump_type] = np.loadtxt(fname)
            except:
                print "error opening pump calibration, all pump calibration parameters set to 2.4ml/min"
                pump_calibration_params[pump_type] = 0.04*np.ones(15)
        else:
            print "no pump calibration file "+fname+", all pump calibration parameters set to 2.4 ml/min"
            pump_calibration_params[pump_type] = 0.04*np.ones(15)
    else:
        if os.path.isfile(fname):
            try:
                pump_calibration_params[pump_type] = np.array([np.loadtxt(fname)])
            except:
                print "error opening pump calibration, all pump calibration parameters set to 2.4ml/min"
                pump_calibration_params[pump_type] = np.array([0.04])
        else:
            print "no pump calibration file "+fname+", all pump calibration parameters set to 2.4 ml/min"
            pump_calibration_params[pump_type] = np.array([0.04])

if os.path.isfile(OD_calibration_file_name):
    try:
        voltage_to_OD_params = np.loadtxt(OD_calibration_file_name)
    except:
        print "error opening OD calibration file, all OD parameters set to zeros"
        voltage_to_OD_params = np.zeros((15,2))
else:
    print "no OD calibration file, all OD parameters set to zero"
    voltage_to_OD_params = np.zeros((15,2))

#############
# define morbidostat class that defines command to work with the device
#############
class morbidostat:

    def __init__(self):
        self.connect()
        self.pump_off_threads = {}
        self.temperature_thread = None
        self.light_state = False
        self.mixing_time = 5 # mixing time in seconds

    def atomic_serial_write(self,msg):
        with lok:
            self.ser.write(msg)
        return len(msg)
    def atomic_serial_readline(self):
        with lok:
            return self.ser.readline()

    def connect(self):
        '''
        open a serial connection to the arduino. look for it on different
        serial ports. if it is not found on the first ten trials, give
        up.
        '''
        try_next = True
        port_number=0
        while try_next:
            try:
                self.ser = serial.Serial('COM2',9600 ,Timeout = 1.0)
                if self.ser.isOpen():
                    print("asdfSerial /dev/ttyACM"+str(port_number)+" opened")
                    # wait a second to let the serial port get up to speed
                    time.sleep(1)
                    self.morbidostat_OK = True
                    try_next=False
            except:
                if port_number<10:
                    print("Serial /dev/ttyACM"+str(port_number)+" not available, trying next")
                    try_next=True
                    port_number+=1
                else:
                    print("asdfOpening serial port failed")
                    try_next=False
                self.morbidostat_OK = False
        return port_number

    def volume_to_time(self,pump_type, pump, volume):
        if pump_type in pump_calibration_params:
            if pump<len(pump_calibration_params[pump_type]):
                return volume/pump_calibration_params[pump_type][pump]
            else:
                print "invalid pump number", pump, 'only ',len(pump_calibration_params[pump_type]), \
                    'calibration parameters'
                return 0
        else:
            print "invalid pump_type", pump_type, 'not in', pump_calibration_params.keys()
            return 0


    def wait_until_mixed(self):
        '''
        waits for the completion of all pumps by joining the
        pump off threads
        '''
        tmp_last_pump_off_time = 0
        for k,t in self.pump_off_threads.iteritems():
            t.join()
        time.sleep(self.mixing_time)

    def disconnect(self):
        '''
        close the serial port
        '''
        if self.morbidostat_OK and self.ser.isOpen():
            # wait for all threads to finish
            while any([t.is_alive() for k,t in self.pump_off_threads.iteritems()]):
                print("\n Before disconnecting waiting for ")
                for k,t in self.pump_off_threads.iteritems():
                    if t.is_alive():
                        print(str(k)+ "\tto finish")
                time.sleep(1)
            self.ser.close()
            self.morbidostat_OK=False

    def pump_to_pin(self, pump_type, pump_number):
        assert pump_type in pumps, "Bad pump type: "+str(pump_type)
        assert pump_number>=0 and pump_number<15, "Bad pump number, got "+str(pump_number)
        return pumps[pump_type][pump_number]


    def vial_to_pin(self, vial):
        assert vial<15, "maximal vial number is 15, got "+str(vial)
        return vials_to_pins_assignment[vial]

    def voltage_to_OD(self,vial, mean_val, std_val):
        if mean_val is None:
            print "got None instead of an AD output for vial",vial
            return 0,0
        else:
            ODval = voltage_to_OD_params[vial,0]*mean_val+voltage_to_OD_params[vial,1]
            ODstd = voltage_to_OD_params[vial,0]*std_val
            return max(ODval, 0.0001), ODstd

    def measure_OD(self, vial, n_measurements=1, dt=10, switch_light_off=True):
        '''
        measure the OD at the specified vial n_measurement times with a time lag
        of dt milli seconds between measurements.
        params:
        ser: open serial port to communicate with the arduino
        vial: number of the vial (or more precisely the A/D it is attached to (<16)
        n_measurments: number of repeated measurements to be taken (<10000)
        dt: time lag between measurements (<10000 ms)
        '''
        analog_pin = self.vial_to_pin(vial)
        mean_val, std_val, cstr= self.measure_voltage_pin( analog_pin, n_measurements, dt, switch_light_off)
        return self.voltage_to_OD(vial, mean_val, std_val)

    def measure_voltage(self,vial, n_measurements=1, dt=10, switch_light_off=True):
        analog_pin = self.vial_to_pin(vial)
        return self.measure_voltage_pin(analog_pin, n_measurements, dt, switch_light_off)

    def measure_voltage_pin(self, analog_pin, n_measurements=1, dt=10, switch_light_off=True):
        '''
        measure the voltage at specified pin n_measurement times with a time lag
        of dt milli seconds between measurements.
        params:
        ser: open serial port to communicate with the arduino
        vial: number of the vial (or more precisely the A/D it is attached to (<16)
        n_measurments: number of repeated measurements to be taken (<10000)
        dt: time lag between measurements (<10000 ms)
        '''
        if self.ser.isOpen():
            self.switch_light(True) # switch IR LEDs on
            command_str = 'A'+'{number:0{width}d}'.format(number=analog_pin, width=2) \
                +'{number:0{width}d}'.format(number=n_measurements, width=4) \
                +'{number:0{width}d}'.format(number=dt, width=4) +'\n'

            bytes_written = self.atomic_serial_write(command_str)
            if debug:
                print(str(time.time())+" out: "+command_str[:-1] + ' bytes_written: '+str(bytes_written))

            # wait and read the response of the arduino
            time_delay = ((n_measurements-1)*dt + 10.0)*0.001  #seconds
            time.sleep(time_delay)
            if debug:
                print self.ser.inWaiting()
            measurement = self.atomic_serial_readline()
            if debug:
                print(str(time.time())+" in: "+measurement)

            if switch_light_off:
                self.switch_light(False) # switch IR LEDs off
            # parse the input
            entries = measurement.split()

            if len(entries)>3 and entries[0]=='A' and int(entries[1])==analog_pin:
                return float(entries[2]), math.sqrt(float(entries[3])), command_str
            else:
                print(measurement)
                print("measure_voltage: received unexpected reply")
                return None, None, command_str
        else:
            print("Serial port is not open")

    def inject_volume(self, pump_type='pump2', pump_number=0, volume=0.1, conc=None):
        '''
        run a specific pump to inject a given volume
        params:
        pump_type: one of "medium", "pump1" and "pump3"
        pump_number: number of the pump to be switched on (0-15)
        volume: volume to be added in ml
        '''
        run_time = self.volume_to_time(pump_type, pump_number, volume)
        if run_time>0:
            # run the pump for calculated time
            self.run_pump(pump_type, pump_number, run_time)

    def remove_waste(self, volume=0.1):
        '''
        run the waste pump to remove the specified volume of waste
        params:
        volume: volume to be removed in ml
        '''
        run_time = self.volume_to_time('waste', 0, volume)
        if run_time>0:
            # run the pump for calculated time
            self.run_waste_pump(run_time)
        return run_time


    def run_pump(self,pump_type='pump2', pump_number=0, run_time=0.1):
        '''
        run a specific pump for a given amount of time
        params:
        pump_type: one of "medium", "pump1" and "pump3"
        pump_number: number of the pump to be switched on (0-15)
        time: time to run the pump in seconds
        '''
        if self.ser.isOpen():
            digital_pin = self.pump_to_pin(pump_type, pump_number)
            if run_time>0:
                # switch pump on
                self.switch_pin(digital_pin, True)
                # generate a time object to switch the pump off after
                # the time interval necessary to pump the required volume
                self.pump_off_threads[(pump_type,pump_number)] = threading.Timer(run_time, self.switch_pin, args=(digital_pin, False))
                self.pump_off_threads[(pump_type,pump_number)].start()
        else:
            print("Serial port is not open")
<<<<<<< HEAD
    def reset_arduino(self):
        self.swith_pin(reset_pin,False)
        time.sleep(2)
        self.switch_pin(reset_pin,True)
=======
    
    def reset_arduino(self):
	command_str = 'R'+'\n'
	self.atomic_serial_write(command_str)
	print("RRRRRRESET")	
>>>>>>> 8bbbe3359dbe0cb99be706dea07b6e9ed8d42853

    def run_waste_pump(self, run_time=0.1):
        '''
        run the waste pump for a given amount of time
        params:
        time: time to run the pump in seconds
        '''
        if self.ser.isOpen():
            digital_pin = suction_pump
            if run_time>0:
                # switch pump on
                self.switch_pin(digital_pin, False)
                # generate a time object to switch the pump off after
                # the time interval necessary to pump the required volume
                self.pump_off_threads[('waste pump',0)] = threading.Timer(run_time, self.switch_pin, args=(digital_pin, True))
                self.pump_off_threads[('waste pump',0)].start()
        else:
            print("Serial port is not open")


    def switch_pin(self, pin_number, state):
        '''
        switch the specified pin to the specified state
        '''
        if state:
            command_str = 'D'+'{number:0{width}d}'.format(number=pin_number, width=2) + '1\n'
        else:
            command_str = 'D'+'{number:0{width}d}'.format(number=pin_number, width=2) + '0\n'
        bytes_written = self.atomic_serial_write(command_str)

        if debug:
            print(str(time.time())+" out: "+command_str[:-1]+ ' bytes_written: '+str(bytes_written))

        # wait for reply and verify
        response = self.atomic_serial_readline()
        if debug:
            print(str(time.time())+" in: "+response)

        # parse the response and verify that the pump was set to the correct state
        entries = response.split()
        if len(entries)>2 and entries[0]=='D' and int(entries[1])==pin_number:
            if (entries[2]=='1')!=state:
                print("pin "+str(pin_number)+" in wrong state\nArduino response")
                print(response)
        else:
	    self.reset_arduino()
            print("switch_pin received bad response:")
            print response

    def switch_light(self, state):
        '''
        switch the light pin to the specified state
        '''
        #arduino high corresponds to open relais
        tmp_state = (1-state)==1
        if self.light_state!=state:
            self.switch_pin(light_switch, tmp_state)
            self.light_state = state


    def measure_temperature(self, switch_light_off=True):
        '''
        switch the specified pin to the specified state
        '''
        self.switch_light(True)
        command_str = 'C\n'
        temperature_conversion_delay = 1.0
        bytes_written = self.atomic_serial_write(command_str)
        self.temperature_thread = threading.Timer(temperature_conversion_delay,
                                                  self.read_temperature,
                                                  args=(switch_light_off,))
        self.temperature_thread.start()

    def read_temperature(self, switch_light_off):
        #for some reason the first measurement is old
        command_str = 'T\n'
        bytes_written = self.atomic_serial_write(command_str)
        if debug:
            print(str(time.time())+" out: "+command_str[:-1]+ ' bytes_written: '+str(bytes_written))

        # wait for reply and verify
        response = self.atomic_serial_readline()
        if debug:
            print(str(time.time())+" in: "+response)

        entries = response.split()
        temp1, temp2 = float(entries[1]), float(entries[2])
        self.temperatures = (temp1, temp2)
        if debug:
            print "temperatures:",self.temperatures
        if switch_light_off:
            self.switch_light(False)


#################################################################
# END interface class
#################################################################

"""
def measure_self_heating(morb, vials = range(15), total_time = 180, dt = 1):
    '''
    expects and morbidostat as argument, measures voltage every
    dt seconds for a total of total_time seconds
    '''
    voltage = np.zeros((total_time//dt, len(vials)+1))
    t_start = time.time()
    for ti, t in enumerate(np.arange(0,total_time, dt)):
        time.sleep(max(0,t-(time.time()-t_start)))
        measurements = []
        print t, time.time()
        for vi,vial in enumerate(vials):
            measurements.append(morb.measure_voltage(vial, n_measurements=1,
                                                     dt=0,switch_light_off=False)[0])
        if ti<voltage.shape[0]:
            voltage[ti,0]=t
            voltage[ti,1:] = measurements
    morb.switch_light(False)
    return voltage

def measure_recovery(morb, vials = range(15), total_time = 180, dt = 5):
    '''
    expects and morbidostat as argument, measures voltage every
    dt seconds for a total of total_time seconds
    '''
    voltage = np.zeros((total_time//dt, len(vials)+1))
    t_start = time.time()
    for ti, t in enumerate(np.arange(0,total_time, dt)):
        time.sleep(max(0,t-(time.time()-t_start)))
        measurements = []
        print t, time.time()
        for vi,vial in enumerate(vials):
            measurements.append(morb.measure_voltage(vial,dt=0, switch_light_off=False)[0])
        morb.switch_light(False)
        if ti<voltage.shape[0]:
            voltage[ti,0]=t
            voltage[ti,1:] = measurements
    return voltage

def take_temperature_profile(morb, total_time = 600, dt=10):
    temperatures = np.zeros((total_time//dt, 3))
    t_start = time.time()
    for ti, t in enumerate(np.arange(0,total_time, dt)):
        morb.measure_temperature()
        time.sleep(2)
        time.sleep(max(0,t-(time.time()-t_start)))
        print t, morb.temperatures
        if ti<temperatures.shape[0]:
            temperatures[ti,0]=t
            temperatures[ti,1:] = morb.temperatures
    return temperatures
"""

