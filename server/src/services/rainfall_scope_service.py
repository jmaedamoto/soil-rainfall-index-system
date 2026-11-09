"""Build mesh collections for prefecture and primary-subdivision adjustment."""

import json
from pathlib import Path


def build_scope_prefectures(prefectures, scope):
    """Return virtual areas without modifying session data or copying mesh payloads."""
    if scope not in {'prefecture', 'primary'}:
        raise ValueError(f'Unsupported adjustment_scope: {scope}')
    hierarchy = None
    if scope == 'primary':
        path = Path(__file__).resolve().parents[2] / 'config' / 'forecast_area_hierarchy.json'
        hierarchy = json.loads(path.read_text(encoding='utf-8'))['forecast_districts']
    result = {}
    for code, pref in prefectures.items():
        areas = pref.get('areas', [])
        if scope == 'prefecture':
            groups = [('全域', areas)]
        else:
            district = hierarchy.get(code)
            if district is None:
                raise ValueError(f"一次細分区域の設定がありません: {pref['name']}")
            mapping = {
                g['name']: p['name']
                for p in district['primary_subdivisions']
                for g in p['municipality_groups']
            }
            by_primary = {p['name']: [] for p in district['primary_subdivisions']}
            covered = set()
            for subdivision in pref.get('secondary_subdivisions', []):
                name = subdivision['name']
                if name not in mapping:
                    raise ValueError(f"一次細分区域との対応がありません: {pref['name']}/{name}")
                members = set(subdivision.get('area_names', []))
                by_primary[mapping[name]].extend(a for a in areas if a['name'] in members)
                covered.update(members)
            missing = {a['name'] for a in areas} - covered
            if missing:
                raise ValueError(f"一次細分区域に所属しない市町村があります: {pref['name']}/{sorted(missing)}")
            groups = list(by_primary.items())
        virtual_areas = []
        for name, members in groups:
            if not members:
                continue
            meshes = {}
            for area in members:
                for mesh in area.get('meshes', []):
                    meshes.setdefault(mesh['code'], mesh)
            virtual_areas.append({'name': name, 'meshes': list(meshes.values())})
        result[code] = {'name': pref['name'], 'areas': virtual_areas}
    return result


def aggregate_three_hour(prefectures):
    result = {}
    for pref in prefectures.values():
        for area in pref['areas']:
            values = {}
            for mesh in area['meshes']:
                for point in mesh.get('rain_timeline', []):
                    ft = int(point['ft'])
                    values[ft] = max(values.get(ft, 0), point['value'])
            result[f"{pref['name']}_{area['name']}"] = [
                {'ft': ft, 'value': value} for ft, value in sorted(values.items())
            ]
    return result
