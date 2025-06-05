import logging
import sys

import qtmodern.styles
from PyQt5.QtWidgets import QApplication, QMainWindow

from lumed_ips.ips_widget import IpsLaserWidget

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler("debug.log"), logging.StreamHandler(sys.stdout)],
    )

    app = QApplication(sys.argv)

    # Changing Theme
    qtmodern.styles.light(app)

    window = QMainWindow()
    window.show()

    window.setCentralWidget(IpsLaserWidget())

    app.exec_()
