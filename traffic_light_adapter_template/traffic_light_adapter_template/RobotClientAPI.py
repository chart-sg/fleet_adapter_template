# Copyright 2026 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Wrapper for API calls to the robot.

Here users are expected to fill up the implementations of functions
which will be used by the TrafficLightCommandHandle. For example, if
your robot has a REST API, you will need to make http request calls to
the appropriate endpoints within these functions.
"""


class RobotAPI:
    """Wrap robot/fleet manager API calls."""

    def __init__(self, config: dict):
        self.prefix = config.get('prefix', '')
        self.user = config.get('user', '')
        self.password = config.get('password', '')
        self.timeout = float(config.get('timeout', 1.0))
        self.debug = bool(config.get('debug', False))

    def get_data(self, robot_name: str):
        """Return a RobotUpdateData snapshot, or None on transient failure."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        return None

    def pause(self, robot_name: str) -> bool:
        """Command the robot's fleet manager to pause this robot."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        return False

    def resume(self, robot_name: str) -> bool:
        """Command the robot's fleet manager to resume this robot."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        return False

    def pause_at_checkpoint(
            self, robot_name: str, checkpoint: int) -> bool:
        """
        Stop the robot AT the given checkpoint of the active path.

        The robot may continue moving toward the checkpoint and decelerate
        to stop there.
        """
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        return False


class RobotUpdateData:
    """
    State snapshot for a single robot.

    Expected `data` dict shape (from the FM's JSON response):
        robot_name: str                     # robot identifier; defaults to queried name
        position: [float, float, float]     # current pose [x, y, yaw] in robot frame
        map_name: str                       # name of the map the robot is on
        current_path: list[dict]            # path the FM is executing; [] when idle
        last_completed_checkpoint: int      # index of last reached wp; -1 if none yet
        is_moving: bool                     # true while the robot is actively moving
        battery_soc: float                  # battery state of charge, 0.0–1.0
        error: str | None                   # fault string; None when operating normally

    Waypoint dict shape (each entry of `current_path`):
        map_name: str                       # map this waypoint is on
        x: float                            # waypoint position in robot frame
        y: float
        yaw: float
        yield: bool                         # optional, default True. RMF may pause here.
        mandatory_delay: float              # optional, default 0.0 (s). Expected dwell.
    """

    def __init__(self, data: dict, robot_name: str = ''):
        # Fall back to the queried name if the FM doesn't echo it back.
        echoed_name = data.get('robot_name')
        if echoed_name:
            self.robot_name = echoed_name
        else:
            self.robot_name = robot_name

        self.position = list(data['position'])
        self.map_name = data['map_name']
        self.current_path = list(data.get('current_path', []))
        self.last_completed_checkpoint = data.get(
            'last_completed_checkpoint', -1)
        self.is_moving = data.get('is_moving', False)

        # Display-only on the RMF side (feeds battery_percent on the
        # published RobotState). The Python binding for
        # update_battery_soc doesn't exist yet, so the adapter cannot
        # push this value today.
        self.battery_soc = data.get('battery_soc', 1.0)

        # When set, the robot is NOT following its path (hardware fault,
        # crash, lost localization, etc.).
        self.error = data.get('error') or None
