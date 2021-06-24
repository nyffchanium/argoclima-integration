[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

# Home Assistant Integration for Argoclima (Argo) climate control devices
This is an unoffical Home Assistant integration I wrote for my Argo Ulisse Eco, using the undocumented API used by the webapp.

## Supported devices
At the moment, only the device I own is supported. There is a good chance that other wifi capable devices use the same API thoug. So if you own a different device, please feel free to get in touch or contribute.

Device | Notes
-- | --
Ulisse 13 DCI Eco WiFi | basic functionality is implemented

**This component will set up the following platforms.**

Platform | Description
-- | --
`climate` | Control of the Argoclima device.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `argoclima`.
4. Download _all_ the files from the `custom_components/argoclima/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Argoclima"

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

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
[license]: https://github.com/nyffchanium/argoclima-integration/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/nyffchanium/argoclima-integration.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Stefan%20Nyffenegger%20%40nyffchanium-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/nyffchanium/argoclima-integration.svg?style=for-the-badge
[releases]: https://github.com/nyffchanium/argoclima-integration/releases
[user_profile]: https://github.com/nyffchanium
