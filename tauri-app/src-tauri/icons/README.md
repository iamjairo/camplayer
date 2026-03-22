# Icons

App icons are NOT committed to this repository.

Generate them from a 1024×1024 source PNG using the Tauri CLI:

```bash
# Install Tauri CLI globally or use npx
npx @tauri-apps/cli icon path/to/source-1024x1024.png
```

This will output all required icon sizes to `tauri-app/src-tauri/icons/`:
- `32x32.png`
- `128x128.png`
- `128x128@2x.png`
- `icon.icns` (macOS)
- `icon.ico` (Windows)
- `icon.png` (Linux)

A placeholder SVG logo is at `resources/logo.svg` in the repository root.
