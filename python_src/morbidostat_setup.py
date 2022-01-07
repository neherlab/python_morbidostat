from morbidostat_experiment import morbidostat
import yaml

# def parse_meta(entries):
#     return {entries[0]:entries[1]}

# time_to_seconds = {"s":1, 'm':60, "h": 3600, "d": 60*60*24}

def convert_time_to_seconds(dictionary):
    """Converts days, hours, minute values into seconds.

    Args:
        Input dictionary containing time and unit keys
            time = Integer, number of days, hours, minutes, seconds
            unit = String with unit in days, hours, minutes, and seconds (d, h, m, s)

    Returns:
        Time in seconds as integer
    """
    time_to_seconds = {"s":1, 'm':60, "h": 3600, "d": 60*60*24}
    try:
        return int(dictionary['value'])*int(time_to_seconds[dictionary['unit']])
    except:
        raise ValueError(f'Cannot convert time, received the following parameters {dictionary}')


# def parse_times(entries):
#     k = entries[0]
#     if len(entries)>2 and entries[2] in time_to_seconds:
#         unit = time_to_seconds[entries[2]]
#     else:
#         unit = 1.0
#     return {k:int(float(entries[1])*unit)}

# def parse_parameters(entries):
#     return {entries[0]:float(entries[1])}

# def parse_drugs(entries):
#     # drugname, drug unit, drug concentration
#     return [entries[0], entries[1], float(entries[2])]

# def parse_bottles(entries):run_params['experiment']['cycle_duration']
# #     drugs = []
#     vials = {}
#     bottles = {}
#     with open(fname) as config:
#         parse_cat = None
#         for line in config:
#             entries = [x for x in line.strip().split(',') if x!=""]
#             if len(entries)==0:
#                 continue
#             elif entries[0][0]=='#':
#                 parse_cat = entries[0][1:]
#             elif entries[0]!="":
#                 if parse_cat=="meta":
#                     parameters.update(parse_meta(entries))
#                 elif parse_cat=="times":
#                     parameters.update(parse_times(entries))
#                 elif parse_cat=="parameters":
#                     parameters.update(parse_parameters(entries))
#                 elif parse_cat=="drugs":
#                     drugs.append(parse_drugs(entries))
#                 elif parse_cat=="bottles":
#                     bottles.update(parse_bottles(entries))
#                 elif parse_cat=="vials":
#                     vials.update(parse_vials(entries))

#     return parameters, drugs, vials, bottles


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
        pkpd_time = [item['time_in_seconds'] for item in pkpd_params['timepoints']]
        pkpd_conc = [item['concentration'] for item in pkpd_params['timepoints']]
    else:
        pkpd_time = 0
        pkpd_conc = 0


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
                    pkpd_conc = pkpd_conc
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
