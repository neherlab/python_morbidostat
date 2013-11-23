import time
import threading
import math
import serial

pump_types = ['medium', 'drug A', 'drug B']
debug = False
baudrate = 9600

def serial_setup():
    for i in range(10):
        try:
            ser = serial.Serial('/dev/ttyACM'+str(i), baudrate, timeout = 1.0)
            if ser.isOpen():
                print("Serial /dev/ttyACM"+str(i)+" opened")
                # wait a second to let the serial port get up to speed
                time.sleep(1)
                return ser
        except:
            if i<9:
                print("Serial /dev/ttyACM"+str(i)+" not available, trying next")
            else:
                print("Opening serial port failed")


def pump_to_pin(pump_type, pump_number):
    try:
        return pump_types.index(pump_type)*15+pump_number
    except:
        print("pump_to_pin: error, bad input\n")
        print("arguments:" +' '.join(map(str, [pump_type, pump_number]))+'\n')

def vial_to_pin(vial):
    return vial

def voltage_to_OD(mean_val, std_val):
    return mean_val, std_val

def measure_OD(ser, vial, n_measurements=1, dt=10):
    '''
    measure the OD at the specified vial n_measurement times with a time lag
    of dt milli seconds between measurements. 
    params:
    ser: open serial port to communicate with the arduino
    vial: number of the vial (or more precisely the A/D it is attached to (<16)
    n_measurments: number of repeated measurements to be taken (<10000)
    dt: time lag between measurements (<10000 ms)
    '''
    mean_val, std_val, cstr= measure_voltage(ser, vial, n_measurements=1, dt=10)
    return voltage_to_OD(mean_val, std_val)

def measure_voltage(ser, vial, n_measurements=1, dt=10):
    '''
    measure the voltage at the specified vial n_measurement times with a time lag
    of dt milli seconds between measurements. 
    params:
    ser: open serial port to communicate with the arduino
    vial: number of the vial (or more precisely the A/D it is attached to (<16)
    n_measurments: number of repeated measurements to be taken (<10000)
    dt: time lag between measurements (<10000 ms)
    '''
    if ser.isOpen():
        analog_pin = vial_to_pin(vial)
        command_str = 'A'+'{number:0{width}d}'.format(number=analog_pin, width=2) \
            +'{number:0{width}d}'.format(number=n_measurements, width=4) \
            +'{number:0{width}d}'.format(number=dt, width=4) +'\n'

        bytes_written = ser.write(command_str)
        if debug:
            print(str(time.time())+" out: "+command_str[:-1] + ' bytes_written: '+str(bytes_written)) 
    
        # wait and read the response of the arduino
        time_delay = (n_measurements*dt + 10.0)*0.001  #seconds
        time.sleep(time_delay)
        print ser.inWaiting()
        measurement = ser.readline()
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
    else:
        print("Serial port is not open")

def inject_volume(ser, pump_type='medium', pump_number=0, volume=0.1):
    '''
    run a specific pump to inject a given volume
    params:
    ser: open serial port to communicate with the arduino
    pump_type: one of "medium", "drug A" and "drug B"
    pump_number: number of the pump to be switched on (0-15)
    volume: volume to be added in ml
    '''
    run_time = volume_to_time(volume, pump_type, pump_number)
    if run_time>0:
        # run the pump for calculated time
        run_pump(ser, pump_type, pump_number, run_time)


def run_pump(ser, pump_type='medium', pump_number=0, run_time=0.1):
    '''
    run a specific pump for a given amount of time
    params:
    ser: open serial port to communicate with the arduino
    pump_type: one of "medium", "drug A" and "drug B"
    pump_number: number of the pump to be switched on (0-15)
    time: time to run the pump in seconds
    '''
    if ser.isOpen():
        if pump_type in pump_types:
            digital_pin = pump_to_pin(pump_type, pump_number)
            if run_time>0:
                # switch pump on
                switch_pin(ser, digital_pin, True)
                # generate a time object to switch the pump off after 
                # the time interval necessary to pump the required volume
                pump_off = threading.Timer(run_time, switch_pin, args=(ser, digital_pin, False))
                pump_off.start()
    else:
        print("Serial port is not open")


def switch_pin(ser, pin_number, state):
    '''
    switch the specified bin to the specified state
    '''
    if state:
        command_str = 'P'+'{number:0{width}d}'.format(number=pin_number, width=2) + '1\n'
    else:
        command_str = 'P'+'{number:0{width}d}'.format(number=pin_number, width=2) + '0\n'
    bytes_written = ser.write(command_str)

    if debug:
        print(str(time.time())+" out: "+command_str[:-1]+ ' bytes_written: '+str(bytes_written)) 

    # wait for reply and verify
    response = ser.readline()
    if debug:
        print(str(time.time())+" in: "+response) 

    entries = response.split()
    if len(entries)>2 and entries[0]=='pump' and int(entries[1])==pin_number:
        if (entries[2]=='1')!=state:
            print("pump "+str(pin_number)+" in wrong state\nArduino response")
            print(response)
    else:
        print("switch_pin received bad response:")
        print response
