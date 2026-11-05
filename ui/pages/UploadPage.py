import customtkinter as ctk
from tkinter import PhotoImage, filedialog, messagebox
from tkinterdnd2 import DND_FILES
from pathlib import Path
import threading
from datetime import datetime

from core.processor import remove_backgrounds, apply_templates, process_mode_logo
from core.history import find_previous_runs, mark_incomplete
from core.cancel import ProcessCancelled, check_cancel, claim_folders, release_folders, is_folder_active
from config import OUTPUT_DIR, TEMPLATE_DIR

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class UploadPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.grid_rowconfigure(2, weight=2)
        self.grid_columnconfigure(4, weight=1)

        self.source_paths = []
        self.cancel_event = threading.Event()
        self.is_running = False

        self.logo_image = PhotoImage(file=BASE_DIR / "assets" / "logo.png")
        self.logo_image = self.logo_image.subsample(2, 2)
        self.logo_append = ctk.CTkLabel(self, image=self.logo_image, text="")
        self.logo_append.grid(row=0, column=0, padx=20, pady=20)

        self.label = ctk.CTkLabel(self, text="Upload Image", font=ctk.CTkFont(size=30, weight="bold"))
        self.label.grid(row=0, column=1, padx=0, pady=20)

        self.reset_button = ctk.CTkButton(self, text="Reset Folder", command=self.reset_folders, fg_color="#E74C3C", hover_color="#C0392B")
        self.reset_button.grid(row=1, column=0, padx=20, pady=20)

        self.home_button = ctk.CTkButton(self, text="Back to Home", command=lambda: parent.show_page("home"))
        self.home_button.grid(row=1, column=1, padx=20, pady=20)

        self.upload_button = ctk.CTkButton(self, text="Pilih Folder Gambar", command=self.select_source_folder)
        self.upload_button.grid(row=1, column=2, padx=20, pady=20)

        self._dnd_registered = False

        self.choose_button = ctk.CTkButton(self, text="Pilih Template", command=self.open_template_dialog)
        self.choose_button.grid(row=1, column=3, padx=20, pady=20)

        self.process_button = ctk.CTkButton(self, text="Mulai Proses", command=self.start_processing, fg_color="green", hover_color="darkgreen")
        self.process_button.grid(row=1, column=4, padx=20, pady=20)

        self.upload_frame = FrameUpload(self)
        self.upload_frame.grid(row=2,
                               column=0, 
                               columnspan=5, 
                               padx=20, 
                               pady=20, 
                               sticky="nsew"
                               )

        self.upload_frame.cancel_button.configure(command=self.cancel_processing)

        self.upload_frame.drop_target_register(DND_FILES)
        self.upload_frame.dnd_bind('<<Drop>>', self.handle_drop)
        self.upload_frame.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.upload_frame.dnd_bind('<<DragLeave>>', self.on_drag_leave)

    def open_template_dialog(self):
        self.dialog = TemplateSelectionDialog(self)
    
    def update_selected_label(self):
        self.selected_templates_list = self.get_selected_templates()
        if not self.selected_templates_list:
            display_text = "No template selected"
        else:
            display_text = ", ".join(f.name for f in self.selected_templates_list)
        
        self.upload_frame.template_selected.configure(text=f"Templates: {display_text}",
                                                      wraplength=500,
                                                      justify="center")

    def _add_folder_path(self, path: Path):
        """Add a folder path to source_paths if it's a valid directory and not a duplicate."""
        if path.is_dir() and path not in self.source_paths:
            self.source_paths.append(path)

    def _refresh_folder_labels(self):
        """Refresh the upload frame labels to reflect current source_paths."""
        if not self.source_paths:
            self.upload_frame.upload_label.configure(text="Drag & drop folder di sini, atau klik 'Pilih Folder Gambar'")
            self.upload_frame.path_label.configure(text="Belum ada folder dipilih")
        elif len(self.source_paths) == 1:
            self.upload_frame.upload_label.configure(text=f"Source: {self.source_paths[0].name}")
            self.upload_frame.path_label.configure(text=str(self.source_paths[0]))
        else:
            self.upload_frame.upload_label.configure(text=f"{len(self.source_paths)} folder terpilih")
            paths_str = "\n".join(f"• {p.name}" for p in self.source_paths)
            self.upload_frame.path_label.configure(text=paths_str)

    def handle_drop(self, event):
        """Handle files/folders dropped onto the upload frame."""
        self.on_drag_leave(event)  # Reset visual
        raw = event.data

        import re
        paths = re.findall(r'\{([^}]+)\}|([^\s]+)', raw)
        paths = [p[0] if p[0] else p[1] for p in paths]

        added = 0
        busy = []
        for p_str in paths:
            path = Path(p_str)
            folder = path if path.is_dir() else path.parent if path.is_file() else None
            if folder is None:
                continue
            if is_folder_active(folder):
                if folder not in busy:
                    busy.append(folder)
                continue
            self._add_folder_path(folder)
            added += 1

        if busy:
            names = "\n".join(f"• {p.name}" for p in busy)
            messagebox.showwarning(
                "Folder Sedang Diproses",
                f"Folder berikut sedang diproses, jadi tidak ditambahkan lagi:\n{names}\n\n"
                "Batalkan proses yang berjalan dulu kalau mau memulai ulang folder ini."
            )

        if added > 0:
            self._refresh_folder_labels()
            self.upload_frame.status_label.configure(text="")
        else:
            self.upload_frame.status_label.configure(text="Tidak ada folder valid yang dikenali")

    def on_drag_enter(self, event):
        """Visual feedback when a drag enters the drop zone."""
        self.upload_frame.configure(border_color="#2FA572", border_width=3)
        self.upload_frame.drag_hint_label.configure(text="⬇Lepas untuk menambahkan folder")

    def on_drag_leave(self, event):
        """Reset visual feedback when drag leaves the drop zone."""
        self.upload_frame.configure(border_color="#444444", border_width=2)
        self.upload_frame.drag_hint_label.configure(text="Drag & drop folder gambar ke sini")

    def select_source_folder(self):
        folder = filedialog.askdirectory(title="Pilih Folder Gambar")
        if folder:
            path = Path(folder)
            self._add_folder_path(path)
            self._refresh_folder_labels()

    def reset_folders(self):
        self.source_paths = []
        self.upload_frame.upload_label.configure(text="Drag & drop folder di sini, atau klik 'Pilih Folder Gambar'")
        self.upload_frame.path_label.configure(text="Belum ada folder dipilih")
        self.upload_frame.status_label.configure(text="Ready")

    def get_selected_templates(self):
        if hasattr(self, "dialog"):
            return self.dialog.get_selected_templates()
        return []

    def start_processing(self):
        if self.is_running:
            # Tombol tetap bisa diklik saat proses jalan supaya bentrok folder bisa diberi notif.
            busy = [p for p in self.source_paths if is_folder_active(p)]
            if busy:
                names = "\n".join(f"• {p.name}" for p in busy)
                messagebox.showwarning(
                    "Folder Sedang Diproses",
                    f"Folder berikut sedang diproses:\n{names}\n\nPermintaan baru dibatalkan."
                )
            else:
                messagebox.showwarning("Peringatan", "Masih ada proses yang berjalan. Tunggu selesai atau batalkan dulu.")
            return

        if not self.source_paths:
            messagebox.showwarning("Peringatan", "Silakan pilih folder sumber gambar terlebih dahulu.")
            return

        templates = self.get_selected_templates()
        if not templates:
            messagebox.showwarning("Peringatan", "Silakan pilih minimal satu template.")
            return

        # Tolak folder yang namanya sudah pernah diproses (hasilnya sudah ada di folder output)
        done = {p: find_previous_runs(p.name) for p in self.source_paths}
        duplicates = [p for p, runs in done.items() if runs]
        if duplicates:
            lines = "\n".join(f"• {p.name}  (hasil: {done[p][-1].name})" for p in duplicates)
            self.source_paths = [p for p in self.source_paths if p not in duplicates]
            self._refresh_folder_labels()
            if self.source_paths:
                tail = "\n\nFolder tersebut dilewati, proses dilanjutkan untuk folder lainnya."
            else:
                tail = "\n\nTidak ada folder lain untuk diproses."
            messagebox.showwarning(
                "Folder Sudah Pernah Diproses",
                f"Tidak bisa memproses folder berikut karena sudah pernah diproses:\n{lines}{tail}\n\n"
                "Hapus folder hasilnya di 'hasil-gambar' atau ganti nama folder sumber kalau memang mau diproses ulang."
            )
            if not self.source_paths:
                return

        # Snapshot folder yang diproses + tandai sebagai 'sedang diproses'
        sources = list(self.source_paths)
        busy = claim_folders(sources)
        if busy:
            names = "\n".join(f"• {p.name}" for p in busy)
            messagebox.showwarning(
                "Folder Sedang Diproses",
                f"Folder berikut sedang diproses:\n{names}\n\nPermintaan baru dibatalkan."
            )
            return

        self.cancel_event.clear()
        self.is_running = True

        # Disable buttons during processing
        self.toggle_buttons(False)
        self.upload_frame.cancel_button.configure(state="normal", text="Batalkan Proses")
        
        # Start threading
        thread = threading.Thread(target=self.run_process_thread, args=(templates, sources))
        thread.daemon = True
        thread.start()

    def toggle_buttons(self, state):
        mode = "normal" if state else "disabled"
        self.upload_button.configure(state=mode)
        self.choose_button.configure(state=mode)
        self.process_button.configure(state="normal")
        self.home_button.configure(state=mode)
        if hasattr(self, "reset_button"):
            self.reset_button.configure(state=mode)
        if state:
            self.upload_frame.cancel_button.configure(state="disabled", text="Batalkan Proses")

    def cancel_processing(self):
        if not self.is_running or self.cancel_event.is_set():
            return
        if not messagebox.askyesno("Batalkan Proses", "Yakin mau membatalkan proses yang sedang berjalan?"):
            return
        self.cancel_event.set()
        self.upload_frame.cancel_button.configure(state="disabled", text="Membatalkan...")
        self.update_status("Membatalkan... menunggu gambar yang sedang diproses selesai")

    def update_status(self, msg, progress=None):
        self.upload_frame.status_label.configure(text=msg)
        if progress is not None:
            self.upload_frame.progress_bar.set(progress)

    def safe_update_status(self, msg, progress=None):
        self.after(0, lambda: self.update_status(msg, progress))

    def _finish_processing(self):
        self.is_running = False
        self.toggle_buttons(True)

    def safe_toggle_buttons(self, state):
        self.after(0, lambda: self.toggle_buttons(state))

    def safe_showinfo(self, title, message):
        self.after(0, lambda: messagebox.showinfo(title, message))

    def safe_showerror(self, title, message):
        self.after(0, lambda: messagebox.showerror(title, message))

    def run_process_thread(self, templates, sources):
        output_paths = []
        finished = set()
        try:
            logos = [t for t in templates if t.name.upper().startswith("LOGO")]
            standards = [t for t in templates if not t.name.upper().startswith("LOGO")]

            num_folders = len(sources)
            steps_per_folder = (1 if standards else 0) + len(standards) + len(logos)
            total_steps = num_folders * steps_per_folder
            current_step = 0

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for folder_idx, source_path in enumerate(sources, 1):
                check_cancel(self.cancel_event)
                self.safe_update_status(f"[{folder_idx}/{num_folders}] Menyiapkan folder output untuk {source_path.name}...", current_step / total_steps)

                parent_folder = OUTPUT_DIR / f"olahan_{source_path.name}_{timestamp}"
                parent_folder.mkdir(parents=True, exist_ok=True)
                output_paths.append(parent_folder)

                rembg_dir = None
                if standards:
                    self.safe_update_status(
                        f"[{folder_idx}/{num_folders}] Menghapus background {source_path.name}...",
                        current_step / total_steps
                    )
                    rembg_dir = parent_folder / "01_rembg"
                    remove_backgrounds(
                        source_path,
                        rembg_dir,
                        callback=lambda m, p=None, idx=folder_idx, sp=source_path, cs=current_step: self.safe_update_status(
                            f"[{idx}/{num_folders}] {sp.name} Rembg: {m}",
                            (cs + (p or 0)) / total_steps if p is not None else None
                        ),
                        cancel_event=self.cancel_event,
                    )
                    current_step += 1

                for tmpl in standards:
                    sub_folder_name = f"_({source_path.name}) ({tmpl.stem})"
                    target_dir = parent_folder / sub_folder_name
                    target_dir.mkdir(parents=True, exist_ok=True)

                    self.safe_update_status(
                        f"[{folder_idx}/{num_folders}] Menerapkan template {tmpl.name} ke {source_path.name}...",
                        current_step / total_steps
                    )
                    apply_templates(
                        rembg_dir,
                        target_dir,
                        [tmpl],
                        sub_folder_name,
                        callback=lambda m, p=None, idx=folder_idx, sp=source_path, cs=current_step, name=tmpl.stem: self.safe_update_status(
                            f"[{idx}/{num_folders}] {sp.name} Template {name}: {m}",
                            (cs + (p or 0)) / total_steps if p is not None else None
                        ),
                        cancel_event=self.cancel_event,
                    )
                    current_step += 1

                for logo in logos:
                    sub_folder_name = f"_({source_path.name}) ({logo.stem})"
                    target_dir = parent_folder / sub_folder_name
                    target_dir.mkdir(parents=True, exist_ok=True)

                    self.safe_update_status(
                        f"[{folder_idx}/{num_folders}] Memproses Logo {logo.name} ke {source_path.name}...",
                        current_step / total_steps
                    )
                    process_mode_logo(
                        source_path,
                        target_dir,
                        logo,
                        sub_folder_name,
                        callback=lambda m, p=None, idx=folder_idx, sp=source_path, cs=current_step, name=logo.stem: self.safe_update_status(
                            f"[{idx}/{num_folders}] {sp.name} Logo {name}: {m}",
                            (cs + (p or 0)) / total_steps if p is not None else None
                        ),
                        cancel_event=self.cancel_event,
                    )
                    current_step += 1

                finished.add(parent_folder)

            self.safe_update_status("Semua proses selesai!", 1.0)

            paths_msg = "\n".join(str(p) for p in output_paths)
            self.safe_showinfo("Selesai", f"Proses berhasil! Hasil ada di folder:\n{paths_msg}")
        except ProcessCancelled:
            self.safe_update_status("Proses dibatalkan", 0.0)
            paths_msg = "\n".join(str(p) for p in output_paths)
            self.safe_showinfo(
                "Dibatalkan",
                "Proses dibatalkan oleh pengguna.\n"
                "Hasil yang sudah sempat dibuat (belum lengkap) ada di:\n" + paths_msg
                if output_paths else "Proses dibatalkan oleh pengguna."
            )
        except Exception as e:
            self.safe_update_status(f"Error: {str(e)}")
            self.safe_showerror("Error", f"Terjadi kesalahan: {str(e)}")

        finally:
            # hasil yang tidak selesai (batal/error) tidak boleh dianggap 'sudah pernah diproses'
            for p in output_paths:
                if p not in finished:
                    mark_incomplete(p)
            release_folders(sources)
            self.after(0, self._finish_processing)

class FrameUpload(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, border_width=2, border_color="#444444", corner_radius=12)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.drag_hint_label = ctk.CTkLabel(
            self,
            text="🗂️  Drag & drop folder gambar ke sini",
            font=ctk.CTkFont(size=13),
            text_color="#888888"
        )
        self.drag_hint_label.pack(pady=(14, 0))

        self.upload_label = ctk.CTkLabel(
            self,
            text="Drag & drop folder di sini, atau klik 'Pilih Folder Gambar'",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.upload_label.pack(pady=(10, 5))

        self.path_label = ctk.CTkLabel(
            self,
            text="Belum ada folder dipilih",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            wraplength=800,
            justify="center"
        )
        self.path_label.pack(pady=(0, 10))

        self.template_selected = ctk.CTkLabel(self, text="Templates: No template selected", font=ctk.CTkFont(size=14), text_color="#2FA572")
        self.template_selected.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=(20, 5))

        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.cancel_button = ctk.CTkButton(
            self,
            text="Batalkan Proses",
            state="disabled",
            fg_color="#E74C3C",
            hover_color="#C0392B",
        )
        self.cancel_button.pack(pady=10)
        
    

class TemplateSelectionDialog(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()  # selalu di atas

        self.overlay = ctk.CTkFrame(self, fg_color="#000000")
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.overlay.bind("<Button-1>", lambda e: self.close_modal())

        self.dialog = ctk.CTkFrame(
            self.overlay,
            corner_radius=10
        )
        self.dialog.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=0.5,
            relheight=0.5
        )
        self.dialog.bind("<Button-1>", lambda e: "break")

        label = ctk.CTkLabel(
            self.dialog,
            text="Pilih Template",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(1, weight=1)
        label.grid(row = 0, column = 0, pady=20)
    
        path_template = TEMPLATE_DIR
        if not path_template.exists():
            path_template.mkdir(parents=True, exist_ok=True)

        self.check_vars = []
        files = sorted([f for f in path_template.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg")])
        
        if not files:
            empty_label = ctk.CTkLabel(self.dialog, text="No templates found in 'template' folder.")
            empty_label.grid(
                row=1,
                column=0,
                pady=10
            )
        else:
            content = ctk.CTkFrame(self.dialog, fg_color="transparent")
            content.grid(row = 1, column = 0, sticky="nsew",padx=20)
            content.grid_columnconfigure(0, weight=1)
            content.grid_rowconfigure(1, weight=1)
            # Checkbox Pilih Semua
            self.select_all_var = ctk.StringVar(value="off")
            self.select_all_checkbox = ctk.CTkCheckBox(
                content, 
                text="Pilih Semua",
                variable=self.select_all_var,
                onvalue="on",
                offvalue="off",
                command=self.toggle_select_all
            )
            self.select_all_checkbox.grid(row=0, column=0, pady=(0, 10), sticky="nsew", padx=20)

            scroll_frame = ctk.CTkScrollableFrame(content)
            scroll_frame.grid(row=1, column=0, sticky="nsew")

            for file in files:
                var = ctk.StringVar(value="off")
                checkbox = ctk.CTkCheckBox(
                    scroll_frame, 
                    text=file.name,
                    variable=var,
                    onvalue="on",
                    offvalue="off",
                    command=self.update_select_all_state
                )
                checkbox.pack(pady=5, anchor="w", padx=20)
                self.check_vars.append((file, var))

        btn = ctk.CTkButton(
            self.dialog,
            text="Simpan & Tutup",
            command=self.close_modal
        )
        btn.grid(row=3, column=0, pady=20)

    def toggle_select_all(self):
        val = self.select_all_var.get()
        for _, var in self.check_vars:
            var.set(val)

    def update_select_all_state(self):
        if not self.check_vars:
            return
        all_checked = all(var.get() == "on" for _, var in self.check_vars)
        if all_checked:
            self.select_all_var.set("on")
        else:
            self.select_all_var.set("off")

    def close_modal(self):
        if hasattr(self.master, "update_selected_label"):
            self.master.update_selected_label()
        self.destroy()

    def get_selected_templates(self):
        return [file for file, var in self.check_vars if var.get() == "on"]