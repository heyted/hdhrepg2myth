# -*- coding: utf-8 -*-
import sys, binascii, json, threading, time, datetime, logging

DEBUG = True

T = None

def LOG(msg):
    logging.debug(msg)

def DEBUG_LOG(msg):
    logging.debug(msg)

def ERROR(txt='',hide_tb=False,notify=False):
    logging.debug('An error has occurred ' + txt)

def Version(ver_string):
    return None

def _processSetting(setting,default):
    if not setting: return default
    if isinstance(default,bool):
        return setting.lower() == 'true'
    elif isinstance(default,float):
        return float(setting)
    elif isinstance(default,int):
        return int(float(setting or 0))
    elif isinstance(default,list):
        if setting: return json.loads(binascii.unhexlify(setting))
        else: return default

    return setting

def _processSettingForWrite(value):
    if isinstance(value,list):
        value = binascii.hexlify(json.dumps(value))
    elif isinstance(value,bool):
        value = value and 'true' or 'false'
    return str(value)

def durationToShortText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds/86400)
    if days:
        return '{0}d'.format(days)
    left = seconds % 86400
    hours = int(left/3600)
    if hours:
        return '{0}h'.format(hours)
    left = left % 3600
    mins = int(left/60)
    if mins:
        return '{0}m'.format(mins)
    secs = int(left % 60)
    if secs:
        return '{0}s'.format(secs)
    return '0s'

def durationToMinuteText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    mins = int(seconds/60)
    if mins:
        mins = '{0}m'.format(mins)
    else:
        mins = ''
    secs = int(seconds % 60)
    if secs:
        return mins + '{0}s'.format(secs)
    elif mins:
        return mins

    return '0s'

def timeInDayLocalSeconds():
    now = datetime.datetime.now()
    sod = datetime.datetime(year=now.year,month=now.month,day=now.day)
    sod = int(time.mktime(sod.timetuple()))
    return int(time.time() - sod)

def sortTitle(title):
    return title.startswith('The ') and title[4:] or title

