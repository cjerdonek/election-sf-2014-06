"""
Usage: python analyze.py

The above needs to be run from the root of the source repository.

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
# Uses the precinct name.
SOV_PATH = "data/SOV_JUN2014_Governor.csv"

KEYS = [
    'counted_in_person',
    'counted_vbm',
    'challenged_vbm',
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
            data['counted_in_person'] += int(row[8])

            # 2) Process VBM precinct total.
            # For example: "Pct 1101 - VBM Reporting"
            row = reader.next()
            parts = row[6].split(" - ")
            if parts[1] != 'VBM Reporting':
                raise AssertionError(repr(parts))
            if parts[0][4:] != precinct_name:
                raise AssertionError(repr(parts))
            data['counted_vbm'] += int(row[8])
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
            precinct_id, challenged = row[0], row[10]
            try:
                precinct_ids.remove(precinct_id)
            except KeyError:
                raise KeyError("%r not in: %r" % (precinct_id, precinct_ids))
            data = precinct_totals[precinct_id]
            data['challenged_vbm'] += int(challenged)

def make_nbhd_totals(precinct_to_nbhd, p_totals):
    """
    Return a dict mapping neighborhood names to dicts of totals.
    """
    nbhd_key = make_nbhd_key()

    # Initialize the neighborhood totals to zero.
    n_totals = {}
    for name in nbhd_key.values():
        n_totals[name] = dict.fromkeys(KEYS, 0)

    for precinct_id, p_data in p_totals.iteritems():
        nbhd_label = precinct_to_nbhd[precinct_id]
        nbhd_name = nbhd_key[nbhd_label]
        n_data = n_totals[nbhd_name]
        for k in KEYS:
            n_data[k] += p_data[k]

    return n_totals

def write_nbhd_totals(f, nbhd_totals):
    w = csv.writer(f)
    w.writerow(['precinct'] + KEYS)
    for nbhd in sorted(nbhd_totals.keys()):
        data = nbhd_totals[nbhd]
        w.writerow([nbhd] + [data[k] for k in KEYS])

def main():
    precinct_to_nbhd, precinct_name_to_id = parse_precinct_nbhd_file()
    precinct_ids = set(precinct_to_nbhd.keys())
    precinct_totals = initialize_precinct_totals(precinct_ids)

    # Calculate total in-person and absentees per precinct.
    process_sov(precinct_name_to_id, precinct_totals)

    process_challenged_vbm(precinct_totals)

    # Aggregate precinct totals by neighborhood.
    n_totals = make_nbhd_totals(precinct_to_nbhd, precinct_totals)

    write_nbhd_totals(sys.stdout, n_totals)

main()
