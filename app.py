import customtkinter as ctk
from tkinterdnd2 import TkinterDnD
from ui.pages.HomePage import HomePage
from ui.pages.UploadPage import UploadPage
from config import TEMPLATE_DIR, OUTPUT_DIR

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.configure(bg="#1a1a1a")

        self.title("Product Template Application")
        self.geometry("1280x720")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)


        self.setup_directories()
        self.pages = {
            "home": HomePage(parent=self),
            "upload": UploadPage(parent=self)
        }
        self.show_page("home")

    def setup_directories(self):
        folders = [TEMPLATE_DIR, OUTPUT_DIR]
        
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

    def show_page(self, page_name):
        for page in self.pages.values():
            page.grid_forget()

        self.pages[page_name].grid(row=0, column=0, sticky="nsew")

