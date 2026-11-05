import av
p = r"D:\Desktop\AI 辅助对话\test.mp4"
c = av.open(p)
v = c.streams.video[0]
dur = float(v.duration * v.time_base) if v.duration else 0
print("codec:", v.codec_context.name)
print("size: %dx%d" % (v.codec_context.width, v.codec_context.height))
print("fps:", v.average_rate)
print("duration: %.1f s" % dur)
print("frames:", v.frames)
print("bitrate: %.2f Mbps" % ((v.bit_rate or 0) / 1e6))
print("audio:", [s.codec_context.name for s in c.streams.audio])
