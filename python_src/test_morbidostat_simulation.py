import morbidostat_experiment as me
import time

morb = me.morbidostat()

morb.start_experiment()
#morb.update_plot()

#while morb.cycle_counter<morb.n_cycles:
#    print morb.cycle_counter, morb.final_OD_estimate
#    time.sleep(1)


