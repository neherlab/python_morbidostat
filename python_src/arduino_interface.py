import time
import threading
import math
import serial

debug = False
baudrate = 9600
# arduino pin controlling the IR LEDs via a relais
light_switch = 53 
# dictionary mapping pumps to pins
pumps = {'medium': range(7,7+15), 
         'drug A': range(22,22+15),
         'drug B': range(38,38+15)}


class morbidostat:

    def __init__(self):
        self.connect()
        self.pump_off_threads = {}
        self.light_state = False

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
                self.ser = serial.Serial('/dev/ttyACM'+str(port_number), baudrate, timeout = 1.0)
                if self.ser.isOpen():
                    print("Serial /dev/ttyACM"+str(port_number)+" opened")
                    # wait a second to let the serial port get up to speed
                    time.sleep(1)
                    self.morbidostat_OK = True
                    try_next=False
            except:
                if i<10:
                    print("Serial /dev/ttyACM"+str(port_number)+" not available, trying next")
                    try_next=True
                else:
                    print("Opening serial port failed")
                    try_next=False
                self.morbidostat_OK = False
        return port_number

    def disconnect(self):
        '''
        close the serial port
        '''
        if self.ser.isOpen():
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
        return vial

    def voltage_to_OD(self,mean_val, std_val):
        return mean_val, std_val

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
        mean_val, std_val, cstr= self.measure_voltage( vial, n_measurements, dt, switch_light_off)
        return self.voltage_to_OD(mean_val, std_val)

    def measure_voltage(self, vial, n_measurements=1, dt=10, switch_light_off=True):
        '''
        measure the voltage at the specified vial n_measurement times with a time lag
        of dt milli seconds between measurements. 
        params:
        ser: open serial port to communicate with the arduino
        vial: number of the vial (or more precisely the A/D it is attached to (<16)
        n_measurments: number of repeated measurements to be taken (<10000)
        dt: time lag between measurements (<10000 ms)
        '''
        if self.ser.isOpen():
            self.switch_light(True) # switch IR LEDs on
            analog_pin = self.vial_to_pin(vial)
            command_str = 'A'+'{number:0{width}d}'.format(number=analog_pin, width=2) \
                +'{number:0{width}d}'.format(number=n_measurements, width=4) \
                +'{number:0{width}d}'.format(number=dt, width=4) +'\n'

            bytes_written = self.ser.write(command_str)
            if debug:
                print(str(time.time())+" out: "+command_str[:-1] + ' bytes_written: '+str(bytes_written)) 

            # wait and read the response of the arduino
            time_delay = ((n_measurements-1)*dt + 10.0)*0.001  #seconds
            time.sleep(time_delay)
            if debug:
                print self.ser.inWaiting()
            measurement = self.ser.readline()
            if debug:
                print(str(time.time())+" in: "+measurement) 

            # parse the input
            entries = measurement.split()

            if len(entries)>3 and entries[0]=='A' and int(entries[1])==analog_pin:
                return float(entries[2]), math.sqrt(float(entries[3])), command_str
            else:
                print(measurement)
                print("measure_voltage: received unexpected reply")
                return None, None, command_str
            if switch_light_off:  self.switch_light(False) # switch IR LEDs off
        else:
            print("Serial port is not open")

    def inject_volume(self, pump_type='medium', pump_number=0, volume=0.1):
        '''
        run a specific pump to inject a given volume
        params:
        ser: open serial port to communicate with the arduino
        pump_type: one of "medium", "drug A" and "drug B"
        pump_number: number of the pump to be switched on (0-15)
        volume: volume to be added in ml
        '''
        run_time = self.volume_to_time(volume, pump_type, pump_number)
        if run_time>0:
            # run the pump for calculated time
            self.run_pump(pump_type, pump_number, run_time)


    def run_pump(self,pump_type='medium', pump_number=0, run_time=0.1):
        '''
        run a specific pump for a given amount of time
        params:
        ser: open serial port to communicate with the arduino
        pump_type: one of "medium", "drug A" and "drug B"
        pump_number: number of the pump to be switched on (0-15)
        time: time to run the pump in seconds
        '''
        if self.ser.isOpen():
            digital_pin = self.pump_to_pin(pump_type, pump_number)
            if run_time>0:
                # switch pump on
                self.switch_pin(digital_pin, False)
                # generate a time object to switch the pump off after 
                # the time interval necessary to pump the required volume
                self.pump_off_threads[(pump_type,pump_number)] = threading.Timer(run_time, self.switch_pin, args=(digital_pin, True))
                self.pump_off_threads[(pump_type,pump_number)].start()
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
        bytes_written = self.ser.write(command_str)

        if debug:
            print(str(time.time())+" out: "+command_str[:-1]+ ' bytes_written: '+str(bytes_written)) 

        # wait for reply and verify
        response = self.ser.readline()
        if debug:
            print(str(time.time())+" in: "+response) 

        # parse the response and verify that the pump was set to the correct state
        entries = response.split()
        if len(entries)>2 and entries[0]=='D' and int(entries[1])==pin_number:
            if (entries[2]=='1')!=state:
                print("pin "+str(pin_number)+" in wrong state\nArduino response")
                print(response)
        else:
            print("switch_pin received bad response:")
            print response

    def switch_light(self, state):
        '''
        switch the light pin to the specified state
        '''
        if self.light_state!=state:
            self.switch_pin(light_switch, state)
