# coding=utf-8
from __future__ import absolute_import

import flask
import octoprint.plugin
import requests
import os
import datetime
import json
from octoprint.events import Events


class NexusAIPlugin(octoprint.plugin.SettingsPlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.SimpleApiPlugin,
                     octoprint.plugin.EventHandlerPlugin
                     ):

    # ~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
        pass

    # ~~ SimpleApiPlugin mixin

    def get_api_commands(self):
        return dict(
            take_snapshot=[]
        )

    def on_api_command(self, command, data):
        import flask

        if command == "take_snapshot":
            relative_url = self.take_snapshot("reference.jpg")
            if "reference_image" in relative_url:
                reference_image_timestamp = "{:%m/%d/%Y %H:%M:%S}".format(datetime.datetime.now())
                self._settings.set(["reference_image_timestamp"], reference_image_timestamp)
                self._settings.set(["reference_image"], relative_url["url"])
                relative_url["reference_image_timestamp"] = reference_image_timestamp
                self._settings.save()

                ip_address = self._settings.get(["nexus_ai_ip"])
                request_url = "http://{}:8002/upload".format(ip_address)
                upload_img = {"media": open(relative_url["reference_image"],"rb")}
                self._logger.info("fiberpunk debug:")
                self._logger.info(relative_url["reference_image"])
                self._logger.info(ip_address)
                self._logger.info(request_url)
                if len(ip_address)>2:
                    try:
                        response = requests.post(request_url, files=upload_img, timeout=5)
                        self._logger.info(response.text)
                        result_json = json.loads(response.text)
                        self._logger.info("the result count:")
                        self._logger.info(result_json["result_count"])
                        
                    except requests.exceptions.ConnectionError:
                        self._logger.info("fiberpunk: requests connect error")
                        return flask.jsonify({"error": "connect error"})
                    except:
                        self._logger.info("fiberpunk: requests unknow error")
                        return flask.jsonify({"error": "unknow error"})

                return flask.jsonify(relative_url)


    def take_snapshot(self, filename=None, filetype="reference_image"):
        snapshot_url = self._settings.global_get(["webcam", "snapshot"])
        if snapshot_url == "" or not filename or not snapshot_url.startswith("http"):
            return {"error": "missing or incorrect snapshot url in webcam & timelapse settings."}

        download_file_name = os.path.join(self.get_plugin_data_folder(), filename)
        response = requests.get(snapshot_url, timeout=20)
        if response.status_code == 200:
            with open(download_file_name, "wb") as f:
                f.write(response.content)
            if os.path.exists(download_file_name):
                return {filetype: download_file_name, "url": "plugin/nexus_ai/images/{}?{:%Y%m%d%H%M%S}".format(filename, datetime.datetime.now())}
            else:
                return {"error": "unable to save file."}
        else:
            return {"error": "unable to download snapshot."}

    # ~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            "reference_image": "",
            "reference_image_timestamp": "",
            "nexus_ai_ip":"",
            "request_interval_time":4,
        }

    # ~~ AssetPlugin mixin

    def get_assets(self):
        return {
            "css": ["css/nexus_ai.css"],
            "js": ["js/nexus_ai.js"]
        }

    # ~~ TemplatePlugin mixin

    def get_template_vars(self):
        return {"plugin_version": self._plugin_version}

    # ~~ Route hook

    def route_hook(self, server_routes, *args, **kwargs):
        from octoprint.server.util.tornado import LargeResponseHandler, path_validation_factory
        from octoprint.util import is_hidden_path
        return [
            (r"/images/(.*)", LargeResponseHandler, dict(path=self.get_plugin_data_folder(),
                                                         as_attachment=True,
                                                         path_validation=path_validation_factory(
                                                             lambda path: not is_hidden_path(path), status_code=404)))
        ]

    def compare_images(self, reference_image, comparison_image):
        return 0.5

    # ~~ @ command hook

    def process_at_command(self, comm, phase, command, parameters, tags=None, *args, **kwargs):
        pass

    def check_bed(self):
        pass

    # ~~ Softwareupdate hook

    def get_update_information(self):
        return {
            "nexus_ai": {
                "displayName": "Nexus AI",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "fiberpunk",
                "repo": "OctoPrint-Nexus-AI",
                "current": self._plugin_version,


            }
        }


__plugin_name__ = "Nexus AI"
__plugin_pythoncompat__ = ">=3.6,<4" 


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = NexusAIPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.server.http.routes": __plugin_implementation__.route_hook,
        # "octoprint.comm.protocol.atcommand.queuing": __plugin_implementation__.process_at_command
    }

    # global __plugin_helpers__
    # __plugin_helpers__ = {'check_bed': __plugin_implementation__.check_bed}
