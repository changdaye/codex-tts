// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "CodexTTSMenuBar",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .library(name: "CodexTTSMenuBarCore", targets: ["CodexTTSMenuBarCore"]),
        .executable(name: "CodexTTSMenuBar", targets: ["CodexTTSMenuBar"]),
    ],
    targets: [
        .target(
            name: "CodexTTSMenuBarCore",
            path: "CodexTTSMenuBar",
            exclude: [
                "CodexTTSMenuBarApp.swift",
            ],
            sources: [
                "CLIClient.swift",
                "MenuBarViewModel.swift",
                "Models.swift",
            ]
        ),
        .executableTarget(
            name: "CodexTTSMenuBar",
            dependencies: ["CodexTTSMenuBarCore"],
            path: "CodexTTSMenuBar",
            exclude: [
                "CLIClient.swift",
                "MenuBarViewModel.swift",
                "Models.swift",
            ],
            sources: [
                "CodexTTSMenuBarApp.swift",
            ]
        ),
        .executableTarget(
            name: "CodexTTSMenuBarSmoke",
            dependencies: ["CodexTTSMenuBarCore"],
            path: "SmokeTests/CodexTTSMenuBarSmoke"
        ),
    ]
)
