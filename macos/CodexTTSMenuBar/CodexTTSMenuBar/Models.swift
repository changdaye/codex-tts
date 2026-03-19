import Foundation

package struct DaemonStatusSnapshot: Codable, Equatable {
    package let globalEnabled: Bool
    package let focusSessionID: String?
    package let sessions: [ManagedSessionSnapshot]
    package let snapshotVersion: Int?

    enum CodingKeys: String, CodingKey {
        case globalEnabled = "global_enabled"
        case focusSessionID = "focus_session_id"
        case sessions
        case snapshotVersion = "snapshot_version"
    }
}

package struct ManagedSessionSnapshot: Codable, Equatable, Identifiable {
    package let sessionID: String
    package let cwd: String
    package let startedAt: Int
    package let status: String
    package let launcherPID: Int?
    package let codexPID: Int?
    package let threadID: String?
    package let rolloutPath: String?
    package let isFocus: Bool
    package let isMuted: Bool
    package let lastFinalText: String?
    package let lastEventAt: Int?

    package var id: String { sessionID }

    enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case cwd
        case startedAt = "started_at"
        case status
        case launcherPID = "launcher_pid"
        case codexPID = "codex_pid"
        case threadID = "thread_id"
        case rolloutPath = "rollout_path"
        case isFocus = "is_focus"
        case isMuted = "is_muted"
        case lastFinalText = "last_final_text"
        case lastEventAt = "last_event_at"
    }
}
