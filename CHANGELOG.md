# Changelog — Percival Deep Research MCP

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Changed
- (placeholder para o refactor)

## [1.0.0] — 2026-07-22

### Security
- Input sanitization for all parameters (prompt injection, length limits).
- Web content prefixed with untrusted-content warning header.
- Generic error messages to prevent internal information leakage.
- UUID v4 validation for `research_id`.
- Secure default host binding (127.0.0.1) for SSE mode.