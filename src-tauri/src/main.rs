// Tauri entry point.
//
// The Python backend ships as a sidecar binary built by PyInstaller (see
// `scripts/build_backend_sidecar.py`). Tauri spawns it on app launch, points
// it at the user's per-app data dir, and connects the WebView to its API.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendChild(Mutex<Option<CommandChild>>);

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendChild(Mutex::new(None)))
        .setup(|app| {
            let data_dir = app
                .path()
                .app_data_dir()
                .expect("could not resolve app data dir");
            std::fs::create_dir_all(&data_dir).ok();

            let sidecar = app
                .shell()
                .sidecar("forlas-backend")
                .expect("missing sidecar binary 'forlas-backend'")
                .env("FORLAS_DATA_DIR", data_dir.to_string_lossy().to_string())
                .env("FORLAS_HOST", "127.0.0.1")
                .env("FORLAS_PORT", "8765");

            let (mut rx, child) = sidecar.spawn().expect("failed to spawn backend sidecar");
            *app.state::<BackendChild>().0.lock().unwrap() = Some(child);

            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) | CommandEvent::Stderr(line) => {
                            eprintln!("[backend] {}", String::from_utf8_lossy(&line));
                        }
                        _ => {}
                    }
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("tauri build")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { .. } = event {
                if let Some(child) = app_handle
                    .state::<BackendChild>()
                    .0
                    .lock()
                    .unwrap()
                    .take()
                {
                    let _ = child.kill();
                }
            }
        });
}
