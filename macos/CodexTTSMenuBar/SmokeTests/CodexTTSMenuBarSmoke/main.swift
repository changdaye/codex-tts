import AppKit
import Foundation
import CodexTTSMenuBarCore

private struct DelayedExecutor: CLIExecuting {
    let delay: TimeInterval
    let output: CommandOutput

    func run(arguments: [String]) throws -> CommandOutput {
        Thread.sleep(forTimeInterval: delay)
        return output
    }
}

@MainActor
private func runSmokeTest() async throws -> Int32 {
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

    let errorMessage = viewModel.errorMessage ?? "nil"
    fputs(
        "FAIL: timed out waiting for status snapshot; reachable=\(viewModel.isReachable) focus=\(viewModel.focusSessionID ?? "nil") error=\(errorMessage)\n",
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
