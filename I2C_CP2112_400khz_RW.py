import time
import hid
import tkinter as tk
from tkinter import messagebox, ttk

class CP2112_I2C:
    def __init__(self, serial=None):
        self.serial = serial
        self.h = hid.device()
        self.open_device()

    def open_device(self):
        """Open the CP2112 device."""
        try:
            self.h.open(0x10C4, 0xEA90, self.serial)  # Connect to CP2112
            print("Manufacturer: %s" % self.h.get_manufacturer_string())
            print("Product: %s" % self.h.get_product_string())
            print("Serial No: %s" % self.h.get_serial_number_string())

            # Configure GPIO (optional, if you need to control LEDs)
            self.h.send_feature_report([0x03, 0xFF, 0x00, 0x00, 0x00])  # Set GPIO to Open-Drain

            # Configure SMBus (I2C) at 400 kHz
            self.h.send_feature_report([
                0x06,               # SMBus configuration command
                0x00,               # Reserved, always 0x00
                0x06,               # SMBus speed = 400 kHz (0x01 = 100khz)
                0x00, 0x32,         # Slave address timeout (50 ms)
                0x00,               # SCL Low timeout disabled (MANDATORY!)
                0x00, 0x00,         # Retry Time disabled
                0xFF, 0x00,         # Reserved, always 0xFF and 0x00
                0xFF,               # Reserved
                0x01,               # Reserved
                0x00,               # Reserved
                0x0F                # Clock stretching enabled (recommended)
            ])
        except Exception as e:
            print(f"Error opening device: {e}")
            raise

    def write_data(self, address, register, value, data_length):
        """Write data to a register (8 or 16 bits)."""
        try:
            if data_length == 1:  # 8-bit data
                # Format: [Report ID, Address, Command, Register High, Register Low, Data]
                self.h.write([0x14, address << 1, 0x03, register >> 8, register & 0xFF, value & 0xFF])
                print(f"Write: Address 0x{address:02X}, Register 0x{register:04X}, Data 0x{value:02X}")
            elif data_length == 2:  # 16-bit data
                # Format: [Report ID, Address, Command, Register High, Register Low, Data High, Data Low]
                self.h.write([0x14, address << 1, 0x04, register >> 8, register & 0xFF, (value >> 8) & 0xFF, value & 0xFF])
                print(f"Write: Address 0x{address:02X}, Register 0x{register:04X}, Data 0x{value:04X}")
            else:
                raise ValueError("Unsupported data length")
        except Exception as e:
            print(f"Write error: {e}")
            self.I2CError()

    def read_data(self, address, register, data_length):
        """Read data from a register (8 or 16 bits)."""
        try:
            # Send a read request
            self.h.write([
                0x11,               # Report ID for Data Write Read Request
                address << 1,       # Device address (with write bit)
                0x00,               # Reserved
                data_length,        # Data length to read (1 or 2 bytes)
                0x02,               # Register address length (2 bytes)
                register >> 8,      # High byte of register address
                register & 0xFF     # Low byte of register address
            ])

            for _ in range(10):
                # Request transfer status
                self.h.write([0x15, 0x01])  # Transfer Status Request
                response = self.h.read(7)
                print(f"Status response: {[hex(x) for x in response]}")  # Debug info

                # Check if the transfer is complete
                if (response[0] == 0x16) and (response[2] == 5):  # Polling a data
                    # Request data
                    self.h.write([0x12, 0x00, data_length])  # Data Read Force
                    response = self.h.read(data_length + 3)
                    print(f"Data response: {[hex(x) for x in response]}")  # Debug info

                    # Check if this is a data read response
                    if response[0] == 0x13:
                        if data_length == 1:
                            data = response[3]
                            print(f"Read: Address 0x{address:02X}, Register 0x{register:04X}, Data 0x{data:02X}")
                            return data
                        elif data_length == 2:
                            data = (response[3] << 8) | response[4]
                            print(f"Read: Address 0x{address:02X}, Register 0x{register:04X}, Data 0x{data:04X}")
                            return data

            print("Data read error...")
            self.I2CError()
        except Exception as e:
            print(f"Read error: {e}")
            self.I2CError()

    def read_multiple_bytes(self, address, register, num_bytes):
        """Read multiple bytes in a row."""
        try:
            data = []
            for i in range(num_bytes):
                byte_data = self.read_data(address, register + i, 1)
                data.append(byte_data)
            return data
        except Exception as e:
            print(f"Error reading multiple bytes: {e}")
            self.I2CError()

    def write_multiple_bytes(self, address, register, data):
        """Write multiple bytes in a row."""
        try:
            for i, value in enumerate(data):
                self.write_data(address, register + i, value, 1)
        except Exception as e:
            print(f"Error writing multiple bytes: {e}")
            self.I2CError()

    def I2CError(self):
        """Handle I2C errors."""
        print("Resetting device...")
        try:
            self.h.send_feature_report([0x01, 0x01])  # Reset Device
        except Exception as e:
            print(f"Error resetting device: {e}")
        finally:
            self.h.close()
            time.sleep(3)  # Give time to release the bus
            self.open_device()  # Reopen the device after reset
            raise IOError("I2C error, device reset and reopened.")

class I2CGUI:
    def __init__(self, root, i2c):
        self.root = root
        self.i2c = i2c
        self.root.title("I2C Control (16-bit registers)")

        # Device address
        self.address_label = tk.Label(root, text="Slave address (hex):")
        self.address_label.grid(row=0, column=0, padx=10, pady=10)
        self.address_entry = tk.Entry(root)
        self.address_entry.grid(row=0, column=1, padx=10, pady=10)
        self.address_entry.insert(0, "0x2d")  # Default address for writing

        # Register
        self.register_label = tk.Label(root, text="Register (hex, 16 bits):")
        self.register_label.grid(row=1, column=0, padx=10, pady=10)
        self.register_entry = tk.Entry(root)
        self.register_entry.grid(row=1, column=1, padx=10, pady=10)
        self.register_entry.insert(0, "0x020E")  # Default Register

        # Data to write
        self.data_label = tk.Label(root, text="Data to write (hex):")
        self.data_label.grid(row=2, column=0, padx=10, pady=10)
        self.data_entry = tk.Entry(root)
        self.data_entry.grid(row=2, column=1, padx=10, pady=10)
        self.data_entry.insert(0, "0x0000")  # Data default

        # Data length selection (8 or 16 bits)
        self.data_length_label = tk.Label(root, text="Data length (bytes):")
        self.data_length_label.grid(row=3, column=0, padx=10, pady=10)
        self.data_length_combobox = ttk.Combobox(root, values=["1", "2"])
        self.data_length_combobox.grid(row=3, column=1, padx=10, pady=10)
        self.data_length_combobox.current(0)  # Default 1 byte

        # Write button
        self.write_button = tk.Button(root, text="Write to register", command=self.write_data)
        self.write_button.grid(row=4, column=0, padx=10, pady=10)

        # Read button
        self.read_button = tk.Button(root, text="Read Register", command=self.read_data)
        self.read_button.grid(row=4, column=1, padx=10, pady=10)

        # Sequential read
        self.read_multiple_label = tk.Label(root, text="Read multiple bytes (count):")
        self.read_multiple_label.grid(row=5, column=0, padx=10, pady=10)
        self.read_multiple_entry = tk.Entry(root)
        self.read_multiple_entry.grid(row=5, column=1, padx=10, pady=10)
        self.read_multiple_entry.insert(0, "4")  # Default 4 bytes

        self.read_multiple_button = tk.Button(root, text="Read Multiple Bytes", command=self.read_multiple_bytes)
        self.read_multiple_button.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

        # Result output field
        self.result_label = tk.Label(root, text="Result:")
        self.result_label.grid(row=7, column=0, padx=4, pady=10)
        self.result_text = tk.Text(root, height=10, width=50)
        self.result_text.grid(row=7, column=1, padx=6, pady=10)

    def write_data(self):
        """Write data to a register."""
        try:
            address = int(self.address_entry.get(), 16)
            register = int(self.register_entry.get(), 16)
            value = int(self.data_entry.get(), 16)
            data_length = int(self.data_length_combobox.get())

            # Check if the data matches the selected length
            if data_length == 1 and value > 0xFF:
                raise ValueError("For 8-bit write, data must be in the range 0x00-0xFF")
            elif data_length == 2 and value > 0xFFFF:
                raise ValueError("For 16-bit write, data must be in the range 0x0000-0xFFFF")

            self.i2c.write_data(address, register, value, data_length)
            messagebox.showinfo("Success", "Data written successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Write error: {e}")

    def read_data(self):
        """Read data from a register."""
        try:
            address = int(self.address_entry.get(), 16)
            register = int(self.register_entry.get(), 16)
            data_length = int(self.data_length_combobox.get())
            data = self.i2c.read_data(address | 0x01, register, data_length)
            self.result_text.delete(1.0, tk.END)
            if data_length == 1:
                self.result_text.insert(tk.END, f"0x{data:02X}")
            elif data_length == 2:
                self.result_text.insert(tk.END, f"0x{data:04X}")
            messagebox.showinfo("Success", "Data read successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Read error: {e}")

    def read_multiple_bytes(self):
        """Read multiple bytes in a row."""
        try:
            address = int(self.address_entry.get(), 16)
            register = int(self.register_entry.get(), 16)
            num_bytes = int(self.read_multiple_entry.get())
            data = self.i2c.read_multiple_bytes(address | 0x01, register, num_bytes)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, ", ".join([f"0x{byte:02X}" for byte in data]))
            messagebox.showinfo("Success", "Data read successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Read error: {e}")

def main():
    # Initialize CP2112
    i2c = CP2112_I2C()

    # Create the GUI
    root = tk.Tk()
    gui = I2CGUI(root, i2c)
    root.mainloop()

if __name__ == "__main__":
    main()
