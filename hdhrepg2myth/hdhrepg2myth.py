#!/usr/bin/env python3

import os, sys, requests, subprocess, time, socket, datetime, configparser, json, logging, signal
os.chdir('/opt/hdhrepg2myth/')
from hdhr import errors
from hdhr import tuners
from hdhr import storageservers
from hdhr import guide
from hdhr import discovery
import util

def delXmlAndExit():
    #Delete guide data in accordance with Silicondust rules and exit
    subprocess.call('rm /tmp/xmltv.xml', shell=True)
    sys.exit(0)

class GracefulKiller(object):
    killNow = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exitGracefully)
        signal.signal(signal.SIGTERM, self.exitGracefully)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
    def exitGracefully(self,signum, frame):
        global sleeping
        if sleeping:
            logging.info('hdhrepg2myth.py exiting (caught signal to exit)')
            delXmlAndExit()
        self.killNow = True

class LocalOffset(datetime.tzinfo):
    def utcoffset(self,dt):
        return utcOffset
    def tzname(self,dt):
        return "local"
    def dst(self,dt):
        return datetime.timedelta(0)

class MythGetUpcomingRec:
    def __init__(self, host, port):
        self.baseAddr = 'http://{}:{}/'.format(host, port)
        self.headers = {'Accept':'application/json'}
    def GetUpcomingRec(self, **params):
        UpcomingRec = requests.get('{}Dvr/GetUpcomingList'.format(self.baseAddr), params = params, headers = self.headers)
        if UpcomingRec:
            return UpcomingRec.json()

def get_lock(process_name):
    #Prevent multiple instances using socket lock Linux-only method
    get_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        get_lock._lock_socket.bind('\0' + process_name)
    except socket.error:
        sys.exit(0)

def tts(time):
    return time.strftime("%Y%m%d%H%M%S %z")

def removeNonAscii(s):
    s = s.replace("&", "and")
    return "".join([x if ord(x) < 128 else '_' for x in s])

def getGuide(lineup):
    try:
        guide_raw = guide.Guide(lineup)
        schedule_json_wa = guide_raw.data
        schedule_json = removeNonAscii(schedule_json_wa)
        return json.loads(schedule_json)
    except:
        logging.info('getGuide:  Unable to fetch guide')

def isbadipv4(s):
    pieces = s.split('.')
    if len(pieces) != 4: return True
    try: return not all(0<=int(p)<256 for p in pieces)
    except ValueError: return True

if __name__ == '__main__':
    get_lock('hdhrepg2myth')    
    sleeping = False
    homepath = os.path.expanduser('~')
    msg = '<mythnotification version="1">  <text>Guide updated</text>  <origin>HDHomeRun</origin>  <type>normal</type></mythnotification>'
    msg_bytes = bytearray(msg,'utf-8')
    udp_port = 6948
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        #Replace INFO with DEBUG for more logging
        logging.basicConfig(format='%(levelname)s:%(message)s', filename='/home/mythtv/hdhrepg2myth.log', filemode='w', level=logging.INFO)
    except IOError:
        logging.basicConfig(format='%(levelname)s:%(message)s', filename='/tmp/hdhrepg2myth.log', filemode='w', level=logging.DEBUG)
    config = configparser.RawConfigParser()
    killer = GracefulKiller()
    logging.info("hdhrepg2myth.py started")
    if os.path.isfile(homepath + '/hdhrepg2myth.cfg'):
        #Get config info
        config.read(homepath + '/hdhrepg2myth.cfg')
        myth_lan_ip = config.get('hdhrepg2mythsettings', 'myth_lan_ip')
        myth_ip_bytes = bytearray(myth_lan_ip,'utf-8')
        if isbadipv4(myth_lan_ip):
            logging.info('Aborting (invalid MythTV backend server IP address in configuration file)')
            sys.exit(0)
        myth_port = config.get('hdhrepg2mythsettings', 'myth_port')
        if not myth_port.isdigit():
            logging.info('Aborting (invalid MythTV backend web server port number in configuration file)')
            sys.exit(0)
        myth_source_id = config.get('hdhrepg2mythsettings', 'myth_source_id')
        if not myth_source_id.isdigit():
            logging.info('Aborting (invalid MythTV channel source id number in configuration file)')
            sys.exit(0)
        try:
            channel_low_range = float(config.get('hdhrepg2mythsettings', 'channel_low_range'))
        except:
            logging.info('Aborting (invalid channel low range number in configuration file)')
            sys.exit(0)
        try:
            channel_high_range = float(config.get('hdhrepg2mythsettings', 'channel_high_range'))
        except:
            logging.info('Aborting (invalid channel high range number in configuration file)')
            sys.exit(0)
    else:
        logging.info("Configuration file not found in home folder")
        logging.info("hdhrepg2myth.py exiting")
        sys.exit(0)
    mgu = MythGetUpcomingRec(myth_lan_ip, myth_port)
    ts = time.time()
    utcOffset = (datetime.datetime.fromtimestamp(ts) - datetime.datetime.utcfromtimestamp(ts))
    local = LocalOffset()
    for i in range(3):
        try:
            device = discovery.Devices()
            lineup = tuners.lineup(device)
            logging.info('Lineup received')
            break
        except:
            if i == 0:
                time.sleep(3)
            if i == 1:
                logging.info('Unable to fetch lineup from compatible device')
                logging.info('Trying again in five seconds')
                time.sleep(5)
            if i == 2:
                logging.info('Unable to fetch lineup from compatible device')
                logging.info('Aborting')
                logging.info('hdhrepg2myth.py exiting')
                sys.exit(0)
    while True:
        guideData = getGuide(lineup)
        gotSchedule = False
        if guideData:
            upcoming = mgu.GetUpcomingRec()['ProgramList']['Programs']
            upcomingSoon = []
            nowPlus10Hr = datetime.datetime.fromtimestamp(ts) + datetime.timedelta(hours=10)
            for i in range(len(upcoming)):
                #Build list of upcoming recordings and skip writing corresponding guide data below
                upcomStartTm = datetime.datetime.strptime(upcoming[i]['StartTime'].replace('Z', ''), '%Y-%m-%dT%H:%M:%S') + utcOffset
                if upcomStartTm < nowPlus10Hr:
                    xid = upcoming[i]['Channel']['XMLTVID']
                    upcomEndTm = datetime.datetime.strptime(upcoming[i]['EndTime'].replace('Z', ''), '%Y-%m-%dT%H:%M:%S') + utcOffset
                    upcomingSoon.append([xid, upcomStartTm, upcomEndTm])
            with open('/tmp/xmltv.xml', 'w') as xml_file:
                xml_file.write('<?xml version="1.0" encoding="ISO-8859-1"?>'+'\n')
                xml_file.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">'+'\n')
                xml_file.write('\n')
                xml_file.write('<tv source-info-name="HDHR" generator-info-name="hdhrepg2myth.py">'+'\n')
                for i in range(len(guideData)):
                    ch_id = guideData[i]['GuideNumber']
                    if not channel_low_range <= float(ch_id) <= channel_high_range: continue
                    for j in range(len(guideData[i]['Guide'])):
                        start = datetime.datetime.fromtimestamp(guideData[i]['Guide'][j]['StartTime'])
                        stop = datetime.datetime.fromtimestamp(guideData[i]['Guide'][j]['EndTime'])
                        title = guideData[i]['Guide'][j]['Title']
                        for k in range(len(upcomingSoon)):
                            if upcomingSoon[k][0] == ch_id:
                                if start <= upcomingSoon[k][1] and stop <= upcomingSoon[k][2] and stop > upcomingSoon[k][1]:
                                    logging.info('Skipping: ' + title + ' (overlap with upcoming recording)')
                                    break
                                if start >= upcomingSoon[k][1] and stop >= upcomingSoon[k][2] and start < upcomingSoon[k][2]:
                                    logging.info('Skipping: ' + title + ' (overlap with upcoming recording)')
                                    break
                        else:
                            strt = start.replace(tzinfo=local)
                            stop = stop.replace(tzinfo=local)
                            if j == 0:
                                #Erase previous guide data in accordance with Silicondust rules
                                startE = start - datetime.timedelta(hours=5)
                                startE = startE.replace(tzinfo=local)
                                xml_file.write('  <programme start="'+tts(startE)+'" stop="'+tts(strt)+'" channel="'+ch_id+'">'+'\n')
                                xml_file.write('    <title lang="en">Guide Erased</title>'+'\n')
                                xml_file.write('  </programme>'+'\n')
                            try:
                                episode = guideData[i]['Guide'][j]['EpisodeTitle']
                            except KeyError:
                                episode = ''
                            try:
                                description = guideData[i]['Guide'][j]['Synopsis']
                            except KeyError:
                                description = ''
                            xml_file.write('  <programme start="'+tts(strt)+'" stop="'+tts(stop)+'" channel="'+ch_id+'">'+'\n')
                            xml_file.write('    <title lang="en">'+title+'</title>'+'\n')
                            xml_file.write('    <sub-title lang="en">'+episode+'</sub-title>'+'\n')
                            xml_file.write('    <desc lang="en">'+description+'</desc>'+'\n')
                            xml_file.write('  </programme>'+'\n')
                            if not gotSchedule:
                                gotSchedule = True
                xml_file.write('</tv>')
        else:
            logging.info('Unable to fetch guide')
            logging.info('hdhrepg2myth.py exiting')
            sys.exit(0)
        if gotSchedule:
            logging.info('Running mythfilldatabase')
            subprocess.call('mythfilldatabase --refresh 1 --file --sourceid ' + myth_source_id + ' --xmlfile /tmp/xmltv.xml', shell=True)
            sock.sendto(msg_bytes, (myth_ip_bytes, udp_port))
        sleeping = True
        time.sleep(10500) #Sleep 2 hr 55 min
        sleeping = False
        try:
            encoderInfo = requests.get('http://' + myth_lan_ip + ':' + myth_port + '/Dvr/GetEncoderList').text
        except:
            logging.info('hdhrepg2myth.py exiting (unable to determine encoder status)')
            delXmlAndExit()
        if '<StorageGroup>LiveTV' in encoderInfo:
            device.reDiscover()
        else:
            logging.info('Live TV no longer being used')
            logging.info('hdhrepg2myth.py exiting')
            delXmlAndExit()
        if killer.killNow:
            logging.info('hdhrepg2myth.py exiting (caught exit signal)')
            delXmlAndExit()

