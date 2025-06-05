import pyvisa
from dataclasses import dataclass

@dataclass
class LampInfo:
    model: str = ""
    serial_number: str = ""
    is_connected: bool = False
    is_enabled: bool = False
    temperature: float = float("nan")
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
    def scpi_write(self, message: str) -> (int, str):
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

    def scpi_query(self, message: str) -> (str, int, str):
        """Sends a serial message to the laser, reads the err_code and
        verifies if any communication error occured.

        Parameter : <message> (string) : Message send to the laser by serial.
        The command syntax for those messages is explained in the documentation provided by IPS.  %

        Returns:
        <value> (string) : Answer provided by the laser to the serial COM.
        <err_code> : communication error code
        <err_msg> : communication error message
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
        """
        Gets the fault status by looking at the 4-bits returned by the lamp 
        Bit   |  Descritpion
        ------------------------
        0     |  Over-temperature
        1     |  Over current
        2     |  Under-voltage
        3     |  Over-voltage
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

        Returns: <coil_temp> : module case temperature in °C"""
        coil_temp = self.scpi_query("TEM")
        coil_temp = float(coil_temp)
        return coil_temp
    
    def get_shutter_position(self) -> float:
        """
        Reports the current shutter position
        """
        shutter_pos = self.scpi_query('POS')
        #shutter_pos = float(shutter_pos)
        return shutter_pos
    
    #Setters
    def set_illumination(self) -> None:
        """
        Turns lamp on
        """
        self.scpi_write("SO")

    def set_disable_illumination(self) -> None:
        """
        Turns lamp off
        """
        self.scpi_write("CO")

    def set_home_position(self) -> None:
        """
        Set the shutter's home position
        """
        self.scpi_write("HO")


    def set_shutter_position(self, shutter_position) -> None:
        """
        Sets the shutter's position relative to the home position (home position = 0)
        """
        self.scpi_write(f'LA{shutter_position}') # Load absolute position (which is relative to home position)
        self.scpi_write('M') #Initiate shutter movement

    def enable_drive(self) -> None:
        """
        Enables drive electronics for the shutter's motor.
        """
        self.scpi_write("EN")

    def disable_drive(self) -> None:
        """
        Disables drive electronics for the shutter's motor.
        """
        self.scpi_write("DI")
    
    ## Compound methods
    def connect(self) -> bool:
        """Connects the lamp"""
        try:
            self.pyvisa_serial = self.resource_manage.open_resource(self.comport)
            self.pyvisa_serial.write_termination = '\r'
            self.enable_drive()
            self.isconnected = True
        except Exception as _:
            self.isconnected = False

        return self.isconnected
    
    def disconnect(self) -> str:
        """Close the serial connection to the lamp,
        disable lamp if enabled."""
        self.disable_drive()
        self.set_disable_illumination()
        self.pyvisa_serial.close()
        self.isconnected = False
        self.idn = None
        return not self.isconnected

    
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