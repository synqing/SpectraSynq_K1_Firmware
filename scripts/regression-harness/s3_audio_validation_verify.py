#!/usr/bin/env python3
"""Independently verify frozen V2 captures; publish no partial fixture index."""
import argparse
import hashlib
import json
from pathlib import Path
import s3_audio_validation_capture as capture


def verify(manifest, runtime, preregistration, source, output):
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'k1-s3-validation-verification/1', 'complete': False,
              'expected': 483, 'clips': {}, 'errors': {}}
    try:
        source_bytes = source.read_bytes()
        frozen = json.loads(preregistration.read_text())
        report.update(source_manifest=str(manifest.resolve()),
                      source_manifest_sha256=capture.sha(manifest),
                      preregistration_sha256=capture.sha(preregistration),
                      capture_sha256=hashlib.sha256(source_bytes).hexdigest(), source_capture=str(source.resolve()))
        for path, key in ((manifest, 'validation_manifest_sha256'),
                          (runtime/'firmware.bin', 'runtime_app_sha256'),
                          (runtime/'firmware.elf', 'runtime_elf_sha256'),
                          (Path(frozen['model_path']), 'model_sha256')):
            if capture.sha(path) != frozen[key]:
                raise ValueError('frozen hash mismatch: '+key)
        identity = json.loads((runtime/'identity.json').read_text())
        if identity['app_sha256'] != frozen['runtime_app_sha256'] or identity['elf_sha256'] != frozen['runtime_elf_sha256']:
            raise ValueError('runtime identity hash mismatch')
        report['runtime'] = identity
        rows = json.loads(manifest.read_text())['rows']
        lookup = {row['id']: row for row in rows}
        if len(rows) != 483 or len(lookup) != 483 or any(r['role'] != 'validation' or r['split'] != 'V2' for r in rows):
            raise ValueError('manifest must contain exactly 483 unique V2 validation rows')
        prior = json.loads(source_bytes)
        if prior['preregistration_sha256'] != report['preregistration_sha256'] or prior['runtime'] != identity:
            raise ValueError('capture preregistration/runtime mismatch')
        cases = prior['cases']
        ids = [r['id'] for r in cases]
        if len(ids) != len(set(ids)) or set(ids) != set(lookup) or prior['expected'] != 483 or prior['pilot']:
            raise ValueError('capture coverage is duplicate, partial, or outside the frozen manifest')
        for rec in cases:
            try:
                report['clips'][rec['id']] = capture.validate_record(lookup[rec['id']], rec, runtime, output)
            except Exception as exc:
                report['errors'][rec['id']] = str(exc)
        if capture.sha(source) != report['capture_sha256']:
            raise ValueError('capture changed during verification')
        report['complete'] = not report['errors'] and len(report['clips']) == 483
    except Exception as exc:
        report['errors']['input'] = str(exc)
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    if report['complete']:
        index = dict(report, schema='k1-tempo-fixture-set/1')
        (output/'index.json').write_text(json.dumps(index, indent=2)+'\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'runtime', 'preregistration', 'capture', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    result = verify(a.manifest, a.runtime, a.preregistration, a.capture, a.output)
    print(json.dumps({'verified': len(result['clips']), 'complete': result['complete'], 'errors': result['errors']}))
    return int(not result['complete'])


if __name__ == '__main__':
    raise SystemExit(main())
