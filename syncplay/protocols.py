# coding:utf8
import json
import time
from functools import wraps
import logging
from typing import Optional
import asyncio
from asyncio import BaseTransport, Protocol

import syncplay
from syncplay.constants import PING_MOVING_AVERAGE_WEIGHT, CONTROLLED_ROOMS_MIN_VERSION, USER_READY_MIN_VERSION, SHARED_PLAYLIST_MIN_VERSION, CHAT_MIN_VERSION
from syncplay.messages import getMessage
from syncplay.utils import meetsMinVersion


class LineReceiver(Protocol):
    # Stolen from:
    # pu.aio.protocols.basic.LineReceiver
    # with some minor modifications
    _buffer = b''
    _delimiter = None
    _loop = None

    def _guess_delimiter(self) -> None:
        if b'\r\n' in self._buffer:
            self._delimiter = b'\r\n'
        elif b'\n' in self._buffer:
            self._delimiter = b'\n'
        elif b'\r' in self._buffer:
            self._delimiter = b'\r'

    def connection_made(self, transport: BaseTransport) -> None:
        self.transport = transport

    def write_line(self, line: bytes) -> None:
        delimiter = self._delimiter or b'\r\n'
        data = line + delimiter
        self.transport.write(data)

    def data_received(self, data: bytes) -> None:
        self._buffer += data

        if not self._delimiter:
            self._guess_delimiter()
            if not self._delimiter:
                return

        while self._buffer:
            try:
                line, self._buffer = self._buffer.split(self._delimiter, 1)
            except:
                break
            self.line_received(line)

    def line_received(self, line) -> None:
        raise NotImplementedError


class JSONCommandProtocol(LineReceiver):
    def handleMessages(self, messages: dict) -> None:
        for command, message in messages.items():
            if command == "Hello":
                self.handleHello(message)
            elif command == "Set":
                self.handleSet(message)
            elif command == "List":
                self.handleList(message)
            elif command == "State":
                self.handleState(message)
            elif command == "Error":
                self.handleError(message)
            elif command == "Chat":
                self.handleChat(message)
            elif command == "TLS":
                await self.handleTLS(message)
            else:
                # TODO: log, not drop
                self.dropWithError(getMessage("unknown-command-server-error").format(message))

    def line_received(self, line: bytes) -> None:
        # Might not work the same as LineReceiver
        # This should be fine... probably
        try:
            line = line.decode('utf-8').strip()
        except UnicodeDecodeError:
            self.dropWithError(getMessage("line-decode-server-error"))
            return
        if not line:
            return
        logging.debug(f"client/server << {line}")
        try:
            messages = json.loads(line)
        except json.decoder.JSONDecodeError:
            self.dropWithError(getMessage("not-json-server-error").format(line))
            return
        else:
            self.handleMessages(messages)

    def sendMessage(self, msg: dict) -> None:
        line = json.dumps(msg)
        logging.debug(f"client/server >> {line}")
        self.write_line(line.encode('utf-8'))

    def drop(self):
        self.transport.close()

    def dropWithError(self, error):
        raise NotImplementedError()


def requireLogged(f):
    @wraps(f)
    def wrapper(self, *args, **kwds):
        if not self._logged:
            self.dropWithError(getMessage("not-known-server-error"))
        return f(self, *args, **kwds)
    return wrapper


class SyncServerProtocol(JSONCommandProtocol):
    def __init__(self, factory):
        self._factory = factory
        self._loop = factory.loop
        self._version = None
        self._features = None
        self._logged = False
        self.clientIgnoringOnTheFly = 0
        self.serverIgnoringOnTheFly = 0
        self._pingService = PingService()
        self._clientLatencyCalculation = 0
        self._clientLatencyCalculationArrivalTime = 0
        self._watcher = None
        self.transport = None

    def __hash__(self) -> int:
        return hash('|'.join((
            self.userIp,
            str(id(self)),
        )))

    @property
    def userIp(self) -> Optional[str]:
        uip = None
        if self.transport is not None:
            uip = self.transport.get_extra_info('peername')
        return uip

    def dropWithError(self, error) -> None:
        logging.error(getMessage("client-drop-server-error").format(self.uip, error))
        self.sendError(error)
        self.drop()

    def connectionLost(self, reason) -> None:
        self._factory.removeWatcher(self._watcher)

    def getFeatures(self) -> dict:
        if not self._features:
            self._features = {
                "sharedPlaylists": meetsMinVersion(self._version, SHARED_PLAYLIST_MIN_VERSION),
                "chat": meetsMinVersion(self._version, CHAT_MIN_VERSION),
                "featureList": False,
                "readiness": meetsMinVersion(self._version, USER_READY_MIN_VERSION),
                "managedRooms": meetsMinVersion(self._version, CONTROLLED_ROOMS_MIN_VERSION)
            }
        return self._features

    def isLogged(self) -> bool:
        return self._logged

    def meetsMinVersion(self, version) -> bool:
        return self._version >= version

    def getVersion(self) -> str:
        return self._version

    def _extractHelloArguments(self, hello):
        roomName = None
        username = hello.get("username")
        if username is not None:
            username = username.strip()
        serverPassword = hello.get("password")
        room = hello.get("room")
        if room:
            roomName = room.get("name")
            if roomName is not None:
                roomName = roomName.strip()
        version = hello.get("version")
        version = hello.get("realversion", version)
        features = hello.get("features")
        return username, serverPassword, roomName, version, features

    def _checkPassword(self, serverPassword) -> bool:
        if self._factory.password:
            if not serverPassword:
                self.dropWithError(getMessage("password-required-server-error"))
                return False
            if serverPassword != self._factory.password:
                self.dropWithError(getMessage("wrong-password-server-error"))
                return False
        return True

    def handleHello(self, hello) -> None:
        username, serverPassword, roomName, version, features = self._extractHelloArguments(hello)
        if not username or not roomName or not version:
            self.dropWithError(getMessage("hello-server-error"))
            return
        else:
            if not self._checkPassword(serverPassword):
                return
            self._version = version
            self.setFeatures(features)
            self._factory.addWatcher(self, username, roomName)
            self._logged = True
            self.sendHello(version)

    @requireLogged
    def handleChat(self, chatMessage):
        if not self._factory.disableChat:
            self._factory.sendChat(self._watcher, chatMessage)

    def setFeatures(self, features):
        self._features = features

    def sendFeaturesUpdate(self):
        self.sendSet({"features": self.getFeatures()})

    def setWatcher(self, watcher):
        self._watcher = watcher

    def sendHello(self, clientVersion: str):
        hello = {}
        username = self._watcher.name
        hello["username"] = username
        userIp = self.userIp
        room = self._watcher.room
        if room:
            hello["room"] = {"name": room.name}
        hello["version"] = clientVersion  # Used so 1.2.X client works on newer server
        hello["realversion"] = syncplay.version
        hello["motd"] = self._factory.getMotd(userIp, username, room, clientVersion)
        hello["features"] = self._factory.getFeatures()
        self.sendMessage({"Hello": hello})

    @requireLogged
    def handleSet(self, settings) -> None:
        for command, setting in settings.items():
            if command == "room":
                roomName = setting.get("name")
                self._factory.setWatcherRoom(self._watcher, roomName)
            elif command == "file":
                self._watcher.setFile(setting)
            elif command == "controllerAuth":
                password = setting.get("password")
                room = setting.get("room")
                self._factory.authRoomController(self._watcher, password, room)
            elif command == "ready":
                manual = setting.get('manuallyInitiated', False)
                self._factory.setReady(self._watcher, setting['isReady'], manuallyInitiated=manual)
            elif command == "playlistChange":
                self._factory.setPlaylist(self._watcher, setting['files'])
            elif command == "playlistIndex":
                self._factory.setPlaylistIndex(self._watcher, setting['index'])
            elif command == "features":
                # TODO: Check
                self._watcher.setFeatures(setting)

    def sendSet(self, setting) -> None:
        self.sendMessage({"Set": setting})

    def sendNewControlledRoom(self, roomName: str, password) -> None:
        self.sendSet({
            "newControlledRoom": {
                "password": password,
                "roomName": roomName
            }
        })

    def sendControlledRoomAuthStatus(self, success, username: str, roomname: str) -> None:
        self.sendSet({
            "controllerAuth": {
                "user": username,
                "room": roomname,
                "success": success
            }
        })

    def sendSetReady(self, username: str, isReady, manuallyInitiated: bool = True) -> None:
        self.sendSet({
            "ready": {
                "username": username,
                "isReady": isReady,
                "manuallyInitiated": manuallyInitiated
            }
        })

    def setPlaylist(self, username: str, files) -> None:
        self.sendSet({
            "playlistChange": {
                "user": username,
                "files": files
            }
        })

    def setPlaylistIndex(self, username: str, index: int) -> None:
        self.sendSet({
            "playlistIndex": {
                "user": username,
                "index": index
            }
        })

    def sendUserSetting(self, username: str, room, file_, event) -> None:
        room = {"name": room.name}
        user = {username: {}}
        user[username]["room"] = room
        if file_:
            user[username]["file"] = file_
        if event:
            user[username]["event"] = event
        self.sendSet({"user": user})

    def _addUserOnList(self, userlist, watcher) -> None:
        room = watcher.room
        if room:
            if room.name not in userlist:
                userlist[room.name] = {}

            userFile = {
                "position": 0,
                "file": watcher.getFile() if watcher.getFile() else {},
                "controller": watcher.isController(),
                "isReady": watcher.isReady(),
                "features": watcher.getFeatures()
            }
            userlist[room.name][watcher.name] = userFile

    def sendList(self) -> None:
        userlist = {}
        watchers = self._factory.getAllWatchersForUser(self._watcher)
        for watcher in watchers:
            self._addUserOnList(userlist, watcher)
        self.sendMessage({"List": userlist})

    @requireLogged
    def handleList(self, _) -> None:
        self.sendList()

    def sendState(self, position, paused, doSeek, setBy, forced: bool = False) -> None:
        processingTime = 0
        if self._clientLatencyCalculationArrivalTime:
            processingTime = time.time() - self._clientLatencyCalculationArrivalTime

        playstate = {
            "position": position if position else 0,
            "paused": paused,
            "doSeek": doSeek,
            "setBy": setBy.name if setBy else None
        }
        ping = {
            "latencyCalculation": self._pingService.newTimestamp(),
            "serverRtt": self._pingService.rtt
        }
        if self._clientLatencyCalculation:
            ping["clientLatencyCalculation"] = self._clientLatencyCalculation + processingTime
            self._clientLatencyCalculation = 0
        state = {
            "ping": ping,
            "playstate": playstate,
        }
        if forced:
            self.serverIgnoringOnTheFly += 1
        if self.serverIgnoringOnTheFly or self.clientIgnoringOnTheFly:
            state["ignoringOnTheFly"] = {}
            if self.serverIgnoringOnTheFly:
                state["ignoringOnTheFly"]["server"] = self.serverIgnoringOnTheFly
            if self.clientIgnoringOnTheFly:
                state["ignoringOnTheFly"]["client"] = self.clientIgnoringOnTheFly
                self.clientIgnoringOnTheFly = 0
        if self.serverIgnoringOnTheFly == 0 or forced:
            self.sendMessage({"State": state})

    def _extractStatePlaystateArguments(self, state):
        position = state["playstate"].get("position", 0)
        paused = state["playstate"].get("paused")
        doSeek = state["playstate"].get("doSeek")
        return position, paused, doSeek

    @requireLogged
    def handleState(self, state) -> None:
        position, paused, doSeek, latencyCalculation = None, None, None, None
        if "ignoringOnTheFly" in state:
            ignore = state["ignoringOnTheFly"]
            if "server" in ignore:
                if self.serverIgnoringOnTheFly == ignore["server"]:
                    self.serverIgnoringOnTheFly = 0
            if "client" in ignore:
                self.clientIgnoringOnTheFly = ignore["client"]
        if "playstate" in state:
            position, paused, doSeek = self._extractStatePlaystateArguments(state)
        if "ping" in state:
            latencyCalculation = state["ping"].get("latencyCalculation", 0)
            clientRtt = state["ping"].get("clientRtt", 0)
            self._clientLatencyCalculation = state["ping"].get("clientLatencyCalculation", 0)
            self._clientLatencyCalculationArrivalTime = time.time()
            self._pingService.receiveMessage(latencyCalculation, clientRtt)
        if self.serverIgnoringOnTheFly == 0:
            self._watcher.updateState(position, paused, doSeek, self._pingService.getLastForwardDelay())

    def handleError(self, error) -> None:
        # TODO: more processing and fallbacking
        self.dropWithError(error["message"])

    def sendError(self, message) -> None:
        self.sendMessage({"Error": {"message": message}})

    def sendTLS(self, message) -> None:
        self.sendMessage({"TLS": message})

    def handleTLS(self, message) -> None:
        inquiry = message.get("startTLS")
        if "send" in inquiry:
            if not self.isLogged() and self._factory.serverAcceptsTLS:
                lastEditCertTime = self._factory.checkLastEditCertTime()
                if lastEditCertTime is not None and lastEditCertTime != self._factory.lastEditCertTime:
                    self._factory.updateTLSContextFactory()
                if self._factory.options is not None:
                    self.sendTLS({"startTLS": "true"})
                    asyncio.ensure_future(
                        self.upgradeTransportStartTLS()
                    )
                else:
                    self.sendTLS({"startTLS": "false"})
            else:
                self.sendTLS({"startTLS": "false"})

    async def upgradeTransportStartTLS(self) -> None:
        # There might be a slight issue with this since
        # there's no mutexes to prevent transport from being used
        # during the upgrade process
        ssl_context = self._factory.options
        self.transport.pause_reading()
        transport_ = await self._factory.loop.start_tls(
            self.transport,
            self,
            ssl_context,
            server_side=True
        )
        self.transport = transport_
        self.transport.resume_reading()


class PingService:
    _rtt: float
    _fd: float
    _avrRtt: float

    def __init__(self):
        self._rtt = 0.0
        self._fd = 0.0
        self._avrRtt = 0.0

    def newTimestamp(self) -> float:
        return time.time()

    def receiveMessage(self, timestamp: float, senderRtt: float) -> None:
        self._rtt = time.time() - timestamp
        if self._rtt < 0 or senderRtt < 0:
            return
        if not self._avrRtt:
            self._avrRtt = self._rtt
        self._avrRtt = self._avrRtt * PING_MOVING_AVERAGE_WEIGHT + self._rtt * (1 - PING_MOVING_AVERAGE_WEIGHT)
        if senderRtt < self._rtt:
            self._fd = self._avrRtt / 2 + (self._rtt - senderRtt)
        else:
            self._fd = self._avrRtt / 2

    def getLastForwardDelay(self) -> float:
        return self._fd

    @property
    def rtt(self) -> float:
        return self._rtt
