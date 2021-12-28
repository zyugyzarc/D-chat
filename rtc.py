import asyncio
import os, sys

from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import BYE, CopyAndPasteSignaling, ApprtcSignaling
from blessed import Terminal

term = Terminal()

def rands(x):
    from random import choice
    return ''.join([choice("1234567890QWERTYUIOPLKJHGFDSAZXCVBNMqwertyuioplkmjnhbgvfcdxsza") for i in range(x)])

def copy(x):
    if sys.platform.startswith("linux"):
        with open('.temp', 'w') as f:
            f.write(x)
        os.system("xclip -sel clip .temp")
        os.remove('.temp')

def log(*a, **k):
    return
    print(*a, **k, flush=True)

def task(coro):
    asyncio.get_event_loop().create_task(coro)
    log("[async] created task", coro)

class Obj(dict):
    def __init__(self, a=None, **kwargs):
        if type(a) == str:
            self.update(**eval(
                'dict('+a.strip('obj{').strip('}')+')'
            ))
        else:
            super().__init__(**kwargs)

    def __str__(self):
        return 'obj{'+', '.join([k+'='+repr(v) for k, v in self.items()]) +'}'
    __repr__ = __str__

    def __getattr__(self, a):
        try:             return self[a]
        except KeyError: return None

    def __iter__(self):          return iter(self.values())
    def __setattr__(self, a, v): self[a] = v

import asyncio
from aiortc.contrib.signaling import object_from_string, object_to_string
import aiohttp
import random

class QSig:
    def __init__(self, server=""):
        self.server = server
        self.id = ''.join([random.choice("1234567890qwertyuiop") for i in range(32)])
        print("clientid: ", self.id)

    async def connect(self):
        pass

    async def receive(self):

        async with aiohttp.ClientSession(headers=dict(id=self.id)) as session:
            while True:
                async with session.get(self.server) as r:
                    if r.status == 200:
                        return object_from_string( await r.text() )
                    await asyncio.sleep(0.5)

    async def send(self, descr):

        async with aiohttp.ClientSession(headers=dict(id=self.id)) as session:
            await session.post(self.server, data = object_to_string(descr))

    async def close(self):
        pass

        
import asyncio
from aiortc.contrib.signaling import object_from_string, object_to_string
import aiohttp
import random

class HTTPSignal:
    def __init__(self, server=""):
        self.server = server
        self.id = ''.join([random.choice("1234567890qwertyuiop") for i in range(32)])
        print("clientid: ", self.id)

    async def connect(self):
        pass

    async def receive(self):
        
        async with aiohttp.ClientSession(headers=dict(id=self.id)) as session:
            while True:
                async with session.get(self.server) as r:
                    if r.status == 200:
                        return object_from_string( await r.text() )
                    await asyncio.sleep(0.5)

    async def send(self, descr):

        async with aiohttp.ClientSession(headers=dict(id=self.id)) as session:
            await session.post(self.server, data = object_to_string(descr))

        
class Channel:
    def __init__(self, node, label,signal, offer = False):
        self.sig = signal
        self.pc  = RTCPeerConnection()
        self._channel = None
        self.offer = offer
        self.connected = False
        self.node = node
        self.label = label

    async def sig_connect(self):

        #run signaling loop
        while True:
            obj = await self.sig.receive()

            if isinstance(obj, RTCSessionDescription):
                await self.pc.setRemoteDescription(obj)

                if obj.type == "offer":
                    await self.pc.setLocalDescription(await self.pc.createAnswer())
                    await self.sig.send(self.pc.localDescription)
            elif isinstance(obj, RTCIceCandidate):
                await self.pc.addIceCandidate(obj)
            elif obj is BYE:
                print(f"Channel {self.label} closed", flush=True)
                self.node.remove_channel(self.label)

    async def connect(self):

        await self.sig.connect() 

        if self.offer:
            
            self._channel = self.pc.createDataChannel("rtc-channel")
            
            @self._channel.on("message")
            def on_message(message):
                self.node.on_msg( Obj(message), self.label)

            @self._channel.on("open")
            def on_open():
                self.connected = True


            await self.pc.setLocalDescription(
                await self.pc.createOffer()
            )
            await self.sig.send(self.pc.localDescription)

        else:
    
            @self.pc.on("datachannel")
            def on_datachannel(channel):

                self._channel = channel

                @self._channel.on("message")
                def on_message(message):
                    self.node.on_msg( Obj(message) , self.label) 

                self.connected = True
                

        loop = asyncio.get_event_loop()
        loop.create_task( self.sig_connect() )

        while not self.connected:
            log(' waiting for connection...\r',end='')
            await asyncio.sleep(0.05)
        log("connected                ")

    def send(self, message):
        if self.connected:
            self.node.cache.append( message.id )
            self._channel.send( str(message) )
            log(f"[channel>>] {self.label}: {message}")
        else:
            raise RuntimeError(f"Channel {self.label} not connected")

    async def flush(self):
        await self._channel._RTCDataChannel__transport._data_channel_flush()
        await self._channel._RTCDataChannel__transport._transmit()


    async def close(self):
        await self.sig.close()
        await self.pc.close()

class Node:
    def __init__(self, username):
        self.channels = Obj()
        self.cache = []
        self.username = username
        self.buffer = ''

    def add_channel(self, label, offer=True, id=None):

        c = Channel(
            self,
            label,
            HTTPSignal( os.environ.get("RTC_SERVER") or "https://rtc.zyugyzarc.repl.co" ),
            offer=offer
        )
        self.channels[label] = c
        return c, id

    def on_msg(self, data, label):


        log(f"[channel<<] {label}: {data}")

        if data.id in self.cache:
            log("^ message already in cache")
            return

        self.cache.append(data.id)

        ev = self.__getattribute__("on_"+data.type)
        task( ev(data, label) )

    async def run(self):

        offer = len(sys.argv) == 3

        c, id = self.add_channel(
                'temp', 
                offer = offer
            )

        await c.connect()

        if not offer:

            await asyncio.sleep(1)
            c.send(
                Obj(
                        type='user_join',
                        username=self.username,
                        id= rands(64),
                        reply=True
                    )
            )
            await c.flush()

        task( self.loop() )
        while True:
            await asyncio.sleep(1)

    async def on_user_join(self, data, label):
        
        self.channels[data.username] = self.channels.pop(label)
        
        if data.reply:
            self.channels[data.username].send( Obj(
                    type='user_join',
                    username=self.username,
                    id= rands(64),
                    reply = False
                )
            )
            data = Obj(
                type='message_raw',
                sender=self.username,
                message=
                    f"\t{term.bold}{term.cyan}{self.username}{term.normal}{term.bold} added {term.bold}{term.cyan}{data.username}{term.normal}{term.bold} to the chat{term.normal}",
                id=rands(64)
            )
            await self.on_message(data, label)

    async def on_user_leave(self, data, label):

        await asyncio.sleep(0.1)
        c = self.channels.pop(data.username)
        await c.close()

    async def on_connect_request(self, data, label):

        if data.to in self.channels.keys():
            self.channels[data.to].send(data)
        else:
            for i in self.channels:
                i.send(data)

    async def on_message(self, data, label):

        for i in self.channels:
            if i.label != data.sender:
                i.send( data )
                await i.flush()

        await self.out(
                '\r['+
                term.cyan+
                data.sender+
                term.normal+'] '+
                data.message
            )

    async def on_message_raw(self, data, label):

        for i in self.channels:
            if i.label != data.sender:
                i.send( data )
                await i.flush()

        await self.out(
                data.message
            )

    async def loop(self):
        
        self.buffer = ''

        while True:
            with term.cbreak():
                s = term.inkey(timeout=0.05)
            if s:
                if not s.is_sequence:
                    self.buffer += s
                    print("\r>> "+self.buffer, end='')
                else:
                    if s.name == 'KEY_BACKSPACE':
                        self.buffer = self.buffer[:-1]
                        print('\r>> '+self.buffer+" ", end='')

                    elif "ENTER" in s.name:

                        if self.buffer.startswith('/'):
                            res, raw = await self.cmd(self.buffer)
                            if res:
                                data = Obj(
                                    type=('message_raw' if raw else "message"),
                                    sender=self.username,
                                    message=res,
                                    id=rands(64)
                                )
                                for i in self.channels:
                                    if i.label != 'temp':
                                        i.send( data )
                                        await i.flush()

                                self.buffer = ''

                                await self.out(
                                    '['+term.cyan+
                                    data.sender+
                                    term.normal+'] '+
                                    data.message
                                )
                        else:
                            data = Obj(
                                type='message',
                                sender=self.username,
                                message=self.buffer,
                                id=rands(64)
                            )
                            for i in self.channels:
                                i.send( data )
                                await i.flush()

                            self.buffer = ''

                            await self.out(
                                '['+term.cyan+
                                data.sender+
                                term.normal+'] '+
                                data.message
                            )

                await asyncio.sleep(0.05)
            await asyncio.sleep(0.05)

    async def cmd(self, command):
        
        if command == '/invite':
        
            c, id = self.add_channel(
                'temp', 
                offer = True,
            )
            task( c.connect() )
            print(f"{term.bold} waiting for connection... {term.normal}")

        elif command == '/leave':
            for i in self.channels:
                i.send( Obj(
                    type='user_leave',
                    username=self.username,
                    id= rands(64)
                ) )
            
            async def kill():
                await asyncio.sleep(1)
                sys.exit()
            task(kill())
            return f"{term.bold}{self.username} left the chat {term.normal}", True

    async def out(self, o):
        print('\r' + str(o) +'\n\r>> ' + self.buffer, end='')


async def __main__():

    n = Node(sys.argv[1])
    await n.run()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(__main__())
