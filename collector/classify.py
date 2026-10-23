"""Classification and spec extraction for PLL / frequency-synthesizer papers.

Pure functions (no network, no files) so they can be unit-tested and re-run over the
cached records whenever the rules change. Abstracts are inputs only; they are never
written to the output.
"""
import math
import re

I = re.IGNORECASE

# ---------------------------------------------------------------- relevance
PLL_PAT = re.compile(
    r"\bPLLs?\b|phase[- ]locked[- ]loop|\b(?:AD|D|SS|S|IL|CP|DT|BB)PLLs?\b|\bMDLLs?\b|multiplying (?:DLL|delay[- ]locked)|"
    r"frequency synthesi[sz]ers?|\bsynthesi[sz]ers?\b|clock (?:generator|multiplier|multiplication unit)s?|\bCMUs?\b|"
    r"fractional[- ]N|integer[- ]N|chirp generator", I)

# direct digital synthesis, audio/music synthesis and data synthesis are not PLLs
NOT_PLL = re.compile(r"direct[- ]digital (?:frequency )?synthes|\bDDFS\b|\bDDS\b|speech|music|logic synthes|"
                     r"high[- ]level synthes|synthesi[sz]ed (?:netlist|design)", I)

# a radio/link/SoC "with" a PLL: the PLL is a block, not the subject
HOST = re.compile(r"\b(?:receiver|transmitter|transceiver|TRX|front[- ]end|SoC|radio|radar)s?\b"
                  r".*\b(?:with|using|featuring|employing|incorporating|based on)\b", I)

NON_PAPER = re.compile(
    r"^(front cover|back cover|table of contents|contents|author index|index|"
    r"call for papers|editorial|guest editorial|reviewers|session \d+ overview|"
    r"(?:tutorials?|short course|evening (?:event|session)|forum|panel)(?=\s*:|\s*$)|"
    r"(ieee )?(transactions|journal) .*information|blank page|copyright)\b", I)


def relevance(title, abstract):
    """Return 'core', 'related' or None."""
    t = title or ""
    if NOT_PLL.search(t) and not re.search(r"\bPLL|phase[- ]locked", t, I):
        return None
    if PLL_PAT.search(t):
        m = HOST.search(t)
        if m and m.start() < PLL_PAT.search(t).start():
            return "related"
        return "core"
    a = abstract or ""
    if re.search(r"\bPLLs?\b|phase[- ]locked loop|frequency synthesi[sz]er", a, I) and not NOT_PLL.search(t):
        return "related"
    return None


# ------------------------------------------------------------- type / architecture / application
def pll_type(title, abstract):
    text = (title or "") + " " + (abstract or "")
    if re.search(r"fractional[- ]N|frac[- ]N|\bfractional\b|Δ\s?Σ|delta[- ]sigma|sigma[- ]delta|\bMASH\b|\bDTC\b", text, I):
        return "Fractional-N"
    if re.search(r"integer[- ]N", text, I):
        return "Integer-N"
    return ""


ARCH_RULES = [
    ("Digital/ADPLL",    r"\bADPLL|all[- ]digital|\bDPLL|digital(?:ly)?[- ](?:intensive )?PLL|\bDCO\b|\bTDC\b|bang[- ]bang|\bBBPD|\bBB[- ]?PLL"),
    ("Sampling",         r"sub[- ]?sampling|\bSS[- ]?PLL|\bSPLL\b|sampling[- ](?:PLL|phase detector|PD)|reference[- ]sampling|double[- ]sampling"),
    ("Charge-pump",      r"charge[- ]pump|\bCP[- ]?PLL|type[- ]II"),
    ("Type-I",           r"\btype[- ]I\b(?!I)"),
    ("Injection-locked", r"injection[- ]lock|\bIL[- ]?PLL|\bILCM|\bILFM"),
    ("MDLL",             r"\bMDLL|multiplying (?:DLL|delay[- ]locked)"),
    ("DTC-based",        r"\bDTC|digital[- ]to[- ]time"),
    ("Cascaded",         r"cascad|dual[- ]loop|two[- ]stage PLL"),
    ("Ring oscillator",  r"ring[- ](?:oscillator|VCO|DCO|osc)|\bRO[- ]based"),
    ("LC oscillator",    r"\bLC[- ]?(?:VCO|DCO|tank|oscillator|PLL)|class[- ](?:B|C|D|F)\d? (?:VCO|oscillator)"),
]
ARCH_RX = [(n, re.compile(p, I)) for n, p in ARCH_RULES]


def architectures(title, abstract):
    def scan(text):
        return [n for n, rx in ARCH_RX if rx.search(text or "")]
    tags = scan(title)
    if abstract:
        first = " ".join(re.split(r"(?<=[.!?])\s+", abstract)[:2])   # the design itself, not the comparisons
        for t in scan(first):
            if t not in tags:
                tags.append(t)
    return tags


APP_RULES = [
    ("Wireline/clocking", r"wireline|serdes|\bPAM[- ]?\d|Gb/s|optical|data[- ]center|clock (?:generator|multiplier|distribution)|\bCDR\b|\bCMU\b"),
    ("Wireless LO",       r"\b[56]G\b|wireless|cellular|\bLTE\b|Wi-?Fi|802\.11|\bBLE\b|bluetooth|\bLO\b|local oscillator|mm-?wave|millimeter|transceiver|satellite"),
    ("Radar/FMCW",        r"radar|FMCW|chirp"),
    ("IoT/low-power",     r"\bIoT\b|ultra[- ]low[- ]power|[µμu]W\b|energy[- ]harvest|wake[- ]up"),
    ("Processor/SoC",     r"processor|\bCPU\b|\bGPU\b|\bSoC\b|microprocessor|clock(?:ing)? for (?:digital|logic)|spread[- ]spectrum"),
    ("Quantum/cryo",      r"quantum|qubit|cryo"),
]
APP_RX = [(n, re.compile(p, I)) for n, p in APP_RULES]
CAL_RX = re.compile(r"calibrat|\bLMS\b|background (?:correction|estimation)|nonlinearity correction|predistortion", I)


def applications(title, abstract):
    text = (title or "") + " " + (abstract or "")
    return [n for n, rx in APP_RX if rx.search(text)]


def has_calibration(title, abstract):
    return bool(CAL_RX.search((title or "") + " " + (abstract or "")))


# ------------------------------------------------------------- spec parsing
NUM = r"(\d+(?:\.\d+)?)"
NEG = r"([−–-]\s?\d+(?:\.\d+)?)"
_SI = {"a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6,
       "m": 1e-3, "": 1.0, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}

# "2.4-GHz", "8-14GHz", "26.2-28.5 GHz", "0.27-THz": the upper end of a range is the output frequency
FREQ_RX = re.compile(r"(?<![\w.])(?:" + NUM + r"\s*(?:-|–|to|-to-)\s*)?" + NUM + r"\s*-?\s*([kMGT])Hz\b")
FREF_RX = re.compile(NUM + r"\s*-?\s*([kMG])Hz\s+(?:reference|ref\.?|crystal|XO|input)", I)
JITTER_RX = [
    re.compile(NUM + r"\s*-?\s*([fp])s\s*(?:,?\s*rms|RMS|-rms|_?rms)?\s*(?:integrated\s+|RMS\s+|rms\s+|absolute\s+)?jitter", I),
    re.compile(r"jitter[^.;\d]{0,40}?(?:of\s+|is\s+|=\s*)?" + NUM + r"\s*-?\s*([fp])s", I),
    re.compile(NUM + r"\s*-?\s*([fp])s\s*-?\s*rms", I),
    re.compile(NUM + r"\s*-?\s*([fp])s(?:rms|RMS)\b", I),
]
FOM_RX = [
    re.compile(r"FoM\w*[^.;\d−–-]{0,40}?(?:of\s+)?" + r"([−–-]\s?2\d\d(?:\.\d+)?)\s*-?\s*dB", I),
    re.compile(r"([−–-]\s?2\d\d(?:\.\d+)?)\s*-?\s*dB[- ]?(?:jitter[- ])?FoM", I),
]
SPUR_RX = [
    re.compile(r"(?:reference|ref\.?)[- ]spur\w*[^.;\d−–-]{0,30}?" + NEG + r"\s*-?\s*dBc", I),
    re.compile(NEG + r"\s*-?\s*dBc\s+(?:reference|ref\.?)[- ]spur", I),
]
FSPUR_RX = [
    re.compile(r"(?:fractional|in-band fractional|worst(?:-case)? fractional)[- ]spurs?\w*[^.;\d−–-]{0,30}?" + NEG + r"\s*-?\s*dBc", I),
    re.compile(NEG + r"\s*-?\s*dBc\s+(?:worst(?:-case)?\s+)?fractional[- ]spur", I),
]
PN_RX = re.compile(NEG + r"\s*-?\s*dBc/Hz\s*(?:phase noise\s*)?(?:at|@)\s*(?:an?\s+)?(?:offset\s+(?:of\s+)?)?" + NUM + r"\s*-?\s*([kM])Hz", I)
LOCK_RX = re.compile(r"(?:lock(?:ing)?|settling)[- ]time[^.;\d]{0,25}?" + NUM + r"\s*-?\s*([nuµμm])s|" + NUM + r"\s*-?\s*([nuµμm])s\s+(?:lock(?:ing)?|settling)", I)
NODE_NM_RX = re.compile(r"(?<![\w.])(\d{1,3})\s*-?\s*nm\b", I)
NODE_UM_RX = re.compile(r"(?<![\w.])(0\.\d{2,3})\s*-?\s*[µμu]m\b", I)
POWER_VAL = NUM + r"\s*-?\s*([nuµμm]?)W\b"
POWER_CTX_RX = re.compile(r"(?:consum\w*|dissipat\w*|power(?:\s+consumption)?|draws|burns)[^.;]{0,40}?" + POWER_VAL, I)
POWER_ANY_RX = re.compile(POWER_VAL)
AREA_RX = re.compile(NUM + r"\s*-?\s*mm\s*(?:2|²|\^2)", I)


FREQ_SKIP_BEFORE = re.compile(r"(?:from|offset|integrat\w*|reference|ref\.?|bandwidth|\bBW|step|resolution|spacing|by)\s*(?:of\s+)?$", I)
FREQ_SKIP_AFTER = re.compile(r"^\s*(?:offset|reference|ref\b|bandwidth|BW\b|loop|crystal|XO\b|input|step|resolution|to\s+\d|-to-)", I)


def output_frequency(title, abstract):
    """Output frequency: from the title if it names one, else the highest plausible one in the abstract."""
    m = FREQ_RX.search(title or "")
    if m:
        return float(m.group(2)) * _SI[m.group(3)]
    best = None
    a = abstract or ""
    for m in FREQ_RX.finditer(a):
        if FREQ_SKIP_BEFORE.search(a[max(0, m.start() - 30):m.start()]) or FREQ_SKIP_AFTER.search(a[m.end():m.end() + 20]):
            continue
        v = float(m.group(2)) * _SI[m.group(3)]
        if v >= 1e6 and (best is None or v > best):
            best = v
    return best


def _neg(s):
    return -abs(float(re.sub(r"[−–\s-]", "", s)))


def _first(rxs, *texts):
    for text in texts:
        for rx in rxs:
            m = rx.search(text or "")
            if m:
                return m
    return None


def parse_specs(title, abstract):
    t, a = title or "", abstract or ""
    out = {}
    f = output_frequency(t, a)
    if f:
        out["f"] = f
    m = FREF_RX.search(a) or FREF_RX.search(t)
    if m:
        out["fref"] = float(m.group(1)) * _SI[m.group(2)]
    m = _first(JITTER_RX, t, a)
    if m:
        v = float(m.group(1)) * _SI[m.group(2).lower()]
        if 1e-15 <= v <= 100e-12:
            out["jitter"] = v
    m = _first(FOM_RX, t, a)
    if m:
        v = _neg(m.group(1))
        if -290 <= v <= -200:
            out["fom"] = v
    m = _first(SPUR_RX, t, a)
    if m:
        out["spur"] = _neg(m.group(1))
    m = _first(FSPUR_RX, t, a)
    if m:
        out["fspur"] = _neg(m.group(1))
    m = PN_RX.search(t) or PN_RX.search(a)
    if m:
        out["pn"] = _neg(m.group(1))
        out["pn_off"] = float(m.group(2)) * _SI[m.group(3)]
    m = LOCK_RX.search(a) or LOCK_RX.search(t)
    if m:
        val, pre = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        out["lock"] = float(val) * _SI[pre.replace("u", "µ")]
    m = NODE_NM_RX.search(t) or NODE_NM_RX.search(a)
    if m and 2 <= int(m.group(1)) <= 500:
        out["node"] = int(m.group(1))
    else:
        m = NODE_UM_RX.search(t) or NODE_UM_RX.search(a)
        if m:
            out["node"] = int(round(float(m.group(1)) * 1000))
    m = POWER_CTX_RX.search(a) or POWER_CTX_RX.search(t) or POWER_ANY_RX.search(t)
    if m:
        out["p"] = float(m.group(1)) * _SI[m.group(2) or ""]
    m = AREA_RX.search(a) or AREA_RX.search(t)
    if m:
        out["area"] = float(m.group(1))
    return out


def jitter_fom(jitter, power):
    """FoM_jitter = 10 log10((sigma_t / 1 s)^2 * (P / 1 mW)) in dB."""
    if not jitter or not power:
        return None
    return round(10 * math.log10(jitter ** 2 * power / 1e-3), 1)


def derived(specs):
    d = {}
    f = jitter_fom(specs.get("jitter"), specs.get("p"))
    if f is not None and "fom" not in specs:
        d["fom_calc"] = f
    return d


# ------------------------------------------------------------- affiliations and dates (same rules as adc-census)
ORG_HINT = re.compile(r"universit|institut|college|school|KAIST|POSTECH|UNIST|DGIST|GIST|\bETH\b|EPFL|\bMIT\b|"
                      r"laborator|\blabs?\b|inc\b|ltd|corp|company|co\.|electronics|semiconductor|technolog|"
                      r"research|centre|center|academy|imec|tsmc|samsung|sk hynix|intel|mediatek|qualcomm|"
                      r"apple|google|huawei|broadcom|analog devices|texas instruments", I)


def org_and_country(aff):
    if not aff:
        return None, None
    parts = [p.strip() for p in aff.split(",") if p.strip()]
    if not parts:
        return None, None
    country = re.sub(r"\s+\d[\d\- ]*$", "", parts[-1])
    if re.fullmatch(r"(korea|south korea|republic of korea|korea \(south\))", country, I):
        country = "South Korea"
    elif re.fullmatch(r"(usa|u\.s\.a\.|united states|united states of america|us)", country, I):
        country = "USA"
    elif re.fullmatch(r"(prc|p\.r\. china|people's republic of china)", country, I):
        country = "China"
    org = None
    for p in parts:
        if ORG_HINT.search(p) and not re.match(r"(department|dept|school of|faculty|division)\b", p, I):
            org = p
            break
    if org is None:
        org = parts[1] if len(parts) > 2 else parts[0]
    if len(country) > 30 or re.search(r"\d", country):
        country = None
    return org, country


MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_month(pubdate, year):
    s = (pubdate or "").lower()
    years = re.findall(r"(?:19|20)\d{2}", s)
    y = years[-1] if years else (str(year) if year else None)
    mon = None
    for tok in re.findall(r"[a-z]{3,}", s):
        if tok[:3] in MONTHS:
            mon = MONTHS[tok[:3]]
            break
    if y and mon:
        return "%s-%02d" % (y, mon)
    return y or ""
