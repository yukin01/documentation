import argparse
import io
import unittest
from pathlib import PosixPath
from unittest import mock

from format_link import parse_file, Node, init_args, assemble_nodes, main, format_link_file


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

    @mock.patch('format_link.open', new=mock.mock_open(
        read_data="""
Root text
{{< site-region region="us3" >}}
    Root site region
    {{< site-region region="us,us5,eu,gov" >}}Nested Region 1{{< /site-region >}}
    {{< site-region region="us3" >}}Nested Region 2{{< /site-region >}}
{{< /site-region >}}
Text after
    """))
    def test_nested_site_region(self):
        actual = parse_file('/content/en/foo.md')
        expected = Node("root")
        self.assertEqual(actual, expected)

    # one liner shortcode we didn't define
    @mock.patch('format_link.open', new=mock.mock_open(read_data="""
This
{{< tab "blah" >}}
Stuff here
{{</ tab >}}
is text {{< foobar test="stuff" >}} and more
{{< tab "durp" >}}
Stuff here
{{</ tab >}}"""))
    def test_non_closing_shortcode_unknown(self):
        parsed = parse_file('/content/en/foo.md')
        actual = len(parsed.children)
        expected = 2
        self.assertEqual(actual, expected)

    @mock.patch('format_link.open', new=mock.mock_open(read_data="""
Here is some root text
{{< tab "MySQL < 4.0" >}}
Text here
{{< /tab >}}
and after
{{< tab "foo" >}}
Stuff here
{{</ tab >}}"""))
    def test_shortcode_argument_containing_arrow(self):
        parsed = parse_file('/content/en/foo.md')
        actual = len(parsed.children)
        expected = 2
        self.assertEqual(actual, expected)

    @mock.patch('format_link.open', new=mock.mock_open(read_data="""
Here is text
{{% tab "ドライバーのみ" %}}
Hello world
{{% /tab %}}
{{% tab "標準" %}}
Hello world 2
{{% /tab %}}"""))
    def test_ja_shortcode(self):
        parsed = parse_file('/content/en/foo.md')
        actual = len(parsed.children)
        expected = 2
        self.assertEqual(actual, expected)
    # test unclosed shortcode, with and without more shortcodes inside it


class TestInitArgs(unittest.TestCase):

    @mock.patch('sys.argv', ['-f', 'content/en/foo/bar.md', '-d', 'content/en/'])
    def test_file_dir_both_exist_error(self):
        with self.assertRaises(SystemExit):
            init_args()


class TestAssembleNodes(unittest.TestCase):

    def test_should_return_list(self):
        node = Node('root')
        node.modified_lines = ['foo']
        actual = type(assemble_nodes(node))
        expected = list
        self.assertEqual(actual, expected)

    def test_should_return_root_text(self):
        node = Node('root')
        node.modified_lines = ['foo']
        actual = assemble_nodes(node)
        expected = ['foo']
        self.assertEqual(actual, expected)

    def test_should_return_nested_text(self):
        node = Node('root')
        node.name = "root"
        node.start_line = 0
        node.end_line = 0
        node.start = 0
        node.end = 0
        node.lines = ['This is root\n', 'and some more\n', '{{% tab "test" %}}\n']
        node.modified_lines = ['This is root\n', 'and some more\n', '{{% tab "test" %}}\n']
        tab_node = Node('tab')
        tab_node.name = "test"
        tab_node.start_line = 2
        tab_node.end_line = 3
        tab_node.start = 0
        tab_node.end = 12
        tab_node.lines = ['This is root\n', 'and some more\n', '{{% tab "test" %}}\n']
        tab_node.modified_lines = ['{{% tab "test" %}}\n', 'Here is some text\n', '{{% /tab %}}\n']
        node.children.append(tab_node)
        actual = assemble_nodes(node)
        expected = ['This is root\n', 'and some more\n', '{{% tab "test" %}}\n', 'Here is some text\n', '{{% /tab %}}\n']
        self.assertEqual(expected, actual)


class TestProcessNodes(unittest.TestCase):
    def test_foo(self):
        pass


class TestFormatLinkFile(unittest.TestCase):

    def test_should_error_when_no_args(self):
        with self.assertRaises(ValueError):
            actual = format_link_file()

    @mock.patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(source='content/en/foo/bar.md'))
    @mock.patch('format_link.parse_file', return_value=Node('fakeroot'))
    @mock.patch('format_link.process_nodes')
    @mock.patch('format_link.assemble_nodes')
    @mock.patch('format_link.open', new_callable=mock.mock_open())
    def test_should_return_string(self, mock_open, mock_assemble_nodes, mock_process_nodes, mock_parse_file,
                                      mock_parse_args):
        response = format_link_file('path/to/file.md')
        actual = type(response)
        expected = str
        self.assertEqual(actual, expected)


class TestMain(unittest.TestCase):

    @mock.patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(source='content/en/foo/bar.md'))
    @mock.patch('format_link.format_link_file', return_value='Hello fake text')
    @mock.patch('format_link.open', new_callable=mock.mock_open())
    @mock.patch('pathlib.Path.is_file', return_value=lambda x: True)
    def test_file_passed_is_processed(self, mock_path, mock_open, mock_format_link_file_response, mock_parse_args):
        """
        Mock all the actual processing and lets check that passing a file does actually attempt to write to file
        """
        main()
        mock_open.assert_called_once_with(PosixPath('content/en/foo/bar.md'), 'w')

    # @mock.patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(source='content/en/foo/'))
    # @mock.patch('format_link.format_link_file', return_value='Hello fake text')
    # @mock.patch('format_link.open', new_callable=mock.mock_open())
    # def test_dir_passed_is_processed(self, mock_open, mock_format_link_file_response, mock_parse_args):
    #     with self.assertRaises(TypeError):
    #         main()


if __name__ == '__main__':
    unittest.main()
