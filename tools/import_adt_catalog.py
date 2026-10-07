"""Build the distributable, traceable catalog. Never imports or executes ADT code."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def convert(path: Path, destination: Path):
    groups = defaultdict(list)
    for item in ET.parse(path).getroot().findall('Cable'):
        groups[item.findtext('Name').strip()].append(item)
    cables = []
    for name, items in groups.items():
        def constant(key):
            values = {float(item.findtext(key)) for item in items}
            if len(values) != 1:
                raise ValueError(f'{name}: nonconstant {key}')
            return values.pop()
        samples = sorted([[float(row.findtext(key)) for key in
                           ('Frequency', 'AttenuationdBm', 'Avpower')] for row in items])
        if len({s[0] for s in samples}) != len(samples):
            raise ValueError(f'{name}: duplicate frequency')
        cables.append(dict(name=name, kind='rigid' if 'Line' in name else 'cable',
                           velocity_factor=constant('VelocityFactor'),
                           impedance_ohm=constant('Impedance'),
                           peak_power_kw=constant('PeakPower'),
                           peak_voltage_v=constant('PeakVol'), samples=samples))
    payload = dict(version=1, source='ADT_PY/assets/original_adt/Rating/CableRating.xml',
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   sample_columns=['frequency_mhz', 'attenuation_db_100m', 'average_power_kw'],
                   cables=cables)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{len(cables)} models; {sum(len(c["samples"]) for c in cables)} samples; SHA256 {payload["sha256"]}')


if __name__ == '__main__':
    convert(Path(sys.argv[1]), Path(__file__).resolve().parents[1] / 'tilt/data/cables.json')
