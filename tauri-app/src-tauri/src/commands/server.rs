use tauri::AppHandle;
use crate::models::ServerInfo;
use std::path::PathBuf;

fn history_path(app: &AppHandle) -> PathBuf {
    app.path()
        .app_data_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("servers.json")
}

#[tauri::command]
pub async fn get_server_history(app: AppHandle) -> Result<Vec<ServerInfo>, String> {
    let path = history_path(&app);
    if !path.exists() {
        return Ok(vec![]);
    }
    let data = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    serde_json::from_str(&data).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn save_server(app: AppHandle, server: ServerInfo) -> Result<(), String> {
    let path = history_path(&app);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let mut servers = get_server_history(app.clone()).await.unwrap_or_default();
    servers.retain(|s| s.host != server.host || s.port != server.port);
    servers.insert(0, server); // most recent first
    servers.truncate(10); // keep max 10
    let json = serde_json::to_string_pretty(&servers).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn remove_server(app: AppHandle, host: String, port: u16) -> Result<(), String> {
    let mut servers = get_server_history(app.clone()).await.unwrap_or_default();
    servers.retain(|s| !(s.host == host && s.port == port));
    let path = history_path(&app);
    let json = serde_json::to_string_pretty(&servers).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn test_connection(api_url: String) -> Result<bool, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| e.to_string())?;
    match client
        .get(format!("{}/api/health", api_url))
        .send()
        .await
    {
        Ok(r) => Ok(r.status().is_success()),
        Err(_) => Ok(false),
    }
}
