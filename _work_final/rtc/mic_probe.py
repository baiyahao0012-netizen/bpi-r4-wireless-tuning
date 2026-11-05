import sounddevice as sd
try:
    devs = sd.query_devices()
    ins = [(i, d['name'], d['max_input_channels']) for i, d in enumerate(devs) if d['max_input_channels'] > 0]
    print("input devices:", len(ins))
    for i, n, c in ins[:5]:
        print(" ", i, n, c)
    print("default input:", sd.default.device)
except Exception as e:
    print("ERR", e)
