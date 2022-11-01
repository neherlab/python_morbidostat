# Script based on morbidostat interface by Richard Neher
from __future__ import absolute_import, division, print_function, \
                                                    unicode_literals
import time
import os
import numpy as np

# Import ADCPi
try:
    from ADCPi import ADCPi
except ImportError:
    print("Failed to import ADCPi from python system path")
    print("Importing from parent folder instead")
    try:
        import sys
        sys.path.append('..')
        from ADCPi import ADCPi
    except ImportError:
        raise ImportError(
            "Failed to import library from parent folder")

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

# #############
# # IO Zero I2C board addresses (Have to be changed on the boards)
# #############

# For pumps1: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
i2c_IO_board01 = IOZero32(0x20)
# For pumps2: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
i2c_IO_board02 = IOZero32(0x21)
# For pumps3: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
i2c_IO_board03 = IOZero32(0x20)
# i2c_IO_board03 = IOZero32(0x23)

# #############
# # ADC Pi I2C board addresses (Have to be changed on the boards)
# #############

# For vials 1-8
ADC_1 = ADCPi(0x68, 0x69, 12)
# For vials 9-15
ADC_2 = ADCPi(0x68, 0x69, 12)
# ADC_2 = ADCPi(0x6A, 0x6B, 12)

# #############
# # Waste pump pin address (Have to be changed on the boards)
# #############

waste_pump = 16  # waste pump

# #############
# # Pump array
# #############

pumps = {'pump1': [0, 1, 2, 3, 4, 5, 6, 7, 8,
                   9, 10, 11, 12, 13, 14],
         'pump2': [0, 1, 2, 3, 4, 5, 6, 7, 8,
                   9, 10, 11, 12, 13, 14],
         'pump3': [0, 1, 2, 3, 4, 5, 6, 7, 8,
                   9, 10, 11, 12, 13, 14],
         'waste': waste_pump}


# Assigns vials to ADC pins, example: Looking for pin of vial 12
# vials_to_pins_assignment[12] = 12
# Inside the functions we need to remember that the ADC boards only have 8
# addresses, so for these vials we need to subtract 8.

vials_to_pins_assignment = [1, 2, 3, 4, 5,
                            6, 7, 8, 9, 10,
                            11, 12, 13, 14, 15]

# #############
# # OD LED control array (Matrix for turning of LEDs)
# #############

led_pins = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]

# #############
# # morb_path = '/home/<user>/python_morbidostat/'
# #############
morb_path = '/'.join(os.path.realpath(__file__).split('/')[:-2])+'/'
print(morb_path)

# #############
# # Initialization (before class is called)
# #############

############
# load calibration parameters
############

# 1. Load path to pump calibration, and path to OD calibration
pump_calibration_file_base = morb_path+'python_src/pump_calibration'
OD_calibration_file_name = morb_path+'python_src/OD_calibration.dat'

# Initialize pump array
pump_calibration_params = {}
print("success")

# Now we create a matrix for every pump type (1, 2, 3)
# with 15 fields filled with 0.004
for pump_type in pumps:
    pump_calibration_params[pump_type] = 0.04*np.ones(15)

# Read in pump calibration data into dictionaries
for pump_type in pumps:
    fname = pump_calibration_file_base + '_' + pump_type + '.dat'
    if pump_type != 'waste':
        if os.path.isfile(fname):
            try:
                with open(fname) as fh:
                    for line in fh:
                        print(line)
                        if line[0] == '#':
                            continue
                        try:
                            entries = line.strip().split('\t')
                            vial = int(entries[0])
                            pump_rate = float(entries[1])
                            pump_calibration_params[pump_type][vial] = \
                                pump_rate
                        except:
                            print('error reading pump calibration', line)
                            pass
            except:
                print("error opening pump calibration, all pump calibration\
                       parameters set to NaN")
        else:
            print("no pump calibration file, all pump calibration parameters\
                   set to NaN")
    else:
        if os.path.isfile(fname):
            try:
                pump_calibration_params[pump_type] = np.array([np.loadtxt(fname)])
            except:
                print("error opening pump calibration, " +
                      "all pump calibration parameters set to 2.4ml/min")
                pump_calibration_params[pump_type] = np.array([0.04])
        else:
            print("no pump calibration file " + fname +
                  ", all pump calibration parameters set to 2.4 ml/min")
            pump_calibration_params[pump_type] = np.array([0.04])

# Here we read in OD calibration data into a list
if os.path.isfile(OD_calibration_file_name):
    try:
        voltage_to_OD_params = np.loadtxt(OD_calibration_file_name)
    except:
        print("error opening OD calibration file," +
              " all OD parameters set to zeros")
        voltage_to_OD_params = np.zeros(15, 2)
else:
    print("no OD calibration file, all OD parameters set to zero")
    voltage_to_OD_params = np.zeros((15, 2))

# #############
# # Define morbidostat class that defines command to work with the device
# #############


class morbidostat:
    def __init__(self):
        self.light_state = False  # Not implemented yet
        self.mixing_time = 5  # mixing time in seconds
        self.morbidostat_OK = True  # Always true for now, used to check if setting up arduino/rasp went well

    # Volume to time
    def volume_to_time(self, pump_type, pump, volume):
        """ Determines how much time a volume takes to pump.

            Looks into dictionary pump type, to select a pump (Number 0 to 14),
            then devides the to be pumped volume through the pump rate of the
            selected pump in the pump calibration file.
            This gives the time in s.

            Args:
                pump_type: str either pump1, pump2, or pump3
                pump: int between 0 and 14 or 15 for the waste pump
                volume: float in ml

            Results:
                time to pump the volume: float
        """
        if pump_type in pump_calibration_params:
            if pump < len(pump_calibration_params[pump_type]):
                return volume*pump_calibration_params[pump_type][pump]
            else:
                print("invalid pump number", pump, 'only ',
                      len(pump_calibration_params[pump_type]),
                      'calibration parameters')
                return 0
        else:
            print("invalid pump_type", pump_type, 'not in',
                  list(pump_calibration_params.keys()))
            return 0

    # Wait untion mixed
    def wait_until_mixed(self, run_time):
        """ Waits while pumps are on.

        Waits for the completion of all pumps.
        """
        time.sleep(run_time + self.mixing_time)

    # Pump to pin
    def pump_to_pin(self, pump_type, pump_number):
        """ To test if pump type and number are reasonable

            Args:
                pump_type: str pump1, pump2, pump3
                pump_number: int between 0, 14

        """
        assert pump_type in pumps, "Bad pump type: "+str(pump_type)
        assert pump_number >= 0 and pump_number < 15, "Bad pump number, got "\
               + str(pump_number)
        return pumps[pump_type][pump_number]

    # Vial to pin
    def vial_to_pin(self, vial):
        """
        Needs to change
        """

        vial = vial + 1  # Adds plus 1 to all vials, needs to change

        assert vial <= 15, "Maximal vial number is 15, got "+str(vial)
        assert vial != 0, "Vial number cannot be 0, must be between 1 and 15"
        return vials_to_pins_assignment[vial-1]

    # Voltage to OD
    def voltage_to_OD(self, vial, mean_val, std_val):
        """ Converts voltage read in to OD via calibration

            Converts voltage from pin into OD value, by multiplying the slope
            that was measured during the calibration with the measured voltage.
            Then it adds the standard deviation also from the
            calibration to it. The function also calculates
            the std individually.

            Args:
                vial: int between 0 and 14
                mean_val: int measured voltage
                std_val: int measured std

            Results:

        """
        if mean_val is None:
            print("Got None instead of an AD output for vial", vial)
            return 0, 0
        else:
            ODval = voltage_to_OD_params[vial, 0]*mean_val + \
                    voltage_to_OD_params[vial, 1]
            ODstd = voltage_to_OD_params[vial, 0]*std_val
            return max(ODval, 0.0001), ODstd

    # Not done: measure OD
    def measure_OD(self, vial, n_measurements=1, dt=10, switch_light_off=True):
        """ Measures OD from raspberry pi pin.

            Measure the OD at the specified vial n_measurement times with a
            time lag of dt milli seconds between measurements.

            Args:
                ser: open serial port to communicate with the arduino
                vial: number of the vial (or more precisely the A/D it is
                      attached to (<16))
                n_measurments: number of repeated measurements to
                               be taken (<10000)
                dt: time lag between measurements (<10000 ms)
        """

        adc_channel = self.vial_to_pin(vial)
        mean_val, std_val = \
            self.measure_voltage_pin(adc_channel, n_measurements,
                                     dt, switch_light_off)
        return self.voltage_to_OD(vial, mean_val, std_val)

    # Not done: Measure voltage
    def measure_voltage(self, vial, n_measurements=1, dt=10,
                        switch_light_off=True):
        """
        Not done yet, add description here
        """
        adc_channel = self.vial_to_pin(vial)
        return self.measure_voltage_pin(adc_channel, n_measurements,
                                        dt, switch_light_off=True)

    # Not done: measure voltage pin
    def measure_voltage_pin(self, adc_channel, n_measurements=1, dt=10,
                            switch_light_off=True):
        """
        Needs to change

        Measure the voltage at specified pin n_measurement times with a time
        lag of dt milli seconds between measurements.
        params:
        ser: open serial port to communicate with the arduino
        vial: number of the vial (or more precisely
              the A/D it is attached to (<16)
        n_measurments: number of repeated measurements to be taken (<10000)
        dt: time lag between measurements (<10000 ms)
        """

        stored_measurements = []

        # Read the voltage measurement
        if adc_channel > 0 and adc_channel <= 8:
            for measurements in range(0, n_measurements, 1):
                stored_measurements.append(ADC_1.read_voltage(adc_channel))
                time_delay = ((n_measurements-1)*dt + 10.0)*0.001  # seconds
                time.sleep(time_delay)
            return np.mean(stored_measurements), np.std(stored_measurements)
        elif adc_channel > 8 and adc_channel <= 16:
            adc_channel = adc_channel-8
            for measurements in range(0, n_measurements, 1):
                stored_measurements.append(ADC_2.read_voltage(adc_channel))
                time_delay = ((n_measurements-1)*dt + 10.0)*0.001  # seconds
                time.sleep(time_delay)
            return np.mean(stored_measurements), np.std(stored_measurements)
        else:
            print("Received non-valid adc_channel (Not between 1 and 16)")

    # Not done: Inject volume
    def inject_volume(self, pump_type='pump2', pump_number=0, volume=0.1,
                      conc=None):
        """
        Needs to change

        run a specific pump to inject a given volume
        params:
        pump_type: one of "pump1", "pump2" and "pump3"
        pump_number: number of the pump to be switched on (0-15)
        volume: volume to be added in ml
        """
        run_time = self.volume_to_time(pump_type, pump_number, volume)
        if run_time > 0:
            # run the pump for calculated time
            self.run_pump(pump_type, pump_number, run_time)

# Not done: Remove waste
    def remove_waste(self, volume=0.1):
        """
        Run the waste pump to remove the specified volume of waste
        params:
        volume: volume to be removed in ml
        """
        run_time = self.volume_to_time('waste', 0, volume)
        if run_time > 0:
            self.run_waste_pump(run_time)
        return run_time

    # Not done: run pump
    def run_pump(self, pump_type='pump2', pump_number=0, run_time=0.1):
        """
        Needs to change

        Run a specific pump for a given amount of time
        params:
        pump_type: one of "medium", "pump1" and "pump3"
        pump_number: number of the pump to be switched on (0-15)
        time: time to run the pump in seconds
        """
        if pump_type == 'pump1':
            if i2c_IO_board01.get_pin_direction(pump_number) == 1:
                i2c_IO_board01.set_pin_direction(pump_number, 0x00)
                i2c_IO_board01.write_pin(pump_number, 1)
                time.sleep(run_time)
                i2c_IO_board01.write_pin(pump_number, 0)
            else:
                i2c_IO_board01.write_pin(pump_number, 1)
                time.sleep(run_time)
                i2c_IO_board01.write_pin(pump_number, 0)
        elif pump_type == 'pump2':
            if i2c_IO_board02.get_pin_direction(pump_number) == 1:
                i2c_IO_board02.set_pin_direction(pump_number, 0x00)
                i2c_IO_board02.write_pin(pump_number, 1)
                time.sleep(run_time)
                i2c_IO_board02.write_pin(pump_number, 0)
            else:
                i2c_IO_board02.write_pin(pump_number, 1)
                time.sleep(run_time)
                i2c_IO_board02.write_pin(pump_number, 0)
        elif pump_type == 'pump3':
            if i2c_IO_board03.get_pin_direction(pump_number) == 1:
                i2c_IO_board03.set_pin_direction(pump_number, 0x00)
                i2c_IO_board03.write_pin(pump_number, 1)
                time.sleep(run_time)
                i2c_IO_board03.write_pin(pump_number, 0)
            else:
                i2c_IO_board03.write_pin(pump_number, 1)
                time.sleep(run_time)
                i2c_IO_board03.write_pin(pump_number, 0)
        else:
            print("Error: No correct pump type in function run_pump")

    # Not done: run waste pump
    def run_waste_pump(self, run_time=0.1):
        if i2c_IO_board01.get_pin_direction(16) == 1:
            i2c_IO_board01.set_pin_direction(16, 0x00)
            i2c_IO_board01.write_pin(16, 1)
            time.sleep(run_time)
            i2c_IO_board01.write_pin(16, 0)
        elif i2c_IO_board01.get_pin_direction(16) == 0:
            i2c_IO_board01.write_pin(16, 1)
            time.sleep(run_time)
            i2c_IO_board01.write_pin(16, 0)
        else:
            print("Error: Pumping waste function failed")

#         ### Not done: reset arduino
#         def reset_arduino(self):
#             """
#             Change to reset raspberry pi
#             """
#             print('Not done yet')

#         ### Not done: switch pin
#         def switch_pin(self, pin_number, state):
#             """
#             Needs to change
#             """
#             print('Not done yet')

#         ### Not done: switch light
#         def switch_light(self, state):
#             print('Not done yet')

#         # ### Not done: Not really needed
#         # def measure_temperature(self, switch_light_off=True):
#         #     print('Not done yet')

#         # ### Not done: Atomic serial writer
#         # def read_temperature(self, switch_light_off):
#         #     print('Not done yet')
