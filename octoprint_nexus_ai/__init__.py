# coding=utf-8
from __future__ import absolute_import

import flask
import octoprint.plugin
import requests
import os
import datetime
import json
from octoprint.events import Events
from octoprint.util import RepeatedTimer
from email.message import EmailMessage
from email.utils import formatdate


class NexusAIPlugin(octoprint.plugin.SettingsPlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.StartupPlugin,
                     octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.SimpleApiPlugin,
                     octoprint.plugin.EventHandlerPlugin
                     ):

    def __init__(self):
        self.repeated_timer = None
        self.refer_result = None  #nexus_ai's refer result
        # self.octotext_email = None

    def _timer_task(self):
        self.nexus_ai_request()

    # ~~ StartupPlugin API
    def on_after_startup(self):
        # helpers = self._plugin_manager.get_helpers("OctoText", "send_email")
        # if helpers and "send_email" in helpers:
        #     self.octotext_email = helpers["send_email"]
        #     self._logger.info("Fiberpunk: get OctoText plugin helpers")
        self._logger.info("Fiberpunk: Nexus AI plugin loaded!")

    # ~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            self._logger.info("Fiberpunk: print job started!!")
            self.repeated_timer = RepeatedTimer(self._settings.get["request_interval_time"], self._timer_task)
            self.repeated_timer.start()
        elif (event == Events.PRINT_CANCELLED) or (event == Events.PRINT_DONE) or (event == Events.PRINT_FAILED):
            self.repeated_timer.cancel()

    # ~~ SimpleApiPlugin mixin

    def get_api_commands(self):
        return dict(
            take_snapshot=[]
        )
    
    def nexus_ai_request(self):
        relative_url = self.take_snapshot("reference.jpg")
        if "reference_image" in relative_url:
            reference_image_timestamp = "{:%m/%d/%Y %H:%M:%S}".format(datetime.datetime.now())
            self._settings.set(["reference_image_timestamp"], reference_image_timestamp)
            self._settings.set(["reference_image"], relative_url["url"])
            relative_url["reference_image_timestamp"] = reference_image_timestamp
            self._settings.save()

            ip_address = self._settings.get(["nexus_ai_ip"])
            request_url = "http://{}:8002/upload".format(ip_address)
            result_img_url = "http://{}:8002/final_result.jpg".format(ip_address)
            upload_img = {"media": open(relative_url["reference_image"],"rb")}
            self._logger.info("Fiberpunk Nexus AI :")
            self._logger.info(relative_url["reference_image"])
            self._logger.info(ip_address)
            self._logger.info(request_url)
            if len(ip_address)>2:
                try:
                    response = requests.post(request_url, files=upload_img, timeout=5)
                    self._logger.info(response.text)
                    result_json = json.loads(response.text)
                    self._logger.info("Fiberpunk Nexus AI result count:")
                    self._logger.info(result_json["result_count"])
                    if result_json["result_count"]>0:
                        download_file_name = os.path.join(self.get_plugin_data_folder(), "reference.jpg")
                        self._logger.info("Fiberpunk Nexus AI download file name:")
                        self._logger.info(download_file_name)
                        response = requests.get(result_img_url, timeout=5)
                        if response.status_code == 200:
                            with open(download_file_name, "wb") as f:
                                f.write(response.content)

                    
                except requests.exceptions.ConnectionError:
                    self._logger.info("Fiberpunk Nexus AI : requests connect error")
                except:
                    self._logger.info("Fiberpunk Nexus AI : unknow error")     
            return relative_url

    def on_api_command(self, command, data):
        import flask

        if command == "take_snapshot":
            relative_url = self.nexus_ai_request()
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
        "octoprint.comm.protocol.atcommand.queuing": __plugin_implementation__.process_at_command
    }

    # global __plugin_helpers__
    # __plugin_helpers__ = {'check_bed': __plugin_implementation__.check_bed}
