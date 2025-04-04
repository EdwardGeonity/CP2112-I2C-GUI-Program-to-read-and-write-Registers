import time
import hid
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re


import sys

DEBUG = any(arg in sys.argv for arg in ["-d", "--d", "-debug", "--debug"])

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)
class CP2112_I2C:
    def __init__(self, serial=None):
        self.serial = serial
        self.h = hid.device()
        self.open_device()



    def open_device(self):
        """Open the CP2112 device."""
        try:
            self.h.open(0x10C4, 0xEA90, self.serial)  # Connect to CP2112
            debug_print("Manufacturer: %s" % self.h.get_manufacturer_string())
            debug_print("Product: %s" % self.h.get_product_string())
            debug_print("Serial No: %s" % self.h.get_serial_number_string())

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
            debug_print(f"Error opening device: {e}")
            raise

    def write_data(self, address, register, value, data_length):
        """Write data to a register (1–8 bytes)."""
        try:
            if data_length <= 2:
                # Use standard write reports
                if data_length == 1:
                    self.h.write([0x14, address << 1, 0x03, register >> 8, register & 0xFF, value & 0xFF])
                elif data_length == 2:
                    self.h.write([0x14, address << 1, 0x04, register >> 8, register & 0xFF,
                                  (value >> 8) & 0xFF, value & 0xFF])
                debug_print(f"Write: Addr 0x{address:02X}, Reg 0x{register:04X}, Data 0x{value:0{data_length*2}X}")
            elif data_length <= 8:
                # Convert value to bytes (MSB first)
                data_bytes = value.to_bytes(data_length, byteorder='big')

                report = [
                    0x17,                 # Report ID
                    address << 1,         # 7-bit address << 1
                    data_length,          # Byte count
                    0x02,                 # Command: Write to register
                    register >> 8,        # Register MSB
                    register & 0xFF       # Register LSB
                ] + list(data_bytes)

                # Pad to 64 bytes
                report += [0x00] * (64 - len(report))

                self.h.write(report)
                debug_print(f"Write (block): Addr 0x{address:02X}, Reg 0x{register:04X}, Data: {[hex(b) for b in data_bytes]}")
            else:
                raise ValueError("Data length too long (max 8 bytes supported)")
        except Exception as e:
            debug_print(f"Write error: {e}")
            self.I2CError()

    def write_block_data(self, address, register, data_bytes):
        """Write data block (up to 61 bytes) using Report ID 0x14."""
        if not (1 <= len(data_bytes) <= 61):
            raise ValueError("Data length must be between 1 and 61")

        report = [
            0x14,                    # Report ID
            address << 1,            # I2C address (7-bit << 1)
            len(data_bytes) + 2,     # Total bytes: register (2) + data
            (register >> 8) & 0xFF,  # Register MSB
            register & 0xFF          # Register LSB
        ] + list(data_bytes)

        report += [0x00] * (64 - len(report))  # Pad to 64 bytes

        debug_print(f"[→] Sending block write: {[hex(b) for b in report[:6+len(data_bytes)]]}")
        self.h.write(report)



    def read_data(self, address, register, data_length):
        """Read data from a register (1, 2, 4, or 8 bytes)."""
        try:
            # Send read request
            self.h.write([
                0x11,                  # Report ID
                address << 1,          # 7-bit address shifted
                0x00,                  # Reserved
                data_length,           # Bytes to read
                0x02,                  # Register address length (2 bytes)
                register >> 8,         # MSB of register
                register & 0xFF        # LSB of register
            ])

            for _ in range(10):
                time.sleep(0.01)  # slight delay for device response
                self.h.write([0x15, 0x01])  # Transfer Status Request
                response = self.h.read(7)
                debug_print(f"Status response: {[hex(x) for x in response]}")

                if response[0] == 0x16 and response[2] == 0x05:
                    self.h.write([0x12, 0x00, data_length])  # Data Read Force
                    response = self.h.read(data_length + 3)
                    debug_print(f"Data response: {[hex(x) for x in response]}")

                    if response[0] == 0x13 and response[2] == data_length:
                        # Сборка данных из байтов (MSB first)
                        data_bytes = response[3:3 + data_length]
                        result = 0
                        for b in data_bytes:
                            result = (result << 8) | b
                        debug_print(f"Read: Address 0x{address:02X}, Register 0x{register:04X}, Data 0x{result:0{data_length*2}X}")
                        return result

            debug_print("Data read error...")
            self.I2CError()
        except Exception as e:
            debug_print(f"Read error: {e}")
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
            debug_print(f"Error reading multiple bytes: {e}")
            self.I2CError()

    def write_multiple_bytes(self, address, register, data):
        """Write multiple bytes in a row."""
        try:
            for i, value in enumerate(data):
                self.write_data(address, register + i, value, 1)
        except Exception as e:
            debug_print(f"Error writing multiple bytes: {e}")
            self.I2CError()

    def I2CError(self):
        """Handle I2C errors."""
        debug_print("Resetting device...")
        try:
            self.h.send_feature_report([0x01, 0x01])  # Reset Device
        except Exception as e:
            debug_print(f"Error resetting device: {e}")
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




        # Device Bin address        
        self.addressbin_label = tk.Label(root, text="Slave address (7-bit BIN):")
        self.addressbin_label.grid(row=0, column=0, padx=10, pady=10)
        self.addressbin_entry = tk.Entry(root)
        self.addressbin_entry.grid(row=0, column=1, padx=10, pady=10)
        self.addressbin_entry.insert(0, "00101101")
        self.addressbin_entry.bind("<KeyRelease>", self.sync_bin_to_hex)

        # Device Hex address
        self.address_label = tk.Label(root, text="Slave address (HEX):")
        self.address_label.grid(row=1, column=0, padx=10, pady=10)
        self.address_entry = tk.Entry(root)
        self.address_entry.grid(row=1, column=1, padx=10, pady=10)
        self.address_entry.insert(0, "0x2D")
        self.address_entry.bind("<KeyRelease>", self.sync_hex_to_bin)

        # Register Hex Index
        self.register_label = tk.Label(root, text="Register (hex, 16 bits):")
        self.register_label.grid(row=2, column=0, padx=10, pady=10)
        self.register_entry = tk.Entry(root)
        self.register_entry.grid(row=2, column=1, padx=10, pady=10)
        self.register_entry.insert(0, "0x020E")

        # Data to write
        self.data_label = tk.Label(root, text="Data to write (hex):")
        self.data_label.grid(row=3, column=0, padx=10, pady=10)
        self.data_entry = tk.Entry(root)
        self.data_entry.grid(row=3, column=1, padx=10, pady=10)
        self.data_entry.insert(0, "0x0000")

        # Data length
        self.data_length_label = tk.Label(root, text="Data length (bytes):")
        self.data_length_label.grid(row=4, column=0, padx=10, pady=10)
        self.data_length_combobox = ttk.Combobox(root, values=["1", "2", "4", "8", "16", "32"])
        self.data_length_combobox.grid(row=4, column=1, padx=10, pady=10)
        self.data_length_combobox.current(0)

        # Write button
        self.write_button = tk.Button(root, text="Write to register", command=self.write_data)
        self.write_button.grid(row=5, column=0, padx=10, pady=10)

        # Read button
        self.read_button = tk.Button(root, text="Read Register", command=self.read_data)
        self.read_button.grid(row=5, column=1, padx=10, pady=10)

        # Sequential read
        self.read_multiple_label = tk.Label(root, text="Read multiple bytes (count):")
        self.read_multiple_label.grid(row=6, column=0, padx=10, pady=10)
        self.read_multiple_entry = tk.Entry(root)
        self.read_multiple_entry.grid(row=6, column=1, padx=10, pady=10)
        self.read_multiple_entry.insert(0, "4")  # Default 4 bytes

        self.read_multiple_button = tk.Button(root, text="Read Multiple Bytes", command=self.read_multiple_bytes)
        self.read_multiple_button.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

        # Result output field
        self.result_label = tk.Label(root, text="Result:")
        self.result_label.grid(row=8, column=0, padx=4, pady=10)
        self.result_text = tk.Text(root, height=10, width=50)
        self.result_text.grid(row=8, column=1, padx=6, pady=10)

        # Script runner section
        self.open_btn = tk.Button(root, text="Open Script", command=self.open_script)
        self.open_btn.grid(row=9, column=0, padx=4, pady=4)

        self.dropdown_var = tk.StringVar(value="No Script Loaded")
        self.dropdown_menu = tk.OptionMenu(root, self.dropdown_var, [])
        self.dropdown_menu.grid(row=9, column=1, padx=4, pady=4)

        self.run_btn = tk.Button(root, text="Run Script", command=self.run_script)
        self.run_btn.grid(row=9, column=2, padx=4, pady=4, sticky='e')




    def get_address(self):
        bin_value = self.addressbin_entry.get().strip()
        if bin_value:
            if not all(c in '01' for c in bin_value):
                raise ValueError("Binary address must contain only 0 or 1")
            if len(bin_value) > 7:
                raise ValueError("Binary address must be 7 bits")
            return int(bin_value, 2)
        return int(self.address_entry.get(), 16)

    def sync_bin_to_hex(self, event=None):
        bin_value = self.addressbin_entry.get().strip()
        if all(c in '01' for c in bin_value) and len(bin_value) <= 7:
            try:
                value = int(bin_value, 2)
                self.address_entry.delete(0, tk.END)
                self.address_entry.insert(0, f"0x{value:02X}")
            except:
                pass

    def sync_hex_to_bin(self, event=None):
        hex_value = self.address_entry.get().strip()
        try:
            if hex_value.lower().startswith("0x"):
                value = int(hex_value, 16)
            else:
                value = int(hex_value)
            if value <= 0x7F:
                bin_str = format(value, '07b')
                self.addressbin_entry.delete(0, tk.END)
                self.addressbin_entry.insert(0, bin_str)
        except:
            pass








    def open_script(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not file_path:
            return

        with open(file_path, 'r') as f:
            lines = f.readlines()

        self.script_data = {}
        current_block = None
        inside_block = False

        # <-- Инициализация адреса по умолчанию из GUI -->
        self.address = self.address_entry.get().strip().upper()

        for line in lines:
            line = line.strip()

            if line.startswith("Addr="):
                addr_match = re.match(r"Addr\s*=\s*([0-9A-Fa-fxX]+)", line)
                if addr_match:
                    self.address = addr_match.group(1).strip().upper()
                continue

            # New block
            if line.startswith("WBlock"):
                match = re.match(r'WBlock\((\d+),\s*([^)]+)\)', line)
                if match:
                    block_num = match.group(1).zfill(2)
                    block_name = match.group(2).strip()
                    current_block = (block_num, block_name)
                    self.script_data[current_block] = []
                    inside_block = True
                continue

            if inside_block:
                if line.startswith("]"):
                    inside_block = False
                    continue
                if line.startswith("("):
                    # Extract tuple data
                    match = re.match(r'\(([^)]+)\)', line)
                    if match:
                        parts = match.group(1).split(",")
                        if len(parts) >= 3:
                            reg = int(parts[0].strip(), 16)
                            dataSC = int(parts[1].strip(), 16)
                            length = int(parts[2].strip())
                            self.script_data[current_block].append((reg, dataSC, length))

        # Update dropdown menu
        menu = self.dropdown_menu["menu"]
        menu.delete(0, "end")
        for _, name in self.script_data:
            menu.add_command(label=name, command=lambda n=name: self.dropdown_var.set(n))
        if len(self.script_data) > 1:
            menu.add_command(label="Sequence all", command=lambda: self.dropdown_var.set("Sequence all"))

        first_block = next(iter(self.script_data.values()), None)
        self.dropdown_var.set("Sequence all" if len(self.script_data) > 1 else list(self.script_data.values())[0][1])

    def run_script(self):
        selected_name = self.dropdown_var.get()
        if not self.script_data:
            messagebox.showerror("Error", "No script loaded")
            return

        if selected_name == "Sequence all":
            for block, commands in self.script_data.items():
                self.execute_block(block, commands)
        else:
            for block, commands in self.script_data.items():
                if block[1] == selected_name:
                    self.execute_block(block, commands)
                    break

    def execute_block(self, block, commands):
        block_num, block_name = block
        debug_print(f"--- Start Block {block_num} ({block_name}) ---")
        for reg, dataSC, length in commands:
            data_bytes = dataSC.to_bytes(length, byteorder='big')
            self.i2c.write_block_data(int(self.address, 16), reg, data_bytes)
        debug_print(f"--- End Block {block_num} ({block_name}) ---")
        self.root.bell()



    def write_data(self):
        """Write data to a register."""
        try:
            address = int(self.address_entry.get(), 16)
            register = int(self.register_entry.get(), 16)
            value = int(self.data_entry.get(), 16)
            data_length = int(self.data_length_combobox.get())

            if data_length == 1 and value > 0xFF:
                raise ValueError("For 8-bit write, data must be in the range 0x00-0xFF")
            elif data_length == 2 and value > 0xFFFF:
                raise ValueError("For 16-bit write, data must be in the range 0x0000-0xFFFF")
            elif data_length > 2:
                value_bytes = value.to_bytes(data_length, byteorder='big')
                self.i2c.write_block_data(address, register, value_bytes)
                self.root.bell()
                return

            self.i2c.write_data(address, register, value, data_length)
            self.root.bell()

        except Exception as e:
            messagebox.showerror("Error", f"Write error: {e}")

    def read_data(self):
        """Read data from a register."""
        try:
            address = int(self.address_entry.get(), 16)
            register = int(self.register_entry.get(), 16)
            data_length = int(self.data_length_combobox.get())
            #data = self.i2c.read_data(address | 0x01, register, data_length)
            data = self.i2c.read_data(address, register, data_length)
            self.result_text.delete(1.0, tk.END)
            hex_width = data_length * 2
            self.result_text.insert(tk.END, f"0x{data:0{hex_width}X}")

            #messagebox.showinfo("Success", "Data read successfully!")
            self.root.bell()
        except Exception as e:
            messagebox.showerror("Error", f"Read error: {e}")

    def read_multiple_bytes(self):
        """Read multiple bytes in a row."""
        try:
            address = int(self.address_entry.get(), 16)
            register = int(self.register_entry.get(), 16)
            num_bytes = int(self.read_multiple_entry.get())
            #data = self.i2c.read_multiple_bytes(address | 0x01, register, num_bytes)
            data = self.i2c.read_multiple_bytes(address, register, num_bytes)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, ", ".join([f"0x{byte:02X}" for byte in data]))
            #messagebox.showinfo("Success", "Data read successfully!")
            self.root.bell()
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
