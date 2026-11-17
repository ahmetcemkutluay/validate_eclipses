import sys
from pathlib import Path

#PyQt5 imports
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QShortcut
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

#Qt5 backends
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

#imported from this path
from decisions import Flags, append_decision, decisions_map
from lightcurve import load_target, phase_fold, flux_limits
from catalogue import load_catalogue, format_value

base = Path(__file__).resolve().parent
csv_path = base / "records.csv" ### PLEASE CHANGE IT ACCORDING TO YOUR RESULTING SAMPLE.
lc_root = base / "fits"
decisions_path = base / "decisions.csv"

info_fields = [
    ("Period (d)",     "period",      None,              6),
    ("T0",             "t_0",         None,              5),
    ("n_eclipses",     "n_eclipses",  None,              0),
    ("score",          "score",       None,              3),
    ("n_prim",         "n_prim",      None,              0),
    ("n_sec",          "n_sec",       None,              0),
    ("depth_prim",     "depth_prim",  "depth_prim_err",  4),
    ("depth_sec",      "depth_sec",   "depth_sec_err",   4),
    ("width_prim",     "width_prim",  "width_prim_err",  4),
    ("width_sec",      "width_sec",   "width_sec_err",   4),
    ("TESS mag",       "tess_mag",    None,              2),
    ("Cadence (min)",  "cadence_min", None,              1),
    ("Baseline (d)",   "baseline_d",  None,              2),
    ("n_points",       "n_points",    None,              0),
    ("n_gaps",         "n_gaps",      None,              0),
    ("pipeline",       "pipeline",    None,              0),
]

period_factors = [
    (0.25,      "P/4"),
    (1.0 / 3.0, "P/3"),
    (0.5,       "P/2"),
    (1.0,       "P"),
    (2.0,       "2P"),
    (3.0,       "3P"),
    (4.0,       "4P"),
]

PHASE_STEP = 0.005
PHASE_STEP_BIG = 0.05

default_factor = 3 #index of default P factor.

verdict_keys = {"F1": "accept", "F2": "reject", "F3": "uncertain"}

flag_keys = {"F4": "period_fix", "F5": "phase_fix", "F6": "not_eclipse", "F7": "bad_data", "F8": "additional_variabilities"}

verdict_colors = {"accept": "#1f7d49", "reject": "#bf3411" , "uncertain": "#915413"}

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("validate eclipses")
        self.setGeometry(500,100, 900, 800)
        self.setWindowIcon(QIcon(str(base / "logo" / "eclipse_logo_256.png")))

        self.df = load_catalogue(csv_path)
        self.decisions = decisions_map(decisions_path)
        self.index = 0
        self.factor_index = default_factor
        self.phase_offset = 0.0
        self.verdict = None
        self.flags = set()
        self.saved = False

        self._build_body()
        self._build_statusbar()
        self._build_shortcuts()

        self.canvas.setMinimumHeight(420)
        self.show_star(self.index)


    def _build_body(self):
            central = QWidget()
            layout = QVBoxLayout(central)
            header_row = QHBoxLayout()

            self.header = QLabel()
            self.header.setFont(QFont("Serif", 20))
            self.header.setAlignment(Qt.AlignLeft)

            self.counter = QLabel()
            self.counter.setFont(QFont("Serif", 11))
            self.counter.setStyleSheet("color: grey;")

            header_row.addStretch(1)
            header_row.addWidget(self.header)
            header_row.addSpacing(12)
            header_row.addWidget(self.counter, alignment= Qt.AlignBottom)
            header_row.addStretch(1)

            layout.addLayout(header_row)

            self.tags = QLabel()
            self.tags.setFont(QFont("Monospace", 11))
            self.tags.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.tags)

            self.figure = Figure(figsize=(9, 5), constrained_layout=True)
            #self.figure.subplots_adjust(left=0.09, right=0.98, top=0.93, bottom=0.08)
            self.canvas = FigureCanvas(self.figure)

            self.ax_full = self.figure.add_subplot(211)
            self.ax_full.set_xlabel("BTJD")
            self.ax_full.set_ylabel("norm. flux")
            self.line_full, = self.ax_full.plot([], [], ".", ms=1, color="0.25")

            self.ax_phase = self.figure.add_subplot(212)
            self.ax_phase.set_xlabel("Phase")
            self.ax_phase.set_ylabel("norm. flux")
            self.line_phase, = self.ax_phase.plot(
                [], [], ".", ms=1, alpha=0.75, color="black"
            )

            layout.addWidget(NavigationToolbar(self.canvas, self))
            layout.addWidget(self.canvas, stretch=1)
            
            layout.addLayout(self._build_info_panel())
            layout.addWidget(self._build_legend())
            self.setCentralWidget(central)

    def _build_statusbar(self):
            bar = self.statusBar()
            bar.showMessage("Ready")

            credit = QLabel("validate_eclipses v0.1.0  ·  © 2026 A. C. Kutluay")
            credit.setFont(QFont("Serif", 6))
            credit.setStyleSheet("color: #666; padding-right: 8px;")
            bar.addPermanentWidget(credit)

    def show_star(self, index):
        row = self.df.iloc[index]
        saved = self.decisions.get(str(row["tic"]))

        if saved:
            self.verdict = saved["verdict"]
            self.flags = set(saved["flags"])
            self.factor_index = factor_index_for(saved["period_factor"])
            self.phase_offset = saved["phase_offset"]
            self.saved = True
        else:
            self.verdict = None
            self.flags = set()
            self.factor_index = default_factor
            self.phase_offset = 0.0
            self.saved = False

        self._update_tags()

        self.header.setText(f"TIC {row['tic']} - Sector {row['sectors']}")
        self.counter.setText(
            f"{index + 1} / {len(self.df)}  ·  {len(self.decisions)} saved"
        )

        for title, column, err_column, decimals in info_fields:
            err = row[err_column] if err_column else None
            self.info_labels[column].setText(format_value(row[column], err, decimals))

        self._load_lightcurve(row)

    @property #allows me to use method like a variable without parantheses.
    def period_factor(self):
        return period_factors[self.factor_index][0]

    @property
    def period_label(self):
        return period_factors[self.factor_index][1]

    def _load_lightcurve(self, row):
        try:
            self.lc_time, self.lc_flux = load_target(
                lc_root, row["tic"], row["pipeline"], row["sectors"]
            )
        except (FileNotFoundError, ValueError) as err:
            self.lc_time = self.lc_flux = None
            self.line_full.set_data([], [])
            self.line_phase.set_data([], [])
            self.ax_full.set_title(str(err), fontsize=9, color="firebrick")
            self.ax_phase.set_title("")
            self.canvas.draw_idle()
            return

        self._draw_full(row)
        self._draw_phase(row)

        self._draw_phase(row)

    def _draw_full(self, row):
        period = row["period"] * self.period_factor
        t, flux = self.lc_time, self.lc_flux

        self.line_full.set_data(t, flux)
        self.ax_full.set_xlim(t.min(), t.max())
        self.ax_full.set_ylim(*flux_limits(flux))
        self.ax_full.set_title(f"P = {period:.5f} d - "
                    f"score = {row['score']:.3f} - "
            f"{row['pipeline']}  S{row['sectors']} - "
            f"cad {row['cadence_min']:.1f} min - ",
            fontsize=9,
        )

    def _draw_phase(self, row):
        period = row["period"] * self.period_factor
        t_0 = row["t_0"] + self.phase_offset * period

        ph, flux = phase_fold(self.lc_time, self.lc_flux, period, t_0)

        self.line_phase.set_data(ph, flux)
        self.ax_phase.set_xlim(-0.25, 0.75)
        self.ax_phase.set_ylim(*flux_limits(flux))

        title = f"folded with {self.period_label}  ·  P = {period:.5f} d"
        if self.phase_offset:
            title += f"  ·  Δφ = {self.phase_offset:+.3f}"
        self.ax_phase.set_title(title, fontsize=9)

        self.canvas.draw_idle()

    def _build_info_panel(self):
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(4)

        self.info_labels = {}

        for i, (title, column, err_column, decimals) in enumerate(info_fields):
            row = i // 2
            col = (i % 2) * 2

            name = QLabel(f"{title}:")
            name.setStyleSheet("color: #666;")
            name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            value = QLabel("—")
            value.setStyleSheet("font-family: monospace;")

            grid.addWidget(name, row, col)
            grid.addWidget(value, row, col + 1)

            self.info_labels[column] = value

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        return grid

    def _build_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Right), self, self.next_star)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.prev_star)

        QShortcut(QKeySequence(Qt.Key_Up), self, lambda: self.change_factor(+1))
        QShortcut(QKeySequence(Qt.Key_Down), self, lambda: self.change_factor(-1))

        QShortcut(QKeySequence(Qt.Key_BracketLeft),  self, lambda: self.change_phase(-PHASE_STEP))
        QShortcut(QKeySequence(Qt.Key_BracketRight), self, lambda: self.change_phase(+PHASE_STEP))
        QShortcut(QKeySequence(Qt.Key_BraceLeft),    self, lambda: self.change_phase(-PHASE_STEP_BIG))
        QShortcut(QKeySequence(Qt.Key_BraceRight),   self, lambda: self.change_phase(+PHASE_STEP_BIG))
        QShortcut(QKeySequence(Qt.Key_0),            self, self.reset_view)

        for key, verdict in verdict_keys.items():
            QShortcut(QKeySequence(key), self, lambda v=verdict: self.set_verdict(v))

        for key, flag in flag_keys.items():
            QShortcut(QKeySequence(key), self, lambda f=flag: self.toggle_flag(f))

        QShortcut(QKeySequence("Return"), self, self.save_and_next)
        QShortcut(QKeySequence("Enter"),  self, self.save_and_next)

    def next_star(self):
        if self.index < len(self.df) - 1:
            self.index += 1
            self.show_star(self.index)
        else:
            self.statusBar().showMessage("Last object", 2000)

    def prev_star(self):
        if self.index > 0:
            self.index -= 1
            self.show_star(self.index)
        else:
            self.statusBar().showMessage("First object", 2000)

    def current_row(self):
        return self.df.iloc[self.index]

    def change_factor(self, step):
        new_index = self.factor_index + step
        if not 0 <= new_index < len(period_factors):
            return
        self.factor_index = new_index
        self._draw_phase(self.current_row())
        self.statusBar().showMessage(f"Folded with {self.period_label}", 1500)

    def reset_view(self):
        self.saved = False
        self.factor_index = default_factor
        self.phase_offset = 0.0
        self._draw_phase(self.current_row())
        self._update_tags()

    def change_phase(self, delta):
        self.saved = False
        value = self.phase_offset + delta
        self.phase_offset = round(((value + 0.5) % 1.0) - 0.5, 4)
        self._draw_phase(self.current_row())
        self.statusBar().showMessage(f"Δφ = {self.phase_offset:+.3f}", 1500)

    def set_verdict(self, verdict):
        self.saved = False
        # aynı tuşa tekrar basmak kararı geri alır
        self.verdict = None if self.verdict == verdict else verdict
        self._update_tags()

    def toggle_flag(self, flag):
        self.saved = False
        if flag in self.flags:
            self.flags.discard(flag)
        else:
            self.flags.add(flag)
        self._update_tags()

    def _update_tags(self):
        parts = []
        if self.verdict:
            parts.append(self.verdict.upper())
        parts.extend(key for key in Flags if key in self.flags)

        if not parts:
            self.tags.setText("no decision yet  ·  F1 accept   F2 reject   F3 uncertain")
            self.tags.setStyleSheet("color: #aaa;")
            return

        text = "   ".join(parts)
        text += "   ✓ saved" if self.saved else "   • unsaved"

        color = verdict_colors.get(self.verdict, "#444")
        self.tags.setText(text)
        self.tags.setStyleSheet(f"color: {color}; font-weight: bold;")

        color = verdict_colors.get(self.verdict, "#444")
        self.tags.setText("   ".join(parts))
        self.tags.setStyleSheet(f"color: {color}; font-weight: bold;")

    def save_and_next(self):
        if not self.verdict:
            self.statusBar().showMessage("Pick a verdict first (F1 / F2 / F3)", 2000)
            return

        row = self.current_row()
        append_decision(
            decisions_path,
            tic=row["tic"],
            sectors=row["sectors"],
            verdict=self.verdict,
            flags=self.flags,
            period_factor=self.period_factor,
            period_label=self.period_label,
            phase_offset=self.phase_offset,
        )

        self.decisions[str(row["tic"])] = {
            "verdict": self.verdict,
            "flags": set(self.flags),
            "period_factor": self.period_factor,
            "phase_offset": self.phase_offset,
            "note": "",
        }
        self.saved = True
        self._update_tags()

        self.statusBar().showMessage(f"Saved  TIC {row['tic']}", 2000)
        self.next_star()

    def _build_legend(self):
        verdicts = "   ".join(f"{key} {name}" for key, name in verdict_keys.items())
        flags = "   ".join(f"{key} {name}" for key, name in flag_keys.items())

        legend = QLabel(
            f"{verdicts}      {flags}\n"
            "← → object      ↑ ↓ period      [ ] phase      0 reset      Enter save"
        )
        legend.setFont(QFont("Monospace", 8))
        legend.setStyleSheet("color: #888; padding-top: 6px;")
        legend.setAlignment(Qt.AlignCenter)
        return legend

def factor_index_for(value):
    diffs = [abs(factor - value) for factor, _ in period_factors]
    return diffs.index(min(diffs))

def main():
    app = QApplication(sys.argv)


    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()