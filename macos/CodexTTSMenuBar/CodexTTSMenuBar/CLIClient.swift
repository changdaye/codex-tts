import Foundation

package struct CommandOutput: Equatable, Sendable {
    package let stdout: String
    package let stderr: String
    package let exitCode: Int32

    package init(stdout: String, stderr: String, exitCode: Int32) {
        self.stdout = stdout
        self.stderr = stderr
        self.exitCode = exitCode
    }
}

package protocol CLIExecuting: Sendable {
    func run(arguments: [String]) throws -> CommandOutput
}

struct ProcessCLIExecutor: CLIExecuting, @unchecked Sendable {
    let executable: String
    let environment: [String: String]
    let fileManager: FileManager

    init(
        executable: String = "codex-tts",
        environment: [String: String] = ProcessInfo.processInfo.environment,
        fileManager: FileManager = .default
    ) {
        self.executable = executable
        self.environment = environment
        self.fileManager = fileManager
    }

    func run(arguments: [String]) throws -> CommandOutput {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: try resolveExecutable())
        process.arguments = arguments

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

    private func resolveExecutable() throws -> String {
        if executable.contains("/") {
            guard fileManager.isExecutableFile(atPath: executable) else {
                throw CLIClientError.executableNotFound([executable])
            }
            return executable
        }

        let override = environment["CODEX_TTS_EXECUTABLE"]?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let override, !override.isEmpty {
            guard fileManager.isExecutableFile(atPath: override) else {
                throw CLIClientError.executableNotFound([override])
            }
            return override
        }

        let searchDirectories = candidateSearchDirectories()
        let candidates = searchDirectories.map {
            URL(fileURLWithPath: $0, isDirectory: true).appendingPathComponent(executable).path
        }
        if let resolved = candidates.first(where: { fileManager.isExecutableFile(atPath: $0) }) {
            return resolved
        }
        throw CLIClientError.executableNotFound(candidates)
    }

    private func candidateSearchDirectories() -> [String] {
        var directories: [String] = []
        if let pathValue = environment["PATH"] {
            directories.append(contentsOf: pathValue.split(separator: ":").map(String.init))
        }

        let homeDirectory = environment["HOME"]?.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolvedHome = (homeDirectory?.isEmpty == false)
            ? homeDirectory!
            : fileManager.homeDirectoryForCurrentUser.path
        directories.append(contentsOf: [
            "\(resolvedHome)/.local/bin",
            "\(resolvedHome)/bin",
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
        ])

        var seen = Set<String>()
        return directories.filter { directory in
            guard !directory.isEmpty else {
                return false
            }
            return seen.insert(directory).inserted
        }
    }
}

enum CLIClientError: LocalizedError {
    case emptyOutput
    case invalidStatusJSON(String)
    case commandFailed(CommandOutput)
    case executableNotFound([String])

    var errorDescription: String? {
        switch self {
        case .emptyOutput:
            return "The codex-tts command returned no output."
        case .invalidStatusJSON(let raw):
            return "Could not decode daemon status JSON: \(raw)"
        case .commandFailed(let output):
            let message = output.stderr.isEmpty ? output.stdout : output.stderr
            return "codex-tts command failed: \(message.trimmingCharacters(in: .whitespacesAndNewlines))"
        case .executableNotFound(let candidates):
            let joined = candidates.joined(separator: ", ")
            return "Could not find codex-tts. Checked: \(joined)"
        }
    }
}

package final class CLIClient: @unchecked Sendable {
    private let executor: any CLIExecuting

    package init(executor: any CLIExecuting = ProcessCLIExecutor()) {
        self.executor = executor
    }

    func fetchStatus() throws -> DaemonStatusSnapshot {
        let output = try executor.run(arguments: ["status", "--json"])
        let payload = output.stdout.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !payload.isEmpty else {
            throw CLIClientError.emptyOutput
        }

        let decoder = JSONDecoder()
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
