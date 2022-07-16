# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc
import xbmcgui

import os
import requests

from resources.lib import logging
from resources.lib import qr
from resources.lib import settings
from resources.lib import tools
from resources.lib.github_api import GithubAPI

API = GithubAPI()

_addon_name = settings.get_addon_info("name")
_addon_data = tools.translate_path(settings.get_addon_info("profile"))

_color = settings.get_setting_string("general.color")


def raise_issue(repo):
    dialog = xbmcgui.Dialog()
    if title := dialog.input(settings.get_localized_string(30006)):
        description = dialog.input(settings.get_localized_string(30007))
        log_key = None
        response, log_key = logging.upload_log()

        if response:
            try:
                resp = API.raise_issue(
                    repo["user"],
                    repo["repo"],
                    _format_issue(title, description, log_key),
                )

                if "message" not in resp:
                    qr_code = qr.generate_qr(
                        resp["html_url"], _addon_data, f'{resp["number"]}.png'
                    )

                    top = [
                        (
                            settings.get_localized_string(30008),
                            "#efefefff",
                        ),
                        (f'{repo["user"]}/{repo["repo"]}', _color),
                    ]

                    bottom = [
                        (settings.get_localized_string(30079), "#efefefff"),
                        (resp["html_url"], _color),
                    ]
                    qr.qr_dialog(
                        qr_code,
                        top_text=top,
                        bottom_text=bottom,
                    )

                    tools.execute_builtin(f"ShowPicture({qr_code})")
                    while tools.get_condition("Window.IsActive(slideshow)"):
                        xbmc.sleep(1000)
                    os.remove(qr_code)
                else:
                    dialog.ok(_addon_name, resp["message"])
            except requests.exceptions.RequestException as e:
                dialog.notification(_addon_name, settings.get_localized_string(30009))
                tools.log(f"Error opening issue: {e}", "error")
    else:
        dialog.ok(_addon_name, settings.get_localized_string(30010))
    del dialog


def _format_issue(title, description, log_key):
    log_desc = f"{settings.get_localized_string(30012).format(_addon_name)}\n\n{description}\n\nLog File - {logging.log_url(log_key)}"


    return {"title": title, "body": log_desc}
