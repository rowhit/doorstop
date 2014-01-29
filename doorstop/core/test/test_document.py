#!/usr/bin/env python

"""
Unit tests for the doorstop.core.document module.
"""

import unittest
from unittest.mock import patch, Mock

import os
import logging

from doorstop.core.document import Document
from doorstop import common
from doorstop.common import DoorstopError, DoorstopWarning, DoorstopInfo

from doorstop.core.test import ENV, REASON
from doorstop.core.test import ROOT, FILES, EMPTY, NEW, MockFileObject
from doorstop.core.test.test_item import MockItem

YAML_DEFAULT = """
settings:
  digits: 3
  prefix: REQ
  sep: ''
""".lstrip()

YAML_CUSTOM = """
settings:
  digits: 4
  prefix: CUSTOM
  sep: '-'
""".lstrip()

YAML_CUSTOM_PARENT = """
settings:
  digits: 4
  parent: PARENT
  prefix: CUSTOM
  sep: '-'
""".lstrip()


class MockDocument(MockFileObject, Document):  # pylint: disable=W0223,R0902,R0904
    """Mock Document class with stubbed file IO."""


@patch('doorstop.core.item.Item', MockItem)  # pylint: disable=R0904
class TestDocument(unittest.TestCase):  # pylint: disable=R0904
    """Unit tests for the Document class."""  # pylint: disable=C0103,W0212

    def setUp(self):
        self.document = MockDocument(FILES, root=ROOT)

    def test_load_empty(self):
        """Verify loading calls read."""
        self.document.load()
        self.document._read.assert_called_once_with(self.document.config)

    def test_load_error(self):
        """Verify an exception is raised with invalid YAML."""
        self.document._file = "invalid: -"
        self.assertRaises(DoorstopError, self.document.load)

    def test_load(self):
        """Verify the document config can be loaded from file."""
        self.document._file = YAML_CUSTOM
        self.document.load()
        self.assertEqual('CUSTOM', self.document.prefix)
        self.assertEqual('-', self.document.sep)
        self.assertEqual(4, self.document.digits)

    def test_load_parent(self):
        """Verify the document config can be loaded from file with a parent."""
        self.document._file = YAML_CUSTOM_PARENT
        self.document.load()
        self.assertEqual('PARENT', self.document.parent)

    def test_save_empty(self):
        """Verify saving calls write."""
        self.document.save()
        self.document._write.assert_called_once_with(YAML_DEFAULT,
                                                     self.document.config)

    def test_save_parent(self):
        """Verify a document can be saved with a parent."""
        self.document.parent = 'SYS'
        self.document.save()
        self.assertIn("parent: SYS", self.document._file)

    def test_str(self):
        """Verify documents can be converted to strings."""
        common.VERBOSITY = 2
        self.assertEqual("REQ", str(self.document))

    def test_str_verbose(self):
        """Verify documents can be converted to strings in verbose mode."""
        common.VERBOSITY = 3
        relpath = os.path.relpath(self.document.path, self.document.root)
        text = "REQ (@{}{})".format(os.sep, relpath)
        self.assertEqual(text, str(self.document))

    def test_ne(self):
        """Verify document non-equality is correct."""
        self.assertNotEqual(self.document, None)

    def test_items(self):
        """Verify the items in a document can be accessed."""
        items = self.document.items
        logging.debug("items: {}".format(items))
        self.assertEqual(4, len(items))

    @patch('doorstop.core.document.Document', MockDocument)
    def test_new(self):
        """Verify a new document can be created with defaults."""
        path = os.path.join(EMPTY, '.doorstop.yml')
        document = MockDocument.new(EMPTY, root=FILES, prefix='NEW', digits=2)
        self.assertEqual('NEW', document.prefix)
        self.assertEqual(2, document.digits)
        MockDocument._new.assert_called_once_with(path, name='document')

    def test_new_existing(self):
        """Verify an exception is raised if the document already exists."""
        self.assertRaises(DoorstopError, Document.new, FILES, ROOT, 'DUPL')

    def test_invalid(self):
        """Verify an exception is raised on an invalid document."""
        self.assertRaises(DoorstopError, Document, EMPTY)

    def test_relpath(self):
        """Verify the document's relative path string can be determined."""
        relpath = os.path.relpath(self.document.path, self.document.root)
        text = "@{}{}".format(os.sep, relpath)
        self.assertEqual(text, self.document.relpath)

    def test_prefix_relpath(self):
        """Verify the document's prefix and relpath can be determined."""
        relpath = os.path.relpath(self.document.path, self.document.root)
        text = "{} (@{}{})".format(self.document.prefix, os.sep, relpath)
        self.assertEqual(text, self.document.prefix_relpath)

    def test_depth(self):
        """Verify the maximum item level depth can be determined."""
        self.assertEqual(3, self.document.depth)

    def test_next(self):
        """Verify the next item number can be determined."""
        self.assertEqual(4, self.document.next)

    @patch('doorstop.core.item.Item.new')
    def test_add(self, mock_new):
        """Verify an item can be added to a document."""
        self.document.add()
        mock_new.assert_called_once_with(FILES, ROOT,
                                         'REQ', '', 3,
                                         4, level=(2, 2))

    @patch('doorstop.core.item.Item.new')
    def test_add_empty(self, mock_new):
        """Verify an item can be added to an new document."""
        document = MockDocument(NEW, ROOT)
        document.prefix = 'NEW'
        self.assertIsNot(None, document.add())
        mock_new.assert_called_once_with(NEW, ROOT,
                                         'NEW', '', 3,
                                         1, level=None)

    def test_find_item(self):
        """Verify an item can be found by ID."""
        item = self.document.find_item('req2')
        self.assertIsNot(None, item)

    def test_find_item_exact(self):
        """Verify an item can be found by its exact ID."""
        item = self.document.find_item('req2-001')
        self.assertIsNot(None, item)

    def test_find_item_unknown_number(self):
        """Verify an exception is raised on an unknown number."""
        self.assertRaises(DoorstopError, self.document.find_item, 'req99')

    def test_find_item_unknown_ID(self):
        """Verify an exception is raised on an unknown ID."""
        self.assertRaises(DoorstopError, self.document.find_item, 'unknown99')

    @patch('doorstop.core.item.Item.iter_issues')
    def test_valid(self, mock_iter_issues):
        """Verify a document can be validated."""
        mock_iter_issues.return_value = [DoorstopInfo('i')]
        self.assertTrue(self.document.valid())
        self.assertEqual(4, mock_iter_issues.call_count)

    @unittest.skipUnless(os.getenv(ENV), REASON)
    def test_valid_long(self):
        """Verify a document can be validated (long)."""
        self.assertTrue(self.document.valid())

    def test_valid_item(self):
        """Verify an item error fails the document check."""
        with patch.object(self.document, 'iter_issues',
                          Mock(return_value=[DoorstopError('e'),
                                             DoorstopWarning('w'),
                                             DoorstopInfo('i')])):
            self.assertFalse(self.document.valid())


class TestModule(unittest.TestCase):  # pylint: disable=R0904
    """Unit tests for the doorstop.core.document module."""  # pylint: disable=C0103

    def test_tbd(self):
        """Verify TBD."""
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
