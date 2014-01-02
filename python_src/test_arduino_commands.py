import arduino_interface as M
import time

morb = M.morbidostat()

if morb.morbidostat_OK:
    m,v,c = morb.measure_voltage(1, 10, 10)
    for pump_type in ['medium', 'drugA', 'drugB']:        
        for pin in range(105):
            morb.run_pump(pump_type, pin, 1)
            time.sleep(1.2)

else:
    print("Initializing morbidostat failed")

