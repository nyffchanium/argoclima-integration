# Argoclima for Home Assistant

[![GitHub Release][release-badge]][releases]
[![HACS][hacs-badge]][hacs]
[![CI][ci-badge]][ci]
[![License][license-badge]](LICENSE)

Unofficial Home Assistant integration for Argo (Argoclima) WiFi air conditioners. It talks to the device directly over the local network, using the same undocumented API as the Argo web app.

> **Maintained fork** of [@nyffchanium](https://github.com/nyffchanium)'s [argoclima-integration][upstream], which is no longer maintained and stopped working with Home Assistant 2026.10. It includes the open pull requests of the original repository. Existing installations can [switch over](#switching-from-the-original-integration) without setting their devices up again.

## Supported devices

| Device                 | Status    |
| ---------------------- | --------- |
| Ulisse 13 DCI Eco WiFi | Supported |

Other WiFi models likely use the same API. If you own one, please [open an issue][issues].

## Features

| Feature                        | Entity                     |
| ------------------------------ | -------------------------- |
| On / off, operation mode       | `climate`                  |
| Current and target temperature | `climate`                  |
| Fan speed                      | `climate` fan mode         |
| Eco, turbo and night mode      | `climate` preset           |
| Eco mode power limit           | `number`                   |
| Display unit (°C / °F)         | `select`                   |
| Active timer                   | `select`                   |
| Device light                   | `switch`                   |
| Use remote temperature         | `switch`                   |
| Set time and weekday           | `argoclima.set_time` action |
| Firmware version               | device info                |

Flap and filter mode, timer configuration and device reset are not implemented.

## Installation

Requires Home Assistant 2025.10 or newer.

### HACS

1. In HACS, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/Gadund/argoclima-integration` with type **Integration**.
3. Search for **Argoclima**, download it and restart Home Assistant.

### Manual

Copy `custom_components/argoclima` from the [latest release][releases] into the `custom_components` folder of your Home Assistant configuration and restart Home Assistant.

### Switching from the original integration

Your devices and entities are kept, including entity ids, history, names, areas and automations.

1. In HACS, remove the original Argoclima integration. This only removes its files; your devices stay configured.
2. Install this repository as described above and restart Home Assistant.

Existing entities are migrated automatically on startup. If you end up with duplicated entities ending in `_2`, please [open an issue][issues] with the [debug log](#troubleshooting).

## Configuration

Assign the device a static IP address in your router first. The integration addresses the device by IP.

Go to **Settings → Devices & services → Add integration → Argoclima** and choose **Set up device manually**. Select the device type, give it a name and enter its IP address. The IP address can be changed later in the integration options.

### Dummy server

By default, the device keeps a connection to Argo's cloud server (`31.14.128.210`). The device and therefore this integration only work reliably while that server answers. The built-in dummy server replaces it, so all traffic stays in your local network. The official Argo web app no longer works while the dummy server is in use.

1. Go to **Add integration → Argoclima → Set up Argoclima Dummy Server** and choose a port (default `8080`).
2. On your router, forward (DNAT) the device's traffic for `31.14.128.210:80` to `<Home Assistant IP>:<port>`. If possible, limit the rule to the IP of your Argo device.

Devices reporting to the dummy server are discovered automatically and appear under it. They then receive state updates by push instead of being polled.

### Using the remote's temperature sensor

The temperature sensor in the remote can be used instead of the one in the device:

1. Cover the remote's IR diode so it doesn't overwrite the device's settings.
2. Turn the remote on (grid lines and fan icon are visible).
3. Turn on **Use Remote Temperature** in Home Assistant. Enabling remote temperature mode on the remote itself (hold the fan button for 2 seconds; the user icon appears) may also be required.

The remote sends the temperature roughly every 6 minutes and whenever the displayed value changes.

## Limitations

- The device only processes the most recent request; a running request is cancelled by a new one. Avoid using the official web app at the same time.
- Changes are re-sent until the device confirms them, up to three times.
- Write-only settings (time, weekday) can't be confirmed and are sent once.
- Eco, turbo and night mode can be combined on the remote but are exposed as mutually exclusive presets.

## Troubleshooting

To get debug logs, add this to `configuration.yaml` and restart:

```yaml
logger:
  logs:
    custom_components.argoclima: debug
```

**The device can't be added or is unavailable although the IP is correct.**
Unplug the device for about a minute and try again.

**The connection drops every few seconds.**
This happens when Argo's server is overloaded: the device resets its WiFi connection when its requests to the server time out. Use the [dummy server](#dummy-server).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- [@nyffchanium](https://github.com/nyffchanium) wrote the original integration. You can [buy them a coffee](https://www.buymeacoffee.com/nyffchanium).
- [@lallinger](https://github.com/lallinger) contributed the original dummy server.
- Thanks to everyone who contributed pull requests to the original repository.

[upstream]: https://github.com/nyffchanium/argoclima-integration
[issues]: https://github.com/Gadund/argoclima-integration/issues
[releases]: https://github.com/Gadund/argoclima-integration/releases
[release-badge]: https://img.shields.io/github/v/release/Gadund/argoclima-integration
[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[ci]: https://github.com/Gadund/argoclima-integration/actions/workflows/ci.yml
[ci-badge]: https://github.com/Gadund/argoclima-integration/actions/workflows/ci.yml/badge.svg
[license-badge]: https://img.shields.io/github/license/Gadund/argoclima-integration
