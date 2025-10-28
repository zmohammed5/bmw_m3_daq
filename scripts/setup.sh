#!/bin/bash
# BMW M3 DAQ System - Setup Script
# Run this script on first-time installation to configure the Raspberry Pi

set -e  # Exit on error

echo "======================================"
echo "BMW M3 DAQ System - Setup"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
echo "Setting up for user: $ACTUAL_USER"
echo ""

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install system dependencies
echo ""
echo "Installing system dependencies..."
apt-get install -y \
    python3-pip \
    python3-venv \
    git \
    i2c-tools \
    gpsd \
    gpsd-clients \
    bluetooth \
    bluez \
    python3-dev \
    libatlas-base-dev \
    libopenjp2-7

# Enable I2C
echo ""
echo "Enabling I2C..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
    echo "I2C enabled (reboot required)"
else
    echo "I2C already enabled"
fi

# Enable 1-Wire (for DS18B20 temperature sensors)
echo ""
echo "Enabling 1-Wire..."
if ! grep -q "^dtoverlay=w1-gpio" /boot/config.txt; then
    echo "dtoverlay=w1-gpio" >> /boot/config.txt
    echo "1-Wire enabled (reboot required)"
else
    echo "1-Wire already enabled"
fi

# Enable UART for GPS
echo ""
echo "Enabling UART for GPS..."
if ! grep -q "^enable_uart=1" /boot/config.txt; then
    echo "enable_uart=1" >> /boot/config.txt
    echo "UART enabled (reboot required)"
else
    echo "UART already enabled"
fi

# Disable serial console (conflicts with GPS)
echo ""
echo "Disabling serial console..."
systemctl disable serial-getty@ttyS0.service 2>/dev/null || true

# Configure gpsd
echo ""
echo "Configuring gpsd..."
cat > /etc/default/gpsd << EOF
# Default settings for gpsd
START_DAEMON="true"
GPSD_OPTIONS="-n"
DEVICES="/dev/serial0"
USBAUTO="false"
GPSD_SOCKET="/var/run/gpsd.sock"
EOF

# Enable and start gpsd
systemctl enable gpsd
systemctl start gpsd

# Add user to necessary groups
echo ""
echo "Adding $ACTUAL_USER to required groups..."
usermod -a -G dialout,i2c,gpio,bluetooth $ACTUAL_USER

# Create project directory structure
echo ""
echo "Setting up project directory..."
PROJECT_DIR="/home/$ACTUAL_USER/bmw_m3_daq"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Please run this script from the project directory"
    echo "Or manually copy files to $PROJECT_DIR"
else
    cd $PROJECT_DIR

    # Create virtual environment
    echo ""
    echo "Creating Python virtual environment..."
    sudo -u $ACTUAL_USER python3 -m venv venv

    # Install Python packages
    echo ""
    echo "Installing Python dependencies..."
    sudo -u $ACTUAL_USER venv/bin/pip install --upgrade pip
    sudo -u $ACTUAL_USER venv/bin/pip install -r requirements.txt

    # Set permissions
    chown -R $ACTUAL_USER:$ACTUAL_USER $PROJECT_DIR

    echo ""
    echo "======================================"
    echo "Setup Complete!"
    echo "======================================"
    echo ""
    echo "Next steps:"
    echo "1. Reboot the Raspberry Pi: sudo reboot"
    echo "2. After reboot, test sensors: cd $PROJECT_DIR && ./scripts/test_sensors.sh"
    echo "3. Calibrate sensors: venv/bin/python src/utils/calibration.py"
    echo "4. Start logging: venv/bin/python src/main.py"
    echo ""
    echo "Optional:"
    echo "- Enable auto-start: sudo ./scripts/install_service.sh"
    echo "- Start dashboard: venv/bin/python src/dashboard/app.py"
    echo ""
fi
