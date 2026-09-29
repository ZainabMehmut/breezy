# Copyright (C) 2020 Jelmer Vernooij <jelmer@jelmer.uk>
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from datetime import datetime

from dromedary import errors as transport_errors

from breezy.forge import UnsupportedForge
from breezy.tests import TestCase

from .. import forge as _mod_gitlab
from ..forge import (
    GitLab,
    NotGitLabUrl,
    NotMergeRequestUrl,
    parse_gitlab_merge_request_url,
    parse_timestring,
)


class ParseGitLabMergeRequestUrlTests(TestCase):
    def test_invalid(self):
        self.assertRaises(
            NotMergeRequestUrl,
            parse_gitlab_merge_request_url,
            "https://salsa.debian.org/",
        )
        self.assertRaises(
            NotGitLabUrl, parse_gitlab_merge_request_url, "bzr://salsa.debian.org/"
        )
        self.assertRaises(
            NotGitLabUrl, parse_gitlab_merge_request_url, "https:///salsa.debian.org/"
        )
        self.assertRaises(
            NotMergeRequestUrl,
            parse_gitlab_merge_request_url,
            "https://salsa.debian.org/jelmer/salsa",
        )

    def test_old_style(self):
        self.assertEqual(
            ("salsa.debian.org", "jelmer/salsa", 4),
            parse_gitlab_merge_request_url(
                "https://salsa.debian.org/jelmer/salsa/merge_requests/4"
            ),
        )

    def test_new_style(self):
        self.assertEqual(
            ("salsa.debian.org", "jelmer/salsa", 4),
            parse_gitlab_merge_request_url(
                "https://salsa.debian.org/jelmer/salsa/-/merge_requests/4"
            ),
        )


class ParseTimestringTests(TestCase):
    def test_simple(self):
        self.assertEqual(
            datetime(2018, 9, 7, 11, 16, 17, 520000),
            parse_timestring("2018-09-07T11:16:17.520Z"),
        )


class StubTransport:
    """Stand-in for the transport probing would otherwise open."""

    def __init__(self, base):
        self.base = base
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url))
        raise transport_errors.UnexpectedHttpStatus(url, 404)


class ProbeFromUrlTests(TestCase):
    def setUp(self):
        super().setUp()
        self.credentials = {"private_token": "sekrit"}
        self.transports = []
        self.overrideAttr(_mod_gitlab, "get_transport", self._get_transport)
        self.overrideAttr(
            _mod_gitlab, "get_credentials_by_url", lambda url: self.credentials
        )
        self.overrideAttr(GitLab, "_retrieve_user", lambda self: None)

    def _get_transport(self, url, possible_transports=None):
        transport = StubTransport(url)
        self.transports.append(transport)
        return transport

    def test_scheme_and_port_preserved(self):
        forge = GitLab.probe_from_url("http://gitlab.example.com:8080/jelmer/example")
        self.assertEqual("http://gitlab.example.com:8080/", forge.base_url)

    def test_ssh_url_probed_over_https(self):
        forge = GitLab.probe_from_url(
            "git+ssh://git@gitlab.example.com:2222/jelmer/example"
        )
        self.assertEqual("https://gitlab.example.com/", forge.base_url)

    def test_api_request_uses_the_same_base(self):
        self.credentials = None
        self.assertRaises(
            UnsupportedForge,
            GitLab.probe_from_url,
            "http://gitlab.example.com:8080/jelmer/example",
        )
        self.assertEqual(
            [
                (
                    "GET",
                    "http://gitlab.example.com:8080/api/v4/projects/jelmer%2Fexample",
                )
            ],
            self.transports[0].requests,
        )
