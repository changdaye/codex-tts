import Foundation

struct DaemonStatusSnapshot: Codable, Equatable {
    let globalEnabled: Bool
    let focusSessionID: String?
    let sessions: [ManagedSessionSnapshot]
    let snapshotVersion: Int?
}

struct ManagedSessionSnapshot: Codable, Equatable, Identifiable {
    let sessionID: String
    let cwd: String
    let startedAt: Int
    let status: String
    let launcherPID: Int?
    let codexPID: Int?
    let threadID: String?
    let rolloutPath: String?
    let isFocus: Bool
    let isMuted: Bool
    let lastFinalText: String?
    let lastEventAt: Int?

    var id: String { sessionID }
}
