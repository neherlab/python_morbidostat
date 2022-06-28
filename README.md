<p align="center"><img src="misc/Element 2.png" alt="Morbidostat" width="600"></p>

A morbidostat is an automated continuous culture machine. With wich one can study the emergence of bacterial drug tolerance and resistance over time. [Erdal Toprak et al.](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3708598/)

This code repository drives the current version of the morbidostat of the NeherLab ([Biozentrum, University of Basel](https://www.biozentrum.unibas.ch/research/research-groups/research-groups-a-z/overview/unit/research-group-richard-neher)). It controls the pumps, optical density measurements (OD), waste pumps and structures them into cyclic procedures.

## Morbidostat user manual

### Table of contents
* [1. Starting a morbidostat run](1.-STARTING-A-MORBIDOSTAT-RUN)
    *[a. Classic morbidostat experiments](a.-Classic-morbidostat-experiments)
    *[b. Pharmacokinetic, pharmacodynamic expeiments (PKPD)](b.-Pharmacokinetic,-pharmacodynamic-experiments-(PKPD))
* [2. Displaying experiments](2.-DISPLAYING-EXPERIMENTS)
* [3. Optical density (OD) calibration](3.-OPTICAL-DENSITY-(OD)-CALIBRATION)
* [4. Pump calibration](4.-PUMP-CALIBRATION)
* [5. Additional commands](5.-ADDITIONAL-COMMANDS)
    *[5.1. Classic morbidostat experiments](5.1.-Change-dilution-factor-during-a-run:)
    *[5.2. Classic morbidostat experiments](5.2.-Change-target-OD-during-a-run:)
    *[5.3. Classic morbidostat experiments](5.3.-Change-cycle-time-during-a-run:)
    *[5.4. Classic morbidostat experiments](5.4.-Interrupt-and-resume-an-experiment-during-a-run:)
    *[5.5. Classic morbidostat experiments](5.5.-Stopp-an-experiment:)
    *[5.6. Classic morbidostat experiments](5.6.-Change-drug-concentration-of-input-bottles-during-a-run:)
    *[5.7. Classic morbidostat experiments](5.7.-Change-MIC-of-the-strain-during-a-run:)
    *[5.8. Classic morbidostat experiments](5.8.-Reset-vial-concentrations-during-a-run:)
* [6. Starting a morbidostat run](6.-ADDING-CHANGES-TO-THE-VERSION-CONTROL-(I.E-AFTER-OD-CALIBRATION))


#### 1. STARTING A MORBIDOSTAT RUN

Clone the repository onto the computer which is controlling the morbidostat (Or any other computer for using the simulation mode without morbidostat).

Open a terminal and navigate into the python_morbidostat folder:
```
cd python_morbidostat
```

Start Ipython:
```
ipython --pylab
```

**a. Classic morbidostat experiments**

Set parameters using the example.yml file. (pkpd must be set to False)

Next, run the following command inside the Ipython environment:
```
run python_src/morbidostat_setup.py --config example.yml
```

**b. Pharmacokinetic, pharmacodynamic experiments (PKPD)**

Set parameters using the example.yml file. (pkpd must be set to True)

> Now also set the additional parameters inside the pkpd_config.yml

Next, run the following command inside the Ipython environment:
```
run python_src/morbidostat_setup.py --config example.yml --pkpd pjpd_config.yml
```

#### 2. DISPLAYING EXPERIMENTS

1. Open a new terminal shell by a right click on the Terminal button on the left.
2. Again navigate to the python_morbidostat folder.
2. Run the following command in the new shell:
```
./display.sh data/<EXPERIMENT_FOLDER> <ANTIBIOTIC_USED>
```
3. A figure will open showing the OD of all measured vials and the temperature trajectory. (Red line = Antibiotic concentration, Blue line = OD)
4. To update, type (inside the terminal shell):
```
morb_monitor.update_all()
```
5. To change the time window shown in the figure, type:
```
morb_monitor.data_range = number_of_seconds_you_want_to_see
morb_monitor.update_all()
```
#### 3. OPTICAL DENSITY (OD) CALIBRATION

Type the following:
```
cd python_src
ipython --pylab
```

An Ipython shell will open.
In the shell, type:
```
from morbidostat_experiment import *
```
The latter imports the necessary functions.
Then type:
```
calibrate_OD()
```
You will be prompted for the OD of the standard used, enter a number,
Following that, confirm that the vial is placed in the correct receptible by pressing enter.
Repeat for 1-15.
Repeat for all available OD standards (at least 2).
After all standards have been measured, press q.

Regression statistics will be printed and a figure should open showing the gauge curves.
If figure doesn't open, type:
```
import matplotlib.pyplot as plt
plt.show()
```
The routine will save a file OD_calibration.dat in python_src,
and a file voltage_measurements_YYYYMMDD.dat in the data directory

#### 4. PUMP CALIBRATION
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

Empty all vials.

Set pump time:
```
dt=200

calibrate_pumps(mymorb, pump_type, dt=dt)
```
#### 5. ADDITIONAL COMMANDS
These commands can be typed into the terminal shell of the running morbidostat program.

5.1. Change dilution factor during a run:
'''
morb.dilution_factor = x
'''

5.2. Change target OD during a run:
'''
morb.target_OD = x
'''

5.3. Change cycle time during a run:
'''
morb.cycle_dt = x
'''

5.4. Interrupt and resume an experiment during a run:

Useful during media, or antibiotic bottle exchange.

'''
morb.interrupt_experiment()

morb.resume_experiment()
'''

5.5. Stopp an experiment:
'''
morb.stop_experiment()
'''

5.6. Change drug concentration of input bottles during a run:

a. Change the first bottle:
'''
morb..drug_concentrations[0][0] = x
'''

b. Change the second bottle:
'''
morb..drug_concentrations[1][0] = x
'''

c. Change the third bottle:
'''
morb..drug_concentrations[2][0] = x
'''

5.7. Change MIC of the strain during a run:
'''
morb.mics[0] = x
'''

5.8. Reset vial concentrations during a run:

Sets all vial concentrations to 0.

'''
morb.reset_concentrations()
'''

#### 6. ADDING CHANGES TO THE VERSION CONTROL (I.E. AFTER OD CALIBRATION)

Type:

```
git commit -a -m "A useful message explaining why this change is necessary"
```

