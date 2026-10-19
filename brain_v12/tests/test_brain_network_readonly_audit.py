"""Safety and report-shape tests for the local network audit helper."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'tools' / 'brain_network_readonly_audit.py'
spec = importlib.util.spec_from_file_location('brain_network_readonly_audit', MODULE_PATH)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)


def test_default_audit_uses_only_explicit_local_status_endpoints():
    assert all(path.startswith('/api/') for path in audit.ENDPOINTS.values())
    assert len(audit.ENDPOINTS) == 6
    assert audit.OPTIONAL_NETWORK_DIAGNOSTICS_ENDPOINT == '/api/network-diagnostics/report'


def test_report_does_not_infer_asic_from_empty_inventory():
    fixtures = {
        'directory_status': {'ok': True, 'network_scan_performed': False},
        'directory_devices': {'items': []},
        'directory_overview': {'devices': [], 'asic_contacted': False},
        'asic_bridge': {'device_contacted': False, 'mining_started': False},
        'mining_readiness': {'real_mining_ready': False},
        'follow_up': {'total_tasks': 8},
    }
    calls = []
    def fake_fetch(base_url, path, timeout):
        calls.append(path)
        name = next(key for key, endpoint in audit.ENDPOINTS.items() if endpoint == path)
        return {'http_status': 200, 'data': fixtures[name]}
    with patch.object(audit, 'fetch_json', side_effect=fake_fetch):
        report = audit.build_report('http://127.0.0.1:8012')
    assert audit.OPTIONAL_NETWORK_DIAGNOSTICS_ENDPOINT not in calls
    assert report['network_diagnostics_included'] is False
    assert report['results']['network_diagnostics']['skipped'] is True
    result = report['conclusion']
    assert result['brain_local_api_reachable'] is True
    assert result['known_device_count'] == 0
    assert result['known_asic_count'] == 0
    assert result['asic_contacted'] is False
    assert result['network_scan_performed'] is False
    assert result['settings_changed'] is False
    assert result['mining_started'] is False
    assert result['real_mining_verified'] is False


def test_failed_endpoint_is_not_reported_as_fully_reachable():
    with patch.object(audit, 'fetch_json', return_value={'http_status': None, 'error': 'TimeoutError'}):
        report = audit.build_report('http://127.0.0.1:8012')
    assert report['conclusion']['brain_local_api_reachable'] is False


def test_network_diagnostics_requires_explicit_opt_in():
    paths = []
    def fake_fetch(base_url, path, timeout):
        paths.append(path)
        return {'http_status': 200, 'data': {}}
    with patch.object(audit, 'fetch_json', side_effect=fake_fetch):
        report = audit.build_report('http://127.0.0.1:8012', include_network_diagnostics=True)
    assert audit.OPTIONAL_NETWORK_DIAGNOSTICS_ENDPOINT in paths
    assert report['network_diagnostics_included'] is True
    assert report['results']['network_diagnostics']['http_status'] == 200
