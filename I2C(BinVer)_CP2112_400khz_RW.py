
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
        try:
            self.h.open(0x10C4, 0xEA90, self.serial)
            print("Manufacturer: %s" % self.h.get_manufacturer_string())
            print("Product: %s" % self.h.get_product_string())
            print("Serial No: %s" % self.h.get_serial_number_string())

            self.h.send_feature_report([0x03, 0xFF, 0x00, 0x00, 0x00])  # Set GPIO to Open-Drain

            self.h.send_feature_report([
                0x06, 0x00, 0x06, 0x00, 0x32,
                0x00, 0x00, 0x00,
                0xFF, 0x00,
                0xFF, 0x01, 0x00, 0x0F
            ])
        except Exception as e:
            print(f"Error opening device: {e}")
            raise

    def write_data(self, address, register, value, data_length):
        try:
            if data_length == 1:
                self.h.write([0x14, address, 0x03, register >> 8, register & 0xFF, value & 0xFF])
                print(f"Write: Address 0x{address:02X}, Register 0x{register:04X}, Data 0x{value:02X}")
            elif data_length == 2:
                self.h.write([0x14, address, 0x04, register >> 8, register & 0xFF,
                              (value >> 8) & 0xFF, value & 0xFF])
                print(f"Write: Address 0x{address:02X}, Register 0x{register:04X}, Data 0x{value:04X}")
            else:
                raise ValueError("Unsupported data length")
        except Exception as e:
            print(f"Write error: {e}")
            self.I2CError()

    def read_data(self, address, register, data_length):
        try:
            self.h.write([
                0x11, address, 0x00, data_length,
                0x02, register >> 8, register & 0xFF
            ])

            for _ in range(10):
                self.h.write([0x15, 0x01])
                response = self.h.read(7)
                print(f"Status response: {[hex(x) for x in response]}")

                if (response[0] == 0x16) and (response[2] == 5):
                    self.h.write([0x12, 0x00, data_length])
                    response = self.h.read(data_length + 3)
                    print(f"Data response: {[hex(x) for x in response]}")

                    if response[0] == 0x13:
                        if data_length == 1:
                            return response[3]
                        elif data_length == 2:
                            return (response[3] << 8) | response[4]
            self.I2CError()
        except Exception as e:
            print(f"Read error: {e}")
            self.I2CError()

    def read_multiple_bytes(self, address, register, num_bytes):
        try:
            return [self.read_data(address, register + i, 1) for i in range(num_bytes)]
        except Exception as e:
            print(f"Error reading multiple bytes: {e}")
            self.I2CError()

    def write_multiple_bytes(self, address, register, data):
        try:
            for i, value in enumerate(data):
                self.write_data(address, register + i, value, 1)
        except Exception as e:
            print(f"Error writing multiple bytes: {e}")
            self.I2CError()

    def I2CError(self):
        print("Resetting device...")
        try:
            self.h.send_feature_report([0x01, 0x01])
        except Exception as e:
            print(f"Error resetting device: {e}")
        finally:
            self.h.close()
            time.sleep(3)
            self.open_device()
            raise IOError("I2C error, device reset and reopened.")

class I2CGUI:
    def __init__(self, root, i2c):
        self.root = root
        self.i2c = i2c
        self.root.title("I2C Control (16-bit registers)")

        self.addressbin_label = tk.Label(root, text="Slave address (7-bit BIN):")
        self.addressbin_label.grid(row=0, column=0, padx=10, pady=10)
        self.addressbin_entry = tk.Entry(root)
        self.addressbin_entry.grid(row=0, column=1, padx=10, pady=10)
        self.addressbin_entry.insert(0, "1011010")
        self.addressbin_entry.bind("<KeyRelease>", self.sync_bin_to_hex)

        self.address_label = tk.Label(root, text="Slave address (HEX):")
        self.address_label.grid(row=1, column=0, padx=10, pady=10)
        self.address_entry = tk.Entry(root)
        self.address_entry.grid(row=1, column=1, padx=10, pady=10)
        self.address_entry.insert(0, "0x5A")
        self.address_entry.bind("<KeyRelease>", self.sync_hex_to_bin)

        self.register_label = tk.Label(root, text="Register (hex, 16 bits):")
        self.register_label.grid(row=2, column=0, padx=10, pady=10)
        self.register_entry = tk.Entry(root)
        self.register_entry.grid(row=2, column=1, padx=10, pady=10)
        self.register_entry.insert(0, "0x020E")

        self.data_label = tk.Label(root, text="Data to write (hex):")
        self.data_label.grid(row=3, column=0, padx=10, pady=10)
        self.data_entry = tk.Entry(root)
        self.data_entry.grid(row=3, column=1, padx=10, pady=10)
        self.data_entry.insert(0, "0x0000")

        self.data_length_label = tk.Label(root, text="Data length (bytes):")
        self.data_length_label.grid(row=4, column=0, padx=10, pady=10)
        self.data_length_combobox = ttk.Combobox(root, values=["1", "2"])
        self.data_length_combobox.grid(row=4, column=1, padx=10, pady=10)
        self.data_length_combobox.current(0)

        self.write_button = tk.Button(root, text="Write to register", command=self.write_data)
        self.write_button.grid(row=5, column=0, padx=10, pady=10)

        self.read_button = tk.Button(root, text="Read Register", command=self.read_data)
        self.read_button.grid(row=5, column=1, padx=10, pady=10)

        self.read_multiple_label = tk.Label(root, text="Read multiple bytes (count):")
        self.read_multiple_label.grid(row=6, column=0, padx=10, pady=10)
        self.read_multiple_entry = tk.Entry(root)
        self.read_multiple_entry.grid(row=6, column=1, padx=10, pady=10)
        self.read_multiple_entry.insert(0, "4")

        self.read_multiple_button = tk.Button(root, text="Read Multiple Bytes", command=self.read_multiple_bytes)
        self.read_multiple_button.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

        self.result_label = tk.Label(root, text="Result:")
        self.result_label.grid(row=8, column=0, padx=4, pady=10)
        self.result_text = tk.Text(root, height=10, width=50)
        self.result_text.grid(row=8, column=1, padx=6, pady=10)

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

    def write_data(self):
        try:
            address = self.get_address()
            register = int(self.register_entry.get(), 16)
            value = int(self.data_entry.get(), 16)
            data_length = int(self.data_length_combobox.get())
            if data_length == 1 and value > 0xFF:
                raise ValueError("For 8-bit write, data must be 0x00-0xFF")
            elif data_length == 2 and value > 0xFFFF:
                raise ValueError("For 16-bit write, data must be 0x0000-0xFFFF")
            self.i2c.write_data(address, register, value, data_length)
            messagebox.showinfo("Success", "Data written successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Write error: {e}")

    def read_data(self):
        try:
            address = self.get_address()
            register = int(self.register_entry.get(), 16)
            data_length = int(self.data_length_combobox.get())
            data = self.i2c.read_data(address, register, data_length)
            self.result_text.delete(1.0, tk.END)
            if data_length == 1:
                self.result_text.insert(tk.END, f"0x{data:02X}")
            elif data_length == 2:
                self.result_text.insert(tk.END, f"0x{data:04X}")
            messagebox.showinfo("Success", "Data read successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Read error: {e}")

    def read_multiple_bytes(self):
        try:
            address = self.get_address()
            register = int(self.register_entry.get(), 16)
            num_bytes = int(self.read_multiple_entry.get())
            data = self.i2c.read_multiple_bytes(address, register, num_bytes)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, ", ".join([f"0x{byte:02X}" for byte in data]))
            messagebox.showinfo("Success", "Data read successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Read error: {e}")

def main():
    i2c = CP2112_I2C()
    root = tk.Tk()
    gui = I2CGUI(root, i2c)
    root.mainloop()

if __name__ == "__main__":
    main()
