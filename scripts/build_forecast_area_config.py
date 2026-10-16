#!/usr/bin/env python3
"""Build the forecast-area hierarchy from a downloaded JMA HTML table."""

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path


SOURCE_URL = 'https://www.jma.go.jp/jma/kishou/know/yougo_hp/shichoson_ichiran.html'


class AreaTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.table_number = 0
        self.active = False
        self.rows = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            self.table_number += 1
            self.active = self.table_number == 1
        if not self.active:
            return
        if tag == 'tr':
            self.row = {'anchor': attrs.get('id'), 'cells': []}
        elif tag in ('td', 'th'):
            if int(attrs.get('colspan', '1')) != 1:
                raise ValueError('Unexpected colspan: review the source table')
            self.cell = {'text': '', 'rowspan': int(attrs.get('rowspan', '1'))}

    def handle_data(self, data):
        if self.active and self.cell is not None:
            self.cell['text'] += data

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag in ('td', 'th'):
            self.cell['text'] = ''.join(self.cell['text'].split())
            self.row['cells'].append(self.cell)
            self.cell = None
        elif tag == 'tr':
            self.rows.append(self.row)
        elif tag == 'table':
            self.active = False


def build_config(raw_html):
    html = raw_html.decode('utf-8-sig')
    parser = AreaTableParser()
    parser.feed(html)
    expected = ['府県予報区', '一次細分区域', '市町村等をまとめた地域', '二次細分区域の名称']
    if not parser.rows or [c['text'] for c in parser.rows[0]['cells']] != expected:
        raise ValueError('Unexpected table header: review the source page')
    date_match = re.search(r'令和(\d+)年(\d+)月(\d+)日現在', html)
    if not date_match:
        raise ValueError('Source effective date not found')
    year, month, day = map(int, date_match.groups())
    districts = {}
    spans = {}
    district = None
    for row in parser.rows[1:]:
        values = []
        cells = iter(row['cells'])
        for column in range(4):
            if column in spans:
                text, remaining = spans.pop(column)
            else:
                cell = next(cells)
                text, remaining = cell['text'], cell['rowspan']
            values.append(text)
            if remaining > 1:
                spans[column] = (text, remaining - 1)
        if next(cells, None) is not None:
            raise ValueError('Unexpected extra table cell')
        district_name, primary_name, group_source_name, _ = values
        if row['anchor']:
            key = row['anchor']
            if key in districts:
                raise ValueError(f'Duplicate district: {key}')
            district = districts[key] = {'name': district_name, 'primary_subdivisions': []}
        if district is None or district['name'] != district_name:
            raise ValueError(f'Missing district anchor: {district_name}')
        primary = next((p for p in district['primary_subdivisions'] if p['name'] == primary_name), None)
        if primary is None:
            primary = {'name': primary_name, 'municipality_groups': []}
            district['primary_subdivisions'].append(primary)
        group_name = group_source_name
        if group_name.startswith('（') and group_name.endswith('）'):
            group_name = group_name[1:-1]
        if any(g['name'] == group_name for p in district['primary_subdivisions'] for g in p['municipality_groups']):
            raise ValueError(f'Duplicate municipality group: {district_name}/{group_name}')
        primary['municipality_groups'].append({'name': group_name, 'source_name': group_source_name})
    if spans:
        raise ValueError('Unfinished rowspan in source table')
    return {
        'schema_version': 1,
        'source': {
            'url': SOURCE_URL,
            'effective_date': f'{year + 2018:04d}-{month:02d}-{day:02d}',
            'html_sha256': hashlib.sha256(raw_html).hexdigest(),
        },
        'forecast_districts': districts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html_file', type=Path)
    parser.add_argument('output_json', type=Path)
    args = parser.parse_args()
    config = build_config(args.html_file.read_bytes())
    args.output_json.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    districts = config['forecast_districts']
    primary_count = sum(len(d['primary_subdivisions']) for d in districts.values())
    group_count = sum(len(p['municipality_groups']) for d in districts.values() for p in d['primary_subdivisions'])
    print(f'{len(districts)} districts, {primary_count} primary subdivisions, {group_count} municipality groups')


if __name__ == '__main__':
    main()
