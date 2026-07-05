"""
Plain Tkinter front-end for the Body Scan pipeline.

Pick a video, enter height (and optionally weight/age/gender and a one-time
tape-measure calibration), press Scan. Internals stay metric; the Settings
tab switches the displayed/entered units to imperial.

Run:  python ui.py
"""

import threading
import tkinter as tk
from tkinter import ttk, filedialog

import config
from pipeline import run_pipeline
from sizing import SIZE_CHARTS, calibration_from_size

CM_PER_IN = 2.54
KG_PER_LB = 0.453592

# Result keys that are lengths (cm) vs mass (kg) vs unitless.
LENGTH_KEYS = ["neck", "chest", "waist", "hip",
               "bicep", "forearm", "wrist", "thigh", "calf"]


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BodyScanApp:

    def __init__(self, root):
        self.root = root
        root.title("Body Scan")
        self.unit = tk.StringVar(value="metric")
        self.video_path = tk.StringVar()

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.scan_tab = ttk.Frame(notebook)
        self.settings_tab = ttk.Frame(notebook)
        notebook.add(self.scan_tab, text="Scan")
        notebook.add(self.settings_tab, text="Settings")

        self._build_scan_tab()
        self._build_settings_tab()
        self._refresh_unit_labels()

    # ---------- layout ----------
    def _build_scan_tab(self):
        f = self.scan_tab

        ttk.Label(f, text="Video:").grid(row=0, column=0, sticky="e", pady=3)
        ttk.Entry(f, textvariable=self.video_path, width=34).grid(row=0, column=1, pady=3)
        ttk.Button(f, text="Browse...", command=self.browse).grid(row=0, column=2, padx=4)

        self.height_lbl = ttk.Label(f, text="Height:")
        self.height_lbl.grid(row=1, column=0, sticky="e", pady=3)
        self.height_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.height_var, width=12).grid(row=1, column=1, sticky="w", pady=3)

        self.weight_lbl = ttk.Label(f, text="Weight (optional):")
        self.weight_lbl.grid(row=2, column=0, sticky="e", pady=3)
        self.weight_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.weight_var, width=12).grid(row=2, column=1, sticky="w", pady=3)

        ttk.Label(f, text="Gender:").grid(row=3, column=0, sticky="e", pady=3)
        self.gender_var = tk.StringVar(value="neutral")
        ttk.OptionMenu(f, self.gender_var, "neutral", "male", "female", "neutral").grid(
            row=3, column=1, sticky="w", pady=3)

        ttk.Label(f, text="Age (optional):").grid(row=4, column=0, sticky="e", pady=3)
        self.age_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.age_var, width=12).grid(row=4, column=1, sticky="w", pady=3)

        # optional one-time calibration via a known clothing size
        ttk.Label(f, text="Calibrate by size (optional):").grid(
            row=5, column=0, sticky="e", pady=3)
        self.calib_chart = tk.StringVar(value="(none)")
        chart_names = ["(none)"] + list(SIZE_CHARTS.keys())
        ttk.OptionMenu(f, self.calib_chart, chart_names[0], *chart_names,
                       command=self._on_chart_change).grid(row=5, column=1, sticky="w", pady=3)
        self.calib_size = tk.StringVar(value="")
        self.size_menu = ttk.OptionMenu(f, self.calib_size, "")
        self.size_menu.grid(row=5, column=2, sticky="w", pady=3)

        self.scan_btn = ttk.Button(f, text="Scan", command=self.start_scan)
        self.scan_btn.grid(row=6, column=0, columnspan=3, pady=8)

        self.status = ttk.Label(f, text="")
        self.status.grid(row=7, column=0, columnspan=3)

        self.results = tk.Text(f, width=44, height=16, state="disabled")
        self.results.grid(row=8, column=0, columnspan=3, pady=4)

    def _build_settings_tab(self):
        f = self.settings_tab
        ttk.Label(f, text="Units:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Radiobutton(f, text="Metric (cm / kg)", variable=self.unit,
                        value="metric", command=self._refresh_unit_labels).grid(
            row=1, column=0, sticky="w", padx=16)
        ttk.Radiobutton(f, text="Imperial (in / lb)", variable=self.unit,
                        value="imperial", command=self._refresh_unit_labels).grid(
            row=2, column=0, sticky="w", padx=16)

    def _refresh_unit_labels(self):
        if self.unit.get() == "imperial":
            self.height_lbl.config(text="Height (in):")
            self.weight_lbl.config(text="Weight (lb, optional):")
        else:
            self.height_lbl.config(text="Height (cm):")
            self.weight_lbl.config(text="Weight (kg, optional):")

    def _on_chart_change(self, chart_name):
        """Repopulate the size dropdown for the selected chart."""
        menu = self.size_menu["menu"]
        menu.delete(0, "end")
        self.calib_size.set("")
        if chart_name in SIZE_CHARTS:
            _, chart = SIZE_CHARTS[chart_name]
            for size in chart:
                menu.add_command(label=size, command=lambda s=size: self.calib_size.set(s))

    # ---------- actions ----------
    def browse(self):
        path = filedialog.askopenfilename(
            title="Select scan video",
            filetypes=[("Video", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*")])
        if path:
            self.video_path.set(path)

    def start_scan(self):
        imperial = self.unit.get() == "imperial"
        height = _to_float(self.height_var.get())
        if not self.video_path.get() or not height:
            self._set_status("Please choose a video and enter height.")
            return

        weight = _to_float(self.weight_var.get())
        age = _to_float(self.age_var.get())

        # convert entered values to metric for the pipeline
        config.USER_HEIGHT_CM = height * CM_PER_IN if imperial else height
        config.GENDER = self.gender_var.get()
        config.USER_WEIGHT_KG = (weight * KG_PER_LB if imperial else weight) if weight else None
        config.USER_AGE = int(age) if age else None

        # calibration from a known clothing size (returns cm, unit-independent)
        part, cm = calibration_from_size(self.calib_chart.get(), self.calib_size.get())
        config.CALIBRATION_PART = part
        config.CALIBRATION_CM = cm

        self.scan_btn.config(state="disabled")
        self._set_status("Scanning... (this takes a minute)")
        threading.Thread(target=self._run, args=(self.video_path.get(),), daemon=True).start()

    def _run(self, video_path):
        try:
            _, _, measurements = run_pipeline(video_path)
            self.root.after(0, self._show_results, measurements)
        except Exception as exc:
            self.root.after(0, self._set_status, f"Error: {exc}")
            self.root.after(0, lambda: self.scan_btn.config(state="normal"))

    def _show_results(self, measurements):
        imperial = self.unit.get() == "imperial"
        lines = []
        for key, value in measurements.items():
            if key in LENGTH_KEYS:
                val = value / CM_PER_IN if imperial else value
                unit = "in" if imperial else "cm"
                lines.append(f"{key:>16}: {val:6.1f} {unit}")
            elif key == "weight_kg":
                val = value / KG_PER_LB if imperial else value
                unit = "lb" if imperial else "kg"
                lines.append(f"{'weight':>16}: {val:6.1f} {unit}")
            elif key == "bmi":
                lines.append(f"{'bmi':>16}: {value:6.1f}")
            else:  # body_fat_% and body_fat_bmi_%
                lines.append(f"{key:>16}: {value:6.1f} %")

        self.results.config(state="normal")
        self.results.delete("1.0", "end")
        self.results.insert("1.0", "\n".join(lines))
        self.results.config(state="disabled")
        self._set_status("Done.")
        self.scan_btn.config(state="normal")

    def _set_status(self, text):
        self.status.config(text=text)


if __name__ == "__main__":
    root = tk.Tk()
    BodyScanApp(root)
    root.mainloop()
