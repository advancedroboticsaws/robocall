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

ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
ROBOT1_LOG = '/home/advrobot/robocall_server_robot1_' + st + '.log'
ROBOT1_BATTERY_LOG = '/home/advrobot/robocall_server_robot1_battery_' + st + '.log'
ROBOT2_LOG = "/home/advrobot/robocall_server_robot2" + st + ".log"
ROBOT2_BATTERY_LOG = "/home/advrobot/robocall_server_robot2_battery_" + st + ".log"


# ROBOCALL_LOG = '/home/kkuei/robocall_server.log'

# ROBOCALL_IP = '192.168.30.132'
ROBOCALL_IP = '192.168.64.10'

sqlite_file = '/home/advrobot/amr_status_db.sqlite'

# For Office
# ext_front_code = ''
# For Shang_Hai
# ext_front_code = '6'
# For Bei Jing
ext_front_code = ''

#reception
reception_extension = ''

# Jason phone
Jason_phone = '0958331981'
# Jimmy phone
Jimmy_phone = '0921842654'



c = None
conn = None


def robocall_reboot():
    time.sleep(3.0)
    os.system('sync;sync;')
    # Reboot
    os.system('echo "@Advrobot" | sudo -S reboot')


def delivery_call(rid ,user_pick_up, roomId, pw):
    loop_count = 0
    robotExitString = ""
    robotId = str(rid)
    
    while loop_count < 3:
        if not user_pick_up:
            p = subprocess.Popen('asterisk -rvvvvv', shell=True, stdout=PIPE, stdin=PIPE, stderr=STDOUT)


            if rid == "001":
                print("try to dial from port 1")
                p.stdin.write('dialplan set global pw1 ' + pw + '\n')
                #ss0 = 'channel originate DAHDI/1/' + str(ext_front_code) + str(int(roomId))\
                #      + ' extension 100@context_001\n'
                ss0 = 'channel originate DAHDI/1/' + str(Jimmy_phone) \
                  + ' extension 100@context_001\n'
                robotExitString = "Robot1 pickup"
            elif rid == "002":
                print("try to dial from port 2")
                p.stdin.write('dialplan set global pw2 ' + pw + '\n')
                #ss0 = 'channel originate DAHDI/4/' + str(ext_front_code) + str(int(roomId))\
                #      + ' extension 100@context_002\n'
                ss0 = 'channel originate DAHDI/4/' + str(Jason_phone) \
                  + ' extension 100@context_002\n'
                robotExitString = "Robot2 pickup"

                        
            # for testing roomId=141
            # roomId = str(141)            
            
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
                    elif bool(re.search( robotExitString , line)):
                        user_pick_up = True
                        print("find pickup msg!!!: "+robotExitString)
                else:  # print "Hungup"
                    time.sleep(5)
                    if not user_pick_up:
                        print "Hangup but not pressing 0... back to loop"
                    loop_count += 1
                    break

            p.stdin.write('exit \n')
            p.stdin.close()
            p.stdout.close()
            p.kill()

        elif user_pick_up:
            print "user_picp_up == True"
            break
        else:
            pass

        p.stdin.write('exit \n')
        p.kill()

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


def remove_call(rid ,user_pick_up, ext, currentRoomId, targetRoomId):
    print(">>>>>>>>>>>>>>>>>>> remove_call start.")
    # for testing purpose in office, ext=21
    # ext = str(8141)
    
    ext = str(ext)
    robotId = str(rid)
    robotExitString = ""
    currentRoomId = str(currentRoomId).zfill(4)
    targetRoomId = str(targetRoomId).zfill(4)

    ss0 = 'rid: '+rid +' ext: ' + ext + ' currentRoomId: ' + currentRoomId + ' targetRoomId:' + targetRoomId
    print(ss0)

    loop_count = 0

    while loop_count < 3:
        if not user_pick_up:


            p = subprocess.Popen('asterisk -rvvvvv', shell=True, stdout=PIPE, stdin=PIPE, stderr=STDOUT)

            if rid == "001":
                print("try to dial from port 1")
                p.stdin.write('dialplan set global robot1_currentRoomId ' + currentRoomId + '\n')
                p.stdin.write('dialplan set global robot1_targetRoomId ' + targetRoomId + '\n')
                #ss0 = 'channel originate DAHDI/1/' + ext + ' extension 200@context_001\n'
                ss0 = 'channel originate DAHDI/1/' + str(Jimmy_phone) + ' extension 200@context_001\n'               
                robotExitString = "Robot1 pickup"
            elif rid == "002":
                print("try to dial from port 2")
                p.stdin.write('dialplan set global robot2_currentRoomId ' + currentRoomId + '\n')
                p.stdin.write('dialplan set global robot2_targetRoomId ' + targetRoomId + '\n')
                #ss0 = 'channel originate DAHDI/4/' + ext + ' extension 200@context_002\n'
                ss0 = 'channel originate DAHDI/4/' + str(Jimmy_phone) + ' extension 200@context_002\n'
                robotExitString = "Robot2 pickup"


            # generate call
            
            print("==========================")
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
                    elif bool(re.search(robotExitString, line)):
                        user_pick_up = True
                else:  # Hungup
                    time.sleep(5)
                    if not user_pick_up:
                        print "Hangup but not pressing 1... back to loop"
                    loop_count += 1
                    break
            
            p.stdin.write('exit \n')
            p.stdin.close()
            p.stdout.close()
            p.kill()

        elif user_pick_up:
            print "user_picp_up == True"
            break
        else:
            pass

        

    if user_pick_up == True:
        return "Status: Completed"
    elif user_pick_up == False:
        print("request push notification!")
        return "Status: Expired"

def box_not_closed(rid, roomId):
    
    loop_count = 0
    # ignore calling
    user_pick_up = False

    robotId = str(rid)
    roomId = str(roomId)
    robotExitString = ""

    print ("robotId :"+rid)
    print ("roomid :" + roomId)
    while loop_count < 3:
        if not user_pick_up:
            p = subprocess.Popen('asterisk -rvvvvv', shell=True, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
            
            # for testing roomId=141
            # roomId = str(141)
            
            if rid == "001":
                print("try to dial from port 1")
                p.stdin.write('dialplan set global robot1Id ' + robotId + '\n')
                p.stdin.write('dialplan set global robot1_roomId ' + roomId + '\n')
                #ss0 = 'channel originate DAHDI/1/' + str(reception_extension)\
                #      + ' extension 300@context_001\n'

                ss0 = 'channel originate DAHDI/1/' + str(Jimmy_phone) \
                      + ' extension 300@context_001\n'
                robotExitString = "Robot1 pickup"
            elif rid == "002":
                print("try to dial from port 2")
                p.stdin.write('dialplan set global robot2Id ' + robotId + '\n')
                p.stdin.write('dialplan set global robot2_roomId ' + roomId + '\n')
                #ss0 = 'channel originate DAHDI/4/' + str(reception_extension)\
                #      + ' extension 300@context_002\n'
                ss0 = 'channel originate DAHDI/4/' + str(Jimmy_phone) \
                      + ' extension 300@context_002\n'
                robotExitString = "Robot2 pickup"
            
            print("dial to :", ss0)
            p.stdin.write(ss0)
            
            
            while True:
                line = p.stdout.readline()
                if re.search("Hungup", line) is None:
                    print("stdout: ",line.rstrip())
                    if bool(re.search("NOTICE", line)):
                        print "Wait for dahdi channel resource!"
                        time.sleep(10)
                        break
                    elif bool(re.search(robotExitString, line)):
                        print("find pickup msg!!!: "+robotExitString)
                        user_pick_up = True
                else:  # print "Hungup"
                    time.sleep(5)
                    if not user_pick_up:
                        print "Hangup but not pressing 0... back to loop"
                    loop_count += 1
                    break
            
            p.stdin.write('exit \n')
            p.stdin.close()
            p.stdout.close()
            p.kill()
            

        elif user_pick_up:
            print "user_picp_up == True"
            break
        else:
            pass
        

    #user_pick_up = True

    if user_pick_up:
        print "Status: Completed"
        return "Status: Completed"
    else:
        print "Status: Expired"
        return "Status: Expired"

    '''
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
    '''

def delivery_overtime(rid, roomId):
    loop_count = 0
    # ignore calling
    user_pick_up = False
    robotId = str(rid)
    roomId = str(roomId)
    robotExitString = ""


    while loop_count < 3:
        if not user_pick_up:
            p = subprocess.Popen('asterisk -rvvvvv', shell=True, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
            
            # for testing roomId=141
            # roomId = str(141)
            if rid == "001":
                ss0 = 'channel originate DAHDI/1/' + str(Jimmy_phone) \
                      + ' extension 400@context_001\n'
                #ss0 = 'channel originate DAHDI/1/' + str(ext_front_code) + str(int(roomId))\
                #      + ' extension 400@context_001\n'
                robotExitString = "Robot1 pickup"
            elif rid == "002":
                ss0 = 'channel originate DAHDI/4/' + str(Jason_phone) \
                      + ' extension 400@context_002\n'
                #ss0 = 'channel originate DAHDI/4/' + str(ext_front_code) + str(int(roomId))\
                #      + ' extension 400@context_002\n'
                robotExitString = "Robot2 pickup"

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
                    elif bool(re.search(robotExitString, line)):
                        print("find pickup msg!!!: "+robotExitString)
                        user_pick_up = True
                else:  # print "Hungup"
                    time.sleep(5)
                    if not user_pick_up:
                        print "Hangup but not pressing 0... back to loop"
                    loop_count += 1
                    break
            
            p.stdin.write('exit \n')
            p.stdin.close()
            p.stdout.close()
            p.kill()

        elif user_pick_up:
            print "user_picp_up == True"
            break
        else:
            pass

            

    if user_pick_up:
        print "Status: Completed"
        return "Status: Completed"
    else:
        print "Status: Expired"
        return "Status: Expired"

    '''
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
    '''

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
    def logging(self, rid, msg):
        global ROBOT1_LOG, ROBOT2_LOG
        logging.getLogger("cherrypy").propagate = False
        if rid == "001":
            logging.basicConfig(filename=ROBOT1_LOG,format='%(asctime)s %(levelname)s: %(message)s',level=logging.DEBUG)
            logging.info(msg)
        elif rid == "002":
            logging.basicConfig(filename=ROBOT2_LOG,format='%(asctime)s %(levelname)s: %(message)s',level=logging.DEBUG)
            logging.info(msg)
        

    @cherrypy.expose
    def batterylogging(self, rid, msg):
        global ROBOT1_BATTERY_LOG, ROBOT2_BATTERY_LOG
        logging.getLogger("cherrypy").propagate = False
        if rid == "001":
            logging.basicConfig(filename=ROBOT1_BATTERY_LOG,format='%(asctime)s %(levelname)s: %(message)s',level=logging.DEBUG)
            logging.info(msg)
        elif rid =="002":
            logging.basicConfig(filename=ROBOT2_BATTERY_LOG,format='%(asctime)s %(levelname)s: %(message)s',level=logging.DEBUG)
            logging.info(msg)
        

    @cherrypy.expose
    def remove_car_req(self, rid, ext=1234, currentRoomId=2345, targetRoomId=3456):
        user_pick_up = False
        
        # uncomment this line to ignore making calls for testing purposes
        # user_pick_up = True

        call_thread = threading.Thread(target=remove_call, args=(rid, user_pick_up, ext, currentRoomId, targetRoomId,))
        call_thread.start()
        print("robocall_received_remove_task")
        return "robocall_received_remove_task"

    @cherrypy.expose
    def robocall(self, rid, roomId=0, pw=1234):
        user_pick_up = False

        # uncomment this line to ignore making calls for testing purposes
        # user_pick_up = True

        call_thread = threading.Thread(target=delivery_call, args=(rid, user_pick_up, roomId, pw))
        call_thread.start()
        print("robocall_received_inform_task")
        return "robocall_received_inform_task"

    @cherrypy.expose
    def box_not_closed_req(self ,rid= 0 ,roomId=0 ):
	
	
	call_thread = threading.Thread(target=box_not_closed, args=(rid, roomId))

        call_thread.start()
	print("robocall_received_remove_task")
     
    	return "robocall_received_inform_task"

    @cherrypy.expose
    def delivery_overtime_req(self,rid = 0 ,roomId= 0 ):

	call_thread = threading.Thread(target=delivery_overtime, args=(rid, roomId))
	call_thread.start()	
	print("robocall_received_inform_task")
	return "robocall_received_inform_task"

    @cherrypy.expose
    def reboot(self, robot_id=0, tid=0, pw=0):
        # Reboot robocall by AMR.
        if pw == 'robocall_server':
            print("robocall reboot.")
            reboot_thread = threading.Thread(target=robocall_reboot)
            reboot_thread.start()
            return 'OK'
        else:
            return "Wrong password, permission denied."


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
