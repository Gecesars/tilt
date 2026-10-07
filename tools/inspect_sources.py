"""Read-only extraction of legacy XLS cells and BIFF formulas for engineering review."""
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.analysis_deps'))
import xlrd
import olefile
from xlrd.formula import decompile_formula, FMLA_TYPE_CELL


def extract(path):
    book = xlrd.open_workbook(path, formatting_info=True)
    result = {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'sheets': []}
    for sheet in book.sheets():
        cells = {xlrd.formula.cellname(r, c): sheet.cell_value(r, c)
                 for r in range(sheet.nrows) for c in range(sheet.ncols)
                 if sheet.cell_type(r, c) not in (0, 6)}
        result['sheets'].append({'name': sheet.name, 'cells': cells, 'formulas': {}})
    with olefile.OleFileIO(path) as ole:
        stream = ole.openstream('Workbook' if ole.exists('Workbook') else 'Book').read()
    offset, sheet_index = 0, -1
    while offset + 4 <= len(stream):
        code, length = struct.unpack_from('<HH', stream, offset)
        data = stream[offset+4:offset+4+length]
        offset += 4 + length
        if code == 0x0809 and len(data) >= 4 and struct.unpack_from('<H', data, 2)[0] == 0x0010:
            sheet_index += 1
        if code == 0x0006 and sheet_index >= 0:
            row, col = struct.unpack_from('<HH', data)
            token_length = struct.unpack_from('<H', data, 20)[0]
            formula = decompile_formula(book, data[22:22+token_length], token_length,
                                        FMLA_TYPE_CELL, browx=row, bcolx=col)
            result['sheets'][sheet_index]['formulas'][xlrd.formula.cellname(row, col)] = formula
    return result


if __name__ == '__main__':
    output = Path(__file__).resolve().parents[1] / '.artifacts' / 'source_workbooks.json'
    output.parent.mkdir(exist_ok=True)
    data = [extract(Path(p)) for p in sys.argv[1:]]
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(data, indent=2, ensure_ascii=False))
