"""Listen to every MIDI source on this Mac for N seconds and print what
arrives (CoreMIDI through ctypes; nothing to install).

usage: python3 midimon.py [seconds]
"""
import ctypes
import ctypes.util
import sys
import time

cm = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreMIDI"))
cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
cf.CFStringCreateWithCString.restype = ctypes.c_void_p
cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
UTF8 = 0x08000100


def cfstr(s):
    return cf.CFStringCreateWithCString(None, s.encode(), UTF8)


cm.MIDIGetNumberOfSources.restype = ctypes.c_ulong
cm.MIDIGetSource.restype = ctypes.c_uint32
cm.MIDIGetSource.argtypes = [ctypes.c_ulong]
cm.MIDIObjectGetStringProperty.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
kName = ctypes.c_void_p.in_dll(cm, "kMIDIPropertyDisplayName")


def name_of(ep):
    s = ctypes.c_void_p()
    cm.MIDIObjectGetStringProperty(ep, kName, ctypes.byref(s))
    buf = ctypes.create_string_buffer(256)
    cf.CFStringGetCString(s, buf, 256, UTF8)
    return buf.value.decode()


class MIDIPacket(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("timeStamp", ctypes.c_uint64), ("length", ctypes.c_uint16), ("data", ctypes.c_ubyte * 256)]


class MIDIPacketList(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("numPackets", ctypes.c_uint32), ("packet", MIDIPacket * 1)]


READPROC = ctypes.CFUNCTYPE(None, ctypes.POINTER(MIDIPacketList), ctypes.c_void_p, ctypes.c_void_p)
srcnames = {}
t0 = time.time()


@READPROC
def on_midi(pktlist, refcon, srcref):
    pl = pktlist.contents
    p = ctypes.addressof(pl.packet)
    for _ in range(pl.numPackets):
        pk = MIDIPacket.from_address(p)
        data = bytes(pk.data[:pk.length])
        src = srcnames.get(srcref or 0, "?")
        i = 0
        while i < len(data):
            st = data[i]
            kind = st & 0xF0
            n = 3 if kind in (0x80, 0x90, 0xA0, 0xB0, 0xE0) else 2 if kind in (0xC0, 0xD0) else 1
            msg = data[i:i + n]
            if kind == 0xB0:
                print(f"{time.time() - t0:6.2f}s  [{src}]  CC {msg[1]} = {msg[2]}  (ch {(st & 15) + 1})", flush=True)
            elif kind in (0x80, 0x90):
                print(f"{time.time() - t0:6.2f}s  [{src}]  note {'on ' if kind == 0x90 else 'off'} {msg[1]} vel {msg[2]}", flush=True)
            i += n
        p += 10 + pk.length                                # timeStamp(8) + length(2) + data


cm.MIDIClientCreate.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
cm.MIDIInputPortCreate.argtypes = [ctypes.c_uint32, ctypes.c_void_p, READPROC, ctypes.c_void_p,
                                   ctypes.POINTER(ctypes.c_uint32)]
cm.MIDIPortConnectSource.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
client = ctypes.c_uint32()
port = ctypes.c_uint32()
cm.MIDIClientCreate(cfstr("cello-midimon"), None, None, ctypes.byref(client))
cm.MIDIInputPortCreate(client, cfstr("in"), on_midi, None, ctypes.byref(port))
for i in range(cm.MIDIGetNumberOfSources()):
    ep = cm.MIDIGetSource(i)
    nm = name_of(ep)
    srcnames[i + 1] = nm
    cm.MIDIPortConnectSource(port, ep, ctypes.c_void_p(i + 1))
print("listening to:", list(srcnames.values()), flush=True)
time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 10)
