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
| Firmware versions              | device info                |
| Firmware update check          | `update` (optional)        |

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

There are two ways to connect your devices. The dummy server is recommended.

### With the dummy server (recommended)

By default, the device stays connected to Argo's cloud server (`31.14.128.210`), and it only works reliably while that server answers. When the server is overloaded, the device keeps dropping its WiFi connection. The built-in dummy server takes the place of Argo's server inside Home Assistant:

- The device no longer depends on Argo's server, which avoids these connection drops. It keeps working without internet access and if Argo ever shuts its servers down.
- Devices report their state by themselves about every 12 seconds, so changes made on the device or the remote show up faster than with polling (every 15 seconds), and Home Assistant doesn't need to poll them.
- Devices are discovered automatically; adding several devices needs no extra steps.
- IP address changes are picked up automatically.

All traffic stays in your local network. The official Argo web app no longer works while the dummy server is in use.

1. Go to **Settings → Devices & services → Add integration → Argoclima**, choose **Set up Argoclima Dummy Server** and pick a port (default `8239`).
2. On your router, redirect (DNAT) the devices' traffic for `31.14.128.210:80` to `<Home Assistant IP>:<port>`. If the devices and Home Assistant are in the same subnet, an additional hairpin NAT rule and the dummy server's **NAT gateway** option are needed. See the **[DNAT guide](docs/dnat.md)** for step-by-step instructions for OPNsense, pfSense, UniFi, FortiGate, MikroTik, OpenWrt and Linux.
3. Each device shows up as a discovered device as soon as it reports to the dummy server. Confirm it and give it a name.

### Without the dummy server

Assign the device a static IP address in your router first; the integration addresses the device by IP and polls it every 15 seconds.

Go to **Settings → Devices & services → Add integration → Argoclima**, choose **Set up device manually**, select the device type, give it a name and enter its IP address. The IP address can be changed later in the integration options.

### Using the remote's temperature sensor

The temperature sensor in the remote can be used instead of the one in the device:

1. Cover the remote's IR diode so it doesn't overwrite the device's settings.
2. Turn the remote on (grid lines and fan icon are visible).
3. Turn on **Use Remote Temperature** in Home Assistant. Enabling remote temperature mode on the remote itself (hold the fan button for 2 seconds; the user icon appears) may also be required.

The remote sends the temperature roughly every 6 minutes and whenever the displayed value changes.

## Firmware updates

The device info shows the firmware of the device and, with the dummy server, of its WiFi module.

To be notified about new firmware, enable the **Firmware** (and **WiFi Firmware**) update entities of a device; they are disabled by default. Home Assistant then checks the latest versions on Argo's server once a day. The check doesn't send any credentials or device information.

Updates can't be installed from Home Assistant. Install them with the official Argo web app; if you use the dummy server, disable the DNAT rule while updating and enable it again afterwards. Argo publishes updates very rarely: as of October 2026, the latest versions are `01416` for the device and `00003` for the WiFi module.

## Limitations

- The device only processes the most recent request; a running request is cancelled by a new one. Avoid using the official web app at the same time.
- Changes are re-sent until the device confirms them, up to three times.
- Write-only settings (time, weekday) can't be confirmed and are sent once.
- Eco, turbo and night mode can be combined on the remote but are exposed as mutually exclusive presets.

## Security

The Argo device API and its cloud protocol have no authentication or encryption: anyone in your local network can control the device directly, with or without this integration. Keep your Argo devices in a trusted network.

- Never expose the dummy server port to the internet, and limit the DNAT rule to your Argo devices.
- The dummy server only accepts a device report if the IP address it claims matches the address it connects from, or if it comes from the configured NAT gateway. Limit your router's NAT rules to the Argo devices.
- The cloud credentials the device sends along are never stored and are removed from logs.

To report a vulnerability, see [SECURITY.md](SECURITY.md).

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
This happens when Argo's server is overloaded: the device resets its WiFi connection when its requests to the server time out. Use the [dummy server](#with-the-dummy-server-recommended).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- [@nyffchanium](https://github.com/nyffchanium) wrote the original integration. You can [buy them a coffee](https://www.buymeacoffee.com/nyffchanium).
- [@0SkillAllLuck](https://github.com/0SkillAllLuck) built the dummy server into the integration, including device discovery and push updates.
- [@SaphiraDraco](https://github.com/SaphiraDraco) made polling more robust and modernized the `set_time` action.
- [@soft-song3425](https://github.com/soft-song3425) fixed compatibility with Home Assistant 2026.10.
- [@pimeys](https://github.com/pimeys) replaced deprecated Home Assistant APIs.
- [@lallinger](https://github.com/lallinger) contributed the original dummy server.

[upstream]: https://github.com/nyffchanium/argoclima-integration
[issues]: https://github.com/Gadund/argoclima-integration/issues
[releases]: https://github.com/Gadund/argoclima-integration/releases
[release-badge]: https://img.shields.io/github/v/release/Gadund/argoclima-integration
[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[ci]: https://github.com/Gadund/argoclima-integration/actions/workflows/ci.yml
[ci-badge]: https://github.com/Gadund/argoclima-integration/actions/workflows/ci.yml/badge.svg
[license-badge]: https://img.shields.io/github/license/Gadund/argoclima-integration
