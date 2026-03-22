use tauri::{Manager, WindowEvent};
mod commands;
mod models;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![
            commands::discovery::discover_servers,
            commands::discovery::stop_discovery,
            commands::server::get_server_history,
            commands::server::save_server,
            commands::server::remove_server,
            commands::server::test_connection,
            commands::shortcuts::register_shortcuts,
            commands::shortcuts::unregister_shortcuts,
        ])
        .setup(|app| {
            // Start mDNS discovery background task
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                commands::discovery::start_background_discovery(app_handle).await;
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                window.app_handle().exit(0);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
