[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

## Supported devices and features

At the moment, only the device I own is supported. There is a good chance that other wifi capable devices use the same API thoug. So if you own a different device, please feel free to get in touch or contribute.

| Feature / Device             | Ulisse 13 DCI Eco WiFi |
| ---------------------------- | ---------------------- |
| on / off                     | `climate` operation    |
| operation mode               | `climate` operation    |
| eco mode                     | `climate` preset       |
| turbo mode                   | `climate` preset       |
| night mode                   | `climate` preset       |
| current temperature          | `climate`              |
| set target temperature       | `climate`              |
| set fan speed                | `climate` fan mode     |
| set flap mode                | -                      |
| set filter mode              | -                      |
| set timer mode               | x                      |
| timer configuration          | x                      |
| set current time and weekday | x                      |
| device lights on / off       | x                      |
| measurement unit             | x                      |
| eco mode power limit         | x                      |
| firmware version             | x                      |
| firmware version             | x                      |
| reset device                 | x                      |

[`text`] _platform the features is represented by in HA_\
[-] _not supported by the device_\
[x] _not implemented_

{% if not installed %}

## Installation

1. Click install.
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Argoclima".

{% endif %}

## Adding your device to Home Assistant

At the moment, the integration will communicate with the device locally. Cloud based communication is not supported.

### Set up WiFi

Follow the instructions provided with the device to connect it to your network. Once that is done, I highly recommend assigning it a static IP via router configuration. The integration is IP based and can not identify the device by any other means.

### Configuration

Select your device type, give it a name and enter the IP. The IP can be changed later.\
![configuration](https://raw.githubusercontent.com/nyffchanium/argoclima-integration/master/config.png)

## Credits

This project was generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component) template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

---

[argoclima]: https://github.com/nyffchanium/argoclima-integration
[buymecoffee]: https://www.buymeacoffee.com/nyffchanium
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/nyffchanium/argoclima-integration.svg?style=for-the-badge
[commits]: https://github.com/nyffchanium/argoclima-integration/commits/master
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license]: https://github.com/nyffchanium/argoclima-integration/blob/master/LICENSE
[license-shield]: https://img.shields.io/github/license/nyffchanium/argoclima-integration.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40nyffchanium-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/nyffchanium/argoclima-integration.svg?style=for-the-badge
[releases]: https://github.com/nyffchanium/argoclima-integration/releases
[user_profile]: https://github.com/nyffchanium
