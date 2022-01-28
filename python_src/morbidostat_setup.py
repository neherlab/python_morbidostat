from morbidostat_experiment import morbidostat
import yaml


def convert_time_to_seconds(dictionary):
    """Converts days, hours, minute values into seconds.

    Args:
        Input dictionary containing time and unit keys
            time = Integer, number of days, hours, minutes, seconds
            unit = String with unit in days, hours, minutes,
            and seconds (d, h, m, s)

    Returns:
        Time in seconds as integer
    """
    time_to_seconds = {"s": 1, 'm': 60, "h": 3600, "d": 60*60*24}
    try:
        return int(dictionary['value'])*int(time_to_seconds[dictionary['unit']])
    except:
        raise ValueError(f'Cannot convert time, received the following parameters {dictionary}')

def pkpd_convert_time(dictionary):
    """Converts days, hours, minute values into seconds for the pkpd program.

    Args:
        Input dictionary containing time and unit keys.
            time = Integer, number of days, hours, minutes, seconds.
            unit = String with unit in days, hours, minutes, and seconds (d, h, m, s).

    Returns:
        Time in seconds as integer list.
    """
    time_to_seconds = {"s":1, 'm':60, "h": 3600, "d": 60*60*24}
    pkpd_timepoints_list = []

    try:
        for timepoint in dictionary.keys():
            pkpd_timepoints_list.append(timepoint*time_to_seconds[dictionary[timepoint]])
        return pkpd_timepoints_list
    except:
        raise ValueError(f'Cannot convert pkpd time, received the following parameters {dictionary}')


if __name__ == '__main__':
    import argparse, shutil
    parser = argparse.ArgumentParser(
            description='Instantiates a morbidostat')
    parser.add_argument('--config', required = True, type = str,  help ="YML config file")
    parser.add_argument('--pkpd', required = False, type = str, help ="pkpd config")
    parser.add_argument('--nostart', action="store_true", default = False,
                                    help ="start recording on launch")
    parser.add_argument('--out', required = False, type = str,  help ="outpath")
    params = parser.parse_args()

    with open(params.config, 'r') as fh:
        run_params = yaml.safe_load(fh)

    if run_params['experiment']['pkpd'] == True:
        with open(params.pkpd, 'r') as fi:
            pkpd_params = yaml.safe_load(fi)
        pkpd_time = pkpd_convert_time({item['time']:item['unit'] for item in pkpd_params['timepoints']})
        relative_curve_form = [item['relative_curve_form'] for item in pkpd_params['timepoints']]
        pkpd_peak_conc = {x['vial_number']-1:x['conc_max'] for x in pkpd_params['pkpd_peak_conc']}

        pkpd_burn_in_time = pkpd_params.get('burn_in_seconds',0)
        pkpd_burn_in_conc = pkpd_params.get('burn_in_concentration', 0)

    else:
        pkpd_time = 0
        relative_curve_form = 0
        pkpd_burn_in_time = 0
        pkpd_burn_in_conc = 0


    run_params["vials"].sort(key=lambda x:x["number"])
    bug_name = run_params['experiment']['bacteria']['name']+":"+run_params['experiment']['bacteria']['strain']

    morb = morbidostat(vials = [v["number"]-1 for v in run_params['vials']],
                    experiment_duration = convert_time_to_seconds(run_params['experiment']['total_duration']),
                    cycle_dt = convert_time_to_seconds(run_params['experiment']['cycle_duration']),
                    OD_dt = convert_time_to_seconds(run_params['experiment']['OD_duration']),
                    dilution_factor = run_params['experiment']['dilution'],
                    target_OD = run_params['experiment']['target_OD'],
                    bug = bug_name,
                    experiment_name = run_params['experiment']['name'],
                    drugs = list(run_params['drugs'].keys()),
                    mics = [item["mic"] for item in run_params["drugs"].values()],
                    bottles = [item for item in run_params['bottles'].keys()],
                    pkpd_time = pkpd_time,
                    relative_curve_form = relative_curve_form,
                    pkpd_burn_in_time = pkpd_burn_in_time,
                    pkpd_burn_in_conc = pkpd_burn_in_conc,
                    pkpd_peak_conc = pkpd_peak_conc
                    )


    morb.set_vial_properties({vial['number']-1:{"feedback": vial['program'], 'bottles': vial['bottles'], 'feedback_drug': vial['drug']} for vial in run_params['vials']})
    morb.debug=False

    morb.drug_units = [run_params["drugs"][drug]['unit'] for drug in morb.drugs]

    for bottle in morb.bottles:
        print(run_params['bottles'][bottle]['concentration'])
        morb.set_drug_concentrations(bottle, run_params['bottles'][bottle]['concentration'], initial=True)

    if not params.nostart:
        morb.start_experiment()
        shutil.copy(params.config, morb.base_name+'/example.yml')
