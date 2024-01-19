![Project Status][project-status-shield]
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

# Home Assistant Integration for Argoclima (Argo) climate control devices

This is an unofficial Home Assistant integration I wrote for my Argo Ulisse Eco WiFi, using the undocumented API used by the webapp.

## Supported devices and features

At the moment, only the device I own is supported. There is a good chance that other wifi capable devices use the same API though. So if you own a different device, please feel free to get in touch or contribute.
| Feature | Implementation / Supported for | Ulisse 13 DCI Eco WiFi |
| ---------------------------- | ------------------------------ | ---------------------- |
| on / off | `climate` operation | ✓ |
| operation mode | `climate` operation | ✓ |
| eco mode | `climate` preset | ✓ |
| turbo mode | `climate` preset | ✓ |
| night mode | `climate` preset | ✓ |
| current temperature | `climate` | ✓ |
| set target temperature | `climate` | ✓ |
| set fan speed | `climate` fan mode | ✓ |
| set flap mode | x | - |
| set filter mode | x | - |
| set active timer | `select` | ✓ |
| use remote temperature | `switch` | ✓ |
| timer configuration | x | x |
| set current time and weekday | set_time service | ✓ |
| device lights on / off | `switch` | ✓ |
| display unit \* | `select` | ✓ |
| eco mode power limit | `number` | ✓ |
| firmware version \*\* | device registry | ✓ |
| reset device | x | x |

[`text`] _platform the feature is represented by in HA_\
[-] _not supported by the device_\
[x] _not implemented_

\* This only affects the value displayed on the device and the web interface.
\*\* Not visible in the frontend.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `argoclima`.
4. Download _all_ the files from the `custom_components/argoclima/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Argoclima"

## Adding your device to Home Assistant

At the moment, the integration will communicate with the device locally. Cloud based communication is not supported.

### Set up WiFi

Follow the instructions provided with the device to connect it to your network. Once that is done, I highly recommend assigning it a static IP via router configuration. The integration is IP based and can not identify the device by any other means.

### Configuration

Select your device type, give it a name and enter the IP. The IP can be changed later.\
![configuration](config.png)

## Using the Remote Sensor

The temperature sensor integrated in the remote can still be used.\
To make this work:

1. To not overwrite the device's configuration, e.g. cover up the IR diode of the remote.
2. Set the state of the remote to On (indicated by e.g. the grid lines and the fan icon being visible).
3. Enable remote temperature mode (indicated by the user icon, toggled by holding the fan button for 2 seconds). _This might not be required. Not sure._

If my observations are correct, the remote will now send the temperature (no other settings):

- every 6 minutes if no change is detected
- whenever the temperature displayed on the remote changes

Probably more often, but that's what I found.

## Dummy Server

By default, your device periodically communicates with Argos's server (hardcoded IP `31.14.128.210`). Without this connection, the API this integration uses won't work. This repository provides a dummy server docker image, so you can keep the traffic in your local network. By doing this, you will lose the ability to use the original web UI.

You can pull the docker image from https://hub.docker.com/r/nyffchanium/argoclima-dummy-server, or you can run the server without docker by using the Go script in the `dummy-server` folder.

You can set the port the dummy server listens to via the env `SERVER_PORT`. It defaults to `8080`.

### Routing
For the dummy server to be of any use, you need to redirect the traffic to it. As the original server is a hardcoded public IP you need to change the routing through your router.

Example with an Asus router running Asuswrt-Merlin:
1. Enable custom scripts and SSH via the router UI (Administration -> System).
2. SSH into your router and create a file called `nat-start` in `/jffs/scripts` (replace `YOUR_SERVER` and `YOUR_PORT` with the address and port of your dummy server instance).
   ```sh
   #!/bin/sh
   iptables -t nat -I PREROUTING -s 0.0.0.0/0 -d 31.14.128.210 -p tcp -j DNAT --to-destination YOUR_SERVER:YOUR_PORT
   ```
4. Make sure the file is executable. `chmod a+rx /jffs/scripts/*`.
5. Restart your router.

## Restrictions / Problems

- With the remote / web interface, the _eco_, _turbo_ and _night_ modes can be activated all at the same time. It is possible to implement this, but I find it unnecessary. I don't know whether those mixed modes would actually do something "special" or if it's just ignored. If you need any of these combinations, open an issue.
- If an API request is sent while another one is still in progress, the latter will be cancelled. It does not matter whether any of the requests actually changes anything. I.e. concerning parallel requests, only the most recent one is regarded by the device.\
  Because of this, you should not use the official wep app in addition to this integration.
- In case a value could not be changed (due to the problem mentioned above), it will be sent again until it is confirmed.
- Because the response of an update request does not contain the updated information, updates will be sent twice in most cases.
- There are however settings that can only be written and thus there is no way to check if they have been accepted. This affects current time and weekday, timer configuration and reset. Those values will only be sent once.

## Troubleshooting

**Device can't be created / Device is unavailable, the IP is correct and the device is connected:**\
Turn off the device and unplug it, leave it for _an unknown amount of time (1min is enough for sure)_, then try again.

**Home Assistant loses the connection to the device every few seconds:**\
![image](https://github.com/nyffchanium/argoclima-integration/assets/55743116/9a19f95c-9685-4a49-a959-22d8ce2db0de)\
This seems to be caused by Argo's server being overloaded and not responding to the device's requests. Apparently, dropped / timed out requests result in the device resetting the WLAN connection.\
At the moment, the only known workaround is to use the [dummy server](#dummy-server).

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

The dummy server has been contributed by [@lallinger](https://github.com/lallinger).

This project was initially generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter][cookie_cutter] template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template.

---

[argoclima]: https://github.com/nyffchanium/argoclima-integration
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[project-status-shield]: https://img.shields.io/badge/project%20status-released-brightgreen.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/nyffchanium
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/nyffchanium/argoclima-integration.svg?style=for-the-badge
[commits]: https://github.com/nyffchanium/argoclima-integration/commits/master
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Default-brightgreen.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license]: https://github.com/nyffchanium/argoclima-integration/blob/master/LICENSE
[license-shield]: https://img.shields.io/github/license/nyffchanium/argoclima-integration.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40nyffchanium-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/nyffchanium/argoclima-integration.svg?style=for-the-badge
[releases]: https://github.com/nyffchanium/argoclima-integration/releases
[user_profile]: https://github.com/nyffchanium
[cookie_cutter]: https://github.com/oncleben31/cookiecutter-homeassistant-custom-component
[integration_blueprint]: https://github.com/custom-components/integration_blueprint
