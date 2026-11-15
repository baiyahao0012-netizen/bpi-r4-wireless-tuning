import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject
Gst.init(None)

for name in GObject.signal_list_names(Gst.Element):
    if "key" in name.lower() or "pli" in name.lower() or "fir" in name.lower():
        print("Element signal:", name)

el = Gst.ElementFactory.make("rtpsession", "x")
print("rtpsession signals:")
for sig in GObject.signal_list_names(type(el)):
    print(" -", sig)
print("actions:")
for prop in ("request-pt-map",):
    print(prop)
