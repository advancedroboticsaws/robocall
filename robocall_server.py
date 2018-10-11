#!/usr/bin/python
# coding=utf-8
#from __future__ import print_function

import threading
import cherrypy
import urllib
import requests
import os
import os.path
import sys, subprocess, re
import logging
from subprocess import Popen, PIPE, STDOUT
from pushy import PushyAPI
from json import loads
import sqlite3
import atexit
import time, datetime
import collections
import paho.mqtt.client as mqtt
reload(sys)
sys.setdefaultencoding('utf-8')


ROBOCALL_LOG = '/home/advrobot/robocall_server.log'
# ROBOCALL_LOG = '/home/kkuei/robocall_server.log'

# ROBOCALL_IP = '192.168.30.132'
ROBOCALL_IP = '192.168.30.62'

sqlite_file = '/home/advrobot/amr_status_db.sqlite'

# For Office
ext_front_code = ''
# For Shang_Hai
# ext_front_code = '6'
# For Bei Jing
# ext_front_code = '8'


c = None
conn = None


def delivery_call(user_pick_up, roomId, pw):
    loop_count = 0
    while loop_count < 3:
        if not user_pick_up:
            p = subprocess.Popen('asterisk -rvvvvv', shell=True, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
            p.stdin.write('dialplan set global pw ' + pw + '\n')
            # for testing purpose in office, ext=21
            # ext = str(21)

            ss0 = 'channel originate DAHDI/1/' + str(ext_front_code) + str(int(roomId))\
                  + ' extension 100@from-internal\n'
            
            print(ss0)
            p.stdin.write(ss0)
            while True:
                line = p.stdout.readline()
                if re.search("Hungup", line) is None:
                    print(line.rstrip())
                    if bool(re.search("NOTICE", line)):
                        print "Wait for dahdi channel resource!"
                        time.sleep(10)
                        break
                    elif bool(re.search("KKUEI ext0", line)):
                        user_pick_up = True
                else:  # print "Hungup"
                    time.sleep(5)
                    if not user_pick_up:
                        print "Hangup but not pressing 0... back to loop"
                    loop_count += 1
                    break
        elif user_pick_up:
            print "user_picp_up == True"
            break
        else:
            pass

    if user_pick_up:
        print "Status: Completed"
        return "Status: Completed"

    elif not user_pick_up:
        print("request push notification!")

        # push notification
        s = requests.Session()
        a = {'msg': '机器人送行李到' + str(roomId) + '却无人接听'}
        announceMsg1 = urllib.urlencode(a)
        uri = str('http://' + ROBOCALL_IP + ':8080/push?' + announceMsg1)

        try:
            r = s.get(uri)
        except:
            print("[robocall] push notification failure")

        return "Status: Expired"


def remove_call(user_pick_up, ext, currentRoomId, targetRoomId):
    print(">>>>>>>>>>>>>>>>>>> remove_call start.")
    ext = str(ext)
    currentRoomId = str(currentRoomId).zfill(4)
    targetRoomId = str(targetRoomId).zfill(4)

    ss0 = 'ext: ' + ext + ' currentRoomId: ' + currentRoomId + ' targetRoomId:' + targetRoomId
    print(ss0)

    loop_count = 0

    while loop_count < 3:
        if not user_pick_up:
            p = subprocess.Popen('asterisk -rvvvvv', shell=True, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
            p.stdin.write('dialplan set global ext ' + ext + '\n')
            p.stdin.write('dialplan set global currentRoomId ' + currentRoomId + '\n')
            p.stdin.write('dialplan set global targetRoomId ' + targetRoomId + '\n')

            # generate call

            # for testing purpose in office, ext=21
            # ext = str(21)

            ss0 = 'channel originate DAHDI/1/' + ext + ' extension 200@from-internal\n'
            p.stdin.write(ss0)

            while True:
                line = p.stdout.readline()
                if re.search("Hungup", line) is None:
                    print(line.rstrip())
                    if bool(re.search("NOTICE", line)):
                        print "Wait for dahdi channel resource!"
                        time.sleep(10)
                        break
                    elif bool(re.search("KKUEI ext1", line)):
                        user_pick_up = True
                else:  # Hungup
                    time.sleep(5)
                    if not user_pick_up:
                        print "Hangup but not pressing 1... back to loop"
                    loop_count += 1
                    break

        elif user_pick_up:
            print "user_picp_up == True"
            break
        else:
            pass

    p.stdin.close()
    p.stdout.close()

    if user_pick_up == True:
        return "Status: Completed"
    elif user_pick_up == False:
        print("request push notification!")
        return "Status: Expired"


class robocall_server(object):
    push_token=[]

    @cherrypy.expose
    def index(self):
        return "Hello world!"

    @cherrypy.expose
    def set_token(self,token):
        if not token in self.push_token:
            self.push_token.append(token)
        print(self.push_token)
        return "set token:"+token

    @cherrypy.expose
    def push(self,msg):
        #print ('push:'+msg)
        data = {'message': msg}
        PushyAPI.sendPushNotification(data, self.push_token, None)
        return "notification pushed:"+msg
    
    @cherrypy.expose
    def shutdown(self):  
        cherrypy.engine.exit()

    @cherrypy.expose
    def logging(self, msg):
        logging.getLogger("cherrypy").propagate = False
        logging.basicConfig(filename=ROBOCALL_LOG,format='%(asctime)s %(levelname)s: %(message)s',level=logging.DEBUG)
        logging.info(msg)

    @cherrypy.expose
    def remove_car_req(self, ext=1234, currentRoomId=2345, targetRoomId=3456):
        user_pick_up = False
        # uncomment this line to ignore making calls for testing purposes
        # user_pick_up = True

        call_thread = threading.Thread(target=remove_call, args=(user_pick_up, ext, currentRoomId, targetRoomId,))
        call_thread.start()
        print("robocall_received_remove_task")
        return "robocall_received_remove_task"

    @cherrypy.expose
    def robocall(self, roomId=0, pw=1234):
        user_pick_up = False

        # uncomment this line to ignore making calls for testing purposes
        # user_pick_up = True

        call_thread = threading.Thread(target=delivery_call, args=(user_pick_up, roomId, pw))
        call_thread.start()
        print("robocall_received_inform_task")
        return "robocall_received_inform_task"


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
    global c, conn
    print('System Start up')
    # MQTT listener
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(ROBOCALL_IP, 1883, 60)
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()
    # name of the table to be created
    table_name1 = 'amr_status_db'

    # Connecting to the database file
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()

    # Creating a new SQLite table
    c.executescript("""CREATE TABLE IF NOT EXISTS amr_status_db(tid REAL, ts_start REAL, amr_status TEXT,
                     mission TEXT, task_position TEXT, closet_position TEXT,
                     capacity REAL,
                     EV_abort INTEGER, EV_entering_abort INTEGER, mb_abort INTEGER,
                     mb_abort_counter INTEGER);""")
    atexit.register(exit_handler)
    client.loop_forever()

if __name__ == '__main__':

    mqtt_logging_thread = threading.Thread(target=mqtt_listener)
    mqtt_logging_thread.start()

    # Cherrypy Server
    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.server.thread_pool = 10
    cherrypy.quickstart(robocall_server())