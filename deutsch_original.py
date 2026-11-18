# deutsch_original.py - the FIRST version: German lyrics -> sung syllables (onset / nucleus / coda in IPA) for the
# singing synthesizer CHIMERA (https://github.com/jamesondh/chimera-vocal-synth, MIT), whose own front ends read Latin
# script as English. The improved, singing-optimised version is deutsch.py next to this file.
# Input: one word as the syllables a score writes under its notes ("Al", "le"); output: one syllable per piece.
# Rules (stage German, choir style): rolled r in front of vowels and after short vowels, r after long vowels and in
# unstressed -er vocalised; final devoicing; ich/ach sound; sp/st at the word start; glottal stop before a word-initial
# vowel; long vowel when doubled, followed by h, written ie, or the syllable is open; unstressed e -> schwa.
# Wrong readings are fixed per word with `aussprache` = {word: IPA, one piece per note}, e.g. {"Mond": "moːnt"}.
#
# MIT License. Copyright (c) 2026 the deutsch-gesang-aussprache authors. Permission is hereby granted, free of charge,
# to any person obtaining a copy of this software, to deal in it without restriction, including the rights to use,
# copy, modify, merge, publish, distribute, sublicense and/or sell copies, subject to keeping this notice. THE SOFTWARE
# IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
import re

VOK = 'aeiouäöüy'
LANG = {'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u', 'ä': 'ɛ', 'ö': 'ø', 'ü': 'y', 'y': 'y'}
KURZ = {'a': 'a', 'e': 'ɛ', 'i': 'ɪ', 'o': 'ɔ', 'u': 'ʊ', 'ä': 'ɛ', 'ö': 'œ', 'ü': 'y', 'y': 'y'}
DIPH = {'ei': 'aɪ', 'ai': 'aɪ', 'ey': 'aɪ', 'ay': 'aɪ', 'au': 'aʊ', 'eu': 'ɔɪ', 'äu': 'ɔɪ'}
# one-syllable words whose vowel stays short although only one consonant follows
KURZWORT = {'das', 'in', 'im', 'mit', 'an', 'am', 'um', 'es', 'ob', 'ab', 'hat', 'bis', 'man', 'von', 'vom', 'was', 'des',
            'ich', 'mich', 'dich', 'sich', 'doch', 'noch', 'ach', 'dann', 'wenn', 'denn', 'und', 'ist', 'nicht', 'bin', 'hin', 'zum'}
VORSILBE = {'be', 'ge', 'ver', 'er', 'zer', 'ent', 'emp'}
VOKAL_IPA = ['aɪ', 'aʊ', 'ɔɪ', 'a', 'e', 'i', 'o', 'u', 'y', 'ø', 'œ', 'ɛ', 'ɪ', 'ɔ', 'ʊ', 'ə', 'ɐ', 'æ', 'ɑ', 'ʌ', 'ɒ', 'ɨ', 'ɯ', 'ɤ', 'ɝ', 'ɚ']
KONS_IPA = ['tʃ', 'dʒ', 'ts', 'dz', 'pf', 'ʃ', 'ʒ', 'ç', 'x', 'ŋ', 'ʁ', 'ʔ', 'ɾ', 'r', 'p', 'b', 't', 'd', 'k', 'g', 'f', 'v', 's',
            'z', 'h', 'j', 'l', 'm', 'n', 'θ', 'ð', 'w', 'ɹ']


def _graph(s):
    """letters -> tokens ('V', letters) / ('C', letters); multi-letter spellings first"""
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
                if out and out[-1] == ('C', c): i += 1; continue      # doubled consonant: one sound
                out.append(('C', c)); i += 1
            else:
                i += 1
    return out


def silbe(text, wort, k, n, betont, wortende, naechste=''):
    """one Chimera syllable for piece k of n of a word (wort: the whole word, lower case)"""
    s = re.sub(r"[^a-zäöüß]", '', text.lower())
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
    # vowel
    if v in DIPH:
        nuc = DIPH[v]
    elif v == 'ie':
        nuc = 'i'
    else:
        b = v[0]
        if not betont and b == 'e' and not lang and s not in ('ent', 'emp') and not (einsilbig and wort not in KURZWORT and not post):
            nuc = 'ə'
            if post and post[-1] == ('C', 'r') and len(post) == 1:   # unstressed -er / ver- / zer-: vocalised
                nuc, post = 'ɐ', []
        elif not post and naechste[:2] in ('ck', 'tz'):
            nuc = KURZ[b]                # Glo-cken, Kat-ze: split ck/tz closes the syllable
        elif lang or not post:
            nuc = LANG[b]
        elif einsilbig and len(post) == 1 and wort not in KURZWORT and post[0][1] not in ('ng', 'nk', 'sch', 'ch', 'ck', 'tz', 'ss', 'pf'):
            nuc = LANG[b]                # Tag, gut, Weg: one-syllable words with one consonant are mostly long
        else:
            nuc = KURZ[b]
    long_v = nuc in ('a', 'e', 'i', 'o', 'u', 'y', 'ø') and (lang or not post or einsilbig)
    back = nuc in ('a', 'o', 'ɔ', 'u', 'ʊ', 'aʊ')
    # onset
    on = []
    for j, (_, g) in enumerate(pre):
        nxt = pre[j + 1][1] if j + 1 < len(pre) else None
        if g == 's' and k == 0 and nxt in ('p', 't'): on.append('ʃ'); continue
        on += {'sch': ['ʃ'], 'tsch': ['tʃ'], 'ch': ['ç'], 'chs': ['k', 's'], 'ck': ['k'], 'ph': ['f'], 'qu': ['k', 'v'], 'tz': ['ts'],
               'z': ['ts'], 'v': ['f'], 'w': ['v'], 'th': ['t'], 'dt': ['t'], 'ß': ['s'], 'ss': ['s'], 'x': ['k', 's'], 'c': ['k'],
               'j': ['j'], 'r': ['r'], 's': ['z'] if nxt is None else ['s'], 'ng': ['ŋ'], 'nk': ['ŋ', 'k']}.get(g, [g])
    if not on and k == 0:
        on = ['ʔ']
    # coda (final devoicing everywhere in the coda)
    co = []
    for j, (_, g) in enumerate(post):
        if g == 'r':
            if long_v or nuc in ('ə', 'ɐ'): continue          # vocalised r after long vowels
            co.append('r'); continue
        if g == 'ch': co.append('x' if back else 'ç'); continue
        if g == 'g' and wortende and j == len(post) - 1 and nuc == 'ɪ': co.append('ç'); continue    # -ig
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


def wort(stuecke, aussprache=None):
    """the syllables of one word: stuecke = the pieces under its notes; aussprache = {word: 'ipa.ipa'} overrides"""
    w = ''.join(stuecke)
    key = re.sub(r"[^a-zäöüß]", '', w.lower())
    for k_, v_ in (aussprache or {}).items():
        if re.sub(r"[^a-zäöüß]", '', k_.lower()) == key:
            teile = [t for t in re.split(r'[.\s-]+', v_) if t]
            if len(teile) == len(stuecke):
                out = [ipa_silbe(t) for t in teile]
                if not any(o['nucleus']['stress'] for o in out): out[0]['nucleus']['stress'] = 1
                return out
    n = len(stuecke)
    erste = re.sub(r"[^a-zäöüß]", '', stuecke[0].lower())
    letzte = re.sub(r"[^a-zäöüß]", '', stuecke[-1].lower())
    beton = 1 if (n > 1 and erste in VORSILBE and not (n == 2 and letzte in ('chen', 'lein'))) else 0   # Ent-chen: no prefix
    return [silbe(t, key, k, n, k == beton, k == n - 1, re.sub(r"[^a-zäöüß]", '', stuecke[k + 1].lower()) if k + 1 < n else '')
            for k, t in enumerate(stuecke)]


if __name__ == '__main__':
    import sys, json
    for w in sys.argv[1:]:
        st = w.split('-')
        r = wort(st)
        print(w, ' '.join('/' + ''.join(x['ipa'] for x in s['onset']) + ('ˈ' if s['nucleus']['stress'] else '') + s['nucleus']['ipa']
                          + ''.join(x['ipa'] for x in s['coda']) + '/' for s in r if s))
