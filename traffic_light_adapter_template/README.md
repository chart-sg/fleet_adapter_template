# traffic_light_adapter_template

> Note: This template targets Open-RMF on **ROS 2 Jazzy**. It is the `traffic_light` counterpart to the `full_control` [fleet_adapter_template](https://github.com/open-rmf/fleet_adapter_template).

The objective of this package is to serve as a reference or template for writing a python based `EasyTrafficLight` RMF fleet adapter.

Use a traffic light adapter when your robots self-navigate (the robot's own fleet manager plans and drives the path) but still need RMF for traffic deconfliction. Unlike a `full_control` adapter, the adapter does not send individual waypoint commands to RMF's planner, it reports the robot's position and movement state, and RMF tells it when to pause and resume so robots don't collide.

> Note: The implementation in this package is not the only way to write a `traffic_light` fleet adapter. It is only one such example that may be helpful for users to quickly integrate their fleets with RMF.

## How it works

RMF registers each robot via `Adapter.add_easy_traffic_light(...)`, which wires up three callbacks (see `traffic_light_command_handle.py`):

- `traffic_light_cb`: fires once with the `EasyTrafficLight` handle.
- `pause_cb`: fires when an imminent traffic conflict requires an emergency stop.
- `resume_cb`: fires when the conflict has cleared.

Each update cycle, the adapter polls the robot, then reports its state to the handle via `moving_from()`, `waiting_at()`, and `waiting_after()`. RMF returns one of `Resume`, `WaitAtNextCheckpoint`, or `PauseImmediately`, and the adapter translates that into `pause` / `resume` / `pause_at_checkpoint` commands to the robot.

## Step 1: Fill up missing code

Fill up the blocks of code which make API calls to your mobile robotic fleet. These blocks are highlighted as seen below and are found in `RobotClientAPI.py`:

```python
# IMPLEMENT YOUR CODE HERE #
```

The bulk of the work is in populating the `RobotClientAPI.py` file, which defines a wrapper for communicating with your fleet. The four functions to implement are:

| Function | Purpose |
| --- | --- |
| `get_data(robot_name)` | Return a `RobotUpdateData` snapshot of the robot's state, or `None` on transient failure. |
| `pause(robot_name)` | Command the robot's fleet manager to pause this robot. |
| `resume(robot_name)` | Command the robot's fleet manager to resume this robot. |
| `pause_at_checkpoint(robot_name, checkpoint)` | Stop the robot at the given checkpoint of the active path (it may keep moving toward the checkpoint and decelerate to stop there). |

For example, if your fleet offers a `REST API` with a `GET` method to obtain the state of the robot, then `get_data()` might be implemented as below:

```python
def get_data(self, robot_name):
    url = self.prefix + f'/data/{robot_name}/state'
    try:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return RobotUpdateData(response.json(), robot_name)
    except Exception as err:
        print(f'Error fetching state for {robot_name}: {err}')
    return None
```

Alternatively, if your robotic fleet offers a websocket port for communication or allows for messages to be exchanged over ROS 1/2, then these functions can be implemented using those protocols respectively.

## Step 2: Update config.yaml

The `config.yaml` file contains the parameters for setting up the fleet adapter. There are three broad sections to this file:

1. **rmf_fleet**: parameters that describe the robots in this fleet
2. **fleet_manager**: containing configurations to connect to the robot's API in order to retrieve robot status and send commands from RMF
3. **reference_coordinates**: per map level, two sets of `[x, y]` coordinates that correspond to the same locations recorded in the RMF (`traffic_editor`) and robot specific coordinate frames respectively. These are required to estimate the coordinate transform between frames. A minimum of 4 matching waypoints per level is recommended.

> Note: This fleet adapter uses the nudged python library to compute transformations from RMF to Robot frame and vice versa. If the user is aware of the scale, rotation and translation values for each transform, they may modify the code in fleet_adapter.py to directly create the nudged transform objects from these values.

## Step 3: Run the fleet adapter

Run the command below while passing the path to the configuration file.

```bash
ros2 run traffic_light_adapter_template fleet_adapter -c CONFIG_FILE
```
