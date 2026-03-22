use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerInfo {
    pub name: String,
    pub host: String,
    pub port: u16,
    pub api_url: String,
    pub discovered: bool,
    pub last_connected: Option<String>,
}

impl ServerInfo {
    pub fn new(host: &str, port: u16) -> Self {
        Self {
            name: format!("Camplayer @ {}", host),
            host: host.to_string(),
            port,
            api_url: format!("http://{}:{}", host, port),
            discovered: false,
            last_connected: None,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DiscoveryResult {
    pub servers: Vec<ServerInfo>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ShortcutEvent {
    pub key: String,
    pub action: String,
}
