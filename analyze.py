"""
Usage: python analyze.py

The above needs to be run from the root of the source repository.

The script writes its output to a file called out.csv.

"""

# Terminology notes:
#
# Each precinct has an ID and a name.  For example--
#
#   7041,Pct 7041 MB
#
# We need to keep track of this distinction because some data files use
# the ID and some use the name.


import csv
import sys

# Uses the precinct ID.
CHALLENGED_VBM_PATH = "data/Challenged_VBMs_June_2014.csv"
# Has the precinct ID and name.
PRECINCT_NEIGHBORHOOD_PATH = "data/Precinct-Neighborhoods_20140321.csv"
# Uses precinct ID.
PROVISIONAL_REPORT_PATH = "data/Provisional Ballot Report_June 2014.csv"
# Uses the precinct name.
SOV_PATH = "data/SOV_JUN2014_Governor.csv"

KEYS = [
    'in_person_counted',
    'vbm_counted',
    'vbm_uncounted',
    'provisional_cast',
    'provisional_uncounted',  # equivalent to "in_person_uncounted"
]

ALL_KEYS = [
    'all_cast',  # in_person_counted + vbm_counted + provisional_uncounted + vbm_uncounted
    'in_person_cast',  # in_person_counted + provisional_uncounted
    'vbm_cast',  # vbm_counted + vbm_uncounted
    'provisional_cast',
    'total_counted',  # in_person_counted + vbm_counted
    'in_person_counted',
    'vbm_counted',
    'total_uncounted',  # vbm_uncounted + provisional_uncounted
    'vbm_uncounted',
    'provisional_uncounted',
]

# This string maps neighborhood labels in the precinct-to-neighborhood
# file to more human-friendly names.
NEIGHBORHOODS = """
BAYVW/HTRSPT:BAYVIEW/HUNTERS POINT
CHINA:CHINATOWN
CVC CTR/DWTN:CIVIC CENTER/DOWNTOWN
DIAMD HTS:DIAMOND HEIGHTS
EXCELSIOR:EXCELSIOR (OUTER MISSION)
HAIGHT ASH:HAIGHT ASHBURY
INGLESIDE:INGLESIDE
INNER SUNSET:INNER SUNSET
LAKE MERCED:LAKE MERCED
LRL HTS/ANZA:LAUREL HEIGHTS/ANZA VISTA
MAR/PAC HTS:MARINA/PACIFIC HEIGHTS
MISSION:MISSION
N BERNAL HTS:NORTH BERNAL HTS
N EMBRCDRO:NORTH EMBARCADERO
NOE VALLEY:NOE VALLEY
PORTOLA:PORTOLA
POTRERO HILL:POTRERO HILL
RICHMOND:RICHMOND
S BERNAL HTS:SOUTH BERNAL HEIGHT
SECLF/PREHTS:SEA CLIFF/PRESIDIO HEIGHTS
SOMA:SOUTH OF MARKET
SUNSET:SUNSET
UPRMKT/EURKA:UPPER MARKET/EUREKA VALLEY
VISITA VLY:VISITATION VALLEY
W TWIN PKS:WEST OF TWIN PEAKS
WST ADDITION:WESTERN ADDITION
"""

def make_nbhd_key():
    """
    Return a dict mapping neighborhood labels to human-friendly names.
    """
    data = {}
    for s in NEIGHBORHOODS.strip().splitlines():
        label, name = s.split(":")
        data[label] = name
    return data

def parse_precinct_nbhd_file():
    """
    Return a dict mapping precinct ID to neighborhood label and a dict
    mapping precinct name to precinct ID.
    """
    precinct_to_nbhd = {}
    precinct_name_to_id = {}
    with open(PRECINCT_NEIGHBORHOOD_PATH) as f:
        reader = csv.reader(f)
        # Skip the header row.
        reader.next()
        for row in reader:
            precinct_id, precinct, nbhd_label = row[0], row[1], row[7]
            if not precinct.startswith("Pct "):
                raise AssertionError(row)
            precinct_name = precinct[4:]  # truncate "Pct "
            if precinct_id in precinct_to_nbhd:
                print "skipping: precinct ID already in dict: %r" % precinct_id
                continue
            precinct_to_nbhd[precinct_id] = nbhd_label
            precinct_name_to_id[precinct_name] = precinct_id
    return precinct_to_nbhd, precinct_name_to_id

def initialize_precinct_totals(precinct_ids):
    totals = {}
    for precinct_id in precinct_ids:
        data = {}
        for k in KEYS:
            data[k] = 0
        totals[precinct_id] = data
    return totals

def process_sov(precinct_name_to_id, precinct_totals):
    """
    Add SOV data to the given precinct totals.

    The SOV data contains counted in-person and counted VBM ballots.
    """
    precinct_ids = set(precinct_totals.keys())

    with open(SOV_PATH) as f:
        reader = csv.reader(f)
        # Skip the header row.
        reader.next()
        # The following rows come in pairs: two per precinct.
        for row in reader:
            # 1) Process in-person precinct total.
            # For example: "Pct 1154 MB - Election Day Reporting"
            parts = row[6].split(" - ")
            if parts[1] != 'Election Day Reporting':
                raise AssertionError(repr(parts))
            precinct_name = parts[0][4:]  # truncate "Pct "
            precinct_id = precinct_name_to_id[precinct_name]
            try:
                precinct_ids.remove(precinct_id)
            except KeyError:
                raise KeyError("%r not in: %r" % (precinct_id, precinct_ids))
            data = precinct_totals[precinct_id]
            data['in_person_counted'] += int(row[8])

            # 2) Process VBM precinct total.
            # For example: "Pct 1101 - VBM Reporting"
            row = reader.next()
            parts = row[6].split(" - ")
            if parts[1] != 'VBM Reporting':
                raise AssertionError(repr(parts))
            if parts[0][4:] != precinct_name:
                raise AssertionError(repr(parts))
            data['vbm_counted'] += int(row[8])
    # Make sure all precincts were listed in the SOV file.
    assert not len(precinct_ids)

def process_challenged_vbm(precinct_totals):
    """Add challenged VBM data to the given precinct totals."""
    precinct_ids = set(precinct_totals.keys())

    with open(CHALLENGED_VBM_PATH) as f:
        reader = csv.reader(f)
        # Skip the header row.
        reader.next()
        for row in reader:
            precinct_id, challenged = row[0], int(row[10])
            try:
                precinct_ids.remove(precinct_id)
            except KeyError:
                raise KeyError("%r not in: %r" % (precinct_id, precinct_ids))
            data = precinct_totals[precinct_id]
            data['vbm_uncounted'] += challenged

def process_provisionals(precinct_totals):
    """Add challenged VBM data to the given precinct totals."""
    precinct_ids = set(precinct_totals.keys())

    with open(PROVISIONAL_REPORT_PATH) as f:
        reader = csv.reader(f)
        # Skip the header row.
        reader.next()
        for row in reader:
            precinct, uncounted, cast = row[0], int(row[-3]), int(row[-1])
            precinct_id = precinct.split()[1]
            try:
                precinct_ids.remove(precinct_id)
            except KeyError:
                print "precinct ID not found: %r" % precinct_id
                if cast:
                    raise KeyError("%r not in: %r" % (precinct_id, precinct_ids))
                else:
                    # Skip the precinct if there were no totals.
                    # The provisional report seems to have extra empty
                    # precincts, e.g. precinct 9998.
                    continue
            data = precinct_totals[precinct_id]
            data['provisional_cast'] += int(cast)
            data['provisional_uncounted'] += int(uncounted)
    # Make sure all precincts were listed in the file.
    assert not len(precinct_ids)

def compute_extra_fields(precinct_totals):
    for data in precinct_totals.values():
        def subtotal(*keys):
            return sum(data[k] for k in keys)
        data['all_cast'] = subtotal('in_person_counted', 'vbm_counted',
                                    'provisional_uncounted', 'vbm_uncounted')
        data['in_person_cast'] = subtotal('in_person_counted', 'provisional_uncounted')
        data['vbm_cast'] = subtotal('vbm_counted', 'vbm_uncounted')
        data['total_counted'] = subtotal('in_person_counted', 'vbm_counted')
        data['total_uncounted'] = subtotal('vbm_uncounted', 'provisional_uncounted')

def make_nbhd_totals(precinct_to_nbhd, p_totals):
    """
    Return a dict mapping neighborhood names to dicts of totals.
    """
    nbhd_key = make_nbhd_key()

    # Initialize the neighborhood totals to zero.
    n_totals = {}
    for name in nbhd_key.values():
        n_totals[name] = dict.fromkeys(ALL_KEYS, 0)

    for precinct_id, p_data in p_totals.iteritems():
        nbhd_label = precinct_to_nbhd[precinct_id]
        nbhd_name = nbhd_key[nbhd_label]
        n_data = n_totals[nbhd_name]
        for k in ALL_KEYS:
            n_data[k] += p_data[k]

    return n_totals

def write_nbhd_totals(f, nbhd_totals):
    w = csv.writer(f)
    w.writerow(['Neighborhood'] + ALL_KEYS)

    for nbhd in sorted(nbhd_totals.keys()):
        data = nbhd_totals[nbhd]
        w.writerow([nbhd] + [data[k] for k in ALL_KEYS])

    # Add a totals row.
    totals = []
    for k in ALL_KEYS:
        total = sum(data[k] for data in nbhd_totals.values())
        totals.append(total)
    w.writerow(['TOTAL'] + totals)

def main():
    precinct_to_nbhd, precinct_name_to_id = parse_precinct_nbhd_file()
    precinct_ids = set(precinct_to_nbhd.keys())
    precinct_totals = initialize_precinct_totals(precinct_ids)

    # Now parse precinct totals.

    # In-person and VBMs counted per precinct.
    process_sov(precinct_name_to_id, precinct_totals)

    # VBMs challenged (i.e. not counted) per precinct.
    process_challenged_vbm(precinct_totals)

    # Provisionals (both counted and uncounted) per precinct.
    process_provisionals(precinct_totals)

    compute_extra_fields(precinct_totals)

    # Aggregate precinct totals by neighborhood.
    nbhd_totals = make_nbhd_totals(precinct_to_nbhd, precinct_totals)

    with open('out.csv', 'wb') as f:
        write_nbhd_totals(f, nbhd_totals)

main()
