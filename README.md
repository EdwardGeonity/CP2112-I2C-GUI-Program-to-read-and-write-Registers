# CP2112

**CP2112 I2C Controller with GUI**

This repository contains a Python-based application for controlling and communicating with I2C devices using the CP2112 USB-to-I2C bridge. The software provides a graphical user interface (GUI) for easy interaction with I2C devices, allowing users to read from and write to registers, as well as perform sequential read/write operations.

**Features**

    CP2112 Device Initialization:

        Automatically detects and initializes the CP2112 USB-to-I2C bridge.

        Configures GPIO and sets the I2C bus speed to 400 kHz (configurable).

    I2C Communication:

        Write Data: Write 8-bit or 16-bit data to a specific register on an I2C device.

        Read Data: Read 8-bit or 16-bit data from a specific register on an I2C device.

        Sequential Read: Read multiple bytes sequentially from consecutive registers.

        Error Handling: Automatically resets the CP2112 device in case of I2C communication errors.

    Graphical User Interface (GUI):

        Slave Address Input: Specify the I2C device address in hexadecimal format.

        Register Input: Specify the target register address in hexadecimal format.

        Data Input: Enter data to write in hexadecimal format.

        Data Length Selection: Choose between 8-bit (1 byte) or 16-bit (2 bytes) data operations.

        Read Multiple Bytes: Specify the number of bytes to read sequentially.

        Result Display: Outputs the result of read operations in a text box.

    Error Handling and Debugging:

        Detailed error messages for I2C communication failures.

        Debugging information printed to the console for troubleshooting.

**Requirements**

    Hardware:

        CP2112 USB-to-I2C bridge.

        I2C-compatible device (e.g., sensors, EEPROMs, etc.).

    Software:

        Python 3.x

        Libraries: hidapi, tkinter

**Install the required libraries using pip:**

  pip install hidapi

**How to Use**

    Connect the CP2112 Device:

        Plug the CP2112 USB-to-I2C bridge into your computer.

        Connect the I2C device to the CP2112.

    Run the Application:

        Execute the script:
        bash
        Copy

        python cp2112_i2c_gui.py

        The GUI will open, allowing you to interact with the I2C device.

    Using the GUI:

        Enter the Slave Address, Register Address, and Data in hexadecimal format.

        Select the data length (1 byte or 2 bytes).

        Use the Write to Register button to write data or the Read Register button to read data.

        For sequential reads, specify the number of bytes and click Read Multiple Bytes.

**Example Use Cases**

    Reading Sensor Data:

        Read temperature, humidity, or other sensor data from I2C sensors.

    Configuring I2C Devices:

        Write configuration settings to I2C devices such as DACs, ADCs, or EEPROMs.

    Debugging I2C Communication:

        Use the debugging output to troubleshoot I2C communication issues.

**Code Structure**

    CP2112_I2C Class:

        Handles low-level communication with the CP2112 device.

        Implements methods for reading/writing data and handling errors.

    I2CGUI Class:

        Provides a user-friendly interface for interacting with I2C devices.

        Includes input fields, buttons, and a result display area.

    Main Function:

        Initializes the CP2112 device and launches the GUI.

**Screenshot**

![App](https://github.com/user-attachments/assets/cb636a1b-1f2d-4459-9093-545ee4614659)


**Contributing**

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.
License

This project is licensed under the MIT License. See the LICENSE file for details.
Acknowledgments

    Silicon Labs for the CP2112 USB-to-I2C bridge.

    hidapi for providing the Python library for HID device communication.

**Contact**

For questions or support, feel free to reach out

**Donations**

PayPal donations are welcome: edwardgeonity@gmail.com


Based on "Python code to talk to CP2112 I2C to USB bridge IC 'https://github.com/artizirk/cp2112'"
