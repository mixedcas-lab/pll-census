"""Offline tests: python3 -m unittest discover -s collector -v"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import classify as C  # noqa: E402


class TestRelevance(unittest.TestCase):
    def test_core(self):
        for t in ("A 5GHz Fractional-N PLL with 97fsrms Jitter and -255.3dB FoM",
                  "0.45-mW 2.35-3.0 GHz Multiplying DLL with Calibration Loop in 28nm CMOS FD-SOI",
                  "A BiCMOS Dual-Band Millimeter-Wave Frequency Synthesizer for Automotive Radars",
                  "An all-digital phase-locked loop for high-speed clock generation"):
            self.assertEqual(C.relevance(t, ""), "core", t)

    def test_dds_is_not_pll(self):
        self.assertIsNone(C.relevance("24-Bit 5.0 GHz Direct Digital Synthesizer RFIC With Direct Digital Modulations", ""))

    def test_pll_as_a_block_is_related(self):
        t = "A Single Path Digital-IF Receiver Supporting Inter/Intra 5-CA With a Single Integer LO-PLL in 14-nm CMOS FinFET"
        self.assertEqual(C.relevance(t, ""), "related")
        t = "Design Techniques for a Multi-Phase Injection-Based Eight-Phase 17-GHz Clock Generator for Multi-Phase Wireline Receivers"
        self.assertEqual(C.relevance(t, ""), "core")

    def test_abstract_only(self):
        self.assertEqual(C.relevance("A Transformer-Based Series-Resonance CMOS VCO", "The VCO is used in a PLL."), "related")


class TestSpecs(unittest.TestCase):
    def test_title(self):
        s = C.parse_specs("34.1 A 65fsrms-Jitter and -272dB-FoMjitter,N 10.1GHz Fractional-N Digital PLL", "")
        self.assertEqual((s["f"], s["jitter"], s["fom"]), (10.1e9, 65e-15, -272.0))

    def test_abstract(self):
        a = ("The 5.6-GHz PLL achieves 78 fs rms jitter integrated from 10 kHz to 100 MHz and a FoM of -250.1 dB "
             "while consuming 9.4 mW in 28-nm CMOS. The reference spur is -70 dBc and the worst fractional spur is "
             "-58 dBc. Phase noise is -110 dBc/Hz at 1 MHz offset with a 100 MHz reference.")
        s = C.parse_specs("A Low-Jitter Fractional-N LC-PLL", a)
        self.assertEqual(s["f"], 5.6e9)                      # not the 10 kHz integration bound
        self.assertEqual((s["fref"], s["p"], s["node"]), (100e6, 9.4e-3, 28))
        self.assertAlmostEqual(s["jitter"], 78e-15)
        self.assertEqual((s["fom"], s["spur"], s["fspur"], s["pn"], s["pn_off"]), (-250.1, -70.0, -58.0, -110.0, 1e6))

    def test_range_takes_upper_end(self):
        self.assertEqual(C.parse_specs("A 0.7-V 26.2-28.5 GHz Dual-Loop Double-Sampling PLL", "")["f"], 28.5e9)

    def test_fom_formula(self):
        self.assertEqual(C.jitter_fom(100e-15, 10e-3), -250.0)
        self.assertEqual(C.derived({"jitter": 100e-15, "p": 10e-3}), {"fom_calc": -250.0})
        self.assertEqual(C.derived({"jitter": 100e-15, "p": 10e-3, "fom": -251}), {})

    def test_type_and_arch(self):
        t = "A Low-Spur Fractional-N Digital PLL Based on an Inverse-Constant-Slope DTC"
        self.assertEqual(C.pll_type(t, ""), "Fractional-N")
        self.assertEqual(C.architectures(t, ""), ["Digital/ADPLL", "DTC-based"])
        self.assertIn("Sampling", C.architectures("A Type-II Sub-Sampling PLL", ""))


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = {k: getattr(build, k) for k in ("DATA", "PAPERS", "META")}
        build.DATA = os.path.join(self.tmp, "data")
        build.PAPERS = os.path.join(build.DATA, "papers.json")
        build.META = os.path.join(build.DATA, "meta.json")
        os.makedirs(build.DATA)
        self.cache = os.path.join(self.tmp, "cache")
        os.makedirs(self.cache)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(build, k, v)
        shutil.rmtree(self.tmp)

    def put(self, n, title, pub, abstract="", year=2025):
        with open(os.path.join(self.cache, "%d.json" % n), "w", encoding="utf-8") as f:
            json.dump({"article_number": n, "title": title, "publication_title": pub, "abstract": abstract,
                       "publication_year": year, "publication_date": "Feb. %d" % year, "doi": "10.1109/x.%d" % n,
                       "authors": {"authors": [{"full_name": "A. Kim", "author_order": 1,
                                                "affiliation": "KAIST, Daejeon, South Korea"}]}}, f)

    def test_rebuild(self):
        config = build.load_json(build.CONFIG, None)
        self.put(1, "A 5GHz Fractional-N PLL with 97fsrms Jitter", "IEEE Journal of Solid-State Circuits",
                 "It consumes 5 mW in 22-nm CMOS.")
        self.put(2, "A 12-b SAR ADC", "IEEE Journal of Solid-State Circuits")
        self.put(3, "A 10-GHz PLL", "2025 IEEE Custom Integrated Circuits Conference (CICC)")
        self.put(4, "A 2-GHz PLL", "Some Other Conference")
        self.put(5, "An Old PLL", "IEEE Journal of Solid-State Circuits", year=1990)
        meta = build.rebuild(config, self.cache, "2026-10-23")
        papers = {p["id"]: p for p in build.load_json(build.PAPERS, [])}
        self.assertEqual(set(papers), {"1", "3"})
        p = papers["1"]
        self.assertEqual((p["v"], p["ty"], p["cn"], p["x"]["fom_calc"]), ("JSSC", "Fractional-N", ["South Korea"], -253.3))
        self.assertNotIn("abstract", json.dumps(list(papers.values())))
        self.assertEqual((meta["core"], meta["last_run_new"]), (2, 0))
        self.put(6, "A 28-GHz Sampling PLL", "IEEE Journal of Solid-State Circuits")
        meta = build.rebuild(config, self.cache, "2026-11-20")
        papers = {p["id"]: p for p in build.load_json(build.PAPERS, [])}
        self.assertEqual((meta["last_run_new"], papers["6"]["first"], papers["1"]["first"]), (1, "2026-11-20", "2026-10-23"))


if __name__ == "__main__":
    unittest.main()
