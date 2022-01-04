# Morbidostat user manual

### 1. OD CALIBRATION:

Type the following:
```
cd python_src
ipython --pylab
```

An Ipython shell will start,
in the shell, type:
```
from morbidostat_experiment import *
```
The latter imports the necessary functions.
then type:
```
calibrate_OD()
```
You will be prompted for the OD of the standard used, enter a number,
following that, confirm that the vial is placed in the correct receptible by pressing enter
repeat for 1-15
repeat for all available OD standards (at least 2)
after all standards have been measured, press q

regression statistics will be printed and a figure should open showing the gauge curves.
if figure doesn't open, type
```
import matplotlib.pyplot as plt
plt.show()
```
the routine will save a file OD_calibration.dat in python_src
and a file voltage_measurements_YYYYMMDD.dat in the data directory


######################################################################
### 2.0 DISPLAYING EXPERIMENTS

1. Open a new terminal by right click on the Terminal button on the left
2. run
```
./display.sh data/EXPERIMENT_FOLDER
```
in the shell
3. A figure will open showing the OD of all measured vials and the temperature trajectory
4. to update, type:
```
morb_monitor.update_all()
```
5. To change the time window shown in the figure, type
```
morb_monitor.data_range = number_of_seconds_you_want_to_see
morb_monitor.update_all()
```
######################################################################
### 3.0 RUNNING AN EXPERIMENT

1. Open a new terminal by right click on the Terminal button on the left
2. type:
```
./experiment.sh
```
3. two windows will open. Choose the type of experiment in the small one, and press "DONE".
4. Select the "PARAMETERS" button. A dialog will open
5. To select the active vials, click on vial selector. Uncheck any vials not in use and press "DONE".
6. Start the experiment by pressing "START"



#####################################################################
### 4.0 adding changes to the version control (i.e. after OD calibration)

1. Type:
```
git commit -a -m "A useful message explaining why this change is necessary"
```

################################################################
### 5.0 Pump calibration
```
cd python_src
ipython --pylab
```

The latter imports the necessary functions.
Then type (choose between pump1, pump2, and pump3):
```
pump_type = 'pump1'

from morbidostat_experiment import *
mymorb = morbidostat()
mymorb.run_all_pumps(pump_type, 200)
```
**Make sure all tubing is filled with liquid and a steady stream of drops enters each vial**
Empty all vials

Set pump time
```
dt=200

calibrate_pumps(mymorb, pump_type, dt=dt)
```
