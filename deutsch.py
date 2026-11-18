# deutsch.py - German lyrics -> sung syllables (onset / nucleus / coda in IPA) for a singing synthesizer.
# Written for CHIMERA (https://github.com/jamesondh/chimera-vocal-synth, MIT), whose own front ends read Latin script as English, but the output
# is plain IPA per note and fits any synthesizer that sings syllables.
# Input: one word as the syllables a score writes under its notes ("Al", "le"); output: one syllable per piece:
#   {"onset": [{"ipa": "l"}], "nucleus": {"ipa": "ə", "stress": 0}, "coda": []}
#
# Reading rules (stage German, Siebs / Mangold): final devoicing; ich/ach sound (ich-sound after consonants: durch,
# Milch; ach-sound in ma-chen; k in Christ, Chor); -ig = [ɪç]; sp/st at the word start; s voiced before a vowel (not
# the second half of ss: Was-ser); glottal stop before a word-initial vowel; long = closed vowel when doubled,
# followed by h or ß, written ie, the syllable is open, or the word is in the small list below (Erde, erst, Mond,
# hoch, Buch ...); doubled consonant = short vowel (Gott, Herr, Bett); n-g and n-k across two notes = [ŋ] (sin-gen,
# dan-ken); silent h between vowels (ge-hen); unstressed e = schwa, always sung (Fa-den = [fadən], no swallowed e).
#
# Singing style: tuned for clear choir singing (a pure treble voice, little consonant noise), measured on CHIMERA
# renders at soprano pitch. Every value of GESANG below can be overridden (stil({...})); {"stil": "sprache"} gives a
# speech-like reading.
#   r_auslaut        r after a long vowel (mir, der, Ohr): 'gerollt' (stage German; the trill stays voiced in the
#                    model, a single tap [ɾ] breaks the voice for 26 ms) | 'stumm' (r dropped, as in speech)
#   er               unstressed -er: 'ɐ' (open, carries on high notes) | 'ər' (strict stage German)
#   vorsilbe_er      er- / ver- / zer-: 'ɛr' | 'ɐ'
#   doppel           Mut-ter, Al-le: 'einfach' = one consonant, sung with the next note (the vowel sings longer) | 'beide'
#   bindung          a last consonant goes to the next note of the word when that note starts with a vowel (sing-en)
#   ue_kurz          short ü (Glück): CHIMERA has no [ʏ]; 'ø' is its nearest vowel, 'y' the alternative
#   zisch_ms         length of the voiceless s ʃ ç x f (model: 110-120 ms; 70 = -2 dB noise, still clear); 0 = model's own
#   hauch_ms         length of h (model 90 ms)
#   affrikate_ms     length of ts pf tʃ (model 140-150 ms)
#   auslaut_behaucht p t k at the end of a syllable with a puff of air (True) or released softly (False = -5 dB noise)
#   zwielaut_ms      ei / au / eu on a long note: the first vowel is held, the glide comes this many ms before the
#                    note ends (the caller splits the note, see zwielaut_teile()); 0 = the synthesizer's own glide
#   zwielaut_ziel    'buehne' = [ae] [ao] [ɔø] (sung German) | 'sprache' = [aɪ] [aʊ] [ɔɪ]
# Wrong readings are fixed per word with `aussprache` = {word: IPA, one piece per note}, e.g. {"Mond": "moːnt"}.
#
# The first, speech-like version of this reader is deutsch_original.py next to this file.
#
# MIT License. Copyright (c) 2026 the german-singing-pronunciation authors. Permission is hereby granted, free of charge,
# to any person obtaining a copy of this software, to deal in it without restriction, including the rights to use,
# copy, modify, merge, publish, distribute, sublicense and/or sell copies, subject to keeping this notice. THE SOFTWARE
# IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
import re

GESANG = {'r_auslaut': 'gerollt', 'er': 'ɐ', 'vorsilbe_er': 'ɛr', 'doppel': 'einfach', 'bindung': True, 'ue_kurz': 'ø', 'zisch_ms': 70,
          'hauch_ms': 60, 'affrikate_ms': 100, 'auslaut_behaucht': False, 'zwielaut_ms': 130, 'zwielaut_ziel': 'buehne'}
SPRACHE = {'r_auslaut': 'stumm', 'er': 'ɐ', 'vorsilbe_er': 'ɐ', 'doppel': 'beide', 'bindung': False, 'ue_kurz': 'y', 'zisch_ms': 0,
           'hauch_ms': 0, 'affrikate_ms': 0, 'auslaut_behaucht': True, 'zwielaut_ms': 0, 'zwielaut_ziel': 'sprache'}


def stil(S=None):
    """the style settings: GESANG (or SPRACHE with {"stil": "sprache"}) with your own values on top"""
    S = S or {}
    return {**(SPRACHE if S.get('stil') == 'sprache' else GESANG), **{k: v for k, v in S.items() if k != 'stil' and not k.startswith('_')}}


VOK = 'aeiouäöüy'
LANG = {'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u', 'ä': 'ɛ', 'ö': 'ø', 'ü': 'y', 'y': 'y'}
KURZ = {'a': 'a', 'e': 'ɛ', 'i': 'ɪ', 'o': 'ɔ', 'u': 'ʊ', 'ä': 'ɛ', 'ö': 'œ', 'ü': 'y', 'y': 'y'}
DIPH = {'ei': 'aɪ', 'ai': 'aɪ', 'ey': 'aɪ', 'ay': 'aɪ', 'au': 'aʊ', 'eu': 'ɔɪ', 'äu': 'ɔɪ'}
ZWIELAUT = {'buehne': {'aɪ': ('a', 'e'), 'aʊ': ('a', 'o'), 'ɔɪ': ('ɔ', 'ø')}, 'sprache': {'aɪ': ('a', 'ɪ'), 'aʊ': ('a', 'ʊ'), 'ɔɪ': ('ɔ', 'ɪ')}}
# one-syllable words whose vowel stays short although only one consonant follows
KURZWORT = {'das', 'in', 'im', 'mit', 'an', 'am', 'um', 'es', 'ob', 'ab', 'hat', 'bis', 'man', 'von', 'vom', 'was', 'des',
            'ich', 'mich', 'dich', 'sich', 'doch', 'noch', 'ach', 'dann', 'wenn', 'denn', 'und', 'ist', 'nicht', 'bin', 'hin', 'zum',
            'zur', 'drum', 'un', 'bus', 'plus', 'stadt'}
# words whose stressed vowel is long although the syllable is closed (no rule tells them from Herz, Stern, Nacht):
# the stem alone or with one of the endings
LANG_STAMM = ('erd', 'erst', 'pferd', 'schwert', 'wert', 'werd', 'herd', 'hör', 'stör', 'schwör', 'spür', 'geburt', 'mond', 'trost', 'tröst',
              'klost', 'klöst', 'hust', 'wüst', 'düst', 'schust', 'nächst', 'höchst', 'rös', 'bart', 'zart', 'art', 'papst', 'obst',
              'stets', 'nebst', 'keks')
ENDUNG = {'', 'e', 'en', 'er', 'es', 'em', 's', 'st', 't', 'te', 'ten', 'et', 'est', 'ern', 'chen', 'lein', 'lich', 'ig', 'ung'}
LANG_GENAU = {'nach', 'hoch', 'buch', 'buchs', 'tuch', 'tuchs', 'fluch', 'such', 'sucht', 'suchst', 'sprach', 'sprachst', 'brach', 'stach',
              'ostern'}
# last pieces of longer words that are long words themselves (A-bend-rot, Sonn-tag, Hei-mat)
LANG_ENDSTUECK = {'rot', 'tag', 'weg', 'hof', 'tor', 'tal', 'mal', 'rat', 'tat', 'mut', 'gut', 'blut', 'not', 'tod', 'brot', 'los', 'sam',
                  'bar', 'tum', 'schön', 'grün', 'kühn', 'mat', 'zug', 'flug', 'lob', 'grab', 'stab', 'graf', 'schlaf', 'ruf', 'schwur', 'tür', 'her'}
VORSILBE = {'be', 'ge', 'ver', 'er', 'zer', 'ent', 'emp'}
STAMM_ANFANG = ('erde', 'ernte', 'erbe')                              # Er-den-rund: no prefix
NG_AUS = {'an', 'un', 'ein', 'hin', 'in', 'heran', 'hinein'}          # an-ge-nehm, un-klar: n and g / k stay apart
HER_VOR = {'da', 'wo', 'hin', 'vor', 'nach', 'bis', 'seit', 'hier', 'um', 'ein'}   # da-her: the h sounds
VOKAL_IPA = ['aɪ', 'aʊ', 'ɔɪ', 'a', 'e', 'i', 'o', 'u', 'y', 'ø', 'œ', 'ɛ', 'ɪ', 'ɔ', 'ʊ', 'ə', 'ɐ', 'æ', 'ɑ', 'ʌ', 'ɒ', 'ɨ', 'ɯ', 'ɤ', 'ɝ', 'ɚ']
KONS_IPA = ['tʃ', 'dʒ', 'ts', 'dz', 'pf', 'ʃ', 'ʒ', 'ç', 'x', 'ŋ', 'ʁ', 'ʔ', 'ɾ', 'r', 'p', 'b', 't', 'd', 'k', 'g', 'f', 'v', 's',
            'z', 'h', 'j', 'l', 'm', 'n', 'θ', 'ð', 'w', 'ɹ']


def _rein(t):
    return re.sub(r"[^a-zäöüß]", '', (t or '').lower())


def _doppelt(g):
    return len(g) == 2 and g[0] == g[1] and g != 'ss'


def _graph(s):
    """letters -> tokens ('V', letters) / ('C', letters); multi-letter spellings first; a doubled consonant stays
    one token ('C', 'tt') = one sound that marks the vowel before it as short"""
    out, i = [], 0
    while i < len(s):
        for g in ('tsch', 'sch', 'chs', 'ch', 'ck', 'pf', 'ph', 'qu', 'tz', 'ng', 'nk', 'th', 'dt', 'ss', 'ß'):
            if s.startswith(g, i):
                out.append(('C', g)); i += len(g); break
        else:
            c = s[i]
            if c in VOK:
                d = s[i:i + 2]
                if d in DIPH: out.append(('V', d)); i += 2; continue
                if d == 'ie': out.append(('V', 'ie')); i += 2; continue
                if len(d) == 2 and d[0] == d[1]: out.append(('V', d)); i += 2; continue
                out.append(('V', c)); i += 1
            elif c.isalpha():
                if s[i + 1:i + 2] == c: out.append(('C', c + c)); i += 2; continue
                out.append(('C', c)); i += 1
            else:
                i += 1
    return out


def _lang_wort(w):
    return w in LANG_GENAU or any(w.startswith(st) and w[len(st):] in ENDUNG for st in LANG_STAMM)


def _e_endung(s):
    """a piece that is only an unstressed ending: consonants + e + nothing / n r l m s nd ns rn ln (ten, de, gen, hen)"""
    return bool(re.fullmatch(r'[^aeiouäöüy]*e(n|r|l|m|s|nd|ns|rn|ln)?', s))


def silbe(text, wort, k, n, betont, wortende, naechste='', vorige='', S=None):
    """one Chimera syllable for piece k of n of a word (wort: the whole word, lower case; naechste / vorige: the
    neighbouring pieces, lower case; S: the style from stil())"""
    S = S or GESANG
    s = _rein(text)
    if not s:
        return None
    T = _graph(s)
    vi = next((j for j, t in enumerate(T) if t[0] == 'V'), None)
    if vi is None:                       # no vowel letter (a hum "mm", "hm"): sing it on a schwa
        return {'onset': [{'ipa': 'm'}], 'nucleus': {'ipa': 'ə', 'stress': 0}, 'coda': []}
    pre, v, post = T[:vi], T[vi][1], [t for t in T[vi + 1:]]
    # an h right after the vowel only lengthens it
    lang_h = bool(post) and post[0] == ('C', 'h')
    if lang_h: post = post[1:]
    post = [t for t in post if t[0] == 'C']          # a second vowel group in one piece is rare (typo); ignore it
    lang = lang_h or v == 'ie' or (len(v) == 2 and v[0] == v[1])
    einsilbig = n == 1
    kurz = dict(KURZ); kurz['ü'] = S['ue_kurz']
    vorsilbe_r = k == 0 and n > 1 and not betont and s in ('er', 'ver', 'zer')
    gs = [g for _, g in post]
    L = False                            # the vowel is long (decides the r after it in the 'stumm' style)
    if v in DIPH:
        nuc, L = DIPH[v], True
    elif v == 'ie':
        nuc, L = 'i', True
    else:
        b = v[0]
        if vorsilbe_r:
            nuc = 'ɛ' if S['vorsilbe_er'] == 'ɛr' else 'ɐ'
            if nuc == 'ɐ': post = []
        elif not betont and b == 'e' and not lang and s not in ('ent', 'emp') and not (einsilbig and wort not in KURZWORT and not post) and not (s == 'her' and k == 1 and vorige in HER_VOR):
            nuc = 'ə'
            if gs and gs[0] == 'r' and (len(gs) == 1 or ''.join(gs[1:]) in ('n', 't', 's', 'st', 'nd', 'nt', 'ns')) and S['er'] == 'ɐ':
                nuc, post = 'ɐ', post[1:]                            # -er, -ern, -ert: vocalised (Va-ter, Kin-dern)
        elif betont and not lang and (gs or naechste[:2] == 'st') and _lang_wort(wort):
            nuc, L = LANG[b], True       # Er-de, erst, Mond, hoch: long by the word list
        elif gs and gs[0] == 'ß':
            nuc, L = LANG[b], True       # Fuß, grüßt: ß follows long vowels (ss follows short ones)
        elif not post and (naechste[:2] in ('ck', 'tz') or (naechste[:2] == 'st' and not lang)):
            nuc = kurz[b]                # Glo-cken, Kat-ze, Chri-stus, Schwe-ster: ck / tz / st close the syllable (O-stern: word list)
        elif lang or not post:
            nuc, L = LANG[b], True
        elif len(gs) >= 2 and gs[0] in ('b', 'd', 'g') and ''.join(gs[1:]) in ('t', 'st', 's', 'te') and (einsilbig or betont):
            nuc, L = LANG[b], True       # sagt, lebt, gibt, Magd, Krebs: an ending does not shorten the stem
        elif (einsilbig or (betont and wortende and k > 0)) and len(post) == 1 and wort not in KURZWORT and not _doppelt(gs[0]) and gs[0] not in ('ng', 'nk', 'sch', 'ch', 'ck', 'tz', 'ss', 'pf', 'x'):
            nuc, L = LANG[b], True       # Tag, gut, Weg, Ge-bet: a stem of one syllable with one consonant is mostly long
        elif wortende and n > 1 and s in LANG_ENDSTUECK:
            nuc, L = LANG[b], True       # A-bend-rot, Sonn-tag
        else:
            nuc = kurz[b]
    back = nuc in ('a', 'o', 'ɔ', 'u', 'ʊ', 'aʊ')
    # onset
    on = []
    for j, (_, g) in enumerate(pre):
        nxt = pre[j + 1][1] if j + 1 < len(pre) else None
        if _doppelt(g): g = g[0]
        if g == 's' and k == 0 and nxt in ('p', 't'): on.append('ʃ'); continue
        if g == 's' and nxt is None and j == 0:                       # s before the vowel: voiced, but Was-ser, Stra-ße
            on.append('s' if vorige[-1:] in ('s', 'ß') else 'z'); continue
        if g == 'ch':
            if k == 0: on.append('k' if nxt in ('r', 'l') or (nxt is None and v[0] in 'aou') else 'ç')   # Christ, Chor | Chi-na
            else: on.append('x' if j == 0 and vorige[-1:] in ('a', 'o', 'u') else 'ç')                    # ma-chen | Mäd-chen
            continue
        if g == 'h' and k > 0 and len(pre) == 1 and vorige[-1:] in VOK + 'h' and _e_endung(s) and not (k == 1 and vorige in HER_VOR):
            continue                                                  # ge-hen, Ru-he, frü-her: the h is silent
        on += {'sch': ['ʃ'], 'tsch': ['tʃ'], 'chs': ['k', 's'], 'ck': ['k'], 'ph': ['f'], 'qu': ['k', 'v'], 'tz': ['ts'],
               'z': ['ts'], 'v': ['f'], 'w': ['v'], 'th': ['t'], 'dt': ['t'], 'ß': ['s'], 'ss': ['s'], 'x': ['k', 's'], 'c': ['k'],
               'j': ['j'], 'r': ['r'], 's': ['s'], 'ng': ['ŋ'], 'nk': ['ŋ', 'k']}.get(g, [g])
    if not on and k == 0:
        on = ['ʔ']
    # coda (final devoicing everywhere in the coda)
    co = []
    for j, (_, g) in enumerate(post):
        letzter = j == len(post) - 1
        if _doppelt(g): g = g[0]
        if g == 'r':
            if L and S['r_auslaut'] == 'stumm': continue              # speech style: mir = [mi]
            co.append('r'); continue
        if g == 'ch': co.append('x' if back and j == 0 else 'ç'); continue                 # ach | ich, durch, Milch
        if g == 'g' and letzter and nuc == 'ɪ' and (wortende or naechste == 'keit'): co.append('ç'); continue   # -ig, E-wig-keit
        if g == 'n' and letzter and naechste[:1] in ('k', 'q') and not (k == 0 and s in NG_AUS): co.append('ŋ'); continue   # dan-ken
        co += {'sch': ['ʃ'], 'tsch': ['tʃ'], 'chs': ['k', 's'], 'ck': ['k'], 'ph': ['f'], 'qu': ['k', 'v'], 'tz': ['ts'], 'z': ['ts'],
               'v': ['f'], 'w': ['f'], 'b': ['p'], 'd': ['t'], 'g': ['k'], 'th': ['t'], 'dt': ['t'], 'ß': ['s'], 'ss': ['s'],
               'x': ['k', 's'], 'c': ['k'], 'ng': ['ŋ'], 'nk': ['ŋ', 'k'], 'h': [], 'j': []}.get(g, [g])
    return {'onset': [{'ipa': x} for x in on], 'nucleus': {'ipa': nuc, 'stress': 1 if betont else 0}, 'coda': [{'ipa': x} for x in co]}


def ipa_silbe(p):
    """one syllable from hand-written IPA ("moːnt", "ˈʔɛnt"): onset / nucleus / coda"""
    st = 1 if 'ˈ' in p else 0
    p = p.replace('ː', '').replace('ˈ', '').replace('ˌ', '').replace('.', '')
    tok, i = [], 0
    while i < len(p):
        for sym in sorted(VOKAL_IPA + KONS_IPA, key=len, reverse=True):
            if p.startswith(sym, i): tok.append(sym); i += len(sym); break
        else:
            i += 1
    vi = next((j for j, t in enumerate(tok) if t in VOKAL_IPA), None)
    if vi is None: raise ValueError(f'kein Vokal in {p!r}')
    return {'onset': [{'ipa': x} for x in tok[:vi]], 'nucleus': {'ipa': tok[vi], 'stress': st}, 'coda': [{'ipa': x} for x in tok[vi + 1:]]}


def _feinschliff(out, S):
    """the singing style on the finished syllables of a word: one consonant for a doubled one, consonants carried to
    the next note, shorter hiss, soft final stops"""
    for a, b in zip(out, out[1:]):
        if a is None or b is None: continue
        if S['doppel'] == 'einfach' and a['coda'] and b['onset'] and a['coda'][-1]['ipa'] == b['onset'][0]['ipa']:
            a['coda'] = a['coda'][:-1]                                # Mut-ter: [mʊ tɐ]
        if S['bindung'] and a['coda'] and not b['onset']:
            b['onset'] = [a['coda'][-1]]; a['coda'] = a['coda'][:-1]   # sing-en: [zɪ ŋən]
    for o in out:
        if o is None: continue
        for teil in ('onset', 'coda'):
            for seg in o[teil]:
                i = seg['ipa']
                if i in ('s', 'ʃ', 'ç', 'x', 'f') and S['zisch_ms']: seg['dur'] = S['zisch_ms'] / 1000
                elif i == 'h' and S['hauch_ms']: seg['dur'] = S['hauch_ms'] / 1000
                elif i in ('ts', 'pf', 'tʃ') and S['affrikate_ms']: seg['dur'] = S['affrikate_ms'] / 1000
                elif i in ('p', 't', 'k') and teil == 'coda' and not S['auslaut_behaucht']: seg['aspirated'] = False
    return out


def wort(stuecke, aussprache=None, S=None):
    """the syllables of one word: stuecke = the pieces under its notes; aussprache = {word: 'ipa.ipa'} overrides;
    S = the style from stil() (None: GESANG)"""
    S = S or GESANG
    key = _rein(''.join(stuecke))
    for k_, v_ in (aussprache or {}).items():
        if _rein(k_) == key:
            teile = [t for t in re.split(r'[.\s-]+', v_) if t]
            if len(teile) == len(stuecke):
                out = [ipa_silbe(t) for t in teile]
                if not any(o['nucleus']['stress'] for o in out): out[0]['nucleus']['stress'] = 1
                return _feinschliff(out, dict(S, doppel='beide', bindung=False))    # a hand-written reading stays as written
    n = len(stuecke)
    st = [_rein(t) for t in stuecke]
    # sin-gen, En-gel, lan-ge: n + g across two notes is one [ŋ] (not an-ge-nehm); read as "sing" + "en"
    for k in range(n - 1):
        if st[k].endswith('n') and st[k + 1].startswith('g') and _e_endung(st[k + 1]) and not (k == 0 and st[0] in NG_AUS and k + 2 < n):
            st[k] += 'g'; st[k + 1] = st[k + 1][1:]
    # the stress: on the first piece; after an unstressed prefix on the second (ge-bo-ren, er-wacht, ge-ge-ben) - but
    # be-ten, ge-ben, Er-de, be-ten-de are stems (the second piece is only an ending), and Ent-chen has no prefix
    beton = 0
    if n > 1 and st[0] in VORSILBE and not (n == 2 and st[-1] in ('chen', 'lein')) and not key.startswith(STAMM_ANFANG):
        if not (_e_endung(st[1]) and (n == 2 or st[2][:1] in ('d', 't') or st[2] in ('chen', 'lein'))): beton = 1
    out = [silbe(t, key, k, n, k == beton, k == n - 1, st[k + 1] if k + 1 < n else '', st[k - 1] if k else '', S) for k, t in enumerate(st)]
    return _feinschliff(out, S)


def zwielaut_teile(ipa, S=None):
    """the two vowels of a diphthong for a long sung note (None: no diphthong, or the style leaves it to Chimera)"""
    S = S or GESANG
    return ZWIELAUT.get(S['zwielaut_ziel'], ZWIELAUT['buehne']).get(ipa) if S['zwielaut_ms'] else None


def lesbar(r):
    """/onset ˈnucleus coda/ per syllable, for checking a reading by eye"""
    return ' '.join('/' + ''.join(x['ipa'] for x in s['onset']) + ('ˈ' if s['nucleus']['stress'] else '') + s['nucleus']['ipa']
                    + ''.join(x['ipa'] for x in s['coda']) + '/' for s in r if s)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    a = sys.argv[1:]
    S = stil({'stil': 'sprache'}) if '--sprache' in a else GESANG
    for w in [x for x in a if not x.startswith('--')]:
        print(w, lesbar(wort(w.split('-'), None, S)))
