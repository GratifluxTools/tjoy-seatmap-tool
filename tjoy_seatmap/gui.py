"""tkinter製GUI。HAR/ZIP/フォルダを選んで座席表を生成・プレビュー・保存する。"""
from __future__ import annotations

import io
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from . import __version__
from .pipeline import attach_official, load_screens, write_outputs
from .render import render_official_png, render_plain_png


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"T・ジョイ 座席表ジェネレーター {__version__}")
        self.geometry("1120x740")
        self.minsize(860, 560)
        try:
            from .icon_data import PNG_B64
            self._icon = tk.PhotoImage(data=PNG_B64)
            self.iconphoto(True, self._icon)
        except Exception:
            pass
        self.inputs: list[str] = []
        self.schedules: list[str] = []
        self.items = []
        self._photo = None
        self._cancel = False
        self._build()

    # ---- UI ------------------------------------------------------------
    def _build(self):
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=8)
        right.pack(side="right", fill="both", expand=True)

        ttk.Label(left, text="座席HAR / ZIP / フォルダ").pack(anchor="w")
        self.lb_in = tk.Listbox(left, width=46, height=4)
        self.lb_in.pack(fill="x")
        row = ttk.Frame(left)
        row.pack(fill="x", pady=2)
        ttk.Button(row, text="ファイル追加…", command=self.add_files).pack(side="left")
        ttk.Button(row, text="フォルダ追加…", command=self.add_dir).pack(side="left", padx=4)
        ttk.Button(row, text="クリア", command=self.clear).pack(side="left")

        ttk.Label(left, text="スケジュールHAR（任意・作品名の補完）").pack(anchor="w", pady=(4, 0))
        self.lb_sch = tk.Listbox(left, width=46, height=2)
        self.lb_sch.pack(fill="x")
        ttk.Button(left, text="スケジュールを追加…", command=self.add_schedule).pack(anchor="w", pady=2)
        ttk.Button(left, text="座席表を読み込む", command=self.load).pack(fill="x", pady=(6, 2))

        ttk.Label(left, text="検出した画面（チェックで保存対象）").pack(anchor="w", pady=(4, 0))
        self.tree = ttk.Treeview(left, columns=("seats", "official"), show="tree headings", height=9)
        self.tree.heading("#0", text="画面")
        self.tree.heading("seats", text="座席")
        self.tree.heading("official", text="公式画像")
        self.tree.column("#0", width=300)
        self.tree.column("seats", width=56, anchor="e")
        self.tree.column("official", width=70, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.refresh_preview())
        self.tree.bind("<space>", lambda _e: self.toggle_selected())
        self.tree.bind("<Double-1>", lambda _e: self.toggle_selected())
        ttk.Button(left, text="選択中の画面に公式画像を設定…", command=self.set_official).pack(fill="x", pady=2)
        ttk.Button(left, text="公式画像フォルダから一括設定…", command=self.pick_official_dir).pack(fill="x")

        opt = ttk.LabelFrame(left, text="出力オプション", padding=6)
        opt.pack(fill="x", pady=4)
        self.v_official = tk.BooleanVar(value=True)
        self.v_plain = tk.BooleanVar(value=True)
        self.v_obj_on = tk.BooleanVar(value=True)
        self.v_obj_off = tk.BooleanVar(value=True)
        r = ttk.Frame(opt)
        r.pack(anchor="w")
        ttk.Checkbutton(r, text="公式風（公式画像をそのまま）", variable=self.v_official).pack(side="left")
        ttk.Checkbutton(r, text="プレーン", variable=self.v_plain, command=self.refresh_preview).pack(side="left", padx=6)
        self.v_png = tk.BooleanVar(value=True)
        self.v_svg = tk.BooleanVar(value=True)
        self.v_webp = tk.BooleanVar(value=False)
        self.v_title = tk.BooleanVar(value=True)
        self.v_legend = tk.BooleanVar(value=True)
        self.v_scale = tk.DoubleVar(value=2.0)
        r = ttk.Frame(opt)
        r.pack(anchor="w", pady=2)
        ttk.Checkbutton(r, text="PNG", variable=self.v_png).pack(side="left")
        ttk.Checkbutton(r, text="SVG", variable=self.v_svg).pack(side="left", padx=6)
        ttk.Checkbutton(r, text="WebP", variable=self.v_webp).pack(side="left")
        r = ttk.Frame(opt)
        r.pack(anchor="w")
        ttk.Label(r, text="SVGのオブジェクト:").pack(side="left")
        ttk.Checkbutton(r, text="あり", variable=self.v_obj_on).pack(side="left", padx=4)
        ttk.Checkbutton(r, text="なし", variable=self.v_obj_off).pack(side="left")
        ttk.Checkbutton(opt, text="プレーン: タイトル帯", variable=self.v_title, command=self.refresh_preview).pack(anchor="w")
        ttk.Checkbutton(opt, text="プレーン: 凡例", variable=self.v_legend, command=self.refresh_preview).pack(anchor="w")
        r = ttk.Frame(opt)
        r.pack(anchor="w")
        ttk.Label(r, text="プレーンの拡大率").pack(side="left")
        ttk.Spinbox(r, from_=0.5, to=6.0, increment=0.5, width=5, textvariable=self.v_scale).pack(side="left", padx=4)

        ttk.Label(left, text="出力フォルダ").pack(anchor="w")
        r = ttk.Frame(left)
        r.pack(fill="x")
        self.v_out = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "seatmaps"))
        ttk.Entry(r, textvariable=self.v_out).pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="参照…", command=self.pick_out).pack(side="left", padx=4)
        ttk.Button(left, text="保存（チェックした画面）", command=self.save_all).pack(fill="x", pady=(6, 0))

        self.log = tk.Text(left, height=5, width=46, state="disabled", wrap="word")
        self.log.pack(fill="x", pady=(6, 0))

        self.canvas = tk.Canvas(right, bg="#f3f4f6", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.refresh_preview())

    # ---- 操作 ----------------------------------------------------------
    def say(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def add_files(self):
        for f in filedialog.askopenfilenames(title="座席HAR / ZIP を選択",
                                             filetypes=[("HAR/ZIP", "*.har *.zip *.txt"), ("すべて", "*.*")]):
            if f not in self.inputs:
                self.inputs.append(f)
                self.lb_in.insert("end", f)

    def add_dir(self):
        d = filedialog.askdirectory(title="HARを含むフォルダ")
        if d and d not in self.inputs:
            self.inputs.append(d)
            self.lb_in.insert("end", d)

    def add_schedule(self):
        for f in filedialog.askopenfilenames(title="スケジュールHAR を選択",
                                             filetypes=[("HAR/ZIP", "*.har *.zip *.txt"), ("すべて", "*.*")]):
            if f not in self.schedules:
                self.schedules.append(f)
                self.lb_sch.insert("end", f)

    def clear(self):
        self.inputs.clear()
        self.schedules.clear()
        self.lb_in.delete(0, "end")
        self.lb_sch.delete(0, "end")

    def pick_out(self):
        d = filedialog.askdirectory(title="出力フォルダ")
        if d:
            self.v_out.set(d)

    def load(self):
        if not self.inputs:
            messagebox.showinfo("T・ジョイ 座席表", "先にHAR/ZIP/フォルダを追加してください。")
            return
        try:
            res = load_screens(self.inputs, self.schedules)
        except Exception as e:
            messagebox.showerror("読み込みエラー", str(e))
            return
        self.items = res.items
        self._fill_tree()
        for w in res.warnings:
            self.say(f"注意: {w}")
        self.say(f"{len(self.items)}画面を読み込みました。")
        if self.items:
            self.tree.selection_set(self.items[0].key)

    def _fill_tree(self):
        self.tree.delete(*self.tree.get_children())
        for it in self.items:
            mark = "☑ " if it.selected else "☐ "
            self.tree.insert("", "end", iid=it.key, text=mark + it.label,
                             values=(len(it.screen.seats), "あり" if it.official else "なし"))

    def selected_item(self):
        sel = self.tree.selection()
        for it in self.items:
            if sel and it.key == sel[0]:
                return it
        return None

    def toggle_selected(self):
        it = self.selected_item()
        if it:
            it.selected = not it.selected
            self._fill_tree()
            self.tree.selection_set(it.key)

    def set_official(self):
        it = self.selected_item()
        if not it:
            messagebox.showinfo("公式画像", "画面を選んでください。")
            return
        f = filedialog.askopenfilename(title="公式の座席表画像", filetypes=[("画像", "*.png *.jpg *.jpeg"), ("すべて", "*.*")])
        if f:
            with open(f, "rb") as fh:
                it.official = fh.read()
            self.say(f"公式画像を設定: {it.label}")
            self._fill_tree()
            self.tree.selection_set(it.key)
            self.refresh_preview()

    def pick_official_dir(self):
        if not self.items:
            messagebox.showinfo("公式画像", "先に座席表を読み込んでください。")
            return
        d = filedialog.askdirectory(title="公式の座席表画像のフォルダ")
        if not d:
            return
        missing = attach_official(self.items, d)
        for label in missing:
            self.say(f"公式画像が見つかりません: {label}")
        self.say(f"公式画像を設定: {len(self.items) - len(missing)}画面")
        self._fill_tree()
        self.refresh_preview()

    def refresh_preview(self):
        it = self.selected_item()
        if not it:
            return
        cw, ch = max(self.canvas.winfo_width(), 100), max(self.canvas.winfo_height(), 100)
        try:
            if not self.v_plain.get() and it.official is not None:
                img = render_official_png(it.screen, it.official, scale=1.0, show_title=self.v_title.get(),
                                          show_legend=self.v_legend.get())
            elif it.official is None and not self.v_plain.get():
                img = Image.new("RGB", (cw, ch), (243, 244, 246))
            else:
                img = render_plain_png(it.screen, scale=1.0, show_title=self.v_title.get(),
                                       show_legend=self.v_legend.get())
        except Exception as e:
            self.say(f"プレビューに失敗: {e}")
            return
        ratio = min(cw / img.width, ch / img.height, 1.0)
        img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))))
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=self._photo)

    def save_all(self):
        targets = [it for it in self.items if it.selected]
        if not targets:
            messagebox.showinfo("保存", "保存する画面がありません（一覧で ☑ を付けてください）。")
            return
        formats = [f for f, v in (("png", self.v_png), ("svg", self.v_svg), ("webp", self.v_webp)) if v.get()]
        styles = [st for st, v in (("official", self.v_official), ("plain", self.v_plain)) if v.get()]
        objs = [o for o, v in ((True, self.v_obj_on), (False, self.v_obj_off)) if v.get()]
        if not formats or not styles:
            messagebox.showinfo("保存", "出力形式と表示形式を1つ以上選んでください。")
            return
        out = self.v_out.get()
        self._cancel = False
        win = tk.Toplevel(self)
        win.title("画像を保存中")
        win.transient(self)
        v_cur = tk.StringVar(value="準備しています…")
        ttk.Label(win, textvariable=v_cur, width=50).pack(padx=16, pady=(14, 4), anchor="w")
        bar = ttk.Progressbar(win, maximum=len(targets), length=420)
        bar.pack(padx=16, fill="x")
        ttk.Button(win, text="中止", command=lambda: setattr(self, "_cancel", True)).pack(pady=10)

        def progress(name, done, total):
            self.after(0, lambda: (v_cur.set(f"保存中: {name}"), bar.configure(value=done)))

        def worker():
            try:
                written, skipped = write_outputs(targets, out, formats, styles=styles, svg_objects=objs,
                                                 scale=self.v_scale.get(),
                                                 show_title=self.v_title.get(), show_legend=self.v_legend.get(),
                                                 progress=progress, cancelled=lambda: self._cancel)
                self.after(0, lambda: self._done(win, written, skipped))
            except Exception as e:
                self.after(0, lambda: (win.destroy(), messagebox.showerror("保存エラー", str(e))))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, win, written, skipped):
        win.destroy()
        for s in skipped:
            self.say(f"飛ばしました: {s}")
        self.say(f"保存: {len(written)}ファイル → {self.v_out.get()}")
        if self._cancel:
            self.say("中止しました（保存済みのファイルは残ります）。")
        else:
            messagebox.showinfo("保存完了", f"{len(written)}ファイルを保存しました。")


def main():
    App().mainloop()
    return 0
