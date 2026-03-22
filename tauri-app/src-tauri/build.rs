fn main() {
    if let Err(e) = tauri_build::try_build(tauri_build::Attributes::new()) {
        eprintln!("tauri_build failed: {e:#}");
        std::process::exit(1);
    }
}
