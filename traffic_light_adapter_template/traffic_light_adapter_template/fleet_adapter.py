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

import sys
import argparse
import yaml
import time
import threading
import asyncio
import nudged

import rclpy
import rclpy.node
from rclpy.parameter import Parameter
from rclpy.duration import Duration

import rmf_adapter
from rmf_adapter import Adapter
import rmf_adapter.vehicletraits as traits
import rmf_adapter.geometry as geometry

from .RobotClientAPI import RobotAPI
from .traffic_light_command_handle import TrafficLightCommandHandle


# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
def compute_transforms(level, coords, node=None):
    """Compute the robot->RMF nudged transform for one map level."""
    rmf_coords = coords['rmf']
    robot_coords = coords['robot']
    tf = nudged.estimate(robot_coords, rmf_coords)
    if node:
        mse = nudged.estimate_error(tf, robot_coords, rmf_coords)
        node.get_logger().info(
            f'Transformation error estimate for {level}: {mse}'
        )
    return tf


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main(argv=sys.argv):
    rclpy.init(args=argv)
    rmf_adapter.init_rclcpp()
    args_without_ros = rclpy.utilities.remove_ros_args(argv)

    parser = argparse.ArgumentParser(
        prog='traffic_light_fleet_adapter',
        description='Configure and spin up the fleet adapter',
    )
    parser.add_argument(
        '-c',
        '--config_file',
        type=str,
        required=True,
        help='Path to the config.yaml file',
    )
    parser.add_argument(
        '-sim',
        '--use_sim_time',
        action='store_true',
        help='Use sim time, default: false',
    )
    args = parser.parse_args(args_without_ros[1:])
    print('Starting traffic light fleet adapter...')

    with open(args.config_file, 'r') as f:
        config_yaml = yaml.safe_load(f)

    fleet_config = config_yaml['rmf_fleet']
    fleet_name = fleet_config['name']
    robots_config = fleet_config['robots']
    fleet_manager_config = config_yaml['fleet_manager']

    node = rclpy.node.Node(f'{fleet_name}_command_handle')
    adapter = Adapter.make(f'{fleet_name}_fleet_adapter')
    assert adapter, (
        'Unable to initialize fleet adapter. '
        'Please ensure RMF Schedule Node is running'
    )

    if args.use_sim_time:
        param = Parameter('use_sim_time', Parameter.Type.BOOL, True)
        node.set_parameters([param])
        adapter.node.use_sim_time()

    # Build VehicleTraits from config
    linear_config = fleet_config['limits']['linear']
    angular_config = fleet_config['limits']['angular']
    profile_config = fleet_config['profile']

    vehicle_traits = traits.VehicleTraits(
        linear=traits.Limits(linear_config[0], linear_config[1]),
        angular=traits.Limits(angular_config[0], angular_config[1]),
        profile=traits.Profile(
            footprint=geometry.Circle(profile_config['footprint']).finalize_convex(),
            vicinity=geometry.Circle(profile_config['vicinity']).finalize_convex(),
        ),
    )

    # Compute coordinate transforms for each map level
    conversions = config_yaml.get('conversions') or {}
    reference_coordinates = conversions.get('reference_coordinates') or {}
    transforms = {}
    for level, coords in reference_coordinates.items():
        transforms[level] = compute_transforms(level, coords, node)

    robot_api = RobotAPI(fleet_manager_config)

    handles = []
    for robot_name in robots_config:
        handle = TrafficLightCommandHandle(
            fleet_name=fleet_name,
            robot_name=robot_name,
            robot_api=robot_api,
            node=node,
            transforms=transforms,
        )
        adapter.add_easy_traffic_light(
            handle.traffic_light_cb,
            fleet_name,
            robot_name,
            vehicle_traits,
            handle.pause_cb,
            handle.resume_cb,
        )
        handles.append(handle)
        node.get_logger().info(
            f'Registered traffic light handle for [{robot_name}]')

    adapter.start()
    time.sleep(1.0)
    
    node.get_logger().info(
        f'[{fleet_name}] traffic light adapter started '
        f'with {len(handles)} robot(s)')

    update_period = 1.0 / max(fleet_config.get('robot_state_update_frequency', 2.0), 0.5)

    def update_loop():
        asyncio.set_event_loop(asyncio.new_event_loop())
        while rclpy.ok():
            now = node.get_clock().now()

            # Update all the robots in parallel using a thread pool
            update_jobs = []
            for handle in handles:
                update_jobs.append(update_robot(handle))

            asyncio.get_event_loop().run_until_complete(
                asyncio.wait(update_jobs)
            )

            next_wakeup = now + Duration(nanoseconds=update_period * 1e9)
            while node.get_clock().now() < next_wakeup:
                time.sleep(0.001)

    update_thread = threading.Thread(target=update_loop, args=())
    update_thread.start()

    rclpy_executor = rclpy.executors.SingleThreadedExecutor()
    rclpy_executor.add_node(node)
    rclpy_executor.spin()

    node.destroy_node()
    rclpy_executor.shutdown()
    rclpy.shutdown()


# Parallel processing solution derived from
# https://stackoverflow.com/a/59385935
def parallel(f):
    def run_in_parallel(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(
            None, f, *args, **kwargs
        )

    return run_in_parallel


@parallel
def update_robot(handle):
    try:
        data = handle.fetch_state()
        if data is None:
            return
        handle.update_state(data)
    except Exception as err:
        handle.logger.error(
            f'[{handle.robot_name}] update loop error: {err}')

if __name__ == '__main__':
    main(sys.argv)
