#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import glob
from collections import OrderedDict
import logging
import sys
from pathlib import Path


class Formatter(logging.Formatter):
    def format(self, record):
        reset = "\x1b[0m"
        color = {
            logging.INFO: 32,
            logging.WARNING: 33,
            logging.ERROR: 31,
            logging.FATAL: 31,
            logging.DEBUG: 36
        }.get(record.levelno, 0)
        self._style._fmt = f"\x1b[{color}m%(levelname)s:{reset} %(message)s"
        return super().format(record)


logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter())
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


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

    def __eq__(self, other):
        return self.name == other.name


def parse_file(file):
    """
    Goes through a file and parses it into different sections. Those sections are a list of lines and are put within an Array.
    The first item of the Array is the main section, all other item if any are sub sections, a.k.a tabs within the page.

    :param file: file to break down into sections.
    :return root: Root node from parsing
    """
    root = Node("root")
    current_node = root

    open_tag_regex = r"{{[<|%]\s+([A-Za-z0-9-_]+)(.*)\s+[%|>]}}"
    closed_tag_regex = r"{{[<|%]\s+/([A-Za-z0-9-_]+)(.*)\s+[%|>]}}"
    backtick_code_regex = r"(```)"

    # list of tags that don't have open/close and are just one liner
    # this isn't sustainable, we need to detect one liners or specify includes not excludes
    one_liner_tags = ("partial", "img", "region-param", "latest-lambda-layer-version")

    with open(file, 'r', encoding='utf-8') as f:
        new_line_number = 0
        for line_number, line in enumerate(f):
            current_node.push_line(line)

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
                if tag_name == current_node.name and current_node.parent:
                    current_node.end_line = current_node.start_line + 1
                    new_line_number = current_node.end_line
                    current_node = current_node.parent
                    current_node.push_line(line)

            new_line_number += 1

    if not root.lines:
        raise ValueError

    return root


def process_nodes(node):
    """
    Takes the parsed node structure and processes the link formatting we desire throughout each node.
    @param node: node
    """
    ignored_nodes = ('code-block', )

    # we want to skip code-block nodes
    if node.name not in ignored_nodes:
        content = ''.join(node.lines)

        # extract footer reference links
        refs = {}
        ref_nums = []
        matches = re.finditer(r"^\s*\[(\d*?)\]: (\S*)", content, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            ref_num, ref_link = match.group(1), match.group(2)
            # alert on duplicate reference numbers
            if ref_num in ref_nums:
                logger.warning(f'Duplicated reference index number:\n\t[{ref_num}]: {ref_link}\n\t[{ref_num}]: {refs[ref_num]}\nin section {node}')
                raise SystemExit
            else:
                refs[ref_num] = ref_link
                ref_nums.append(ref_num)
        all_references = OrderedDict(sorted(refs.items()))

        # we need to raise the error and return the original section, so hugo can fail with this

        # remove footer reference links
        # content = re.sub(r"^\s*\[(\d*?)\]: (\S*)", "", content, 0, re.MULTILINE)
        start_line, end_line = None, None
        for ln, line in enumerate(node.lines):
            if re.search(r"^\s*\[(\d*?)\]: (\S*)", line):
                if start_line:
                    end_line = ln + 1
                else:
                    start_line = ln

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

        if not start_line:
            start_line = len(node.modified_lines) - 1 if node.parent else len(node.modified_lines)
            end_line = start_line
        node.modified_lines[start_line:end_line] = [f"[{i+1}]: {link}\n" for i, link in enumerate(all_links)]

    # process children
    for child in node.children:
        process_nodes(child)


def assemble_nodes(node):
    """
    Takes a node and assembles the text contents of itself and children nodes into a final string
    This allows us to modify each node individually and inject it into the parent.
    we process in reverse so that we don't introduce offsets
    @param node: node
    @return: list of strings
    """
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


def init_args():
    """
    Sets up argument parsing and returns the arguments
    :return: argparse values
    """
    parser = argparse.ArgumentParser(description='Format links in markdown file')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-f', '--file', action='store', default=None, dest='source', help='File to format link in reference')
    group.add_argument('-d', '--directory', action='store', default=None, dest='source', help='Directory to format link in reference for all markdown file')
    args = parser.parse_args()
    return args


def format_link_file(*args):
    """
    Kept for legacy usage in other scripts
    Takes a filepath and parses/processes and returns the string text
    @param args: filepath, (we don't care about other args passed from legacy scripts)
    @return: string of changed file
    """
    if len(args) == 0:
        raise ValueError("Filepath is required argument")
    filepath = args[0]
    # parse the file shortcode hierarchy
    root = parse_file(filepath)
    # process each node text contents, each node will store original and modified content
    process_nodes(root)
    # reassemble the file with the changes we have made
    contents_list = assemble_nodes(root)
    reassembled_file = ''.join(contents_list)
    return reassembled_file


def main():
    """
    Entry point taking args and processing directory of files or file
    and responsible for writing the new contents back out to filesystem
    """
    options = init_args()
    if options.source:
        source_path = Path(options.source)
        files = [source_path] if source_path.is_file() else glob.iglob(str(source_path / '**/*.md'), recursive=True)
        for filepath in files:
            logger.info(f'Formating file {filepath}')
            final_text = format_link_file(filepath)
            # overwrite the original file with our changes
            with open(filepath, 'w') as final_file:
                final_file.write(final_text)


if __name__ == '__main__':
    main()

