import Combine
import Dispatch
import Foundation

@MainActor
package final class MenuBarViewModel: ObservableObject {
    @Published private(set) var snapshot: DaemonStatusSnapshot?
    @Published package private(set) var isReachable = false
    @Published package private(set) var errorMessage: String?

    private let client: CLIClient
    private let workerQueue = DispatchQueue(label: "CodexTTS.MenuBarViewModel.worker", qos: .utility)
    private var timer: Timer?
    private var refreshInFlight = false
    private var hasPendingRefresh = false
    private var pendingRefreshClearError = true

    package init(client: CLIClient = CLIClient()) {
        self.client = client
        refresh()
        startPolling()
    }

    package var sessions: [ManagedSessionSnapshot] {
        snapshot?.sessions ?? []
    }

    package var globalEnabled: Bool {
        snapshot?.globalEnabled ?? false
    }

    package var controlsEnabled: Bool {
        isReachable && snapshot != nil
    }

    package var focusSessionID: String? {
        snapshot?.focusSessionID
    }

    package func refresh(clearError: Bool = true) {
        if refreshInFlight {
            hasPendingRefresh = true
            pendingRefreshClearError = pendingRefreshClearError && clearError
            return
        }
        startRefresh(clearError: clearError)
    }

    package func focus(sessionID: String) {
        let client = self.client
        runCommand {
            try client.focus(sessionID: sessionID)
        }
    }

    package func setMuted(sessionID: String, muted: Bool) {
        let client = self.client
        runCommand {
            try client.setMuted(sessionID: sessionID, muted: muted)
        }
    }

    package func setGlobalEnabled(_ enabled: Bool) {
        let client = self.client
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

    private func runCommand(_ action: @escaping @Sendable () throws -> Void) {
        workerQueue.async { [weak self] in
            let result = Result(catching: action)
            Task { @MainActor in
                guard let self else {
                    return
                }
                switch result {
                case .success:
                    self.refresh()
                case .failure(let error):
                    self.errorMessage = error.localizedDescription
                    self.refresh(clearError: false)
                }
            }
        }
    }

    private func startRefresh(clearError: Bool) {
        refreshInFlight = true
        let client = self.client
        workerQueue.async { [weak self] in
            let result = Result(catching: client.fetchStatus)
            Task { @MainActor in
                self?.finishRefresh(result, clearError: clearError)
            }
        }
    }

    private func finishRefresh(_ result: Result<DaemonStatusSnapshot, Error>, clearError: Bool) {
        switch result {
        case .success(let snapshot):
            self.snapshot = snapshot
            isReachable = true
            if clearError {
                errorMessage = nil
            }
        case .failure(let error):
            snapshot = nil
            isReachable = false
            errorMessage = error.localizedDescription
        }

        refreshInFlight = false
        if hasPendingRefresh {
            let nextClearError = pendingRefreshClearError
            hasPendingRefresh = false
            pendingRefreshClearError = true
            startRefresh(clearError: nextClearError)
        }
    }
}
