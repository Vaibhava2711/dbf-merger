"""
DBF Merger — Desktop Tool
Merges multiple .dbf files into one combined output file.

Requirements (install once):
    pip install dbfread dbfwrite pandas

Run:
    python dbf_merger.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from datetime import datetime

# ── auto-install deps if missing ──────────────────────────────────────────────
def _ensure(pkg, import_as=None):
    import importlib, subprocess, sys
    try:
        importlib.import_module(import_as or pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

_ensure("dbfread")
_ensure("dbfwrite")
_ensure("pandas")

from dbfread import DBF
from dbfwrite import dftodbf   # the actual module that has the function
import pandas as pd

def write_dbf(df, path):
    """Write a DataFrame to a .dbf file using dbfwrite."""
    dftodbf.dbfwrite(df, path)

# ─── Color palette ────────────────────────────────────────────────────────────
BG          = "#F7F7F5"
SURFACE     = "#FFFFFF"
BORDER      = "#DDDBD4"
TEXT        = "#1A1A18"
TEXT_MUTED  = "#6B6A66"
ACCENT      = "#2563EB"
ACCENT_DARK = "#1D4ED8"
SUCCESS     = "#16A34A"
DANGER      = "#DC2626"
ROW_ALT     = "#F1F0EC"


class DBFMergerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DBF Merger")
        self.geometry("800x620")
        self.minsize(640, 480)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.files = []
        self.output_path = tk.StringVar(value="")
        self.status_var  = tk.StringVar(value="Add .dbf files to get started.")
        self._build_ui()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=ACCENT, padx=20, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="DBF Merger", font=("Segoe UI", 16, "bold"),
                 bg=ACCENT, fg="white").pack(side="left")
        tk.Label(header, text="Combine multiple .dbf files into one",
                 font=("Segoe UI", 10), bg=ACCENT, fg="#BFDBFE").pack(
                     side="left", padx=(12, 0), pady=(3, 0))

        body = tk.Frame(self, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Section: Input files
        self._section_label(body, "Input files")

        list_frame = tk.Frame(body, bg=SURFACE, relief="flat",
                              highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(fill="both", expand=True, pady=(4, 0))

        cols = ("filename", "records", "fields", "path")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                 selectmode="extended", height=12)
        self._style_tree()
        self.tree.heading("filename", text="File name")
        self.tree.heading("records",  text="Records")
        self.tree.heading("fields",   text="Fields")
        self.tree.heading("path",     text="Full path")
        self.tree.column("filename", width=200, minwidth=120)
        self.tree.column("records",  width=80,  minwidth=60,  anchor="e")
        self.tree.column("fields",   width=60,  minwidth=50,  anchor="e")
        self.tree.column("path",     width=380, minwidth=160)

        vsb = ttk.Scrollbar(list_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.hint = tk.Label(list_frame,
                             text="Click  ＋ Add files  below to choose .dbf files",
                             font=("Segoe UI", 10), fg=TEXT_MUTED, bg=SURFACE)
        self.hint.place(relx=0.5, rely=0.5, anchor="center")

        # File action buttons
        btn_row = tk.Frame(body, bg=BG, pady=8)
        btn_row.pack(fill="x")
        self._btn(btn_row, "＋  Add files",       self._add_files,      primary=True).pack(side="left", padx=(0,6))
        self._btn(btn_row, "↑  Move up",           self._move_up).pack(side="left", padx=(0,6))
        self._btn(btn_row, "↓  Move down",         self._move_down).pack(side="left", padx=(0,6))
        self._btn(btn_row, "✕  Remove selected",   self._remove_selected).pack(side="left", padx=(0,6))
        self._btn(btn_row, "Clear all",            self._clear_all).pack(side="left")

        # Section: Output
        self._section_label(body, "Output file")

        out_row = tk.Frame(body, bg=BG, pady=4)
        out_row.pack(fill="x")
        self.out_entry = tk.Entry(out_row, textvariable=self.output_path,
                                  font=("Segoe UI", 10), bg=SURFACE, fg=TEXT,
                                  relief="flat", highlightbackground=BORDER,
                                  highlightthickness=1)
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0,8))
        self._btn(out_row, "Browse…", self._browse_output).pack(side="left")

        # Bottom bar
        bottom = tk.Frame(body, bg=BG, pady=10)
        bottom.pack(fill="x")
        self.merge_btn = self._btn(bottom, "  Merge  →  ", self._start_merge,
                                   primary=True, big=True)
        self.merge_btn.pack(side="left")

        self.status_lbl = tk.Label(bottom, textvariable=self.status_var,
                                   font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG)
        self.status_lbl.pack(side="left", padx=14)

        self.progress = ttk.Progressbar(body, mode="indeterminate", length=300)

    def _section_label(self, parent, text):
        tk.Label(parent, text=text.upper(), font=("Segoe UI", 8, "bold"),
                 fg=TEXT_MUTED, bg=BG, pady=6).pack(anchor="w")

    def _style_tree(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview",
                        background=SURFACE, fieldbackground=SURFACE,
                        foreground=TEXT, rowheight=26,
                        font=("Segoe UI", 9), borderwidth=0)
        style.configure("Treeview.Heading",
                        background=BG, foreground=TEXT_MUTED,
                        font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Treeview",
                  background=[("selected", "#DBEAFE")],
                  foreground=[("selected", "#1E3A8A")])
        self.tree.tag_configure("odd",  background=SURFACE)
        self.tree.tag_configure("even", background=ROW_ALT)

    def _btn(self, parent, text, cmd, primary=False, big=False):
        bg  = ACCENT    if primary else SURFACE
        fg  = "white"   if primary else TEXT
        abg = ACCENT_DARK if primary else ROW_ALT
        btn = tk.Button(parent, text=text, command=cmd,
                        font=("Segoe UI", 10 if big else 9),
                        bg=bg, fg=fg, activebackground=abg,
                        activeforeground=fg, relief="flat",
                        padx=14, pady=8 if big else 5,
                        cursor="hand2", highlightthickness=1,
                        highlightbackground=BORDER)
        btn.bind("<Enter>", lambda e: btn.config(bg=abg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    # ─── File management ─────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select DBF files",
            filetypes=[("dBASE files", "*.dbf *.DBF"), ("All files", "*.*")])
        added = 0
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                added += 1
        if added:
            self._refresh_tree()
            self._set_default_output()
            self.status_var.set(f"{len(self.files)} file(s) loaded.")

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.files:
            self.hint.place_forget()
        else:
            self.hint.place(relx=0.5, rely=0.5, anchor="center")
            return
        for i, path in enumerate(self.files):
            fname = os.path.basename(path)
            try:
                tbl     = DBF(path, load=True, ignore_missing_memofile=True)
                records = len(tbl)
                fields  = len(tbl.fields)
            except Exception:
                records, fields = "?", "?"
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(i),
                             values=(fname, records, fields, path), tags=(tag,))

    def _set_default_output(self):
        if not self.output_path.get() and self.files:
            folder = os.path.dirname(self.files[0])
            ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_path.set(os.path.join(folder, f"merged_{ts}.dbf"))

    def _remove_selected(self):
        selected = sorted([int(iid) for iid in self.tree.selection()], reverse=True)
        if not selected:
            return
        for idx in selected:
            del self.files[idx]
        self._refresh_tree()
        self.status_var.set(f"{len(self.files)} file(s) remaining.")

    def _clear_all(self):
        self.files.clear()
        self._refresh_tree()
        self.output_path.set("")
        self.status_lbl.config(fg=TEXT_MUTED)
        self.status_var.set("Add .dbf files to get started.")

    def _move_up(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx > 0:
            self.files[idx], self.files[idx-1] = self.files[idx-1], self.files[idx]
            self._refresh_tree()
            self.tree.selection_set(str(idx-1))

    def _move_down(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self.files) - 1:
            self.files[idx], self.files[idx+1] = self.files[idx+1], self.files[idx]
            self._refresh_tree()
            self.tree.selection_set(str(idx+1))

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save merged DBF as",
            defaultextension=".dbf",
            filetypes=[("dBASE files", "*.dbf")])
        if path:
            self.output_path.set(path)

    # ─── Merge logic ─────────────────────────────────────────────────────────

    def _start_merge(self):
        if not self.files:
            messagebox.showwarning("No files", "Please add at least one .dbf file.")
            return
        out = self.output_path.get().strip()
        if not out:
            messagebox.showwarning("No output", "Please set an output file path.")
            return
        self.merge_btn.config(state="disabled")
        self.progress.pack(fill="x", pady=(0, 4))
        self.progress.start(12)
        self.status_lbl.config(fg=TEXT_MUTED)
        self.status_var.set("Merging…")
        threading.Thread(target=self._merge_worker, daemon=True).start()

    def _merge_worker(self):
        try:
            out_path = self.output_path.get().strip()
            frames = []
            for path in self.files:
                tbl = DBF(path, load=True, ignore_missing_memofile=True)
                df  = pd.DataFrame(iter(tbl))
                frames.append(df)

            if not frames:
                raise ValueError("No data found in any input file.")

            merged = pd.concat(frames, ignore_index=True)

            # Ensure column names are plain strings (dbfwrite needs that)
            merged.columns = [str(c) for c in merged.columns]

            write_dbf(merged, out_path)

            total = len(merged)
            self.after(0, self._merge_done, True,
                       f"Done! {total:,} records merged → {os.path.basename(out_path)}")
        except Exception as exc:
            self.after(0, self._merge_done, False, f"Error: {exc}")

    def _merge_done(self, success, message):
        self.progress.stop()
        self.progress.pack_forget()
        self.merge_btn.config(state="normal")
        self.status_lbl.config(fg=SUCCESS if success else DANGER)
        self.status_var.set(message)
        if success:
            if messagebox.askyesno("Merge complete",
                                   f"{message}\n\nOpen containing folder?"):
                self._open_folder(os.path.dirname(self.output_path.get()))

    def _open_folder(self, folder):
        import subprocess, sys
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])


if __name__ == "__main__":
    app = DBFMergerApp()
    app.mainloop()