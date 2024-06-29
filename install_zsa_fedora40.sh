#
# Install Dependencies for ZeffScrapApp.py on Fedora Workstation 40
#

# Install python libraries
sudo dnf install python3-gobject
sudo dnf install gobject-introspection
sudo dnf install gobject-introspection-devel

# Install Beautiful Soup 4 Library for parsing HTML
sudo dnf install python3-beautifulsoup4
sudo dnf install python3-lxml
sudo dnf install python3-html5lib

# Install MatPlotLib library for plotting graphs
sudo dnf install python3-matplotlib
sudo dnf install python3-tkinter

# Install DateUtil Library for the relativedelta routines to do date arithmetic
sudo dnf install python3-dateutil

# Install sqlite3
sudo dnf install sqlite
sudo dnf install sqlite-devel
sudo dnf install sqlitebrowser
sudo dnf install sqlite-doc


