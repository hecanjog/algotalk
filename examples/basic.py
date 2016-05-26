from pippi import dsp, tune
from hcj import keys, data, Tracks, snds, curves

midi = {'mpk': 'MPKmini2 MIDI 1'}
trigger = {
    'device': 'MPKmini2 MIDI 1',
    'notes': range(127)
}

def makeOnsets(length, log, wobble, div, num_beats, offset=False):
    if offset:
        offset = dsp.randint(0, 3)
    else:
        offset = 0

    pattern = dsp.eu(num_beats, dsp.randint(1, num_beats/div), offset)
    dsp.log(pattern)

    if wobble:
        points = [ dsp.mstf(100, 500) for _ in range(dsp.randint(2, 8)) ]
        plength = sum(points)
        mult = length / float(plength)
        onsets = curves.bezier(points, num_beats)
        onsets = [ int(o * mult) for o in onsets ]

    else:
        beat = float(length) / num_beats
        num_beats = length / beat
        beat = int(round(beat))
        onsets = [ beat for _ in range(int(round(num_beats))) ]

    return onsets

def makeKicks(length, log, wobble):
    out = Tracks()
    onsets = makeOnsets(length, log, wobble, 2, 4)

    k = log.choose(snds.search('mc303/*kick*'))

    for onset in onsets:
        out.add(k, onset)

    out = out.mix()

    return (dsp.fill(out, length, silence=False), log)

def makeHats(length, log, wobble):
    out = Tracks()
    onsets = makeOnsets(length, log, wobble, 1, 16)

    h = log.choose(snds.search('mc303/*hat*'))

    for onset in onsets:
        out.add(h, onset)

    out = out.mix()

    return (dsp.fill(out, length, silence=False), log)

def makeClaps(length, log, wobble):
    out = Tracks()
    onsets = makeOnsets(length, log, wobble, 2, 8, True)

    c = log.choose(snds.search('mc303/*clap*'))

    for onset in onsets:
        out.add(c, onset)

    out = out.mix()

    dsp.log(length)
    dsp.log(sum(onsets))

    return (dsp.fill(out, length, silence=False), log)

def play(ctl):
    p = ctl.get('param')
    key = p.get('key', 'c')
    mpk = ctl.get('midi').get('mpk')
    bpm = p.get('bpm', 100)
    beat = dsp.bpm2frames(bpm)
    length = beat * 8

    gamut = mpk.geti(20)
    poly = mpk.geti(21)
    logistic = mpk.geti(22)
    layered = mpk.geti(23)
    fixed = mpk.get(24)
    perc = mpk.get(25)
    wobble = mpk.get(26)

    if fixed:
        seed = mpk.get(5)
        dsp.seed(str(seed))

    if mpk.get(8) == 0:
        return dsp.pad('', 0, dsp.mstf(100))

    pointer = p.get('pointer', default=0)
    log = data.Logistic(r=dsp.rand(3.9, 3.99), x=0.5, size=1024, pointer=pointer)

    def randomScale():
        octave = dsp.randint(3, 6)
        scale = [1,2,3,4,5,6,7,8]
        freqs = tune.fromdegrees(scale, octave=octave, root=key)
        return freqs

    def gamutScale():
        octave = dsp.randint(3, 6)
        num_notes = dsp.randint(3, 6)
        scale = [ dsp.randchoose([1,2,3,4,5,6,7,8]) for _ in range(num_notes) ]
        freqs = tune.fromdegrees(scale, octave=octave, root=key)
        return freqs

    if gamut:
        freqs = gamutScale()
    else:
        freqs = randomScale()

    if layered:
        num_layers = dsp.randint(2, 4)
    else:
        num_layers = 1

    layers = []

    for _ in range(num_layers):
        layer = ''

        elapsed = 0
        while elapsed < length:
            if poly:
                num_poly = dsp.randint(1, 3)
            else:
                num_poly = 1

            note_length = beat / dsp.randchoose([1, 2, 3, 4])

            notes = []
            for _ in range(num_poly):
                freq = dsp.randchoose(freqs)

                if logistic:
                    pulsewidth = log.get(low=0.05, high=1)

                    if log.get() > 0.5:
                        wf = log.choose(['sine', 'tri', 'saw'])
                        wf = dsp.wavetable(wf, 512)
                    else:
                        points = [ log.get(-1, 1) for _ in range(log.geti(4, 20)) ]
                        wf = dsp.breakpoint(points, 512)
                else:
                    pulsewidth = 1
                    wf = dsp.wavetable('sine', 512)

                note = keys.pulsar(length=note_length, freq=freq, wf=wf, env='phasor', pulsewidth=pulsewidth)
                notes += [ note ]
            
            notes = dsp.mix(notes)
            layer += notes

            elapsed += dsp.flen(notes)

        layers += [ layer ]

    out = dsp.mix(layers)
    out = dsp.fill(out, length)
    out = dsp.pad(out, 0, int(dsp.stf(0.5, 1) * mpk.get(7)))

    p.set('pointer', log.pointer)

    out = dsp.amp(out, mpk.get(8))

    if perc:
        kicks, log = makeKicks(dsp.flen(out), log, wobble)
        hats, log = makeHats(dsp.flen(out), log, wobble)
        claps, log = makeClaps(dsp.flen(out), log, wobble)
        out = dsp.mix([ out, kicks, hats, claps ])

    return out
