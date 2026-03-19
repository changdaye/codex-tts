import Combine
import Dispatch
import Foundation

@MainActor
package final class MenuBarViewModel: ObservableObject {
    @Published private(set) var snapshot: DaemonStatusSnapshot?
    @Published package private(set) var isReachable = false
    @Published package private(set) var errorMessage: String?
    @Published package private(set) var isStartingDaemon = false

    private let client: CLIClient
    private let workerQueue = DispatchQueue(label: "CodexTTS.MenuBarViewModel.worker", qos: .utility)
    private var timer: Timer?
    private var refreshInFlight = false
    private var hasPendingRefresh = false
    private var pendingRefreshClearError = true
    private var hasAttemptedAutomaticDaemonStart = false

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

    package var canStartDaemon: Bool {
        !isStartingDaemon
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

    package func startDaemon() {
        startDaemon(automatic: false)
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
            maybeStartDaemonIfNeeded(for: error)
        }

        refreshInFlight = false
        if hasPendingRefresh {
            let nextClearError = pendingRefreshClearError
            hasPendingRefresh = false
            pendingRefreshClearError = true
            startRefresh(clearError: nextClearError)
        }
    }

    private func startDaemon(automatic: Bool) {
        guard !isStartingDaemon else {
            return
        }
        if automatic {
            hasAttemptedAutomaticDaemonStart = true
        }

        isStartingDaemon = true
        if automatic {
            errorMessage = "Starting daemon..."
        }
        let client = self.client
        workerQueue.async { [weak self] in
            let result = Result {
                try client.startDaemon()
            }
            Task { @MainActor in
                self?.finishDaemonStart(result)
            }
        }
    }

    private func finishDaemonStart(_ result: Result<Void, Error>) {
        isStartingDaemon = false
        switch result {
        case .success:
            scheduleStartupRefreshes()
        case .failure(let error):
            errorMessage = error.localizedDescription
        }
    }

    private func scheduleStartupRefreshes() {
        for delay in [0.1, 0.3, 0.6, 1.0] {
            DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
                Task { @MainActor in
                    self?.refresh(clearError: false)
                }
            }
        }
    }

    private func maybeStartDaemonIfNeeded(for error: Error) {
        guard !hasAttemptedAutomaticDaemonStart else {
            return
        }
        let message = error.localizedDescription.lowercased()
        guard message.contains("daemon is not running") else {
            return
        }
        startDaemon(automatic: true)
    }
}
