import ctypes
import threading
import time
import customtkinter as ctk
from pynput import mouse

# Cấu hình giao diện CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Khai báo hằng số Win32 API
MOUSEEVENTF_MOVE = 0x0001
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02

class RecoilAssistApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Recoil Control Pro")
        self.geometry("400x420")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        # --- BIẾN TRẠNG THÁI & CẤU HÌNH ---
        self.is_enabled = True
        self.side_button_held = False

        # Thông số ghìm tâm dọc duy nhất
        self.pull_speed_pps = 15.0      # Lực ghìm dọc (Pixels / giây)
        self.scroll_step = 0.15         # Bước nhảy mỗi nấc lăn chuột

        # Bộ tích lũy Sub-pixel
        self.accum_y = 0.0

        # Khởi tạo UI
        self._build_ui()

        # Khởi chạy luồng xử lý ghìm tâm tốc độ cao
        self.running = True
        self.worker_thread = threading.Thread(target=self._recoil_loop, daemon=True)
        self.worker_thread.start()

        # Khởi chạy bộ lắng nghe sự kiện chuột
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()

    # ==========================================
    # GIAO DIỆN NGƯỜI DÙNG (UI TỐI GIẢN)
    # ==========================================
    def _build_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_lbl = ctk.CTkLabel(header_frame, text="RECOIL CONTROL", font=ctk.CTkFont(size=18, weight="bold"))
        title_lbl.pack(side="left")

        self.status_switch = ctk.CTkSwitch(
            header_frame, text="BẬT", font=ctk.CTkFont(weight="bold"),
            command=self._toggle_tool, progress_color="#2ecc71"
        )
        self.status_switch.select()
        self.status_switch.pack(side="right")

        # Khung hiển thị Lực Ghìm chính (Big Readout)
        readout_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1e272e")
        readout_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(readout_frame, text="LỰC GHÌM DỌC (Y-AXIS)", font=ctk.CTkFont(size=11), text_color="#808e9b").pack(pady=(12, 0))
        self.lbl_pps_big = ctk.CTkLabel(
            readout_frame, text=f"{self.pull_speed_pps:.2f} px/s",
            font=ctk.CTkFont(size=32, weight="bold"), text_color="#0fbcf9"
        )
        self.lbl_pps_big.pack(pady=(0, 5))
        
        hint_lbl = ctk.CTkLabel(
            readout_frame, text="💡 Giữ nút Hông Chuột + Lăn Lên/Xuống để chỉnh nhanh",
            font=ctk.CTkFont(size=11, slant="italic"), text_color="#ffa801"
        )
        hint_lbl.pack(pady=(0, 12))

        # Khung điều chỉnh slider
        controls_frame = ctk.CTkFrame(self, corner_radius=12)
        controls_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Thanh trượt Lực Ghìm Dọc (px/s)
        self.slider_pps, self.val_pps = self._create_slider_row(
            controls_frame, "Tốc độ kéo dọc (px/s):", 0.0, 900.0, self.pull_speed_pps, self._on_slider_pps
        )

        # Cài đặt dưới cùng (Pin cửa sổ)
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(5, 20))

        self.topmost_chk = ctk.CTkCheckBox(
            bottom_frame, text="Luôn nổi trên cửa sổ khác (Topmost)", command=self._toggle_topmost, font=ctk.CTkFont(size=12)
        )
        self.topmost_chk.select()
        self.topmost_chk.pack(side="left")

    def _create_slider_row(self, parent, label_text, min_val, max_val, init_val, callback):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=15)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x")

        lbl = ctk.CTkLabel(top, text=label_text, font=ctk.CTkFont(size=12, weight="bold"))
        lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(top, text=f"{init_val:.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00d8d6")
        val_lbl.pack(side="right")

        slider = ctk.CTkSlider(row, from_=min_val, to=max_val, command=callback)
        slider.set(init_val)
        slider.pack(fill="x", pady=(8, 0))

        return slider, val_lbl

    # ==========================================
    # SỰ KIỆN GIAO DIỆN (CALLBACKS)
    # ==========================================
    def _toggle_tool(self):
        self.is_enabled = bool(self.status_switch.get())

    def _toggle_topmost(self):
        self.attributes("-topmost", bool(self.topmost_chk.get()))

    def _on_slider_pps(self, val):
        self.pull_speed_pps = round(float(val), 2)
        self.val_pps.configure(text=f"{self.pull_speed_pps:.2f}")
        self.lbl_pps_big.configure(text=f"{self.pull_speed_pps:.2f} px/s")

    def _update_pps_display_from_hotkey(self):
        self.slider_pps.set(self.pull_speed_pps)
        self.val_pps.configure(text=f"{self.pull_speed_pps:.2f}")
        self.lbl_pps_big.configure(text=f"{self.pull_speed_pps:.2f} px/s")

    # ==========================================
    # LẮNG NGHE NÚT HÔNG & CON LĂN CHUỘT
    # ==========================================
    def _on_mouse_click(self, x, y, button, pressed):
        if button in (mouse.Button.x1, mouse.Button.x2):
            self.side_button_held = pressed

    def _on_mouse_scroll(self, x, y, dx, dy):
        if self.side_button_held:
            if dy > 0:
                self.pull_speed_pps = min(900.0, round(self.pull_speed_pps + self.scroll_step, 2))
            elif dy < 0:
                self.pull_speed_pps = max(0.0, round(self.pull_speed_pps - self.scroll_step, 2))
            
            self.after(0, self._update_pps_display_from_hotkey)

    # ==========================================
    # ENGINE GHÌM TÂM (WIN32 API + SUB-PIXEL)
    # ==========================================
    def _is_ads_and_firing(self):
        lmb = ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000
        rmb = ctypes.windll.user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000
        return bool(lmb and rmb)

    def _move_mouse_relative(self, dy: int):
        if dy != 0:
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, 0, int(dy), 0, 0)

    def _recoil_loop(self):
        last_time = time.perf_counter()

        while self.running:
            now = time.perf_counter()
            dt = now - last_time
            last_time = now

            if self.is_enabled and self._is_ads_and_firing():
                # Tích lũy quãng đường theo thời gian thực (dt)
                self.accum_y += self.pull_speed_pps * dt

                move_y = int(self.accum_y)
                if move_y != 0:
                    self._move_mouse_relative(move_y)
                    self.accum_y -= move_y

                # Tần số quét cao mượt mà, tối ưu hóa độ trễ thấp nhất
                time.sleep(0.001)
            else:
                self.accum_y = 0.0
                time.sleep(0.005)

    def on_closing(self):
        self.running = False
        self.mouse_listener.stop()
        self.destroy()

if __name__ == "__main__":
    app = RecoilAssistApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
