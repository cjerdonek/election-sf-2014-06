
import csv

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

KEYS = [
    'in_person',
    'absentee'
]


def make_pn_dict():
    """
    Return a dict mapping precinct ID to neighborhood name.
    """
    data = {}
    with open("data/Precinct-Neighborhoods_20140321.csv") as f:
        reader = csv.reader(f)
        # Skip the header row.
        reader.next()
        for row in reader:
            name, nbhd = row[1], row[7]
            if not name.startswith("Pct "):
                raise AssertionError(name)
            precinct = name[4:]  # truncate "Pct "
            if precinct in data:
                print "skipping precinct already in dict: %r" % precinct
                continue
            data[precinct] = nbhd
    return data

def initialize_precinct_data(precincts):
    p_data = {}
    for p in precincts:
        data = {}
        for k in KEYS:
            data[k] = 0
        p_data[p] = data
    return p_data

def process_sov(p_data):
    precincts = set(p_data.keys())

    with open("data/SOV_JUN2014_Governor.csv") as f:
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
            precinct = parts[0][4:]  # truncate "Pct "
            try:
                precincts.remove(precinct)
            except KeyError:
                raise KeyError("%r not in: %r" % (precinct, precincts))
            data = p_data[precinct]
            data['in_person'] += int(row[8])
            
            # 2) Process VBM precinct total.
            # For example: "Pct 1101 - VBM Reporting"
            row = reader.next()
            parts = row[6].split(" - ")
            if parts[1] != 'VBM Reporting':
                raise AssertionError(repr(parts))
            if parts[0][4:] != precinct:
                raise AssertionError(repr(parts))
            data['absentee'] += int(row[8])
    # Make sure all precincts were listed in the SOV file.
    assert not len(precincts)

def main():
    pn_dict = make_pn_dict()
    precincts = set(pn_dict.keys())
    p_data = initialize_precinct_data(precincts)
    process_sov(p_data)
    print p_data
    nbhds = set(pn_dict.values())
    for n in nbhds:
        print n

main()
