# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import collections
from requests import Session

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from resources.lib import settings

_per_page = settings.get_setting_int("general.commits_per_page")


class GithubAPI(Session):
    def __init__(self):
        super(GithubAPI, self).__init__()
        self.access_token = settings.get_setting_string("github.token")
        self.client_id = settings.get_setting_string("github.client_id")
        self.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

        self.base_url = "https://api.github.com/"
        self.auth_url = "https://github.com/login/"

    def _update_token(self):
        token = settings.get_setting_string("github.token")
        self.access_token = token
        self.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def get(self, endpoint, **params):
        return super(GithubAPI, self).get(
            urljoin(self.base_url, endpoint), params=params
        )

    def get_pages(self, endpoint, pages=1, limit=30, **params):
        headers = self.headers.copy()
        headers.update({"per_page": str(limit)})

        for i in range(1, pages + 1):
            headers.update({"page": str(i)})
            yield super(GithubAPI, self).get(
                urljoin(self.base_url, endpoint), headers=headers, **params
            )

    def get_pages_json(self, endpoint, pages=1, limit=30, **params):
        for page in self.get_pages(endpoint, pages, limit, **params):
            page = page.json()
            if isinstance(page, (list, set, collections.Sequence)):
                yield from page
            else:
                yield page

    def get_all_pages(self, endpoint, **params):
        response = self.get(endpoint, **params)
        yield response
        while response.links.get("next", {}).get("url"):
            response = self.get(response.links.get("next", {}).get("url"))
            yield response

    def post(self, endpoint, *args, **params):
        return super(GithubAPI, self).post(
            urljoin(self.base_url, endpoint), *args, **params
        )

    def post_json(self, endpoint, data):
        return self.post(endpoint, json=data).json()

    def get_all_pages_json(self, endpoint, **params):
        for page in self.get_all_pages(endpoint, **params):
            page = page.json()
            if isinstance(page, (list, set, collections.Sequence)):
                yield from page
            else:
                yield page

    def get_json(self, endpoint, **params):
        return self.get(endpoint, **params).json()

    def get_default_branch(self, user, repo):
        return self.get_json(f"repos/{user}/{repo}").get("default_branch")

    def get_repo_branch(self, user, repo, branch):
        return self.get_json(f"repos/{user}/{repo}/branches/{branch}")

    def get_repo_branches(self, user, repo):
        return self.get_all_pages_json(f"repos/{user}/{repo}/branches")

    def get_branch_commits(self, user, repo, branch):
        return self.get_pages_json(
            f"repos/{user}/{repo}/commits?sha={branch}", limit=_per_page
        )

    def raise_issue(self, user, repo, formatted_issue):
        return self.post_json(f"/repos/{user}/{repo}/issues", formatted_issue)

    def get_zipball(self, user, repo, branch):
        return self.get(f"/repos/{user}/{repo}/zipball/{branch}").content

    def get_commit_zip(self, user, repo, commit_sha):
        return self.get(f"{user}/{repo}/archive/{commit_sha}.zip").content

    def get_file(self, user, repo, path, text=False):
        if not text:
            return self.get_json(f"/repos/{user}/{repo}/contents/{path}")
        headers = self.headers.copy()
        headers.update({"Accept": "application/vnd.github.v3.raw"})
        response = super(GithubAPI, self).get(
            urljoin(self.base_url, f"/repos/{user}/{repo}/contents/{path}"),
            headers=headers,
        )

        if response.ok:
            return response.text

    def get_tags(self, user, repo):
        return self.get_all_pages_json(f"/repos/{user}/{repo}/git/refs/tags")

    def get_commit(self, user, repo, commit_sha):
        return self.get_json(f"/repos/{user}/{repo}/commits/{commit_sha}")

    def get_user(self, user):
        return self.get_json(f"/users/{user}")

    def get_username(self):
        self._update_token()
        return self.get_json("/user").get("login", "")

    def get_org_repos(self, org):
        return self.get_json(f"orgs/{org}/repos")

    def get_user_repos(self, user):
        return self.get_json(f"/users/{user}/repos")

    def get_repos(self, access=""):
        return self.get_all_pages_json(f"/user/repos?affiliation={access}")

    def authorize(self, code=None):
        result = (
            super(GithubAPI, self).post(
                urljoin(self.auth_url, "oauth/access_token"),
                data={
                    "client_id": self.client_id,
                    "device_code": code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers=self.headers,
            )
            if code
            else super(GithubAPI, self).post(
                urljoin(self.auth_url, "device/code"),
                data={"client_id": self.client_id, "scope": "repo read:user"},
                headers=self.headers,
            )
        )

        return result.json()

    def revoke(self):
        return self.post(
            f"applications/{self.client_id}/grant",
            data={"access_token": self.access_token},
        ).ok
