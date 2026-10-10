# Security policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please do not open a public issue. Report vulnerabilities privately through [GitHub's vulnerability reporting](https://github.com/nyffchanium/argoclima-integration/security/advisories/new) and include steps to reproduce.

## Security model

The Argo device API and its cloud protocol have no authentication or encryption: anyone in your local network can control the device directly, with or without this integration. Keep your Argo devices in a trusted network.

- Never expose the dummy server port to the internet, and limit the router rules to your Argo devices.
- The dummy server only accepts a device report if the IP address it claims matches the address it connects from, or if it comes from the configured NAT gateway.
- The cloud credentials the device sends along are never stored and are removed from logs.
