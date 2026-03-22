use tauri::AppHandle;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};
use tauri::Emitter;

const SHORTCUTS: &[(&str, &str)] = &[
    ("F11", "toggle-fullscreen"),
    ("Escape", "escape"),
    ("ArrowLeft", "prev-screen"),
    ("ArrowRight", "next-screen"),
    ("1", "layout-1"),
    ("2", "layout-2"),
    ("3", "layout-3"),
    ("4", "layout-4"),
    ("5", "layout-5"),
    ("6", "layout-6"),
    ("7", "layout-7"),
    ("8", "layout-8"),
    ("9", "layout-9"),
    ("KeyQ", "quit"),
];

#[tauri::command]
pub fn register_shortcuts(app: AppHandle) -> Result<(), String> {
    for (key, action) in SHORTCUTS {
        let action = action.to_string();
        let app_clone = app.clone();
        if let Ok(shortcut) = key.parse::<Shortcut>() {
            let _ = app
                .global_shortcut()
                .on_shortcut(shortcut, move |_app, _shortcut, event| {
                    if event.state == ShortcutState::Pressed {
                        let _ = app_clone.emit("shortcut", &action);
                    }
                });
        }
    }
    Ok(())
}

#[tauri::command]
pub fn unregister_shortcuts(app: AppHandle) -> Result<(), String> {
    let _ = app.global_shortcut().unregister_all();
    Ok(())
}
