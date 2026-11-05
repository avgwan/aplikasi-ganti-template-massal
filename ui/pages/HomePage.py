import customtkinter as ctk
from tkinter import PhotoImage, filedialog, messagebox
from pathlib import Path
from core.pdf import create_pdf_from_folder
from config import OUTPUT_DIR

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class HomePage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=1)


        self.logo_image = PhotoImage(file=BASE_DIR / "assets" / "logo.png")
        self.label = ctk.CTkLabel(self, text="Welcome to the Product Template Application!", font=ctk.CTkFont(size=30, weight="bold"), image=self.logo_image, compound="top")
        self.label.grid(row=0, column=1, padx=20, pady=150, sticky="ew")

        self.button_upload = ctk.CTkButton(self, text="Upload Gambar", command=lambda: parent.show_page("upload"))
        self.button_upload.grid(row=1, column=1, padx=20, pady=20)

        self.button_pdf = ctk.CTkButton(self, text="Buat Pdf Langsung", command=self.create_pdf_manual)
        self.button_pdf.grid(row=2, column=1, padx=20, pady=20)

        self.button_exit = ctk.CTkButton(self, text="Exit", command=parent.destroy, fg_color="#E74C3C", hover_color="#C0392B")
        self.button_exit.grid(row=3, column=1, padx=20, pady=20)

    def create_pdf_manual(self):
        folder = filedialog.askdirectory(title="Pilih Folder Berisi Gambar")
        if folder:
            src_path = Path(folder)
            out_path = OUTPUT_DIR / f"Manual_PDF_{src_path.name}.pdf"
            
            try:
                create_pdf_from_folder(src_path, out_path)
                messagebox.showinfo("Selesai", f"PDF Berhasil dibuat di:\n{out_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal membuat PDF: {e}")