import Foundation

struct CommandOutput: Equatable {
    let stdout: String
    let stderr: String
    let exitCode: Int32
}

protocol CLIExecuting {
    func run(arguments: [String]) throws -> CommandOutput
}

struct ProcessCLIExecutor: CLIExecuting {
    let executable: String

    init(executable: String = "codex-tts") {
        self.executable = executable
    }

    func run(arguments: [String]) throws -> CommandOutput {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = [executable] + arguments

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        try process.run()
        process.waitUntilExit()

        let output = CommandOutput(
            stdout: String(decoding: stdoutPipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self),
            stderr: String(decoding: stderrPipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self),
            exitCode: process.terminationStatus
        )
        if output.exitCode != 0 {
            throw CLIClientError.commandFailed(output)
        }
        return output
    }
}

enum CLIClientError: LocalizedError {
    case emptyOutput
    case invalidStatusJSON(String)
    case commandFailed(CommandOutput)

    var errorDescription: String? {
        switch self {
        case .emptyOutput:
            return "The codex-tts command returned no output."
        case .invalidStatusJSON(let raw):
            return "Could not decode daemon status JSON: \(raw)"
        case .commandFailed(let output):
            let message = output.stderr.isEmpty ? output.stdout : output.stderr
            return "codex-tts command failed: \(message.trimmingCharacters(in: .whitespacesAndNewlines))"
        }
    }
}

final class CLIClient {
    private let executor: any CLIExecuting

    init(executor: any CLIExecuting = ProcessCLIExecutor()) {
        self.executor = executor
    }

    func fetchStatus() throws -> DaemonStatusSnapshot {
        let output = try executor.run(arguments: ["status", "--json"])
        let payload = output.stdout.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !payload.isEmpty else {
            throw CLIClientError.emptyOutput
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        guard let data = payload.data(using: .utf8) else {
            throw CLIClientError.invalidStatusJSON(payload)
        }
        do {
            return try decoder.decode(DaemonStatusSnapshot.self, from: data)
        } catch {
            throw CLIClientError.invalidStatusJSON(payload)
        }
    }

    func focus(sessionID: String) throws {
        _ = try executor.run(arguments: ["focus", sessionID])
    }

    func setMuted(sessionID: String, muted: Bool) throws {
        _ = try executor.run(arguments: [muted ? "mute" : "unmute", sessionID])
    }

    func setGlobalEnabled(_ enabled: Bool) throws {
        _ = try executor.run(arguments: [enabled ? "enable" : "disable"])
    }
}
