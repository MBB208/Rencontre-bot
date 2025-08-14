# Matching Bot Discord Project

## Overview

This is a sophisticated Python Discord bot built with discord.py that provides a complete user matching system. Users can create profiles with their interests and find compatible matches through an intelligent algorithm that considers both common interests and vector similarity. The bot features a fully asynchronous architecture with SQLite database, comprehensive safety features, and administrative tools for bot management.

## Recent Changes (August 2025)

### Latest Update: Advanced Matching System Complete ✅
- **Advanced Algorithm Implementation**: Complete IDF + fuzzy matching + synonymes system
- **Database Migrations**: Auto-added columns (interets_canonical, prefs, activity_score)
- **Interactive Buttons UI**: Replaced basic reactions with sophisticated button interactions
- **Double Opt-In Flow**: Full implementation with pending/accepted states
- **Proactive Suggestions**: Automated background system with user opt-out capability
- **Message Templates**: JSON configuration system for consistent UX
- **Testing Framework**: Complete test suite validates all critical functions
- **Production Ready**: All tests pass, strict age segregation verified

### Previous Foundation
- **Complete Architecture Redesign**: Migrated from simple bot to modular cog-based system
- **Asynchronous Database**: Replaced synchronous SQLite with aiosqlite for better performance
- **Security Features**: Added age filtering, profile anonymization, and DM-based notifications
- **Administrative Tools**: Implemented export, statistics, and profile management for administrators
- **Environment Variables**: Migrated from config.json to Replit Secrets for secure token storage
- **Strict Age Segregation**: NEVER mixes minors (13-17) with majors (18-30), enforced at algorithm level
- **Setup System**: Added /setup_channel and /update_info for admin configuration
- **Single Profile Enforcement**: Database prevents multiple profiles per Discord user
- **Privacy Features**: All commands are ephemeral (invisible to other users)

## User Preferences

Preferred communication style: Simple, everyday language.

**Critical Safety Requirements:**
- Strict separation: minors (13-17) and majors (18-30) must NEVER be matched together
- Technology limitations: Bot must communicate it cannot guarantee finding love or lifelong friends
- Single profile: Maximum 1 profile per Discord user account
- Privacy: All user interactions must be ephemeral (invisible to others)

## System Architecture

### Core Framework
- **Discord.py Library**: Uses the discord.py library for Discord API interaction with slash commands only
- **Command System**: Implements discord.ext.commands.Bot with 9 synchronized slash commands
- **Modular Design**: 5-cog architecture (utils, setup, profile, match, admin) for maintainability
- **Database**: SQLite with aiosqlite for async operations, includes migration system

### Configuration Management
- **Environment Variables**: Uses python-dotenv with Replit Secrets for secure DISCORD_TOKEN storage
- **Database Config**: Server-specific configuration stored in database (setup channels, etc.)
- **Admin System**: Built-in admin permission checking for management commands

### Event Handling
- **Discord Intents**: Properly configured intents for message content, guilds, and DM access
- **Bot Lifecycle**: Structured event handlers for bot ready state, error handling, and graceful shutdown
- **Presence Management**: Configurable bot activity status and presence

### Logging System
- **Rotating File Logs**: Implements rotating file handlers with size limits (10MB) and backup retention (5 files)
- **Multi-level Logging**: Supports configurable log levels with both console and file output
- **Structured Logging**: Centralized logging setup through utils/logger.py with consistent formatting

### Command Architecture
- **Hybrid Commands**: Supports both traditional prefix commands and Discord slash commands
- **Command Organization**: Commands organized in separate modules with proper class-based structure
- **Error Handling**: Comprehensive error management and validation for command execution

### System Monitoring
- **Performance Metrics**: Built-in latency monitoring and response time tracking
- **System Stats**: Integration with psutil for system resource monitoring (CPU, memory, platform info)
- **Uptime Tracking**: Bot uptime calculation and display capabilities

## External Dependencies

### Core Libraries
- **discord.py**: Primary Discord API wrapper for bot functionality
- **python-dotenv**: Environment variable management for configuration
- **psutil**: System and process monitoring utilities

### Python Standard Library
- **asyncio**: Asynchronous programming support for Discord API operations
- **logging**: Built-in logging framework with rotating file handlers
- **os/platform**: System information and environment variable access
- **datetime/time**: Timestamp management and uptime calculations

### Discord Platform
- **Discord API**: Bot token authentication and guild/channel access
- **Discord Slash Commands**: Modern command interface support
- **Discord Intents**: Message content and guild member access permissions

### Development Environment
- **Environment Variables**: Requires DISCORD_TOKEN and supports optional configuration variables
- **File System**: Local log file storage with automatic directory creation
- **Bot Permissions**: Requires Discord bot permissions for message sending, reading, and command execution