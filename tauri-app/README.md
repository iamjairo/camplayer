# Camplayer Desktop App (Tauri v2)

A native desktop application that wraps the Camplayer web frontend into a cross-platform app for macOS, Windows, and Linux (including Raspberry Pi ARM64). It connects to a remote Camplayer server (a Pi running Camplayer OS or the Docker stack) and provides a fullscreen/kiosk viewing experience.

## Features

- **mDNS auto-discovery** — scans for `camplayer.local` and `_camplayer._tcp.local.` services on the local network
- **Server history** — recently-used servers are stored in the OS app-data directory
- **Keyboard shortcuts** — native global shortcuts matching the Camplayer keymap
- **Fullscreen/kiosk mode** — F11 to toggle; suitable for dedicated display setups
- **Server web UI via iframe** — zero duplication: the Pi's own React frontend is displayed inside the app

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Rust | stable | `curl https://sh.rustup.rs -sSf \| sh` |
| Node.js | ≥ 20 | https://nodejs.org |
| Tauri CLI v2 | ≥ 2.0 | installed via `npm` (see below) |

On **Linux** you also need the WebKitGTK dev libraries:

```bash
sudo apt-get install -y \
  libwebkit2gtk-4.1-dev libappindicator3-dev \
  librsvg2-dev patchelf libdbus-1-dev pkg-config
```

## Development

```bash
cd tauri-app
npm install
npm run tauri dev
```

This starts the Vite dev server on port 5173 and opens the Tauri window pointing at it. Hot-reload works for the TypeScript/React frontend; Rust changes require a full rebuild.

## Production Build

```bash
cd tauri-app
npm install
npm run tauri build
```

Outputs are placed in `src-tauri/target/release/bundle/`.

## Cross-Compile for Linux ARM64 (Raspberry Pi)

Install the cross-compiler toolchain on a Linux x86_64 host:

```bash
sudo apt-get install -y gcc-aarch64-linux-gnu
rustup target add aarch64-unknown-linux-gnu
```

Add to `~/.cargo/config.toml`:

```toml
[target.aarch64-unknown-linux-gnu]
linker = "aarch64-linux-gnu-gcc"
```

Then build:

```bash
cd tauri-app
npm run tauri build -- --target aarch64-unknown-linux-gnu
```

## macOS Universal Binary

```bash
rustup target add aarch64-apple-darwin x86_64-apple-darwin
cd tauri-app
npm run tauri build -- --target universal-apple-darwin
```

## App Icons

Icons are **not** committed to the repository. Generate them from a 1024×1024 PNG:

```bash
npx @tauri-apps/cli icon path/to/source.png
```

This writes all sizes to `src-tauri/icons/`. See [`src-tauri/icons/README.md`](src-tauri/icons/README.md).

## mDNS Discovery

On first launch (and on the "Rescan" button) the app:

1. Always adds `camplayer.local:80` as a fallback candidate (works with Camplayer OS).
2. Starts a `mdns-sd` browse for `_camplayer._tcp.local.` services with a 5-second timeout.
3. A background task continues listening and emits `server-discovered` / `server-removed` events to the frontend in real time.

The Docker stack can advertise itself by running an mDNS responder (e.g. `avahi-daemon`) that registers a `_camplayer._tcp` service.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` – `9` | Select layout (1–9 cameras) |
| `←` / `→` | Previous / next screen |
| `F11` | Toggle fullscreen |
| `Escape` | Exit fullscreen / back |
| `Q` | Disconnect and return to server selector |

Shortcuts are registered as native global shortcuts via `tauri-plugin-global-shortcut` and forwarded to the embedded iframe as `postMessage` events so the server's frontend can react to them.

## CI / Releases

The GitHub Actions workflow at [`.github/workflows/build-tauri.yml`](../.github/workflows/build-tauri.yml) builds binaries for all platforms when a `v*` tag is pushed, and creates a GitHub Release with the installers attached.

Required repository secrets:
- `TAURI_SIGNING_PRIVATE_KEY` — (optional) for update signing
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` — (optional) corresponding password

## Project Structure

```
tauri-app/
  src-tauri/          Rust backend
    src/
      main.rs         Entry point
      lib.rs          Tauri builder + plugin setup
      models.rs       Shared types (ServerInfo etc.)
      commands/
        discovery.rs  mDNS scan + background listener
        server.rs     History persistence + connection test
        shortcuts.rs  Global shortcut registration
    tauri.conf.json   App metadata, window config
    Cargo.toml        Rust dependencies
    capabilities/
      default.json    Tauri v2 permission grants
    icons/            App icons (generate with `tauri icon`)
  src/                React frontend (Tauri-aware)
    main.tsx          React entry point
    App.tsx           Root component (selector ↔ connected)
    components/
      ServerSelector.tsx  Discovery + manual server picker
      ConnectedApp.tsx    iframe wrapper + shortcut forwarding
    hooks/
      useServerDiscovery.ts
      useServerHistory.ts
    utils/
      tauri-bridge.ts Type-safe invoke() wrappers
      types.ts        Shared TypeScript interfaces
  index.html          Vite HTML entry
  vite.config.ts      Vite configuration
  package.json        NPM dependencies
  tsconfig.json       TypeScript configuration
```
