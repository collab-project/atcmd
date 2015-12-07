# Copyright (c) Collab and contributors.
# See LICENSE for details.

"""
Tests for library version.
"""

from unittest import TestCase

from atcmd import get_version


class VersionTestCase(TestCase):
    """
    Tests for :py:mod:`~atcmd` versioning information.
    """
    def test_regularVersion(self):
        """
        :py:func:`~atcmd.get_version` returns a string version without
        any beta tags, eg. `1.0.1`.
        """
        version = (1, 0, 1)
        self.assertEqual(get_version(version), '1.0.1')

    def test_betaVersion(self):
        """
        :py:func:`~atcmd.get_version` returns a string version with beta tags,
        eg. `1.2.3b1`.
        """
        version = (1, 2, 3, 'b1')
        self.assertEqual(get_version(version), '1.2.3b1')