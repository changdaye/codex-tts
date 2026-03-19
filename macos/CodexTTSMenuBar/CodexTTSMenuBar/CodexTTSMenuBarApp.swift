import SwiftUI
import CodexTTSMenuBarCore

@main
struct CodexTTSMenuBarApp: App {
    @StateObject private var viewModel = MenuBarViewModel()

    var body: some Scene {
        MenuBarExtra("Codex TTS", systemImage: iconName) {
            MenuContentView(viewModel: viewModel)
        }
    }

    private var iconName: String {
        if !viewModel.isReachable {
            return "exclamationmark.triangle"
        }
        return viewModel.globalEnabled ? "speaker.wave.2.fill" : "speaker.slash.fill"
    }
}

private struct MenuContentView: View {
    @ObservedObject var viewModel: MenuBarViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            statusSection
            Divider()
            Toggle("Speech Enabled", isOn: Binding(
                get: { viewModel.globalEnabled },
                set: { viewModel.setGlobalEnabled($0) }
            ))
            .disabled(!viewModel.controlsEnabled)
            Divider()
            sessionsSection
            Divider()
            Button("Refresh") {
                viewModel.refresh()
            }
            Button("Quit") {
                NSApplication.shared.terminate(nil)
            }
        }
        .padding(12)
        .frame(width: 360)
    }

    @ViewBuilder
    private var statusSection: some View {
        if viewModel.isReachable {
            Text("Daemon Connected")
                .font(.headline)
            Text("Focus: \(viewModel.focusSessionID ?? "None")")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        } else {
            Text("Daemon Unreachable")
                .font(.headline)
            if viewModel.isStartingDaemon {
                Text("Starting daemon...")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                Button("Start Daemon") {
                    viewModel.startDaemon()
                }
                .disabled(!viewModel.canStartDaemon)
            }
            if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private var sessionsSection: some View {
        if !viewModel.controlsEnabled {
            Text("Session list unavailable while daemon is disconnected")
                .foregroundStyle(.secondary)
        } else if viewModel.sessions.isEmpty {
            Text("No active sessions")
                .foregroundStyle(.secondary)
        } else {
            ForEach(viewModel.sessions) { session in
                VStack(alignment: .leading, spacing: 6) {
                    Text(session.cwd)
                        .font(.subheadline)
                        .lineLimit(1)
                    Text("status=\(session.status) focus=\(session.isFocus ? "yes" : "no") muted=\(session.isMuted ? "yes" : "no")")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    HStack {
                        Button(session.isFocus ? "Focused" : "Focus") {
                            viewModel.focus(sessionID: session.sessionID)
                        }
                        .disabled(session.isFocus || !viewModel.controlsEnabled)

                        Button(session.isMuted ? "Unmute" : "Mute") {
                            viewModel.setMuted(sessionID: session.sessionID, muted: !session.isMuted)
                        }
                        .disabled(!viewModel.controlsEnabled)
                    }
                    if let lastFinalText = session.lastFinalText, !lastFinalText.isEmpty {
                        Text(lastFinalText)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                }
                .padding(.vertical, 4)
            }
        }
    }
}
