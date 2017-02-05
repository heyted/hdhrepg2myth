# -*- coding: utf-8 -*-
import time, os, sys

try:
    from collections import OrderedDict
except:
    from ordereddict_compat import OrderedDict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath('util.py'))))
import util
import errors


def chanTuple(guide_number,chanCount):
    major, minor = (guide_number + '.0').split('.',2)[:2]
    return (int(major),int(minor),chanCount*-1)

class ChannelSource(dict):
    @property
    def url(self):
        return self['url']

    @property
    def ID(self):
        return self['ID']

class Channel(object):
    def __init__(self,data,device_response):
        self.number = data['GuideNumber']
        self.name = data['GuideName']
        self.sources = [ChannelSource({'url':data['URL'],'ID':device_response.ID})]
        self.favorite = bool(data.get('Favorite',False))
        self.DRM = bool(data.get('DRM',False))
        self.guide = None

    def add(self,data,device_response):
        self.sources.append(ChannelSource({'url':data['URL'],'ID':device_response.ID}))

    def setGuide(self,guide):
        self.guide = guide

    def matchesFilter(self,filter_):
        if filter_.isdigit():
            return self.number.startswith(filter_)
        else:
            return filter_ in self.name.lower() or filter_ in self.guide.affiliate.lower() or filter_ == self.number

    def initialSlice(self):
        return self.guide.initialSlice()

class lineup(object):
    def __init__(self,devices):
        self.channels = OrderedDict()
        self.devices = devices
        self.hasGuideData = False
        self.hasSubChannels = False
        self.collectlineup()

    def __getitem__(self,key):
        return self.channels[key]

    def __contains__(self, key):
        return key in self.channels

    def __len__(self):
        return len(self.channels.keys())

    def isOld(self):
        return (time.time() - self._discoveryTimestamp) > self.MAX_AGE

    def index(self,key):
        if not key in self.channels: return -1
        return self.channels.keys().index(key)

    def indexed(self,index):
        if index < 0 or index >= len(self):
            return None
        return self.channels[ [k for k in self.channels.keys()][index] ]

    def defaultDevice(self):
        return self.devices.defaultTunerDevice()

    def collectlineup(self):
        try:
            self._collectlineup()
        except:
            self.devices = None
            raise

    def _collectlineup(self):
        if not self.devices.hasTunerDevices:
            util.DEBUG_LOG('ERROR: No tuner devices responded!')
            raise errors.NoTunersException()

        lineups = []

        err = None
        for d in self.devices.tunerDevices:
            try:
                lineup = d.lineup()
                if lineup: lineups.append((d,lineup))
            except:
                err = util.ERROR()
                continue

        if not lineups:
            if err:
                util.LOG('ERROR: No compatible devices found!')
                raise errors.NoCompatibleDevicesException()
            else:
                util.DEBUG_LOG('ERROR: Empty lineup!')
                raise errors.EmptylineupException()

        hideDRM = True

        while lineups:
            lowest = min(lineups,key=lambda l: l[1] and chanTuple(l[1][0]['GuideNumber'],l[0].channelCount) or (0,0,0)) #Prefer devices with the most channels assuming (possibly wrongly) that they are getting a better signal
            if not lowest[1]:
                lineups.pop(lineups.index(lowest))
                continue

            chanData = lowest[1].pop(0)

            if hideDRM and chanData.get('DRM'): continue

            channelNumber = chanData['GuideNumber']

            if '.' in channelNumber: self.hasSubChannels = True

            if channelNumber in self.channels:
                self.channels[chanData['GuideNumber']].add(chanData,lowest[0])
            else:
                self.channels[chanData['GuideNumber']] = Channel(chanData,lowest[0])

        if not self.channels: util.DEBUG_LOG(lineups)

    def apiAuthID(self):
        return self.devices.apiAuthID()
