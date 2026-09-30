# Copyright (C) 2021 Jelmer Vernooij <jelmer@jelmer.uk>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
from datetime import datetime

from breezy import bedding
from breezy.forge import UnsupportedForge
from breezy.tests import TestCase, TestCaseInTempDir

from ..forge import (
    Gitea,
    NotGiteaUrl,
    NotMergeRequestUrl,
    parse_gitea_merge_request_url,
    parse_gitea_url,
    parse_timestring,
)


class ParseGiteaUrlTests(TestCase):
    def test_simple(self):
        self.assertEqual(
            ("codeberg.org", "jelmer/example"),
            parse_gitea_url("https://codeberg.org/jelmer/example"),
        )

    def test_strip_git_suffix(self):
        self.assertEqual(
            ("codeberg.org", "jelmer/example"),
            parse_gitea_url("https://codeberg.org/jelmer/example.git"),
        )

    def test_invalid_scheme(self):
        self.assertRaises(NotGiteaUrl, parse_gitea_url, "bzr://codeberg.org/jelmer/x")

    def test_missing_host(self):
        self.assertRaises(NotGiteaUrl, parse_gitea_url, "https:///jelmer/x")


class ParseGiteaMergeRequestUrlTests(TestCase):
    def test_simple(self):
        self.assertEqual(
            ("codeberg.org", "jelmer/example", 4),
            parse_gitea_merge_request_url(
                "https://codeberg.org/jelmer/example/pulls/4"
            ),
        )

    def test_not_a_pull(self):
        self.assertRaises(
            NotMergeRequestUrl,
            parse_gitea_merge_request_url,
            "https://codeberg.org/jelmer/example",
        )

    def test_issue_is_not_a_pull(self):
        self.assertRaises(
            NotMergeRequestUrl,
            parse_gitea_merge_request_url,
            "https://codeberg.org/jelmer/example/issues/4",
        )

    def test_invalid_scheme(self):
        self.assertRaises(
            NotGiteaUrl,
            parse_gitea_merge_request_url,
            "bzr://codeberg.org/jelmer/example/pulls/4",
        )


class ParseTimestringTests(TestCase):
    def test_offset(self):
        self.assertEqual(
            datetime(2018, 9, 7, 11, 16, 17),
            parse_timestring("2018-09-07T11:16:17+02:00"),
        )

    def test_zulu(self):
        self.assertEqual(
            datetime(2018, 9, 7, 11, 16, 17),
            parse_timestring("2018-09-07T11:16:17Z"),
        )


class ProbeFromHostnameTests(TestCaseInTempDir):
    def setUp(self):
        super().setUp()
        os.makedirs(bedding.config_dir(), exist_ok=True)
        with open(os.path.join(bedding.config_dir(), "gitea.conf"), "w") as f:
            f.write(
                "[example]\n"
                "url = http://gitea.example.com:3000/\n"
                "private_token = sekrit\n"
            )

    def test_known_hostname(self):
        forge = Gitea.probe_from_hostname("gitea.example.com")
        self.assertEqual("gitea.example.com", forge.base_hostname)

    def test_unknown_hostname(self):
        self.assertRaises(UnsupportedForge, Gitea.probe_from_hostname, "codeberg.org")
