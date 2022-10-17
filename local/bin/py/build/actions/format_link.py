#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import glob
from collections import OrderedDict
from optparse import OptionParser


class Node:
    def __init__(self, name):
        self.name = name
        self.children = []
        self.parent = None
        self.lines = []
        self.modified_lines = []
        self.start_line = 0
        self.end_line = 0
        self.start = 0
        self.end = 0

    def add(self, child):
        child.parent = self
        self.children.append(child)

    def push_line(self, line):
        self.lines.append(line)

    def pop_line(self):
        return self.lines.pop()

    def __repr__(self):
        return repr(f"<{self.name}>")


def parse_file(file):
    """
    Goes through a file and parses it into different sections. Those sections are a list of lines and are put within an Array.
    The first item of the Array is the main section, all other item if any are sub sections, a.k.a tabs within the page.

    :param file: file to break down into sections.
    :return root: Root node from parsing
    """
    sub_sections = []

    root = Node("root")
    current_node = root

    open_tag_regex = r"{{[<|%]\s+([A-Za-z0-9-_]+)(.*)\s+[%|>]}}"
    closed_tag_regex = r"{{[<|%]\s+/([A-Za-z0-9-_]+)(.*)\s+[%|>]}}"

    # list of tags that don't have open/close and are just one liner
    one_liner_tags = ("partial",)
    # tags we care about contents having its own scope and being a 'subsection'
    subsection_tags = ('tab', 'programming-lang')

    with open(file, 'r', encoding='utf-8') as f:
        new_line_number = 0
        for line_number, line in enumerate(f):
            current_node.push_line(line)
            #if current_node.name not in subsection_tags and current_node.parent:
            #    root.push_line(line)

            # find new open tags and create a node
            new_node = None
            matches = re.finditer(open_tag_regex, line, re.MULTILINE)
            for matchNum, match in enumerate(matches, start=1):
                tag_name = match.group(1)
                current_node.start = match.start(0)
                if tag_name not in one_liner_tags:
                    new_node = Node(tag_name)
                    current_node.add(new_node)

            # if we entered a new node lets set it as the current
            if new_node:
                current_node = new_node
                current_node.push_line(line)
                current_node.start_line = new_line_number
                new_line_number = 0

            # check for closing node and return up the chain to the parent node for next iteration
            matches = re.finditer(closed_tag_regex, line, re.MULTILINE)
            for matchNum, match in enumerate(matches, start=1):
                tag_name = match.group(1)
                current_node.end = match.end(0)
                #if tag_name in subsection_tags:
                #    root.push_line(line)
                if tag_name == current_node.name and current_node.parent:
                    if tag_name in subsection_tags:
                        sub_sections.append(current_node.lines[1:-1])
                    current_node.end_line = current_node.start_line + 1
                    new_line_number = current_node.end_line
                    current_node = current_node.parent
                    current_node.push_line(line)

            new_line_number += 1

    if not root.lines:
        raise ValueError

    return root


def check_references(all_references):
    """
    Goes through a list of reference link and dedupe it, and if two references share the same index, throw an error.

    :param all_references: An array of references
    :return all_references_deduped: An array of references deduped.
    """
    all_references_deduped = []
    reference_indexes_used = []
    duplicated_references = []
    is_duplicated = False

    for reference in all_references:
        if reference not in all_references_deduped:

            reference_index, reference_val = reference

            if reference_index not in reference_indexes_used:
                reference_indexes_used.append(reference_index)
                all_references_deduped.append(reference)
            else:
                duplicated_references.append(reference)
                is_duplicated = True

    if is_duplicated:
        for duplicated_reference in duplicated_references:
            duplicated_reference_index, duplicated_reference_val = duplicated_reference
            print('Duplicated reference: [{}]: {}'.format(
                duplicated_reference_index, duplicated_reference_val))
        raise AssertionError

    return all_references_deduped


def process_nodes(node):
    content = ''.join(node.lines)

    # extract footer reference links
    refs = {}
    matches = re.finditer(r"^\s*\[(\d*?)\]: (\S*)", content, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        refs[match.group(1)] = match.group(2)
    all_references = OrderedDict(sorted(refs.items()))

    # remove footer reference links
    # content = re.sub(r"^\s*\[(\d*?)\]: (\S*)", "", content, 0, re.MULTILINE)
    start_line, end_line = None, None
    for ln, line in enumerate(node.lines):
        if re.search(r"^\s*\[(\d*?)\]: (\S*)", line):
            if start_line:
                end_line = ln + 1
            else:
                start_line = ln
    #     else:
    #         pass
    #         #node.modified_lines.append(line)
    # #content = ''.join(node.modified_lines)

    # inline existing reference links
    for reference_index, reference_val in all_references.items():
        current_link = '][' + reference_index + ']'
        content = content.replace(current_link, '](' + reference_val + ')')

    # extract all inlined links it can find.
    all_links = []
    matches = re.finditer(r"\[.*?\]\((?![#?])(\S*?)\)", content, re.MULTILINE)
    for match in matches:
        all_links.append(match.group(1))
    all_links = set(all_links)

    # create reference footer section again
    for i, link in enumerate(all_links):
        link_to_reference = '](' + str(link) + ')'
        # i is incremented by one in order to start references indexes at 1
        content = content.replace(link_to_reference, '][' + str(i + 1) + ']')

    # assign completed content changes
    node.modified_lines = content.splitlines(keepends=True)

    # remove blank lines
    #for _ in all_references:
    #    index = len(node.modified_lines) - 2 if node.parent else len(node.modified_lines) - 1
    #    del node.modified_lines[index]

    # adds all refrerences at the end of the section
    #index = len(node.modified_lines) - 1 if node.parent else len(node.modified_lines)
    #node.modified_lines[index:index] = [f"FOO[{i+1}]: {link}\n" for i, link in enumerate(all_links)]
    #index = len(node.modified_lines) - 1 if node.parent else len(node.modified_lines)

    # if not start_line or not end_line:
    #     start_line = len(node.modified_lines) - 1 if node.parent else len(node.modified_lines)
    #     end_line = start_line
    #     print(f"A {start_line} {end_line} {node.modified_lines[start_line:end_line]} {node.modified_lines[start_line-1:end_line]}")
    # else:
    #     print(f"B {start_line} {end_line} {node.modified_lines[start_line:end_line]}")
    if not start_line:
        start_line = len(node.modified_lines) - 1 if node.parent else len(node.modified_lines)
        end_line = start_line
    node.modified_lines[start_line:end_line] = [f"FOO[{i+1}]: {link}\n" for i, link in enumerate(all_links)]

    # process children
    for child in node.children:
        process_nodes(child)


def assemble_nodes(node):
    output = [] + node.modified_lines
    for child in reversed(node.children):
        child_output = assemble_nodes(child)
        if child.start_line == child.end_line:
            # single line shortcode
            line = output[child.start_line]
            output[child.start_line] = line[:child.start] + child_output + line[child.end:]
        else:
            # multi line shortcode
            output[child.start_line:child.end_line + 1] = child_output
    return output


def reassemble_file(root):
    contents_list = assemble_nodes(root)
    return ''.join(contents_list)


if __name__ == '__main__':
    parser = OptionParser(usage='usage: %prog [options] file')
    parser.add_option('-f', '--file', help='File to format link in reference', default=None)
    parser.add_option('-d', '--directory', help='Directory to format link in reference for all markdown file', default=None)

    (options, args) = parser.parse_args()
    regex_skip_sections_end = r"(```|\{\{< \/code-block >\}\})"
    regex_skip_sections_start = r"(```|\{\{< code-block)"

    if options.file or options.directory:
        files = [options.file] if options.file else glob.iglob(options.directory + '**/*.md', recursive=True)
        for filepath in files:
            print('\x1b[32mINFO\x1b[0m: Formating file {}'.format(filepath))
            # parse the file shortcode hierarchy
            root = parse_file(filepath)
            # process each node text contents, each node will store original and modified content
            process_nodes(root)
            # reassemble the file with the changes we have made
            reassembled_file = reassemble_file(root)
            # overwrite the original file with our changes
            with open(filepath, 'w') as final_file:
                final_file.write(reassembled_file)
    else:
        print('\x1b[31mERROR\x1b[0m: Please specify a file or a directory')
