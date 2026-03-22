use mdns_sd::{ServiceDaemon, ServiceEvent};
use tauri::{AppHandle, Emitter};
use crate::models::ServerInfo;
use std::time::Duration;

const CAMPLAYER_SERVICE: &str = "_camplayer._tcp.local.";
const DISCOVERY_TIMEOUT: Duration = Duration::from_secs(5);

/// Perform a one-shot mDNS discovery scan and return found servers.
/// Also always tries `camplayer.local:80` as a fallback.
#[tauri::command]
pub async fn discover_servers() -> Result<Vec<ServerInfo>, String> {
    let mut servers: Vec<ServerInfo> = Vec::new();

    // Always include camplayer.local as a candidate
    servers.push(ServerInfo {
        name: "Camplayer OS (camplayer.local)".to_string(),
        host: "camplayer.local".to_string(),
        port: 80,
        api_url: "http://camplayer.local".to_string(),
        discovered: true,
        last_connected: None,
    });

    // mDNS scan for _camplayer._tcp.local.
    match ServiceDaemon::new() {
        Ok(daemon) => {
            let receiver = daemon
                .browse(CAMPLAYER_SERVICE)
                .map_err(|e| e.to_string())?;
            let deadline = std::time::Instant::now() + DISCOVERY_TIMEOUT;
            while std::time::Instant::now() < deadline {
                match receiver.recv_timeout(Duration::from_millis(100)) {
                    Ok(ServiceEvent::ServiceResolved(info)) => {
                        let host = info.get_hostname().trim_end_matches('.').to_string();
                        let port = info.get_port();
                        servers.push(ServerInfo {
                            name: info.get_fullname().to_string(),
                            host: host.clone(),
                            port,
                            api_url: format!("http://{}:{}", host, port),
                            discovered: true,
                            last_connected: None,
                        });
                    }
                    Err(_) => break,
                    _ => {}
                }
            }
            let _ = daemon.shutdown();
        }
        Err(_) => {} // mDNS not available, fall back to camplayer.local only
    }

    Ok(servers)
}

#[tauri::command]
pub async fn stop_discovery() -> Result<(), String> {
    Ok(())
}

/// Background task: continuously emit discovered servers as events.
pub async fn start_background_discovery(app: AppHandle) {
    match ServiceDaemon::new() {
        Ok(daemon) => {
            if let Ok(receiver) = daemon.browse(CAMPLAYER_SERVICE) {
                loop {
                    match receiver.recv_timeout(Duration::from_millis(500)) {
                        Ok(ServiceEvent::ServiceResolved(info)) => {
                            let host = info.get_hostname().trim_end_matches('.').to_string();
                            let port = info.get_port();
                            let server = ServerInfo {
                                name: info.get_fullname().to_string(),
                                host: host.clone(),
                                port,
                                api_url: format!("http://{}:{}", host, port),
                                discovered: true,
                                last_connected: None,
                            };
                            let _ = app.emit("server-discovered", &server);
                        }
                        Ok(ServiceEvent::ServiceRemoved(_, fullname)) => {
                            let _ = app.emit("server-removed", &fullname);
                        }
                        _ => {}
                    }
                    tokio::time::sleep(Duration::from_millis(100)).await;
                }
            }
        }
        Err(_) => {}
    }
}
