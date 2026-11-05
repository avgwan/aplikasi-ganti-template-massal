import sys
import io

if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from app import App

if __name__ == "__main__":
    app = App()
    app.setup_directories()
    app.mainloop()