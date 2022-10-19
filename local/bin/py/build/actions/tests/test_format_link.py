import argparse
import io
import unittest
from unittest import mock

from format_link import parse_file, Node, init_args, main


class TestParse(unittest.TestCase):

    @mock.patch('format_link.open', new=mock.mock_open(read_data='This is some text'))
    def test_no_shortcodes_parses(self):
        actual = parse_file('/content/en/foo.md')
        expected = Node("root")
        self.assertEqual(actual, expected)

    @mock.patch('format_link.open', new=mock.mock_open(
        read_data='**Note**: Mention ```@zenduty``` as a channel under **Notify your team**'))
    def test_inline_triple_backtick_parses(self):
        actual = parse_file('/content/en/foo.md')
        expected = Node("root")
        self.assertEqual(actual, expected)

    @mock.patch('format_link.open', new=mock.mock_open(
        read_data='## Further Reading\n{{< partial name="whats-next/whats-next.html" >}}'))
    def test_non_closing_shortcode_ignored(self):
        actual = parse_file('/content/en/foo.md')
        expected = Node("root")
        self.assertEqual(actual, expected)

    @mock.patch('format_link.open', new=mock.mock_open(
        read_data='{{< programming-lang-wrapper langs="java,dotnet,go,ruby,php,nodejs,python" >}}{{< programming-lang lang="java" >}}{{< /programming-lang >}}{{< /programming-lang-wrapper >}}'))
    def test_lang_shortcode(self):
        actual = parse_file('/content/en/foo.md')
        expected = Node("root")
        self.assertEqual(actual, expected)

    @mock.patch('format_link.open', new=mock.mock_open(
        read_data='{{< programming-lang-wrapper langs="java,dotnet,go,ruby,php,nodejs,python" >}}{{< programming-lang lang="java" >}}{{< tabs >}}{{% tab "set_tag" %}}{{% /tab %}}{{< /tabs >}}{{< /programming-lang >}}{{< /programming-lang-wrapper >}}'))
    def test_lang_tab_shortcode(self):
        actual = parse_file('/content/en/foo.md')
        expected = Node("root")
        self.assertEqual(actual, expected)

    # one liner shortcode we don't know about, we should error
    # test shortcode with < or > in name
    # test ja shortcodes
    # test unclosed shortcode, with and without more shortcodes inside it


class TestInitArgs(unittest.TestCase):

    @mock.patch('sys.argv', ['-f', 'content/en/foo/bar.md', '-d', 'content/en/'])
    def test_file_dir_both_exist_error(self):
        with self.assertRaises(SystemExit):
            init_args()


class TestMain(unittest.TestCase):

    @mock.patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(source='content/en/foo/bar.md'))
    @mock.patch('format_link.parse_file', return_value=Node('fakeroot'))
    @mock.patch('format_link.process_nodes')
    @mock.patch('format_link.assemble_nodes')
    @mock.patch('format_link.open', new_callable=mock.mock_open())
    def test_file_passed_is_processed(self, mock_open, mock_assemble_nodes, mock_process_nodes, mock_parse_file, mock_parse_args):
        """
        Mock all the actual processing and lets check that passing a file does actually attempt to write to file
        """
        main()
        mock_open.assert_called_once_with('content/en/foo/bar.md', 'w')

    @mock.patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(source='content/en/foo/'))
    @mock.patch('format_link.parse_file', return_value=Node('fakeroot'))
    @mock.patch('format_link.process_nodes')
    @mock.patch('format_link.assemble_nodes')
    @mock.patch('format_link.open', new_callable=mock.mock_open())
    def test_dir_passed_is_processed(self, mock_open, mock_assemble_nodes, mock_process_nodes, mock_parse_file, mock_parse_args):
        with self.assertRaises(TypeError):
            main()


if __name__ == '__main__':
    unittest.main()
