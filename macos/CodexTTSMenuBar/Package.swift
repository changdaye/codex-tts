// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "CodexTTSMenuBar",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .executable(name: "CodexTTSMenuBar", targets: ["CodexTTSMenuBar"]),
    ],
    targets: [
        .executableTarget(
            name: "CodexTTSMenuBar",
            path: "CodexTTSMenuBar"
        ),
    ]
)
