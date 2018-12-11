import rospkg
import pandas as pd
from collections import OrderedDict, defaultdict
from heapq import heappop, heappush
import threading
import collections
from json import loads
import paho.mqtt.client as mqtt
import atexit

ROBOCALL_IP = '192.168.30.132'


# Dijkstra Algorithm: find the shortest path
def dijkstra(start, destination, path_dic):
    path_buffer = list()
    q, seen = [(0, start, path_buffer)], set()

    while q:
        # Pop and return the smallest item from the heap, maintaining the heap invariant. If the heap is empty,
        # IndexError is raised. To access the smallest item without popping it, use heap[0].
        (cost, v1, path) = heappop(q)

        if v1 not in seen:
            seen.add(v1)
            path.append(v1)
            if v1 == destination:
                return path

            for c, v2 in path_dic.get(v1, ()):
                if v2 not in seen:
                    path2 = path[0:]
                    # Push the value item onto the heap, maintaining the heap invariant.
                    heappush(q, (cost + c, v2, path2))
        # print(path)
    return None


class TrafficController:
    def __init__(self):
        self.path_dic = defaultdict(list)
        self.path_booking = defaultdict(list)

        self.mission_path = {}
        self.booked_path = {}

    def robots_setting(self, robot_id_list):
        for robot_id in robot_id_list:
            self.mission_path[robot_id] = []
            self.booked_path[robot_id] = []

    def update_nodes_on_all_floor(self):
        # ros_package = rospkg.RosPack()
        # file_name = ros_package.get_path('robot_unique_parameters')
        file_name = 'room_graph.xlsx'

        df_all = pd.read_excel(file_name, dtype=str, sheet_name=None)
        for floor in df_all.keys():
            df = df_all[floor]
            df.values
            df.replace('nan', '')

            # for row, column in
            for row in range(df.shape[0]):
                for col in range(df.shape[1]):
                    value = df.iloc[row][col]

                    left = col - 1
                    right = col + 1
                    up = row - 1
                    down = row + 1

                    if value != "nan":
                        if left < 0:
                            left = 0
                        if right > df.shape[1] - 1:
                            right = df.shape[1] - 1
                        if up < 0:
                            up = 0
                        if down > df.shape[0] - 1:
                            down = df.shape[0] - 1
                        area = [df.iloc[row][left], df.iloc[row][right], df.iloc[up][col], df.iloc[down][col]]
                        for item in area:
                            if item != "nan" and item != value:
                                self.path_dic[value].append((1, item))

            # Connect each floor through 'EVin'
            evw = 'EVW' + str(floor[0])
            evin = 'EVin'
            evws = evw + 'S'

            self.path_dic[evw].append((1, evin))
            self.path_dic[evin].append((1, evw))
            self.path_dic[evw].append((1, evws))
            self.path_dic[evws] = [(1, evw)]

        for node in self.path_dic.keys():
            self.path_booking[node] = 'available'
        print(self.path_booking)

    def path_generator(self, current_position, goal):
        # Access all the pose in global path
        path_temp = dijkstra(current_position, goal, self.path_dic)
        return path_temp

    def booking_agent(self, path, amr_id):
        self.mission_path[amr_id] = path
        booked = []
        for step, node in enumerate(path):
            # Check the node:
            if self.path_booking[node] in ['available', amr_id]:
                self.path_booking[node] = amr_id
                booked.append(node)
            else:
                break
        return booked

    def monitor_agent(self, current_node, amr_id):
        for step, check_node in enumerate(self.booked_path[amr_id]):
            if self.path_booking[check_node] == amr_id:
                if check_node == current_node:
                    # Stay in the same node >>> No Action needed.
                    return
                else:
                    # Step 1. Update the Node Booking
                    if self.booked_path[amr_id][step+1] == current_node:
                        self.path_booking[check_node] = 'available'
                    # Step 2. Check the released node
                    robot_to_check = robots_id_list[:]
                    robot_to_check.remove(amr_id)
                    for robot in robot_to_check:
                        node_in_mission = check_node in self.mission_path[robot]
                        node_in_booked = check_node in self.booked_path[robot]
                        if node_in_mission and not node_in_booked:
                            self.booked_path[robot] = self.booking_agent(self.mission_path[robot], robot)
                            # TODO: Update AMR Booked Path
                            print(self.booked_path[robot])


if __name__ == '__main__':
    robots_id_list = ['#4', '#5']
    tc = TrafficController()
    tc.robots_setting(robots_id_list)
    tc.update_nodes_on_all_floor()
    # Booking Nodes for AMR_1
    amr4_mission_path = tc.path_generator('Station_1', '404')

    tc.booked_path[robots_id_list[0]] = tc.booking_agent(amr4_mission_path, robots_id_list[0])

    # Booking Nodes for AMR_1
    """
    Note:
    How to decide the depart
    """
    amr5_mission_path = tc.path_generator('Station_2', '401')
    tc.booked_path[robots_id_list[1]] = tc.booking_agent(amr5_mission_path, robots_id_list[1])

    for node in tc.booked_path['#4']:
        tc.monitor_agent(node, robots_id_list[0])






"""

# =================== MQTT =====================
def convert(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("/amr_status_agent", qos=2)


def on_message(client, userdata, msg):

    amr_status_dict = convert(loads(msg.payload))
    print(amr_status_dict)
    ts = time.time()
    now = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
    item = (now, amr_status_dict['ts_start'], amr_status_dict['status'],
            amr_status_dict['mission'], amr_status_dict['task_position'], amr_status_dict['closet_position'],
            amr_status_dict['capacity'],
            amr_status_dict['EV_abort'], amr_status_dict['EV_entering_abort'], amr_status_dict['mb_abort'],
            amr_status_dict['mb_abort_counter'])

    c.execute('insert into amr_status_db values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', item)
    conn.commit()


def exit_handler():
    c.close()
    conn.close()
    print 'My application is ending!'


def mqtt_listener():
    print('System Start up')
    # MQTT listener
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(ROBOCALL_IP, 1883, 60)

    atexit.register(exit_handler)
    client.loop_forever()
"""



