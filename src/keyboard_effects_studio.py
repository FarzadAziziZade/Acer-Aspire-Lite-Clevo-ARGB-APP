from __future__ import annotations

import colorsys
import ctypes
from ctypes import wintypes
import json
import math
import os
import random
import struct
import sys
import time
from pathlib import Path

APP_NAME = "Keyboard Effects Studio"
COMMAND_SET_KEYBOARD = 103
WM_APP = 0x8000
WM_COMMAND = 0x0111
WM_USER = 0x0400
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
MF_STRING = 0x00000000
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256), ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wintypes.HICON),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / name


def app_folder() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


if getattr(sys, "frozen", False):
    os.environ.setdefault("TCL_LIBRARY", str(resource_path("_tcl_data")))
    os.environ.setdefault("TK_LIBRARY", str(resource_path("_tk_data")))

import tkinter as tk
from tkinter import colorchooser, messagebox, ttk


def pack_color(red: int, green: int, blue: int) -> bytes:
    # Clevo single-zone dword layout: F0, blue, red, green.
    value = 0xF0000000 | ((blue & 255) << 16) | ((red & 255) << 8) | (green & 255)
    return struct.pack("<I", value)


class KeyboardDriver:
    def __init__(self) -> None:
        path = resource_path("vendor/InsydeDCHU.dll")
        if not path.is_file():
            raise FileNotFoundError("Bundled InsydeDCHU.dll is missing.")
        self._dll_directory = os.add_dll_directory(str(path.parent))
        self.dll = ctypes.WinDLL(str(path), use_last_error=True)
        self.set_data = self.dll.SetDCHU_Data
        self.set_data.restype = ctypes.c_uint32
        self.set_data.argtypes = [
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint32,
        ]

    def set_color(self, rgb: tuple[int, int, int]) -> int:
        payload = (ctypes.c_uint8 * 4).from_buffer_copy(pack_color(*rgb))
        return int(self.set_data(COMMAND_SET_KEYBOARD, payload, 4))


class EffectsApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(APP_NAME)
        try:
            root.iconbitmap(str(resource_path("keyboard-effects-studio.ico")))
        except tk.TclError:
            pass
        root.geometry("820x700")
        root.minsize(760, 650)
        root.configure(bg="#0B1020")
        self.driver: KeyboardDriver | None = None
        self.after_id: str | None = None
        self.phase = 0.0
        self.last_frame = 0.0
        self.primary = "#37D6C0"
        self.secondary = "#8267FF"
        self.effect = tk.StringVar(value="Spectrum cycle")
        self.speed = tk.IntVar(value=5)
        self.intensity = tk.IntVar(value=85)
        self.status = tk.StringVar(value="Connect to load the keyboard controller.")
        self.settings_path = app_folder() / "settings.json"
        self.tray_icon_added = False
        self._wndproc_callback = None
        self._old_wndproc = None
        self._load_settings()
        self._build()
        self._install_tray_icon()

    def _load_settings(self) -> None:
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self.primary = str(data.get("primary", self.primary))
            self.secondary = str(data.get("secondary", self.secondary))
            self.effect.set(str(data.get("effect", self.effect.get())))
            self.speed.set(max(1, min(10, int(data.get("speed", 5)))))
            self.intensity.set(max(5, min(100, int(data.get("intensity", 85)))))
        except (OSError, ValueError, TypeError):
            pass

    def _save_settings(self) -> None:
        data = {
            "primary": self.primary,
            "secondary": self.secondary,
            "effect": self.effect.get(),
            "speed": self.speed.get(),
            "intensity": self.intensity.get(),
        }
        try:
            self.settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _build(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground="#202A40", background="#202A40", foreground="#F9FAFB",
                        padding=7, arrowsize=14)
        style.map("TCombobox", fieldbackground=[("readonly", "#202A40")],
                  foreground=[("readonly", "#F9FAFB")])
        style.configure("Horizontal.TScale", background="#172136", troughcolor="#344154")

        page = tk.Frame(self.root, bg="#0B1020", padx=30, pady=24)
        page.pack(fill="both", expand=True)
        self.hero = tk.Canvas(page, height=112, bg="#172136", highlightthickness=0, bd=0)
        self.hero.pack(fill="x", pady=(0, 22))
        self.hero.bind("<Configure>", self._draw_hero)

        self._section(page, "1   CONNECT")
        box = tk.Frame(page, bg="#172136", padx=18, pady=16,
                       highlightthickness=1, highlightbackground="#26334D")
        box.pack(fill="x", pady=(6, 14))
        self.connect_button = self._button(box, "Connect", self.connect, "#22D3EE", "#082F49")
        self.connect_button.pack(side="left")
        tk.Label(box, textvariable=self.status, bg="#172136", fg="#D1D5DB",
                 anchor="w", justify="left", wraplength=510, font=("Segoe UI", 9)
                 ).pack(side="left", padx=(14, 0), fill="x", expand=True)

        self._section(page, "2   CHOOSE AN EFFECT")
        panel = tk.Frame(page, bg="#172136", padx=18, pady=18,
                         highlightthickness=1, highlightbackground="#26334D")
        panel.pack(fill="x", pady=(6, 14))
        tk.Label(panel, text="Effect", bg="#172136", fg="#CBD5E1",
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=5)
        self.effect_box = ttk.Combobox(
            panel, textvariable=self.effect, state="disabled", width=25,
            values=("Spectrum cycle", "Breathing", "Two-color fade", "Color pulse", "Random color", "Solid color")
        )
        self.effect_box.grid(row=0, column=1, sticky="w", pady=5)
        self._color_picker(panel, 1, "Primary color", "primary")
        self._color_picker(panel, 2, "Second color", "secondary")

        tk.Label(panel, text="Speed", bg="#172136", fg="#CBD5E1",
                 font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", padx=(0, 12), pady=(10, 4))
        self.speed_scale = ttk.Scale(panel, from_=1, to=10, variable=self.speed, orient="horizontal")
        self.speed_scale.grid(row=3, column=1, sticky="ew", pady=(10, 4))
        self.speed_label = tk.Label(panel, textvariable=self.speed, bg="#172136", fg="#C4B5FD", width=3,
                                    font=("Segoe UI", 10, "bold"))
        self.speed_label.grid(row=3, column=2, padx=(6, 0), pady=(10, 4))

        tk.Label(panel, text="Brightness", bg="#172136", fg="#CBD5E1",
                 font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", padx=(0, 12), pady=4)
        self.brightness_scale = ttk.Scale(panel, from_=5, to=100, variable=self.intensity, orient="horizontal")
        self.brightness_scale.grid(row=4, column=1, sticky="ew", pady=4)
        self.brightness_label = tk.Label(panel, text=f"{self.intensity.get()}%", bg="#172136",
                                         fg="#C4B5FD", width=5, font=("Segoe UI", 10, "bold"))
        self.brightness_label.grid(row=4, column=2, padx=(6, 0), pady=4)
        self.intensity.trace_add("write", lambda *_: self.brightness_label.configure(
            text=f"{self.intensity.get()}%"))
        self.speed.trace_add("write", lambda *_: self.speed_label.configure(
            text=str(self.speed.get())))
        panel.grid_columnconfigure(1, weight=1)

        actions = tk.Frame(page, bg="#0B1020")
        actions.pack(fill="x", pady=(2, 14))
        self.start_button = self._button(actions, "Start effect", self.start, "#A855F7", "#FFFFFF")
        self.start_button.pack(side="left")
        self.stop_button = self._button(actions, "Stop animation", self.stop, "#374151", "#F9FAFB")
        self.stop_button.pack(side="left", padx=9)
        self.off_button = self._button(actions, "Turn keyboard off", self.turn_off, "#7F1D1D", "#FEE2E2")
        self.off_button.pack(side="left")
        self._set_controls(False)

        footer = tk.Frame(page, bg="#111A2C", padx=16, pady=13,
                          highlightthickness=1, highlightbackground="#26334D")
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text=("Closing this window keeps the effect running in the notification area. "
                  "Use its tray menu to reopen or exit. Close the stock LED Keyboard Setting app before connecting."),
            bg="#111A2C", fg="#9AA8BE", justify="left", wraplength=720,
            font=("Segoe UI", 9)
        ).pack(anchor="w")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _section(self, parent: tk.Widget, text: str) -> None:
        label = tk.Label(parent, text=text, bg="#0B1020", fg="#A78BFA",
                         font=("Segoe UI", 9, "bold"))
        label.pack(anchor="w")

    def _draw_hero(self, _event=None) -> None:
        canvas = self.hero
        width = max(2, canvas.winfo_width())
        height = max(2, canvas.winfo_height())
        stops = ((239, 68, 68), (249, 115, 22), (250, 204, 21), (34, 197, 94),
                 (6, 182, 212), (59, 130, 246), (168, 85, 247), (236, 72, 153))
        canvas.delete("all")
        for x in range(width):
            position = x / max(1, width - 1) * (len(stops) - 1)
            index = min(len(stops) - 2, int(position))
            blend = position - index
            rgb = tuple(round(a + (b - a) * blend) for a, b in zip(stops[index], stops[index + 1]))
            canvas.create_line(x, 0, x, height, fill="#%02X%02X%02X" % rgb)
        canvas.create_rectangle(0, 0, width, height, fill="#0C1425", stipple="gray50", outline="")
        canvas.create_text(26, 35, anchor="w", text="KEYBOARD EFFECTS STUDIO",
                           fill="#FFFFFF", font=("Segoe UI", 20, "bold"))
        canvas.create_text(28, 72, anchor="w", text="COLOR PLAY FOR YOUR CLEVO KEYBOARD",
                           fill="#E2E8F0", font=("Segoe UI", 9, "bold"))
        canvas.create_text(width - 24, 35, anchor="e", text="RGB  •  6 EFFECTS",
                           fill="#FFFFFF", font=("Segoe UI", 9, "bold"))

    def _button(self, parent: tk.Widget, text: str, command, bg: str, fg: str) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=bg, activeforeground=fg, relief="flat",
                         padx=17, pady=11, font=("Segoe UI", 9, "bold"), cursor="hand2", bd=0)

    def _color_picker(self, parent: tk.Widget, row: int, label: str, attr: str) -> None:
        tk.Label(parent, text=label, bg="#172136", fg="#CBD5E1",
                 font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        button = tk.Button(parent, text="  Choose color", width=17, bg=getattr(self, attr), fg="#0B1020",
                           activebackground=getattr(self, attr), relief="flat", bd=0,
                           font=("Segoe UI", 9, "bold"),
                           command=lambda: self.pick_color(attr), cursor="hand2")
        button.grid(row=row, column=1, sticky="w", pady=5)
        setattr(self, f"{attr}_button", button)

    def _set_controls(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in (self.start_button, self.stop_button, self.off_button,
                       self.primary_button, self.secondary_button):
            button.configure(state=state)
        self.effect_box.configure(state="readonly" if enabled else "disabled")
        self.speed_scale.configure(state=state)
        self.brightness_scale.configure(state=state)

    def connect(self) -> None:
        try:
            self.driver = KeyboardDriver()
        except (OSError, AttributeError) as exc:
            self.status.set("The vendor keyboard interface could not be loaded.")
            messagebox.showerror("Keyboard controller unavailable",
                                 f"Could not load InsydeDCHU.dll:\n\n{exc}", parent=self.root)
            return
        self.connect_button.configure(state="disabled", text="Connected")
        self.status.set("Driver loaded. Start an effect to send the first color frame.")
        self._set_controls(True)

    def pick_color(self, attr: str) -> None:
        chosen = colorchooser.askcolor(color=getattr(self, attr), title=f"Choose {attr} color", parent=self.root)
        if chosen[1]:
            setattr(self, attr, chosen[1].upper())
            button = getattr(self, f"{attr}_button")
            button.configure(bg=chosen[1], activebackground=chosen[1])
            self._save_settings()

    def _rgb(self, color: str) -> tuple[int, int, int]:
        value = color.lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

    def _scaled(self, rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        gain = max(0.0, min(1.0, amount)) * self.intensity.get() / 100.0
        return tuple(max(0, min(255, round(channel * gain))) for channel in rgb)

    def _send(self, rgb: tuple[int, int, int]) -> None:
        if self.driver is None:
            raise RuntimeError("Connect to the keyboard first.")
        self.driver.set_color(rgb)

    def start(self) -> None:
        self.stop()
        self.phase = 0.0
        self.last_frame = 0.0
        self.status.set(f"Running {self.effect.get()}...")
        self._save_settings()
        self._tick()

    def stop(self) -> None:
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        if self.driver is not None:
            self.status.set("Animation stopped; the last color remains on.")
        self._save_settings()

    def turn_off(self) -> None:
        self.stop()
        try:
            self._send((0, 0, 0))
            self.status.set("Keyboard lighting turned off.")
        except Exception as exc:
            self._error(exc)

    def _tick(self) -> None:
        now = time.monotonic()
        speed = max(1, min(10, self.speed.get()))
        self.phase = (self.phase + 0.012 + speed * 0.006) % 1.0
        primary = self._rgb(self.primary)
        secondary = self._rgb(self.secondary)
        mode = self.effect.get()
        try:
            if mode == "Solid color":
                color = self._scaled(primary, 1.0)
            elif mode == "Spectrum cycle":
                hsv = colorsys.hsv_to_rgb(self.phase, 1.0, 1.0)
                color = self._scaled(tuple(round(c * 255) for c in hsv), 1.0)
            elif mode == "Breathing":
                level = 0.10 + 0.90 * (0.5 + 0.5 * math.sin(self.phase * math.tau))
                color = self._scaled(primary, level)
            elif mode == "Two-color fade":
                mix = 0.5 + 0.5 * math.sin(self.phase * math.tau)
                color = self._scaled(tuple(round(a + (b - a) * mix)
                                           for a, b in zip(primary, secondary)), 1.0)
            elif mode == "Color pulse":
                level = 0.12 + 0.88 * max(0.0, math.sin(self.phase * math.tau))
                color = self._scaled(primary, level)
            elif mode == "Random color":
                if now - self.last_frame >= max(0.12, 0.65 - speed * 0.05):
                    color = self._scaled(tuple(random.randint(40, 255) for _ in range(3)), 1.0)
                    self.last_frame = now
                else:
                    color = None
            else:
                color = self._scaled(primary, 1.0)

            if color is not None:
                self._send(color)
            self.after_id = self.root.after(max(45, 150 - speed * 10), self._tick)
        except Exception as exc:
            self.stop()
            self._error(exc)

    def _error(self, exc: Exception) -> None:
        self.status.set(f"LED command failed: {exc}")
        messagebox.showerror(
            "LED command failed",
            "The controller did not accept a color frame.\n\n"
            f"{exc}\n\nClose the stock LED utility, restart this app, and try again.",
            parent=self.root,
        )

    def close(self) -> None:
        if self.tray_icon_added:
            self.root.withdraw()
            self.status.set("Running in the notification area. Right-click the tray icon to reopen or exit.")
            return
        self._exit()

    def _install_tray_icon(self) -> None:
        if os.name != "nt":
            return
        self.hwnd = wintypes.HWND(self.root.winfo_id())
        self.tray_message = WM_APP + 41
        self.tray_data = NOTIFYICONDATAW()
        self.tray_data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.tray_data.hWnd = self.hwnd
        self.tray_data.uID = 1
        self.tray_data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.tray_data.uCallbackMessage = self.tray_message
        self.tray_icon = ctypes.windll.user32.LoadImageW(
            None, str(resource_path("keyboard-effects-studio.ico")), 1, 0, 0, 0x0010
        )
        if not self.tray_icon:
            self._restore_wndproc()
            return
        self.tray_data.hIcon = self.tray_icon
        self.tray_data.szTip = APP_NAME

        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                                           wintypes.WPARAM, wintypes.LPARAM)
        self._wndproc_callback = callback_type(self._tray_wndproc)
        set_proc = ctypes.windll.user32.SetWindowLongPtrW
        set_proc.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        set_proc.restype = ctypes.c_void_p
        self._old_wndproc = set_proc(self.hwnd, -4, ctypes.cast(self._wndproc_callback, ctypes.c_void_p))
        shell = ctypes.windll.shell32
        shell.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
        shell.Shell_NotifyIconW.restype = wintypes.BOOL
        self.tray_icon_added = bool(shell.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.tray_data)))
        if not self.tray_icon_added:
            self._restore_wndproc()

    def _tray_wndproc(self, hwnd, message, wparam, lparam):
        if message == self.tray_message:
            if lparam == WM_LBUTTONDBLCLK:
                self.root.after(0, self._show_window)
                return 0
            if lparam == WM_RBUTTONUP:
                self.root.after(0, self._show_tray_menu)
                return 0
        if message == WM_COMMAND:
            command = wparam & 0xFFFF
            if command == 1001:
                self.root.after(0, self._show_window)
                return 0
            if command == 1002:
                self.root.after(0, self._exit)
                return 0
        call_proc = ctypes.windll.user32.CallWindowProcW
        call_proc.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                              wintypes.WPARAM, wintypes.LPARAM]
        call_proc.restype = ctypes.c_ssize_t
        return call_proc(
            self._old_wndproc, hwnd, message, wparam, lparam
        )

    def _show_tray_menu(self) -> None:
        menu = ctypes.windll.user32.CreatePopupMenu()
        ctypes.windll.user32.AppendMenuW(menu, MF_STRING, 1001, "Open Keyboard Effects Studio")
        ctypes.windll.user32.AppendMenuW(menu, MF_STRING, 1002, "Exit")
        point = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        ctypes.windll.user32.SetForegroundWindow(self.hwnd)
        command = ctypes.windll.user32.TrackPopupMenu(
            menu, TPM_RETURNCMD | TPM_RIGHTBUTTON, point.x, point.y, 0, self.hwnd, None
        )
        ctypes.windll.user32.DestroyMenu(menu)
        if command == 1001:
            self._show_window()
        elif command == 1002:
            self._exit()

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _restore_wndproc(self) -> None:
        if self._old_wndproc:
            restore = ctypes.windll.user32.SetWindowLongPtrW
            restore.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            restore.restype = ctypes.c_void_p
            restore(self.hwnd, -4, self._old_wndproc)
            self._old_wndproc = None

    def _exit(self) -> None:
        self.stop()
        if self.tray_icon_added:
            ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.tray_data))
            self.tray_icon_added = False
        self._restore_wndproc()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    EffectsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

