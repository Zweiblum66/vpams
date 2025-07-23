# Changelog

All notable changes to the Asset Management Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Virus scanning integration with support for multiple backends
  - ClamAV integration for local virus scanning
  - VirusTotal API integration for cloud-based scanning
  - Hybrid Analysis scanner stub for future implementation
- Automatic virus scanning during file upload validation
- API endpoint `/api/v1/assets/virus-scanner/status` to check scanner health
- Configuration options for enabling/disabling virus scanning
- Comprehensive error handling and fallback mechanisms
- Detailed scan result reporting in validation responses
- ClamAV container added to docker-compose.yml
- Documentation for virus scanning setup and configuration
- Unit tests for virus scanner components

### Changed
- Updated file validator to include virus scanning step
- Modified upload validation workflow to reject infected files
- Enhanced validation results to include virus scan information

### Security
- Files are now automatically scanned for viruses during upload
- Infected files are rejected before being stored
- Support for multiple antivirus engines for comprehensive protection