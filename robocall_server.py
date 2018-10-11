#!/usr/bin/python
# coding=utf-8
#from __future__ import print_function

import threading
import cherrypy
import urllib
import requests
import os
import os.path
import sys,time,subprocess,re
import logging
from subprocess import Popen, PIPE, STDOUT
from pushy import PushyAPI
reload(sys)
sys.setdefaultencoding('utf-8')


ROBOCALL_LOG = '/home/advrobot/robocall_server.log'
# ROBOCALL_LOG = '/home/kkuei/robocall_server.log'

# ROBOCALL_IP = '192.168.65.100'
ROBOCALL_IP = '192.168.30.62'

# For Office
ext_front_code = ''
# For Shang_Hai
# ext_front_code = '6'
# For Bei Jing
# ext_front_code = '8'


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

            ss0 = 'channel originate DAHDI/1/' + str(ext_front_code) + ext + ' extension 200@from-internal\n'
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


if __name__ == '__main__':
    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.server.thread_pool = 10
    cherrypy.quickstart(robocall_server())
