# Changelog

## [14.0.0] - 2026-06-20

## [13.0.0] - 2026-06-15
### Features
- improve model status parsing and refine cooldown layout
### Other Changes
- update test_banner to match current banner content
- update

## [12.0.0] - 2026-06-05
### Features
- improve auto-backup visibility and harden status detection

## [11.0.0] - 2026-06-04

## [10.0.0] - 2026-06-04

## [9.0.0] - 2026-06-03
### Features
- rotate accounts by last checked time and change active status style to bright blue

## [8.0.0] - 2026-06-02
### Features
- add agm sync auto for bidirectional cloud synchronization
### Bug Fixes
- update sync auto unit test to mock dependencies inside sync module

## [7.0.0] - 2026-06-02
### Bug Fixes
- pop record_type from consolidated metadata if backup exists to ensure correct listing
- restrict status metadata to a single latest file per account and preserve original one-backup-per-account logic
- generate timestamped archive filenames to support multiple backups per account
- bypass status check and abort backup when antigravity-oauth-token is missing
### Other Changes
- remove temporary metadata files
- consolidate backup and status metadata into a single latest metadata file per account

## [6.0.0] - 2026-06-02

## [5.0.0] - 2026-05-26

## [4.0.0] - 2026-05-26
### Features
- consolidate account detection, implement cloud isolation and quota grouping, and enhance CLI state diagnostics

## [3.0.0] - 2026-05-26
### Other Changes
- update

## [2.0.0] - 2026-05-25
### Documentation
- update README.md to v3 gold standard (#11)
- Add strategic ROADMAP.md (#10)

## [1.0.0] - 2026-05-25
### Other Changes
- mock AGM_HOME in profile tests to fix CI failure
