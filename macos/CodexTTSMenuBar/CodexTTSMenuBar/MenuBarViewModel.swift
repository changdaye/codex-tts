import Combine
import Foundation

@MainActor
final class MenuBarViewModel: ObservableObject {
    @Published private(set) var snapshot: DaemonStatusSnapshot?
    @Published private(set) var isReachable = false
    @Published private(set) var errorMessage: String?

    private let client: CLIClient
    private var timer: Timer?

    init(client: CLIClient = CLIClient()) {
        self.client = client
        refresh()
        startPolling()
    }

    var sessions: [ManagedSessionSnapshot] {
        snapshot?.sessions ?? []
    }

    var globalEnabled: Bool {
        snapshot?.globalEnabled ?? false
    }

    var focusSessionID: String? {
        snapshot?.focusSessionID
    }

    func refresh() {
        do {
            snapshot = try client.fetchStatus()
            isReachable = true
            errorMessage = nil
        } catch {
            isReachable = false
            errorMessage = error.localizedDescription
        }
    }

    func focus(sessionID: String) {
        runCommand {
            try client.focus(sessionID: sessionID)
        }
    }

    func setMuted(sessionID: String, muted: Bool) {
        runCommand {
            try client.setMuted(sessionID: sessionID, muted: muted)
        }
    }

    func setGlobalEnabled(_ enabled: Bool) {
        runCommand {
            try client.setGlobalEnabled(enabled)
        }
    }

    private func startPolling() {
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.refresh()
            }
        }
        timer?.tolerance = 0.2
    }

    private func runCommand(_ action: () throws -> Void) {
        do {
            try action()
            refresh()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
