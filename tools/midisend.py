"""Send one CC to a MIDI destination by name (CoreMIDI via ctypes).
usage: python3 midisend.py "IAC Driver Bus 1" <cc> <value> [channel]"""
import ctypes, ctypes.util, sys
cm = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreMIDI"))
cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
cf.CFStringCreateWithCString.restype = ctypes.c_void_p
cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
U = 0x08000100
cfs = lambda s: cf.CFStringCreateWithCString(None, s.encode(), U)
cm.MIDIGetNumberOfDestinations.restype = ctypes.c_ulong
cm.MIDIGetDestination.restype = ctypes.c_uint32
cm.MIDIGetDestination.argtypes = [ctypes.c_ulong]
cm.MIDIObjectGetStringProperty.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
kName = ctypes.c_void_p.in_dll(cm, "kMIDIPropertyDisplayName")
def name(ep):
    s = ctypes.c_void_p(); cm.MIDIObjectGetStringProperty(ep, kName, ctypes.byref(s))
    b = ctypes.create_string_buffer(256); cf.CFStringGetCString(s, b, 256, U); return b.value.decode()
want, cc, val = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); ch = int(sys.argv[4]) if len(sys.argv) > 4 else 1
dest = next(cm.MIDIGetDestination(i) for i in range(cm.MIDIGetNumberOfDestinations()) if name(cm.MIDIGetDestination(i)) == want)
cm.MIDIClientCreate.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
cm.MIDIOutputPortCreate.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
client, port = ctypes.c_uint32(), ctypes.c_uint32()
cm.MIDIClientCreate(cfs("cello-midisend"), None, None, ctypes.byref(client))
cm.MIDIOutputPortCreate(client, cfs("out"), ctypes.byref(port))
buf = (ctypes.c_ubyte * 1024)()
cm.MIDIPacketListInit.restype = ctypes.c_void_p; cm.MIDIPacketListInit.argtypes = [ctypes.c_void_p]
cm.MIDIPacketListAdd.restype = ctypes.c_void_p
cm.MIDIPacketListAdd.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ubyte)]
pkt = cm.MIDIPacketListInit(buf)
data = (ctypes.c_ubyte * 3)(0xB0 | (ch - 1), cc, val)
cm.MIDIPacketListAdd(buf, 1024, pkt, 0, 3, data)
cm.MIDISend.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
print("MIDISend:", cm.MIDISend(port, dest, buf), "->", want, f"CC {cc} = {val} ch {ch}")
