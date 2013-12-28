import arduino_interface as morb
import time
import numpy as np


ser = morb.serial_setup()
vials_to_calibrate = range(1)
calibration_curves = {}
n_measurements = 10

while True:
    current_OD = raw_input('Enter OD of sample [X to abort]: ')
    if current_OD in ['X', 'x']:
        break
    else:
        try:
            OD = float(current_OD)
            calibration_curves[OD] = np.zeros((max(vials_to_calibrate)+1, 2))
            print("Measuring voltage in all vials for OD "+str(OD))
            try:
                for vial in vials_to_calibrate:
                    print('Place vial in receptible '+str(vial))
                    user_in = raw_input('press Enter when done [X to abort]: ')
                    if user_in=='':
                        voltage = np.zeros((n_measurements,2))
                        for mi in xrange(n_measurements):
                            voltage[mi,:] = morb.measure_voltage(ser, vial, 10, 10)[:2]
                            calibration_curves[OD][vial]=[voltage[:,0].mean(), voltage[:,0].std()]
            except:
                print('morbidostat problem')
            print calibration_curves[OD], voltage
        except:
            print("Enter valid float")
        
