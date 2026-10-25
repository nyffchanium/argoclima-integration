# Blueprints

Ready-made automations for Argoclima devices. Click a button to import a blueprint into Home Assistant, then create an automation from it in **Settings → Automations & scenes → Blueprints**.

## Turn off while a window is open

[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nyffchanium/argoclima-integration/blob/master/blueprints/automation/argoclima/window_open.yaml)

Turns the air conditioner off when a window or door has been open for a while (default 1 minute) and restores its previous mode, temperature and fan speed once it has been closed again (default 30 seconds). If the air conditioner was already off, it stays off. With [anti-mold](features.md#anti-mold) enabled, the device dries before turning off as usual.

## Turn off when everyone has left

[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nyffchanium/argoclima-integration/blob/master/blueprints/automation/argoclima/away.yaml)

Turns one or more air conditioners off when nobody has been in a zone (default: home) for a while (default 15 minutes).

## Remote out of sight

[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/nyffchanium/argoclima-integration/blob/master/blueprints/automation/argoclima/remote_out_of_sight.yaml)

Notifies you when the device stops receiving the temperature from its remote and falls back to its own sensor, i.e. when [Temperature source](features.md#using-the-remotes-temperature-sensor) changes to **Device** while **Use remote temperature** is on. The device itself already waits about 7 minutes before switching; the blueprint waits 1 more minute by default. By default, it creates a notification in Home Assistant.
