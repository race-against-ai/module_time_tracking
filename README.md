# RAAI Module Time Tracking

The Time Tracking component handles lap and checkpoint times based on coordinates sent by the vehicle tracking module. It includes a visual checkpoint definers and publishes time and sector data via pynng.

## Module Overview

This module tracks lap and sector times, providing real-time updates on vehicle progress through checkpoints and the overall lap. The system is designed to receive coordinates from the vehicle tracking module, verify the lap and sector completion, and publish relevant data such as lap times, sector times, and best times.

### Key Features:
- **Checkpoint Definer**: Allows the user to define checkpoints and set a finish line.
- **Lap and Sector Time Calculation**: Computes lap times and sector times based on vehicle progression.
- **Real-Time Data Publishing**: Publishes lap and sector times using pynng.
- **User Handling**: Tracks multiple users and their best times.

### Module Structure:
1. **`LapTimer` Class**: The core class that manages the timing and publishing of data.
2. **`Point` Class**: Represents a coordinate point, used to track vehicle positions.
3. **`CheckpointDefiner`**: A utility for defining checkpoints and finish lines.
4. **`pynng` Integration**: Communication with other modules via pynng for data publishing and receiving.

## Important Configuration & Development Notes

### Configuration:
The module relies on configuration stored in `time_tracking_config.json`. It contains:
- **Checkpoints**: Positions for sector and finish line checkpoints.
- **Pynng Configuration**: Addresses and topics for communication with other modules.

If the configuration file is not found, it will be created using a template.

### Key Functions for Development:
- **Coordinate Handling**: The `receive_coordinates` method receives the vehicle's coordinates and updates the vehicle's position relative to the checkpoints.
- **Lap & Sector Validity**: The `lap_valid` method checks if the vehicle has passed through all necessary checkpoints for a valid lap.
- **Time Calculation**: The `calc_type` function categorizes lap times as personal bests, all-time bests, or normal times.
- **Data Publishing**: The `send_data` method publishes lap and sector times, including driver information, via pynng.

### Data Persistence:
- Best times are fetched from the database through the `request_best_times` method. If the connection to the database is not available, fallback values are used.
- User-specific data is managed with the `change_user` method, which resets personal bests when switching users.

### Visualization:
- The module reads video frames and overlays checkpoint positions, then publishes the frame for visualization in real-time.
- The `draw` method is responsible for rendering the current state of the track and checkpoints.

## Notes for Further Development:
- Ensure proper handling of new configuration files and checkpoints via the `CheckpointDefiner`.
- Modify `pynng` topics or addresses in `time_tracking_config.json` to match the desired communication setup.
- The module assumes that a vehicle tracking system is running and provides coordinate updates in real-time.
- Test configurations and behavior with fallback settings if no real vehicle data is available.

## Requirements:
- `pynng`
- `cv2`
- `numpy`
