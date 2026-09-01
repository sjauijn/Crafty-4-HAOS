<p align="center">
  <img src="https://raw.githubusercontent.com/sjauijn/Crafty-4-OLD-HAOS/refs/heads/master/logo.png" alt="icon">
</p>

# Crafty Controller — Home Assistant app

I maintain this app, along my other apps and custom integrations for the Home Assistant, solely for my own use. As long as I'm actively using them myself, I'll continue developing and updating them; otherwise, support for apps and/or custom integrations I no longer need will be discontinued.

## About

Crafty Controller is a Minecraft Server Control Panel / Launcher. The purpose
of Crafty Controller is to launch a Minecraft Server in the background and present
a web interface for the server administrators to interact with their servers.

## Web interface access

This add-on can be reached two ways:

- **Ingress (recommended)**: click **Open Web UI** from the add-on page.
  Home Assistant proxies the connection for you, so no extra port or
  certificate is needed.
- **Direct access**: the add-on also exposes port `8443/tcp`. You can
  change the host port mapping from the add-on's **Network** tab. Reach it
  at `https://<home-assistant-ip>:<port>` if `ssl` is enabled, or
  `http://<home-assistant-ip>:<port>` otherwise.

## Configuration

```yaml
timezone: Etc/UTC
ssl: false
certfile: fullchain.pem
keyfile: privkey.pem
data_location: ""
log_level: info
```

### Option: `timezone`

The timezone used by Crafty Controller and the game servers it manages.
Use an IANA timezone name, for example `Europe/Moscow` or `America/New_York`.

### Option: `data_location`

Where Crafty Controller stores all of its data: configuration, the
database, server files, worlds, backups, logs, and the import folder.

- Leave empty (the default) to use the add-on's own `/data` folder, which
  Home Assistant keeps across restarts and updates.
- Set it to a full absolute path to store everything there instead, for
  example `/media/MegaLocalCloud/CraftyController` or `/share/Crafty`.
  The path is used exactly as written, so it must start with `/media/` or
  `/share/` (the folders this add-on has access to). The add-on refuses to
  start if the path is not absolute (does not start with `/`), so you
  don't end up with data silently written to the wrong place.

Changing this option after servers already exist does not move existing
data. Set it once before creating your first server, or move the data on
disk yourself and update the option to match.

### Option: `log_level`

Controls how much detail shows up in the add-on's own **Log** tab (the
add-on's startup script, not Crafty's own log files, which are always
available in full detail from within Crafty's web interface).

- `info` (default): only startup status, the Ingress URL, and errors are
  printed. This is what most users should keep.
- `debug`: additionally prints the raw response from the Supervisor
  ingress API, the generated nginx configuration, container network
  interfaces, nginx's listening sockets, and a one-line summary of every
  HTTP request handled by nginx (method, path, status code and redirect
  target). It also starts Crafty itself with verbose logging, so Crafty's
  own log files (viewable from its web interface) capture debug-level
  detail as well.

Use `debug` temporarily when troubleshooting a startup or Ingress
connectivity problem, then switch back to `info` once resolved to keep
the log tab readable.

### Option: `ssl`

Controls only the **direct access** port (`8443/tcp`); Ingress is always
served securely by Home Assistant regardless of this setting. Set this to
`true` to terminate HTTPS on the direct port using your own certificate
from Home Assistant's `/ssl` folder (the same folder used by Home
Assistant Core's own HTTPS configuration), for example so you can reach
the add-on at `https://sxs-home.local:8443/` instead of plain `http`.

### Option: `certfile`

Filename of the certificate to use from Home Assistant's `/ssl` folder,
only used when `ssl` is `true`. Defaults to `fullchain.pem`.

### Option: `keyfile`

Filename of the private key to use from Home Assistant's `/ssl` folder,
only used when `ssl` is `true`. Defaults to `privkey.pem`.

If `ssl` is enabled but the certificate or key file cannot be found in
`/ssl`, the direct port falls back to plain HTTP and the add-on logs a
warning. Ingress is unaffected either way.

Note that the certificate is only copied into place on add-on start. If you
replace the certificate files in `/ssl`, restart the add-on to pick up the
change.

## First login

On first start Crafty generates a random administrator password and prints
it to the add-on log. Open the add-on **Log** tab and look for a line
containing the initial `admin` password, then open the web UI (via
**Open Web UI** or the direct port) and log in.

## Ports

This add-on runs on the host network, so every port a game server listens
on (Minecraft Java, Bedrock, Dynmap, plugins, and so on) is reachable on
your local network as soon as you set that port when creating or
configuring the server in Crafty's own interface. There is nothing to map
manually for game servers.

The only port controlled by the add-on itself is the direct web interface
access port, `8443/tcp` by default, changeable from the add-on's
**Network** tab. It is optional: Ingress works without it.

## Data storage

All persistent data (configuration, the database, server files, worlds,
backups, logs, and the import folder) is stored in one place, controlled
by the `data_location` option:

- By default (`data_location` empty) everything is stored under the
  add-on's own `/data` directory, which Home Assistant keeps across
  add-on restarts and updates, and includes in Home Assistant backups
  (world save files are excluded by default to keep backup sizes
  manageable; back up large worlds separately if needed).
- If `data_location` is set, everything is stored under that path on the
  `media` share instead, and `/data` is left empty.

## Support

This add-on packages the upstream Crafty Controller 4 project. For issues
related to Crafty itself, refer to the upstream project:
https://gitlab.com/crafty-controller/crafty-4
