

import unittest
import sys
import log_analyzer as la
import io

class TestConfigPath(unittest.TestCase):
    def test_path(self):
        sys.argv.append('--config=log/test_config.json')
        path = la.process_args().config_path
        self.assertEqual(path, 'log/test_config.json')
        sys.argv.pop()

    def test_wrong_path(self):
        sys.argv.append('--config=log1/test_config.json')
        self.assertRaises(FileNotFoundError)

class TestProcessLog(unittest.TestCase):
    def test_valid_line(self):
        valid_string = '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] ' \
                       '"GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 ' \
                       'libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" ' \
                       '"1498697422-2190034393-4708-9752759" "dc7161be3" 0.390'
        res = la.process_line(valid_string)
        self.assertIsNotNone(res)


if __name__ == '__main__':
    unittest.main()