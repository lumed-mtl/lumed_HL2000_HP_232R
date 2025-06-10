import pyvisa
from dataclasses import dataclass

@dataclass
class LampInfo:
    firmware_version: str = ""
    is_connected: bool = False
    is_enabled: bool = False
    coil_temperature: float = float("nan")
    shutter_position: float = float("nan")


class HL2000Lamp:
    """Control Ocean Optics' halogen lamp HL-2000-HP-232R."""
    def __init__(self) -> None:
        self.idn: str | None = None
        self.comport: str | None = None #communication port on which the lamp is connected via usb
        self.pyvisa_serial: pyvisa.resources.serial.SerialInstrument | None = None

        self.isconnected: bool = False
        self.resource_manage = pyvisa.ResourceManager("@py")

    def find_lamp_device(self) -> dict[str, pyvisa.highlevel.ResourceInfo]:
        """
        find_lamp_device finds and returns which resources detected by pyvisa's resource manage is associated with HL2000 lamp

        IPS lasers appear as `ASRL/dev/ttyACMX::INSTR`

        Returns
        -------
        dict
            Mapping of resource name to ResourceInfo from pyvisa.
        """
        resources = self.resource_manage.list_resources_info()#query="?*ACM?*"
        connected_lamps = {}

        for k, v in resources.items():
            # ser = serial.Serial(port = COM_port, baudrate = 9600, bytesize = 8, parity='N', stopbits=1, timeout=1)
            try:
                device = self.resource_manage.open_resource(k)
                device.timeout = 50
                version = device.query("VER").strip()
            except Exception as _:
                continue
            if 'Version' in version:
                connected_lamps[k] = {"resourceInfo": v, "version": version.strip()}
        return connected_lamps
    
    ## Basic methods
    def scpi_write(self, message: str) -> (int):
        """Sends a serial message to the laser and verifies if any communication error occured.

        Parameter : <message> (string) : Message send to the laser by serial.
        The command syntax for those messages is explained in the documentation provided by IPS.  %

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        self.pyvisa_serial.write(message)
        # err_msg = self.pyvisa_serial.query("Error?").strip()
        # err_code = err_msg.split(",")[0]
        # err_msg = err_msg.split(",")[-1].strip().strip('"')

        return None #err_code, err_msg

    def scpi_query(self, message: str) -> (str):
        """Sends a serial message to the lamp

        Parameter : <message> (string) : Message send to the laser by serial.

        Returns:
        <value> (string) : Answer provided by the lamp to the serial COM.
        """
        answer = self.pyvisa_serial.query(message).strip()
        #err_msg = self.pyvisa_serial.query("Error?").strip()
        #err_code = int(err_msg.split(",")[0])
        #err_msg = err_msg.split(",")[-1].strip().strip('"')

        return answer#, err_code, err_msg

    def __repr__(self) -> str:
        reprstr = (
            f"IPSLaser(idn = '{self.idn}', "
            f"comport = '{self.comport}', "
            f"connected = {self.isconnected}, "
            f"enabled = {self.laser_enabled}, "
            f"laser current = {self.laser_current} mA, "
            f" laser temperature = {self.laser_temp}C, "
            f"laser power = {self.laser_power} mW)"
        )
        return reprstr
    
    ## Getters
    def get_fault_status(self) -> dict:
        """Requests the fault status by looking at the 4-bits returned by the lamp

        Bit #0 = over-temperature;\n
        Bit #1 = over-current;\n
        Bit #2 = under-voltage;\n
        Bit #3 = over-voltage\n
        
        Returns
        fault_status_dict [dict]: Dictionnary with the state of every fault status
        """
        fault_status = self.scpi_query("GFS")
        fault_status_dict = {"Over-temperature":False, "Over-current":False, "Under-voltage":False, "Over-voltage":False}
        if fault_status[0] == "1":
            fault_status_dict["Over-temperature"] = True
            print("Over-temperature condition reached")

        if fault_status[1] == "1":
            fault_status_dict["Over-current"] = True
            print("Over-current condition reached")
            
        if fault_status[2] == "1":
            fault_status_dict["Under-voltage"] = True
            print("Under-voltage condition reached (<15 VDC)")
            
        if fault_status[3] == "1":
            fault_status_dict["Over-voltage"] = True
            print("Over-voltage condition reached (>28 VDC)")   
        elif fault_status == "0000":
            print("No fault detected")
        return fault_status_dict

    def get_coil_temperature(self) -> float:
        """Reports the lightbulb's coil temperature in °C.

        Returns
        coil_temp [float]: module case temperature in °C"""
        coil_temp = self.scpi_query("TEM")
        coil_temp = float(coil_temp)
        return coil_temp
    
    def get_shutter_position(self) -> float:
        """Reports the current shutter position

        Returns 
        shutter_pos [int]: The shutter position
        """
        shutter_pos = self.scpi_query('POS')
        #shutter_pos = float(shutter_pos)
        return shutter_pos
    def get_firmware_version(self) -> str:

        """Reports the device's firmware version

        Returns 
        firmware_version [str]: The firmware version
        """
        self.scpi_query("VER")

    #Setters

    def set_enable(self, enable) -> None:
        """Controls whether the laser is enabled or disabled.

        Parameter : <enable> (int) : 1/ON = Enables the Lamp, 0/OFF = Disables the lamp
        """
        if enable: 
            #Lamp light will be enabled
            self.scpi_write("SO")
            self.enabled = True
            return
        elif not enable: 
            #Lamp light will be disabled
            self.scpi_write("CO")
            self.enabled = False

    def set_home_position(self) -> None:
        """Sets the shutter's home position
        """
        self.scpi_write("HO")


    def set_shutter_position(self, shutter_position) -> None:
        """Sets the shutter's position relative to the home position (home position = 0)
        """
        self.scpi_write(f'LA{shutter_position}') # Load absolute position (which is relative to home position)
        self.scpi_write('M') #Initiate shutter movement

    def set_drive(self, enable) -> None:
        """Controls wether the shutter motor's drive electronics are enabled or disabled.

        Parameter: <enable> (int) : 1/ON = Enables the drive electronics, 0/OFF = Disables Enables the drive electronics
        """
        if enable:
            self.scpi_write("EN")
            self.drive = True

        elif not enable: 
            self.scpi_write("DI")
            self.drive = False

    ## Compound methods

    def connect(self) -> bool:
        """Connects the lamp"""
        try:
            self.pyvisa_serial = self.resource_manage.open_resource(self.comport)
            self.pyvisa_serial.write_termination = '\r'
            self.set_drive(True)
            self.isconnected = True
        except Exception as _:
            self.isconnected = False

        return self.isconnected
    
    def disconnect(self) -> str:
        """Close the serial connection to the lamp,
        disable lamp if enabled."""
        self.set_enable(False)
        self.set_drive(False)
        self.pyvisa_serial.close()
        self.isconnected = False
        self.idn = None
        return not self.isconnected
    
    def get_info(self) -> LampInfo:
        if not self.isconnected:
            return LampInfo()

        try:
            version = self.get_firmware_version()
            is_enabled = self.enabled
            coil_temperature = self.get_coil_temperature()
            shutter_position = self.get_shutter_position()
            return LampInfo(
                firmware_version=version,
                is_connected=True,
                is_enabled=is_enabled,
                coil_temperature=coil_temperature,
                shutter_position = shutter_position
            )
        except Exception as _:
            return LampInfo()
        
    firmware_version: str = ""
    is_connected: bool = False
    is_enabled: bool = False
    temperature: float = float("nan")
    shutter_position: float = float("nan")


if __name__ == "__main__":
    print("START")
    lamp = HL2000Lamp()
    connected_lamps = lamp.find_lamp_device()
    print("Connected lamps:")
    print(connected_lamps)
    lamp.comport = list(connected_lamps)[0]
    print("comport:", lamp.comport)
    print("Connecting lamp")
    lamp.connect()
    #lamp.set_home_position()
    #lamp.set_shutter_position(100)
    print(lamp.get_shutter_position()) #the returned position is a string 'OK' for an unknown reason
    print("DONE")