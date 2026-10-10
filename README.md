# Argoclima for Home Assistant

[![GitHub Release][release-badge]][releases]
[![HACS][hacs-badge]][hacs]
[![CI][ci-badge]][ci]
[![License][license-badge]](LICENSE)

Unofficial Home Assistant integration for Argo (Argoclima) WiFi air conditioners. It controls the device directly over your local network, no Argo account needed.

## Supported devices

| Device                 | Status    |
| ---------------------- | --------- |
| Ulisse 13 DCI Eco WiFi | Supported |

Other Argo WiFi models probably work too. If you own one, please [open an issue][issues] and tell us whether it works.

## What you get in Home Assistant

| Feature                        | Shown as                    |
| ------------------------------ | --------------------------- |
| On / off, mode, temperature    | Climate control             |
| Fan speed                      | Climate control (fan mode)  |
| Eco, turbo and night mode      | Climate control (preset)    |
| Eco mode power limit           | Number                      |
| Display unit (°C / °F)         | Selection                   |
| Active timer                   | Selection                   |
| Device light                   | Switch                      |
| Use remote temperature         | Switch                      |
| Connection and last contact    | Sensor                      |
| Set time and weekday           | `argoclima.set_time` action |
| Firmware versions              | Device info                 |
| Firmware update check          | Update (optional)           |

Flap and filter mode, timer schedules and device reset are not available.

## Getting started

Requires Home Assistant 2025.10 or newer and [HACS](https://hacs.xyz).

### 1. Connect the device to your WiFi

Follow the instructions that came with the device. Once it's connected, it shows up in your router's list of devices.

### 2. Give the device a fixed IP address

Home Assistant finds the device by its IP address, so the address must not change. In your router, look for **DHCP reservation**, **fixed IP** or **"always assign the same IP address"** (the name depends on the router) and set it up for the Argo device. Note the address, you'll need it in step 4.

### 3. Install the integration

1. In Home Assistant, open **HACS** and search for **Argoclima**.
2. Open it and click **Download**.
3. Restart Home Assistant (**Settings → System → Restart**).

Without HACS: copy the folder `custom_components/argoclima` from the [latest release][releases] into the `custom_components` folder of your Home Assistant configuration and restart.

### 4. Add your device

1. Go to **Settings → Devices & services → Add integration** and search for **Argoclima**.
2. Choose **Set up device manually**.
3. Give the device a name (e.g. "Living room") and enter its IP address from step 2.

That's it. The device and its controls now appear in Home Assistant. Home Assistant checks the device's state every 15 seconds; commands you send take effect right away. To change the IP address later, open the device's integration entry and click **Configure**.

## Updating from version 1.1.4 or earlier

Update the integration in HACS as usual and restart Home Assistant. Your devices and entities are kept, including entity ids, history, names, areas and automations. If you end up with duplicated entities ending in `_2`, please [open an issue][issues].

If you installed the fork `Gadund/argoclima-integration` as a custom repository in the meantime: in HACS, remove the custom repository (⋮ → **Custom repositories**), then download **Argoclima** again from the regular HACS list and restart. Your devices stay set up.

## Using the remote's temperature sensor

The device can use the temperature measured by the remote instead of its own sensor, which is often more accurate as the remote is usually closer to where you are.

The remote sends the temperature by **infrared**, the same way as its commands: only when it points at the device with a clear line of sight. It sends roughly every 6 minutes and whenever the displayed value changes.

1. Place the remote where it can "see" the device, e.g. on a shelf facing it.
2. Turn the remote on (grid lines and fan icon are visible).
3. Turn on **Use Remote Temperature** in Home Assistant. Enabling remote temperature mode on the remote itself (hold the fan button for 2 seconds; the user icon appears) may also be required.

Each transmission also includes the remote's own settings, which can overwrite changes made in Home Assistant. If that's a problem, keep the remote's settings in line with what you set in Home Assistant, or use the device's own sensor.

## Advanced: dummy server

**Optional.** The integration works fine without it. It's worth setting up if your device often loses its connection, or if you want it to work without the manufacturer's cloud.

Argo devices are permanently connected to the manufacturer's cloud on the internet. When the cloud is overloaded, the device keeps dropping its WiFi connection, and if Argo ever shuts it down, the device can no longer be controlled over WiFi. The device also sends your Argo login and your WiFi password to the cloud, unencrypted.

The dummy server built into this integration takes the place of the cloud inside Home Assistant. Your router sends the device's traffic for the cloud to Home Assistant instead, so nothing leaves your network anymore:

- No more connection drops caused by the cloud, and no dependency on the internet.
- Your Argo login and WiFi password stay at home.
- The device reports its state on its own about every 12 seconds, and devices are found automatically.
- The official Argo web app no longer works while the dummy server is in use.

**You need a router that can redirect traffic** (called DNAT or "destination NAT"), e.g. UniFi, OPNsense, pfSense, FortiGate, MikroTik or OpenWrt. Most routers from internet providers, including the AVM FRITZ!Box, can't do this.

1. Go to **Settings → Devices & services → Add integration → Argoclima** and choose **Set up Argoclima Dummy Server**. Keep the suggested port `8239`.
2. Set up the redirect on your router. The **[router guide](docs/dnat.md)** explains it step by step for each router.
3. Within a few minutes, your Argo devices show up under **Discovered** in **Settings → Devices & services**. Confirm them and give them a name. Devices you already added manually switch over automatically.

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

When reporting a problem, attach the diagnostics: **Settings → Devices & services → Argoclima → ⋮ → Download diagnostics**. IP addresses, device ids and names are removed from the file.

To get debug logs, add this to `configuration.yaml` and restart:

```yaml
logger:
  logs:
    custom_components.argoclima: debug
```

**The device can't be added or is unavailable although the IP is correct.**
Unplug the device for about a minute and try again.

**The connection drops every few seconds.**
This happens when Argo's server is overloaded: the device resets its WiFi connection when its requests to the server time out. The [dummy server](#advanced-dummy-server) fixes this.

**The temperature is wrong while "Use Remote Temperature" is on.**
The remote only sends the temperature by infrared while it points at the device. If it's out of sight, covered or turned off, the device doesn't get new values and the temperature can be outdated. See [Using the remote's temperature sensor](#using-the-remotes-temperature-sensor).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- [@nyffchanium](https://github.com/nyffchanium) wrote the original integration. You can [buy them a coffee](https://www.buymeacoffee.com/nyffchanium).
- [@Gadund](https://github.com/Gadund) maintains it since version 1.2.0.
- [@0SkillAllLuck](https://github.com/0SkillAllLuck) built the dummy server into the integration, including device discovery and push updates.
- [@SaphiraDraco](https://github.com/SaphiraDraco) made polling more robust and modernized the `set_time` action.
- [@soft-song3425](https://github.com/soft-song3425) fixed compatibility with Home Assistant 2026.10.
- [@pimeys](https://github.com/pimeys) replaced deprecated Home Assistant APIs.
- [@lallinger](https://github.com/lallinger) contributed the original dummy server.

[upstream]: https://github.com/nyffchanium/argoclima-integration
[issues]: https://github.com/nyffchanium/argoclima-integration/issues
[releases]: https://github.com/nyffchanium/argoclima-integration/releases
[release-badge]: https://img.shields.io/github/v/release/nyffchanium/argoclima-integration
[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg
[ci]: https://github.com/nyffchanium/argoclima-integration/actions/workflows/ci.yml
[ci-badge]: https://github.com/nyffchanium/argoclima-integration/actions/workflows/ci.yml/badge.svg
[license-badge]: https://img.shields.io/github/license/nyffchanium/argoclima-integration
