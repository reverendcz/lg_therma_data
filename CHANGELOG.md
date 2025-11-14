# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-11-15

### Removed
- ❌ Register 40010 (Energy State Input) - removed due to unreliable data and undocumented behavior
- 🗑️ Mystery register analysis tools and documentation
- 🧹 Debug code specific to register 40010
- 📁 Cleanup of temporary analysis files

### Changed  
- 📊 Reduced from 28 to 27 registers for improved reliability
- 🔧 Simplified monitoring output without mystery values
- 📝 Updated documentation to reflect current register count

## [1.0.0] - 2025-11-13

### Added
- ✨ Complete monitoring of 27 registers for LG Therma V heat pump
- 🎨 Colored delta monitoring with emoji indicators in terminal output
- 📊 CSV export with delta tracking and previous value comparison
- 📝 Log file support for detailed analysis
- 🔄 Real-time change detection with configurable intervals
- 🌡️ Temperature monitoring (room, circuits, outdoor, DHW)
- 💧 Hydraulic parameters (flow rate, targets)
- ⚡ Energy consumption tracking (electrical power in kW)
- 🔧 Component status monitoring (pump, compressor, defrost, backup heaters)
- 🌙 Silent mode detection and control
- 📋 Production-ready configuration for LG HN091MR.NK5 (9kW)

### Technical Implementation
- RS485 TO POE ETH (B) communication support
- Modbus RTU/TCP protocol implementation
- ANSI color codes for terminal output
- Type-specific delta coloring (temperature, power, binary, flow)
- Automatic register type detection (holding vs input)
- Error handling and connection recovery

### Configuration
- `registers.yaml` - Main production configuration (28 registers)
- `registers_final_complete.yaml` - Complete register set backup
- Scalable register definitions with units and descriptions

### Documentation
- Complete README.md with usage examples
- LG_Therma_V_Registry_Documentation.md with register details
- Implementation documentation in docs/COMPLETION_SUMMARY.md
- Modbus communication reference in docs/LG_ThermaV_Modbus.md

### Tested Hardware
- LG Therma V HN091MR.NK5 (9kW heat pump)
- RS485 TO POE Ethernet converter
- IP: 192.168.100.199:502

### Color Coding System
- 🔥🔴 Temperature increase - red with fire emoji
- ❄️🔵 Temperature decrease - blue with snow emoji
- ⬆️🟡 Power increase - yellow with up arrow
- ⬇️🟣 Power decrease - magenta with down arrow
- 📈🟢 Binary 0→1 - green with chart emoji
- 🔴 Binary 1→0 - red
- 💪🔵 Flow increase - cyan with muscle emoji

### Initial Release
- First stable release ready for production use
- Comprehensive monitoring solution
- Clean workspace structure
- Git repository with proper versioning

[1.0.0]: https://github.com/reverendcz/lg_therma_data/releases/tag/v1.0