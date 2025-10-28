#!/bin/bash
# Install systemd service for auto-start on boot

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Installing BMW M3 DAQ systemd service..."

# Get actual user
ACTUAL_USER=${SUDO_USER:-$USER}
SERVICE_FILE="scripts/systemd/daq.service"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found: $SERVICE_FILE"
    exit 1
fi

# Copy service file to systemd directory
cp $SERVICE_FILE /etc/systemd/system/

# Update username in service file if not 'pi'
if [ "$ACTUAL_USER" != "pi" ]; then
    sed -i "s/User=pi/User=$ACTUAL_USER/g" /etc/systemd/system/daq.service
    sed -i "s/Group=pi/Group=$ACTUAL_USER/g" /etc/systemd/system/daq.service
    sed -i "s|/home/pi/|/home/$ACTUAL_USER/|g" /etc/systemd/system/daq.service
fi

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable daq.service

echo ""
echo "Service installed successfully!"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start daq"
echo "  Stop:    sudo systemctl stop daq"
echo "  Status:  sudo systemctl status daq"
echo "  Logs:    sudo journalctl -u daq -f"
echo "  Disable: sudo systemctl disable daq"
echo ""
echo "The service will automatically start on boot."
