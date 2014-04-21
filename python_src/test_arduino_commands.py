import arduino_interface as M
import time

# initialize an instance of the morbidostat.
morb = M.morbidostat()

# if it was found on the serial port, loop over all 
# pumps and switch them on for a few seconds
if morb.morbidostat_OK:
    m,v,c = morb.measure_voltage(1, 10, 10)
    for pump_type in ['medium','drug A', 'drug B']:        
        for pin in range(15):
            morb.run_pump(pump_type, pin, 1)
            time.sleep(1.2)

else:
    print("Initializing morbidostat failed")


# run the waste pump for 4 seconds
morb.run_waste_pump(4)

# close the serial port
morb.disconnect()
