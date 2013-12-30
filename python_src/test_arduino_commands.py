import arduino_interface as morb
import time

ser = morb.serial_setup()


if ser:
    m,v,c = morb.measure_voltage(ser, 1, 10, 10)
    #morb.run_pump(ser, 'medium', 2, 0.1)
    #morb.run_pump(ser, 'medium', 3, 0.6)
else:
    print("serial port not available")

for pin in range(30,40):
    print pin
    morb.run_pump(ser, 'medium', pin, 1)
    time.sleep(1.2)

#for i in xrange(10000):
#    m,v,c = morb.measure_voltage(ser, 0, 10, 10)
#    print i, m, v
#    time.sleep(0.5)
#
ser.close()
