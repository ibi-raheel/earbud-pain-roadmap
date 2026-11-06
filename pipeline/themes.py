"""Pain themes for true-wireless earbuds.

Two lexicons per theme:
- NAIVE: the one or two words an analyst would grep for. This is the keyword baseline.
- SEED: a richer pattern set used only to create weak training labels for the
  linear theme classifier (it is never used as the final answer on its own).
"""
import re

THEMES = [
    ("fit_comfort", "Fit and comfort"),
    ("battery", "Battery life and fade"),
    ("charging_case", "Charging case and charging"),
    ("connectivity", "Pairing and connection drops"),
    ("sound_quality", "Sound quality"),
    ("anc_noise", "Noise cancelling and transparency"),
    ("call_mic", "Call and microphone quality"),
    ("controls", "Touch controls"),
    ("failure", "Earbud stops working"),
    ("app_software", "App and firmware"),
]
KEYS = [k for k, _ in THEMES]
LABELS = dict(THEMES)

NAIVE = {
    "fit_comfort": r"\b(fit|comfort\w*)\b",
    "battery": r"\bbattery\b",
    "charging_case": r"\bcase\b",
    "connectivity": r"\b(connect\w*|pair\w*)\b",
    "sound_quality": r"\bsound\b",
    "anc_noise": r"\bnoise\b",
    "call_mic": r"\b(mic|microphone)\b",
    "controls": r"\b(touch|controls?)\b",
    "failure": r"\b(broke|stopped working)\b",
    "app_software": r"\bapp\b",
}

SEED = {
    "fit_comfort": r"\b(fit|fits|fitting|fell out|falls? out|falling out|stay(s)? in|uncomfortable|comfort\w*|hurts?|hurting|ear ?(pain|ache)|sore|pressure in|ear ?tips?|tips|too big|too large|bulky|loose)\b",
    "battery": r"\b(battery|batteries|hours? of (play|use|listening)|holds? (a )?charge|hold charge|dies? (after|quickly|fast|in)|drain\w*|only lasts?|last(s|ed)? (only|about|maybe)|run(s)? out)\b",
    "charging_case": r"\b(case|lid|hinge|magnet\w*|charging port|won'?t charge|wouldn'?t charge|not charg\w*|stopped charging|doesn'?t charge|charging contacts?|usb-?c|cradle)\b",
    "connectivity": r"\b(connect\w*|disconnect\w*|pairing|paired|unpair\w*|re-?pair\w*|(?:won\'?t|wouldn\'?t|doesn\'?t|didn\'?t|can\'?t|couldn\'?t|not|never|to) pair|bluetooth|drop(s|ped|ping)? (out|connection|signal)|cuts? (out|in and out)|signal|sync\w*|cutting out|out of sync|lag\w*|latency|delay)\b",
    "sound_quality": r"\b(sound\w*|audio|bass|treble|tinny|muffled|crisp|clarity|highs|mids|volume|static|crackl\w*|hiss\w*|distort\w*|quiet)\b",
    "anc_noise": r"\b(noise[- ]cancel\w*|anc|transparency|ambient|block(s|ing)? (out )?(noise|sound)|isolation|background noise)\b",
    "call_mic": r"\b(mic|mics|microphone|calls?|phone calls?|hear me|caller|people (couldn'?t|can'?t) hear|voice)\b",
    "controls": r"\b(touch|tap|taps|tapping|controls?|buttons?|press(ing)?|accidental\w*|gesture\w*|sensor)\b",
    "failure": r"\b(stopped working|quit working|quit|died|dead|broke|broken|defective|stopped|malfunction\w*|no longer works?|doesn'?t work|don'?t work|won'?t work|stop working|fell apart|replace(ment)?|warranty)\b",
    "app_software": r"\b(app|firmware|update\w*|software|equalizer|eq)\b",
}

NAIVE_RE = {k: re.compile(v, re.I) for k, v in NAIVE.items()}
SEED_RE = {k: re.compile(v, re.I) for k, v in SEED.items()}


def match(lexicon: dict, sentence: str) -> list:
    return [k for k in KEYS if lexicon[k].search(sentence)]
