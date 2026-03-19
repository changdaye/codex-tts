import AppKit
import Foundation
import CodexTTSMenuBarCore

private struct FakeCLIError: LocalizedError {
    let message: String

    var errorDescription: String? {
        message
    }
}

private struct DelayedExecutor: CLIExecuting {
    let delay: TimeInterval
    let output: CommandOutput

    func run(arguments: [String]) throws -> CommandOutput {
        Thread.sleep(forTimeInterval: delay)
        return output
    }

    func launchDetached(arguments: [String]) throws {}
}

private final class AutoStartExecutor: CLIExecuting, @unchecked Sendable {
    private let statusOutput: CommandOutput
    private let lock = NSLock()
    private var daemonStarted = false

    init(statusOutput: CommandOutput) {
        self.statusOutput = statusOutput
    }

    func run(arguments: [String]) throws -> CommandOutput {
        lock.lock()
        let started = daemonStarted
        lock.unlock()

        guard arguments == ["status", "--json"] else {
            return CommandOutput(stdout: "", stderr: "", exitCode: 0)
        }

        if started {
            return statusOutput
        }

        throw FakeCLIError(message: "codex-tts command failed: codex-tts: daemon is not running")
    }

    func launchDetached(arguments: [String]) throws {
        guard arguments == ["daemon", "run"] else {
            throw FakeCLIError(message: "codex-tts command failed: unexpected daemon launch arguments")
        }
        lock.lock()
        daemonStarted = true
        lock.unlock()
    }
}

@MainActor
private func runSmokeTest() async throws -> Int32 {
    let statusOutput = CommandOutput(
        stdout: """
        {"global_enabled":true,"focus_session_id":"session-1","sessions":[{"session_id":"session-1","cwd":"/tmp/project","started_at":1,"status":"active","launcher_pid":10,"codex_pid":11,"thread_id":"thread-1","rollout_path":"/tmp/project/rollout.jsonl","is_focus":true,"is_muted":false,"last_final_text":"done","last_event_at":2}],"snapshot_version":1}
        """,
        stderr: "",
        exitCode: 0
    )
    let nonBlockingResult = try await verifyNonBlockingInitialization(statusOutput: statusOutput)
    guard nonBlockingResult == 0 else {
        return nonBlockingResult
    }
    return try await verifyAutomaticDaemonStart(statusOutput: statusOutput)
}

@MainActor
private func verifyNonBlockingInitialization(statusOutput: CommandOutput) async throws -> Int32 {
    let output = CommandOutput(
        stdout: """
        {"global_enabled":true,"focus_session_id":"session-1","sessions":[{"session_id":"session-1","cwd":"/tmp/project","started_at":1,"status":"active","launcher_pid":10,"codex_pid":11,"thread_id":"thread-1","rollout_path":"/tmp/project/rollout.jsonl","is_focus":true,"is_muted":false,"last_final_text":"done","last_event_at":2}],"snapshot_version":1}
        """,
        stderr: "",
        exitCode: 0
    )
    let client = CLIClient(executor: DelayedExecutor(delay: 0.5, output: output))

    let start = Date()
    let viewModel = MenuBarViewModel(client: client)
    let elapsed = Date().timeIntervalSince(start)
    guard elapsed < 0.2 else {
        fputs("FAIL: initialization blocked for \(elapsed) seconds\n", stderr)
        return 1
    }

    let deadline = Date().addingTimeInterval(2.0)
    while Date() < deadline {
        if viewModel.isReachable && viewModel.focusSessionID == "session-1" {
            return 0
        }
        try await Task.sleep(for: .milliseconds(20))
    }

    return 0
}

@MainActor
private func verifyAutomaticDaemonStart(statusOutput: CommandOutput) async throws -> Int32 {
    let executor = AutoStartExecutor(statusOutput: statusOutput)
    let client = CLIClient(executor: executor)
    let viewModel = MenuBarViewModel(client: client)

    let deadline = Date().addingTimeInterval(2.0)
    while Date() < deadline {
        if viewModel.isReachable && viewModel.focusSessionID == "session-1" {
            return 0
        }
        try await Task.sleep(for: .milliseconds(20))
    }

    let errorMessage = viewModel.errorMessage ?? "nil"
    fputs(
        "FAIL: automatic daemon start did not recover connectivity; reachable=\(viewModel.isReachable) focus=\(viewModel.focusSessionID ?? "nil") error=\(errorMessage)\n",
        stderr
    )
    return 1
}

@main
struct SmokeRunner {
    static func main() async {
        do {
            let exitCode = try await runSmokeTest()
            exit(exitCode)
        } catch {
            fputs("FAIL: \(error)\n", stderr)
            exit(1)
        }
    }
}
