"""User Interface (UI) for the control of ocean optics HL_2000_HP_232R halogen lamp with the HL2000() class 
imported from the HL_2000_HP_232R_control module"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from time import strftime

import pyqt5_fugueicons as fugue
from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

from HL_2000_HP_232R_control import HL2000Lamp, LampInfo #lumed_HL_2000_HP_232R.
from ui.HL_2000_HP_232R_ui import Ui_HL2000Widget

logger = logging.getLogger(__name__)

LOGS_DIR = Path.home() / "logs/HL_2000_HP_232R"
LOG_PATH = LOGS_DIR / f"{strftime('%Y_%m_%d_%H_%M_%S')}.log"

LAMP_STATE = {0: "Idle", 1: "ON", 2: "Not connected"}
STATE_COLORS = {
    0: "QLabel { background-color : blue; }",
    1: "QLabel { background-color : red; }",
    2: "QLabel { background-color : grey; }",
}

LOG_FORMAT = (
    "%(asctime)s - %(levelname)s"
    "(%(filename)s:%(funcName)s)"
    "(%(filename)s:%(lineno)d) - "
    "%(message)s"
)


def configure_logger():
    """Configures the logger if lumed_HL_2000_HP_232R is launched as a module"""

    if not LOGS_DIR.parent.exists():
        LOGS_DIR.parent.mkdir()
    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir()

    formatter = logging.Formatter(LOG_FORMAT)

    terminal_handler = logging.StreamHandler()
    terminal_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setFormatter(formatter)

    logger.addHandler(terminal_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)


class HL2000Widget(QWidget, Ui_HL2000Widget):
    """User Interface for HL_2000_HP_232R white light lamp control.
    Subclass HL2000Widget to customize the Ui_HL2000Widget widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # logger
        logger.info("Widget intialization")

        self.lamp: HL2000Lamp = HL2000Lamp()
        self.lamp_info: LampInfo = self.lamp.get_info()
        self.last_enabled_state: bool = False

        # ui parameters
        self.setup_default_ui()
        self.connect_ui_signals()
        self.setup_update_timer()
        self.update_ui()
        logger.info("Widget initialization complete")

    def setup_default_ui(self):
        self.pushbtnFindLamp.setIcon(fugue.icon("magnifier-left"))
        self.spinboxShutterPosition.setMaximum(400)  # max position of lamp shutter

        self.spinboxPulseDuration.setEnabled(False)
        self.pushbtnPulse.setEnabled(False)
    
    def connect_ui_signals(self):
        self.pushbtnFindLamp.clicked.connect(self.find_lamp)
        self.pushbtnConnect.clicked.connect(self.connect_lamp)
        self.pushbtnDisconnect.clicked.connect(self.disconnect_lamp)
        self.pushbtnLampEnable.clicked.connect(self.enable_lamp)
        self.pushbtnLampDisable.clicked.connect(self.disable_lamp)
        self.spinboxShutterPosition.valueChanged.connect(self.set_shutter_position)

    def find_lamp(self):
        logger.info("Looking for connected lamps")
        self.pushbtnFindLamp.setEnabled(False)
        self.pushbtnFindLamp.setIcon(fugue.icon("hourglass"))
        self.repaint()

        try:
            lamps = self.lamp.find_lamp_device()
            logger.info("Found lamps : %s", lamps)
            self.comboboxAvailableLamp.clear()
            for lamp in lamps:
                self.comboboxAvailableLamp.addItem(lamp)
        except Exception as e:
            logger.error(e, exc_info=True)
        self.pushbtnFindLamp.setEnabled(True)
        self.pushbtnFindLamp.setIcon(fugue.icon("magnifier-left"))
        self.update_ui()

    def connect_lamp(self):
        logger.info("Connecting lamp")
        self.pushbtnConnect.setEnabled(False)
        try:
            lamp_comport = self.comboboxAvailableLamp.currentText()
            self.lamp.comport = lamp_comport
            self.lamp.connect()
            logger.info("Connected lamp : %s", lamp_comport)
            self.set_initial_configurations()
        except Exception as e:
            logger.error(e, exc_info=True)
        self.update_ui()
        self.update_timer.start()

    def disconnect_lamp(self):
        logger.info("Disconnecting lamp")
        self.pushbtnDisconnect.setEnabled(False)
        try:
            self.set_initial_configurations()
            self.lamp.disconnect()
        except Exception as e:
            logger.error(e, exc_info=True)
        self.update_ui()
        self.update_timer.stop()
    
    def enable_lamp(self):
        logger.info("Enabling lamp")
        self.lamp.set_enable(True)
        self.last_enabled_state = True
        self.update_ui()

    def disable_lamp(self):
        logger.info("Disabling lamp")
        self.lamp.set_enable(False)
        self.last_enabled_state = False
        self.update_ui()

    def set_shutter_position(self):
        shutter_position = self.spinboxShutterPosition.value()
        logger.info("Setting lamp shutter position : %s", shutter_position)
        self.lamp.set_shutter_position(shutter_position)

    def set_initial_configurations(self):
        logger.info("Setting initial lamp configurations")
        logger.info("Setting lamp to disable")
        self.lamp.set_enable(False)
        logger.info("Setting lamp shutter position to a closed position")
        self.lamp.set_shutter_position(-400)
        logger.info("Setting lamp shutter closed position as home position")
        self.lamp.set_home_position()

    def setup_update_timer(self):
        """Creates the PyQt Timer and connects it to the function that updates
        the UI and gets the lamp infos."""
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_ui)

    def setLabelConnected(self, isconnected: bool) -> None:
        if isconnected:
            self.labelLampConnected.setText("Connected")
            self.labelLampConnected.setStyleSheet("color:green")
        else:
            self.labelLampConnected.setText("Not Connected")
            self.labelLampConnected.setStyleSheet("color:red")

    def setLabelEnabled(self, isenabled: bool) -> None:
        if isenabled:
            self.labelLampEnabled.setText("ENABLED")
            self.labelLampEnabled.setStyleSheet("color:red")
        else:
            self.labelLampEnabled.setText("Disabled")
            self.labelLampEnabled.setStyleSheet("color:green")
    
    def update_ui(self):
        self.updateLampInfo()

        # Enable/disable controls if lamp is connected or not
        is_connected = self.lamp_info.is_connected
        self.pushbtnConnect.setEnabled(not is_connected)
        self.comboboxAvailableLamp.setEnabled(not is_connected)
        self.pushbtnFindLamp.setEnabled(not is_connected)
        self.pushbtnDisconnect.setEnabled(is_connected)
        self.groupboxControl.setEnabled(is_connected)
        self.setLabelConnected(is_connected)

        self.pushbtnLampEnable.setEnabled(not self.lamp_info.is_enabled)

    def lamp_safety_check(self):
        is_enabled = self.lamp_info.is_enabled
        if is_enabled != self.last_enabled_state:
            logger.warning(
                "Lamp safety trip setting lamp to %s",
                ["Disabled", "Enabled"][is_enabled],
            )
            self.lamp.set_enable(is_enabled)
            self.last_enabled_state = is_enabled

    def updateLampInfo(self):

        self.lamp_info = self.lamp.get_info()
        self.lamp_safety_check()

        # update UI based on LampInfo
        self.setLabelEnabled(self.lamp_info.is_enabled)
        self.texteditFV.setPlainText(self.lamp_info.firmware_version)
        self.texteditShutterPosition.setPlainText(str(self.lamp_info.shutter_position))
        self.texteditTemperature.setPlainText(str(self.lamp_info.coil_temperature))

if __name__ == "__main__":

    # Set up logging
    configure_logger()

    # Create app window
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.show()

    window.setCentralWidget(HL2000Widget())

    app.exec_()
