import copy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from services.rainfall_scope_service import build_scope_prefectures, aggregate_three_hour
from services.rainfall_adjustment_service import RainfallAdjustmentService
from api.controllers.session_controller import SessionController


def mesh(code, value):
    return {'code': code, 'lat': 35, 'lon': 135, 'rain_timeline': [
        {'ft': ft, 'value': value} for ft in range(3, 49, 3)
    ]}


@pytest.fixture
def prefectures():
    return {
        'shiga': {'name': '滋賀県', 'areas': [
            {'name': '長浜市', 'meshes': [mesh('north1', 10)]},
            {'name': '米原市', 'meshes': [mesh('north2', 5)]},
            {'name': '草津市', 'meshes': [mesh('south', 2)]},
        ], 'secondary_subdivisions': [
            {'name': '湖北', 'area_names': ['長浜市', '米原市']},
            {'name': '近江南部', 'area_names': ['草津市']},
        ]},
        'kyoto': {'name': '京都府', 'areas': [
            {'name': '宮津市', 'meshes': [mesh('kyoto', 3)]},
        ], 'secondary_subdivisions': [{'name': '丹後', 'area_names': ['宮津市']}]},
    }


@pytest.mark.parametrize('scope', ['primary', 'prefecture'])
def test_scopes_include_all_prefectures_without_mutation(prefectures, scope):
    original = copy.deepcopy(prefectures)
    scoped = build_scope_prefectures(prefectures, scope)
    assert set(scoped) == {'shiga', 'kyoto'}
    assert prefectures == original
    assert len(scoped['shiga']['areas']) == (2 if scope == 'primary' else 1)


def test_primary_rejects_unmapped_areas(prefectures):
    prefectures['shiga']['secondary_subdivisions'][0]['name'] = '未設定地域'
    with pytest.raises(ValueError, match='対応がありません'):
        build_scope_prefectures(prefectures, 'primary')


def test_scope_deduplicates_meshes(prefectures):
    prefectures['shiga']['areas'][1]['meshes'].append(prefectures['shiga']['areas'][0]['meshes'][0])
    scoped = build_scope_prefectures(prefectures, 'primary')
    assert len(scoped['shiga']['areas'][0]['meshes']) == 2


def test_24hour_is_maximum_mesh_total_not_sum_of_time_maxima(prefectures):
    prefectures['shiga']['areas'][0]['meshes'][0]['rain_timeline'] = [{'ft': 3, 'value': 20}]
    prefectures['shiga']['areas'][1]['meshes'][0]['rain_timeline'] = [{'ft': 6, 'value': 30}]
    scoped = build_scope_prefectures(prefectures, 'primary')
    totals, _ = RainfallAdjustmentService().aggregate_rainfall_24hour_from_session(scoped)
    assert totals['滋賀県_北部'][0]['value'] == 30
    assert aggregate_three_hour(scoped)['滋賀県_北部'] == [{'ft': 3, 'value': 20}, {'ft': 6, 'value': 30}]


@pytest.mark.parametrize('scope,key', [('primary', '滋賀県_北部'), ('prefecture', '滋賀県_全域')])
@pytest.mark.parametrize('method,second_value', [
    ('build_fill_24hour_uniform_from_session', 20),
    ('build_ratio_24hour_uniform_from_session', 10),
    ('build_fill_24hour_peak_mesh_from_session', 20),
    ('build_ratio_24hour_peak_mesh_from_session', 10),
])
def test_24hour_uses_selected_scope_as_reference(prefectures, scope, key, method, second_value):
    scoped = build_scope_prefectures(prefectures, scope)
    result = getattr(RainfallAdjustmentService(), method)(scoped, {key: {24: 160}})
    assert dict(result['north1'])[3] == 20
    assert dict(result['north2'])[3] == second_value
    assert dict(result['north2'])[27] == 5
    assert 'kyoto' not in result
    assert ('south' in result) == (scope == 'prefecture')


def controller_for(prefectures):
    controller = SessionController.__new__(SessionController)
    controller.session_service = SimpleNamespace(
        get_session=lambda _: {'prefectures': prefectures},
        create_fork_session=Mock(return_value='fork'),
    )
    controller.rainfall_adjustment_service = RainfallAdjustmentService()
    return controller


def test_rainfall_api_returns_both_scopes_for_all_prefectures(prefectures):
    controller = controller_for(prefectures)
    with Flask(__name__).test_request_context():
        data = controller.get_rainfall_data('base').get_json()
    assert not data['scope_errors']
    assert set(data['scope_rainfall']['prefecture']['24hour']) == {'滋賀県_全域', '京都府_全域'}
    assert set(data['scope_rainfall']['primary']['24hour']) == {'滋賀県_北部', '滋賀県_南部', '京都府_北部'}


@pytest.mark.parametrize('scope,key', [('primary', '滋賀県_北部'), ('prefecture', '滋賀県_全域')])
def test_recalculate_routes_scoped_meshes_and_preserves_scope(prefectures, scope, key):
    controller = controller_for(prefectures)
    service = controller.rainfall_adjustment_service
    service.build_fill_24hour_uniform_from_session = Mock(return_value={})
    with Flask(__name__).test_request_context(json={
        'adjustments': {}, 'aggregate_adjustments': {key: [{'ft': 24, 'value': 160}]},
        'input_mode': '24hour', 'adjustment_mode': 'fill_24hour_uniform', 'adjustment_scope': scope,
    }):
        response = controller.recalculate_with_adjusted_rainfall('base')
    assert response.status_code == 200
    args = service.build_fill_24hour_uniform_from_session.call_args.args
    assert args[1] == {key: {24: 160}}
    assert args[0]['shiga']['areas'][0]['name'] == ('北部' if scope == 'primary' else '全域')
    assert controller.session_service.create_fork_session.call_args.kwargs['adjustment_scope'] == scope


def test_invalid_scope_key_is_rejected(prefectures):
    controller = controller_for(prefectures)
    with Flask(__name__).test_request_context(json={
        'adjustments': {'滋賀県_存在しない地域': [{'ft': 3, 'value': 10}]}, 'adjustment_scope': 'primary',
    }):
        _, status = controller.recalculate_with_adjusted_rainfall('base')
    assert status == 400
    controller.session_service.create_fork_session.assert_not_called()


@pytest.mark.parametrize('scope,key', [('primary', '滋賀県_北部'), ('prefecture', '滋賀県_全域')])
@pytest.mark.parametrize('mode,expected', [('ratio', 10), ('fill', 20), ('maximum', 10)])
def test_three_hour_scoped_adjustment(prefectures, scope, key, mode, expected):
    service = RainfallAdjustmentService()
    scoped = build_scope_prefectures(prefectures, scope)
    changes = {key: {3: 20}}
    if mode == 'ratio':
        ratios = service.calculate_mesh_ratios_from_session(scoped, changes)
        result = service.build_adjusted_mesh_rainfall_from_session(scoped, ratios)
    elif mode == 'fill':
        result = service.build_filled_mesh_rainfall_from_session(scoped, changes)
    else:
        result = service.build_area_max_filled_mesh_rainfall_from_session(scoped, changes)
    assert dict(result['north2'])[3] == expected
    assert 'kyoto' not in result
    assert ('south' in result) == (scope == 'prefecture')


def test_missing_primary_mapping_does_not_block_other_modes(prefectures):
    prefectures['shiga']['secondary_subdivisions'][0]['name'] = '未設定'
    controller = controller_for(prefectures)
    with Flask(__name__).test_request_context():
        data = controller.get_rainfall_data('base').get_json()
    assert 'primary' in data['scope_errors']
    assert 'primary' not in data['scope_rainfall']
    assert data['area_rainfall'] and data['scope_rainfall']['prefecture']
