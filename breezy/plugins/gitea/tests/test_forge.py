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

from datetime import datetime

from breezy.tests import TestCase

from .. import forge as gitea_forge
from ..forge import (
    Gitea,
    NotGiteaUrl,
    NotMergeRequestUrl,
    UnsupportedForge,
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


class ProbeFromUrlBaseUrlTests(TestCase):
    """probe_from_url must ask for credentials under the URL a self-hosted
    instance was actually cloned from, not an assumed default HTTPS port.
    """

    def _probe_and_capture_requested_url(self, url):
        requested = []

        def fake_get_transport(base_url, possible_transports=None):
            requested.append(base_url)

            class FakeTransport:
                base = base_url

            return FakeTransport()

        self.overrideAttr(gitea_forge, "get_transport", fake_get_transport)
        self.overrideAttr(gitea_forge, "get_credentials_by_url", lambda url: None)

        # No credentials are ever returned above, so probe_from_url always
        # raises UnsupportedForge - that's fine, the point of this test is
        # which URL it asked get_transport/get_credentials_by_url for.
        self.assertRaises(UnsupportedForge, Gitea.probe_from_url, url)
        return requested[0]

    def test_http_reuses_scheme_and_nondefault_port(self):
        self.assertEqual(
            "http://gitea.example.com:3000",
            self._probe_and_capture_requested_url(
                "http://gitea.example.com:3000/owner/repo.git"
            ),
        )

    def test_https_reuses_scheme_and_nondefault_port(self):
        self.assertEqual(
            "https://gitea.example.com:8443",
            self._probe_and_capture_requested_url(
                "https://gitea.example.com:8443/owner/repo"
            ),
        )

    def test_https_default_port_stays_bare(self):
        self.assertEqual(
            "https://codeberg.org",
            self._probe_and_capture_requested_url(
                "https://codeberg.org/jelmer/example"
            ),
        )

    def test_git_ssh_has_no_web_port_falls_back_to_https(self):
        self.assertEqual(
            "https://gitea.example.com",
            self._probe_and_capture_requested_url(
                "git+ssh://git@gitea.example.com:2222/owner/repo.git"
            ),
        )
