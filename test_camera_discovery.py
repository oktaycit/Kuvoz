import ipaddress
import threading
import unittest
from unittest.mock import patch
from lib.ai import camera_discovery as discovery

MAC = '1c:79:2d:f7:f3:e4'
LAN = (ipaddress.ip_network('192.168.1.0/29'), 'wlan0')
URL = 'rtsp://user:p%40ss@192.168.1.2:554/live/ch00_1?mode=1'


class DiscoveryTests(unittest.TestCase):
    def test_replace_only_host_preserves_auth_stream_port_query(self):
        self.assertEqual(discovery.replace_host(URL, '192.168.1.5'),
                         'rtsp://user:p%40ss@192.168.1.5:554/live/ch00_1?mode=1')

    def test_invalid_mac_rejected(self):
        for mac in ['no', 'ff:ff:ff:ff:ff:ff', '00:00:00:00:00:00', '$(id)']:
            with self.assertRaises(ValueError): discovery.normalize_mac(mac)
        self.assertEqual(discovery.normalize_mac(MAC.upper()), MAC)

    @patch.object(discovery, 'local_network', return_value=LAN)
    @patch.object(discovery, 'neighbors', return_value={'192.168.1.5': MAC})
    @patch.object(discovery, '_probe', side_effect=lambda h, p, s: h)
    def test_cached_matching_mac_avoids_scan(self, probe, neighbors, network):
        self.assertEqual(discovery.discover(URL, MAC), [{'ip': '192.168.1.5', 'mac': MAC}])
        self.assertEqual(probe.call_count, 1)

    @patch.object(discovery, 'local_network', return_value=LAN)
    @patch.object(discovery, 'neighbors', side_effect=[{}, {'192.168.1.5': MAC, '192.168.1.4': '02:00:00:00:00:02'}])
    @patch.object(discovery, '_probe', side_effect=lambda h, p, s: h)
    def test_scan_filters_other_cameras_by_mac(self, *mocks):
        self.assertEqual(discovery.discover(URL, MAC), [{'ip': '192.168.1.5', 'mac': MAC}])

    @patch.object(discovery, 'local_network', return_value=LAN)
    @patch.object(discovery, 'neighbors', return_value={'192.168.1.2': '02:00:00:00:00:02'})
    @patch.object(discovery, '_probe', return_value='192.168.1.2')
    @patch.object(discovery, 'discover', return_value=[{'ip': '192.168.1.5', 'mac': MAC}])
    def test_reconnects_to_same_mac_at_new_ip(self, *mocks):
        resolver = discovery.CameraResolver(URL, MAC, threading.Event())
        self.assertIn('@192.168.1.5:554/', resolver.resolve())

    @patch.object(discovery, 'local_network', return_value=LAN)
    @patch.object(discovery, '_probe', return_value=None)
    @patch.object(discovery, 'discover', return_value=[])
    def test_no_fallback_to_old_ip_and_search_backoff(self, scan, *mocks):
        resolver = discovery.CameraResolver(URL, MAC, threading.Event())
        for _ in range(3): self.assertIsNone(resolver.resolve())
        scan.assert_called_once()
        self.assertEqual(resolver.delay, 10)

    @patch.object(discovery, 'local_network', return_value=None)
    @patch.object(discovery, '_probe')
    def test_no_off_lan_scanning(self, probe, *mocks):
        self.assertEqual(discovery.discover('rtsp://example.org/live', MAC), [])
        probe.assert_not_called()

    @patch.object(discovery, '_ip_json', return_value=[{'ifname': 'wlan0', 'addr_info': [
        {'local': '192.168.1.12', 'prefixlen': 24, 'scope': 'global'}]}])
    def test_only_attached_subnet_is_allowed(self, *mocks):
        self.assertIsNotNone(discovery.local_network('192.168.1.24'))
        self.assertIsNone(discovery.local_network('10.1.1.24'))

    def test_existing_unpinned_camera_keeps_working(self):
        self.assertEqual(discovery.CameraResolver(URL, '', threading.Event()).resolve(), URL)

    def test_stopped_probe_does_not_open_socket(self):
        stop = threading.Event(); stop.set()
        with patch.object(discovery.socket, 'create_connection') as connect:
            self.assertIsNone(discovery._probe('192.168.1.2', 554, stop))
            connect.assert_not_called()


if __name__ == '__main__': unittest.main()
