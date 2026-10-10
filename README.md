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

> [!IMPORTANT]
> **Using the separate dummy server (Docker)?** It keeps working, and the integration then polls your devices as before. It's no longer updated, though: the dummy server is now built into the integration. See [Coming from the separate dummy server](https://github.com/nyffchanium/argoclima-integration/blob/master/docs/dummy-server.md#coming-from-the-separate-dummy-server-docker) to switch.

If you installed the fork `Gadund/argoclima-integration` as a custom repository in the meantime: in HACS, remove the custom repository (⋮ → **Custom repositories**), then download **Argoclima** again from the regular HACS list and restart. Your devices stay set up.

## Documentation

- **[Dummy server (advanced)](https://github.com/nyffchanium/argoclima-integration/blob/master/docs/dummy-server.md)**: run the device without the manufacturer's cloud, with the [router guide](https://github.com/nyffchanium/argoclima-integration/blob/master/docs/dnat.md)
- **[Features in detail](https://github.com/nyffchanium/argoclima-integration/blob/master/docs/features.md)**: remote temperature sensor, firmware updates, device clock, limitations
- **[Troubleshooting](https://github.com/nyffchanium/argoclima-integration/blob/master/docs/troubleshooting.md)**: common problems, diagnostics and debug logs
- **[Security](https://github.com/nyffchanium/argoclima-integration/blob/master/SECURITY.md)**: security model and how to report vulnerabilities

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
