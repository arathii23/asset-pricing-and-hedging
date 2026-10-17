"""Offline interaction checks for the guided dashboard and scenario behaviour."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src import config as C
from src.dashboard import project_scenario
from src.dashboard_content import PAGE_FILES, PAGES, SECTION_THEMES

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((C.EXHIBIT_DIR / "summary.json").read_text())
        cls.saved_files = [*C.EXHIBIT_DIR.glob("*"), *C.MEMO_DIR.glob("*")]
        cls.hashes = {
            p: hashlib.sha256(p.read_bytes()).digest()
            for p in cls.saved_files if p.is_file()
        }

    @classmethod
    def tearDownClass(cls):
        for path, digest in cls.hashes.items():
            assert hashlib.sha256(path.read_bytes()).digest() == digest, path

    def app(self, page=0):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        if page:
            app.switch_page(f"views/{PAGE_FILES[page]}.py").run()
        self.assertFalse(app.exception)
        return app

    @staticmethod
    def button(app, label):
        return next(button for button in app.button if button.label == label)

    def test_navigation_and_all_pages_render(self):
        app = self.app()
        self.button(app, "Open expansion analysis").click().run()
        self.assertEqual(app.title[0].value, "Expansion analysis")
        for page in PAGE_FILES:
            app.switch_page(f"views/{page}.py").run()
            self.assertFalse(app.exception, page)
            accent = SECTION_THEMES[PAGES[PAGE_FILES.index(page)]][0]
            self.assertTrue(any(f"--section-accent: {accent}" in item.value for item in app.markdown))

    def test_section_colours_have_readable_text_contrast(self):
        self.assertEqual(set(SECTION_THEMES), set(PAGES))

        def luminance(colour):
            channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
            return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))

        for page, (accent, background, _) in SECTION_THEMES.items():
            contrast = (luminance(background) + .05) / (luminance(accent) + .05)
            self.assertGreaterEqual(contrast, 4.5, page)

    def test_presets_reset_and_scenario_survives_navigation(self):
        app = self.app(1)
        self.assertEqual(app.metric[0].value, "+₹70.5 crore")
        app.button(key="preset_cash").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.slider(key="scenario_fcf").value, -10)
        self.assertTrue(app.metric[0].value.startswith("−"))
        self.assertTrue(app.error)
        app.switch_page("views/overview.py").run()
        app.switch_page("views/expansion.py").run()
        self.assertEqual(app.slider(key="scenario_fcf").value, -10)
        app.button(key="preset_base").click().run()
        self.assertEqual(app.metric[0].value, "+₹70.5 crore")
        self.assertEqual(app.slider(key="scenario_fcf").value, 0)
        app.button(key="preset_fx").click().run()
        self.assertEqual(app.slider(key="scenario_fx").value, -5)
        self.assertEqual(app.slider(key="scenario_fcf").value, 0)
        self.assertFalse(app.exception)

    def test_base_results_and_future_fx_only(self):
        m = self.summary
        for forward, key in ((False, "npv_unhedged"), (True, "npv_hedged")):
            base = project_scenario(m, C.PROJECT_CAPEX_USD, 0, m["wacc"], 0, forward)
            self.assertAlmostEqual(base[3], m[key], places=4)
            stronger = project_scenario(m, C.PROJECT_CAPEX_USD, 0, m["wacc"], -.05, forward)
            self.assertEqual(base[0][0], stronger[0][0])
            self.assertLess(stronger[3], base[3])
            self.assertAlmostEqual(stronger[0][1], base[0][1] * .95)

    def test_forward_comparison_has_zero_irr_change_at_its_base(self):
        app = self.app(1)
        app.radio(key="scenario_path").set_value("Use the forward-rate path").run()
        self.assertEqual(app.metric[0].value, "+₹92.6 crore")
        self.assertEqual(app.metric[1].delta, "+0.00 percentage points")
        self.assertFalse(app.exception)

    def test_hedge_presets_keep_forward_fixed_and_bound_collar(self):
        app = self.app(2)
        self.button(app, "USDINR −10%").click().run()
        weak = app.dataframe[0].value
        self.button(app, "USDINR +10%").click().run()
        strong = app.dataframe[0].value
        self.assertFalse(app.exception)
        self.assertAlmostEqual(weak.iloc[1, 1], strong.iloc[1, 1])
        self.assertGreater(weak.iloc[3, 1], weak.iloc[0, 1])
        self.assertLess(strong.iloc[3, 1], strong.iloc[0, 1])
        self.assertFalse(app.warning)
        selected_rate = app.slider(key="hedge_future_rate").value
        app.switch_page("views/overview.py").run()
        app.switch_page("views/hedging.py").run()
        self.assertEqual(app.slider(key="hedge_future_rate").value, selected_rate)

    def test_option_sensitivity_reset_and_navigation(self):
        app = self.app(4)
        initial = float(app.metric[0].value.replace("₹", ""))
        self.assertAlmostEqual(initial, self.summary["put_prem"], places=4)
        self.button(app, "Volatility +2pp").click().run()
        self.assertGreater(float(app.metric[0].value.replace("₹", "")), initial)
        vol = app.number_input(key="option_vol").value
        app.switch_page("views/overview.py").run()
        app.switch_page("views/options.py").run()
        self.assertEqual(app.number_input(key="option_vol").value, vol)
        self.button(app, "Reset inputs").click().run()
        self.assertEqual(float(app.metric[0].value.replace("₹", "")), initial)
        app.radio(key="option_kind").set_value("Call · right to buy USD").run()
        self.assertFalse(app.exception)
        app.number_input(key="option_vol").set_value(.1).run()
        app.number_input(key="option_domestic").set_value(30.0).run()
        self.assertTrue(app.warning)
        self.assertEqual(app.metric[1].value, "Adjust settings")
        self.assertFalse(app.exception)

    def test_glossary_search_and_no_result(self):
        app = self.app(5)
        app.text_input(key="glossary_search").set_value("10.96").run()
        self.assertTrue(any("CAPM" in item.label for item in app.expander))
        app.text_input(key="glossary_search").set_value("zzzznomatch").run()
        self.assertTrue(any("No match" in item.value for item in app.info))
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
