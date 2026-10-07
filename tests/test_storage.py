import json
import math

import pytest

from tilt.storage import Database, DATA


def test_catalog_exact_source_and_ranges():
    db = Database(':memory:')
    source = json.loads(DATA.read_text(encoding='utf-8'))
    assert len(db.cables()) == 47
    assert sum(len(c.samples) for c in db.cables()) == 1669
    for record in source['cables']:
        cable = db.cable(record['name'])
        assert cable.velocity_factor == record['velocity_factor']
        for frequency, attenuation, power in record['samples']:
            assert cable.at(frequency) == (attenuation, power)
        lo, hi = cable.frequency_range
        for f in (lo/2, hi*1.001, float('nan')):
            with pytest.raises(ValueError):
                cable.at(f)
    db.close()


def test_log_interpolation_and_not_nearest_neighbor():
    db = Database(':memory:')
    cable = db.cable('LCF12-50')
    a, b = cable.samples[10:12]
    f = math.sqrt(a[0]*b[0])
    loss, power = cable.at(f)
    assert loss == pytest.approx(math.sqrt(a[1]*b[1]))
    assert power == pytest.approx(math.sqrt(a[2]*b[2]))
    assert loss != a[1]
    db.close()


def test_persistence_append_only_and_injection_safe(tmp_path):
    path = tmp_path/'test.sqlite3'
    db = Database(path)
    title = "Estudo '); DROP TABLE cables; --"
    first = db.save_project(title, {'v': 1}, {'power': 12})
    second = db.save_project(title, {'v': 2}, {'power': 13})
    db.close()
    db = Database(path)
    assert first != second
    assert db.project(first)['payload'] == {'v': 1}
    assert db.project(second)['snapshot'] == {'power': 13}
    assert len(db.projects()) == 2
    assert len(db.cables()) == 47
    with pytest.raises(ValueError):
        db.save_project(' ', {}, {})
    with pytest.raises(ValueError):
        db.project(9999)
    db.close()


def test_unknown_model_is_not_silently_replaced():
    db = Database(':memory:')
    with pytest.raises(ValueError):
        db.cable('inventado')
    db.close()
