/*
 * View model for OctoPrint-BedReady
 *
 * Author: jneilliii
 * License: AGPLv3
 */
$(function () {
    function NexusAIViewModel(parameters) {
        var self = this;

        self.taking_snapshot = ko.observable(false);
        self.popup_options = {
            title: 'Bed Not Ready',
            text: '',
            hide: false,
            type: 'error',
            addclass: 'nexus_ai_notice',
            buttons: {
                sticker: false
            }
        };

        self.settingsViewModel = parameters[0];
        self.controlViewModel = parameters[1];

        self.snapshot_valid = ko.pureComputed(function(){
            return self.settingsViewModel.webcam_snapshotUrl().length > 0 && self.settingsViewModel.webcam_snapshotUrl().startsWith('http');
        });

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== 'nexus_ai') {
                return;
            }

            if (data.hasOwnProperty('similarity') && !data.bed_clear) {
                self.popup_options.text = '<div class="row-fluid"><p>Match percentage calculated as <span class="label label-warning">' + (parseFloat(data.similarity) * 100).toFixed(2) + '%</span>.</p><p>Print job has been paused, check bed and then resume.</p><p><img src="/plugin/nexus_ai/images/compare.jpg?' + Math.round(new Date().getTime() / 1000) + '"></p></div>';
                self.popup_options.type = 'error';
                self.popup_options.title = 'Bed Not Ready';
                if (self.popup === undefined) {
                    self.popup = PNotify.singleButtonNotify(self.popup_options);
                } else {
                    self.popup.update(self.popup_options);
                    if (self.popup.state === 'closed'){
                        self.popup.open();
                    }
                }
            } else if (self.popup !== undefined && data.bed_clear) {
                self.popup.remove();
                self.popup = undefined;
            } else if (data.hasOwnProperty('error')) {
                self.popup_options.text = 'There was an error: ' + data.error.error;
                self.popup_options.type = 'error';
                self.popup_options.title = 'Bed Ready Error';
                if (self.popup === undefined) {
                    self.popup = PNotify.singleButtonNotify(self.popup_options);
                } else {
                    self.popup.update(self.popup_options);
                    if (self.popup.state === 'closed'){
                        self.popup.open();
                    }
                }
            }
        };

        self.take_snapshot = function () {
            self.taking_snapshot(true);
            OctoPrint.simpleApiCommand('nexus_ai', 'take_snapshot')
                .done(function (response) {
                    if (response.hasOwnProperty('reference_image')) {
                        self.settingsViewModel.settings.plugins.nexus_ai.reference_image(response.url);
                        self.settingsViewModel.settings.plugins.nexus_ai.reference_image_timestamp(response.reference_image_timestamp);
                    } else {
                        new PNotify({
                            title: 'Bed Ready Error',
                            text: '<div class="row-fluid"><p>There was an error saving the reference snapshot.</p></div><p><pre style="padding-top: 5px;">' + response.error + '</pre></p>',
                            hide: true
                        });
                    }
                    self.taking_snapshot(false);
                });
        };

        self.test_snapshot = function () {
            self.taking_snapshot(true);
            OctoPrint.simpleApiCommand('nexus_ai', 'take_snapshot', {test: true})
                .done(function (response) {
                    if (response.hasOwnProperty('test_image')) {
                        self.popup_options.text = '<div class="row-fluid"><p>Match percentage calculated as <span class="label label-info">' + (parseFloat(response.similarity) * 100).toFixed(2) + '%</span>.</p><p><img src="' + response.test_image + '"></p></div>';
                        if (parseFloat(response.similarity) < parseFloat(self.settingsViewModel.settings.plugins.nexus_ai.match_percentage())) {
                            self.popup_options.type = 'error';
                        } else {
                            self.popup_options.type = 'success';
                        }

                        self.popup_options.title = 'Bed Ready Test';
                        if (self.popup === undefined) {
                            self.popup = PNotify.singleButtonNotify(self.popup_options);
                        } else {
                            self.popup.update(self.popup_options);
                            if (self.popup.state === 'closed') {
                                self.popup.open();
                            }
                        }
                    }
                    self.taking_snapshot(false);
                });
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: NexusAIViewModel,
        dependencies: ['settingsViewModel', 'controlViewModel'],
        elements: ['#settings_plugin_nexus_ai']
    });
});
