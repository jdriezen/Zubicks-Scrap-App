#! /usr/bin/python3
""" Zubick's Scrap App.
    Version 0.04.01

Displays the Zubicks price database in a scrolled window
and plots graphs for selected materials and date ranges, and retrieves
price updates from Zubicks website. """

""" CHANGE LOG

Sunday, September 30, 2024
    Added ORDER BY DATESTAMP DESC clause to select statement when populating the
    GTK TreeView.  Records in the scrolled window now appear in descending order,
    with most recent data first.

Monday July 3, 2023
    Fixed bug where buttons expand when window is maximized.
    Implemented daterange filter function.  The scrolled window now filters data display
    by records in the daterange filter.

Sunday July 2, 2023
    Changed matplotlib.pyplot.plot_date call to matplotlib.pyplot.step call.
    plot_date call will be deprecated in the future.

Monday June 13, 2021
    Changed start_date from the UNIX epoch to the datestamp of first database table entry.
    Added DISTINCT clause to SQLite query fetching datestamp of last database update.

Tuesday July 20, 2021
    Added a menubar at the top of the application window.
    Added an about dialog for the application.
    Added full names of code mentors in about dialog.
    Added credits for open source software used.

Monday July 5, 2021
    Modified plotgraph subroutine to label every nth tickmark on the date axis
    when plotting graphs with date ranges of 2 years or more.

"""

""" ROADMAP / TODO List

Add support for multiple scrap yards by writing new scrapers and changing
some SQL queries to add WHERE YARD = Selected_Yard clause.

Add column to SQLite database to show price change from previous date.

Add unit conversion of masses in a separate window under Tools menu.

"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from datetime import *
from dateutil.relativedelta import *
from pprint import pprint as pp
from pprint import pformat
import bs4 as bs
import urllib.request
import sqlite3
import os
import sys

import matplotlib.pyplot
import matplotlib.dates
import matplotlib.ticker

# Global constants

# change to suit your system
BASE_DIR = '/home/john/Desktop/ZSAPresentation/'
DB_FILE = BASE_DIR+'zubicksprices.db'
POUNDS_PER_NET_TONNE = 2000

CENT_SIGN = '\u00A2' # unicode character for cent symbol

MONTH_NAMES = []
MONTH_NAMES.append("None")
MONTH_NAMES.append("January")
MONTH_NAMES.append("February")
MONTH_NAMES.append("March")
MONTH_NAMES.append("April")
MONTH_NAMES.append("May")
MONTH_NAMES.append("June")
MONTH_NAMES.append("July")
MONTH_NAMES.append("August")
MONTH_NAMES.append("September")
MONTH_NAMES.append("October")
MONTH_NAMES.append("November")
MONTH_NAMES.append("December")

def month_number(month_str):
    """ Returns the month number of given month string. """
    if month_str == "January":
        month_number_str = '01'
    elif month_str == "February":
        month_number_str = '02'
    elif month_str == "March":
        month_number_str = '03'
    elif month_str == "April":
        month_number_str = '04'
    elif month_str == "May":
        month_number_str = '05'
    elif month_str == "June":
        month_number_str = '06'
    elif month_str == "July":
        month_number_str = '07'
    elif month_str == "August":
        month_number_str = '08'
    elif month_str == "September":
        month_number_str = '09'
    elif month_str == "October":
        month_number_str = '10'
    elif month_str == "November":
        month_number_str = '11'
    elif month_str == "December":
        month_number_str = '12'

    return month_number_str

def create_database():
    """ Creates a new database file. """
    # create database in memory (for now)
    # connection = sqlite3.connect(":memory:")
    # create new database file
    connection = sqlite3.connect(DB_FILE)
    connection.execute('''CREATE TABLE PRICES (YARD CHAR(20) NOT NULL,
                          MATERIAL CHAR(40) NOT NULL,
                          PRICE REAL NOT NULL,
                          UNIT CHAR(5),
                          DATESTAMP TEXT);''')

    connection.commit()
    connection.close()

def fetch_price_updates(self, selected_scrap_yard):
    """ Retrieves price updates from selected_scrap_yard website. """

    # read remote file from Zubicks web site
    if selected_scrap_yard == "Zubicks":
        source = urllib.request.urlopen('https://www.zubicks.com/prices/').read()
        content = bs.BeautifulSoup(source, 'lxml')

    # get datestamp
    for header in content.find_all('h4'):
        header_str = header.text
        if header_str.startswith("Updated"):
            junk, month, day, year = header_str.split()
            datestamp = year + '-' + month_number(month) + '-' + day[0:2]

    # check for existing database
    if os.path.isfile(DB_FILE):
        connection = sqlite3.connect(DB_FILE)
        # get datestamp of last update in database table PRICES
        for row in connection.execute("SELECT DISTINCT DATESTAMP FROM PRICES ORDER BY DATESTAMP DESC LIMIT 1"):
            lastdate = row[0]
        if lastdate == datestamp:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="No prices updates available.",
            )
            dialog.run()
            dialog.destroy()
            connection.close
            return
    else:
        create_database()

    # get price updates and insert into database
    # get price tables
    tables = content.find_all('table')

    # store material price pairs in list
    material_prices = []
    for table in tables:
        table_rows = table.find_all('tr')
        for tr in table_rows:
            td = tr.find_all('td')
            columns = [i.text for i in td]
            if columns:                             # if columns are not empty
                material_prices.append(columns)     # add table data to material prices list

    # connect to database
    connection = sqlite3.connect(DB_FILE)

    # get material prices and insert into database
    for row in range(len(material_prices)):
        material_str = material_prices[row][0].rstrip()             # get first string as material
        priceperunit_str, junk = material_prices[row][1].split('|') # get 2nd string as price per unit and discard 3rd string
        price_str, unit_str = priceperunit_str.split('/')           # get price and unit
        price = float(price_str[1:])                                # convert price string to float
        # convert from price per net tonne to price per pound
        if "nt" in unit_str:
            price = price / float(POUNDS_PER_NET_TONNE)
            unit_str = 'lb'
        # print ("Zubicks", material_str, price, unit_str, datestamp)
        # store scrap_yard, material, price, unit, datestamp in sql database.
        if price > 0:
            connection.execute('INSERT INTO PRICES VALUES (?,?,?,?,?)',
                               ("Zubicks", material_str, price, unit_str,
                                datestamp))

    connection.commit()

    # Read back new records added.
    cursor = connection.execute("SELECT YARD, MATERIAL, PRICE, UNIT, DATESTAMP FROM PRICES WHERE DATESTAMP=?", (datestamp,))

    for record in cursor:
        # Add new record to price liststore.
        self.pricestore.append(record)

    connection.close

    update_message = "Prices updated for "+selected_scrap_yard+" on "+datestamp+"."
    dialog = Gtk.MessageDialog(
        transient_for=self,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=update_message,
    )
    dialog.run()
    dialog.destroy()

def text_cell_data_func(tree_view_column, cell_renderer, model, row, column):
    """ Custom cell data function to display currency. """
    textvalue = model.get(row, column)
    textvalue = textvalue[0]
    return cell_renderer.set_property("text", textvalue)

class TextCellRenderer(Gtk.CellRendererText):
    """ Create custom cell renderer for displaying currency values. """
    def __init__(self):
        super().__init__()
        self.set_property("editable", False)
        self.set_property("font", "sans 12")

class TextTreeViewColumn(Gtk.TreeViewColumn):
    """ A custom TreeViewColumn for displaying currency values. """
    def __init__(self, title, cell_renderer, text=0):
        super().__init__(title, cell_renderer, text=text)
        self.set_cell_data_func(cell_renderer, text_cell_data_func, text)

def currencytostr(dollars):
    """ Converts dollars to formatted string with dollar sign or cent sign.
    Assumes monospaced font."""
    if dollars < 1:
        cents = dollars * 100
        if cents.is_integer():
            formatted_cents = ("{:.0f}"+CENT_SIGN).format(cents)
        else:
            formatted_cents = ("{:.2f}"+CENT_SIGN).format(cents)
        padded_cents = "{:>6}".format(formatted_cents)
        return padded_cents
    else:
        formatted_dollars = "${:.2f}".format(dollars)
        padded_dollars = "{:<6}".format(formatted_dollars)
        return padded_dollars

def currency_cell_data_func(tree_view_column, cell_renderer, model, row, column):
    """ Custom cell data function to display currency. """
    currencyvalue = model.get(row, column)
    currencyvalue = currencyvalue[0]
    currencyvalue = currencytostr(currencyvalue)
    return cell_renderer.set_property("text", currencyvalue)

class CurrencyCellRenderer(Gtk.CellRendererText):
    """ Create custom cell renderer for displaying currency values. """
    def __init__(self):
        super().__init__()
        self.set_property("editable", False)
        self.set_property("font", "monospace 12")

class CurrencyTreeViewColumn(Gtk.TreeViewColumn):
    """ A custom TreeViewColumn for displaying currency values. """
    def __init__(self, title, cell_renderer, text=0):
        super().__init__(title, cell_renderer, text=text)
        self.set_cell_data_func(cell_renderer, currency_cell_data_func, text)

def datetostr(date):
    """Converts dates to formatted string. """
    year, month, day = date.split('-')
    daynum = day.lstrip('0')
    monthnum = int(month.lstrip('0'))
    datestr = MONTH_NAMES[monthnum] + ' ' + daynum + ', ' + year
    return datestr

def date_cell_data_func(tree_view_column, cell_renderer, model, row, column):
    """ Custom cell data function to display dates. """
    datevalue = model.get(row, column)
    datevalue = datevalue[0]
    datevalue = datetostr(datevalue)
    return cell_renderer.set_property("text", datevalue)

class DateCellRenderer(Gtk.CellRendererText):
    """ Create custom cell renderer for displaying date values. """
    def __init__(self):
        super().__init__()
        self.set_property("editable", False)
        self.set_property("font", "sans 12")

class DateTreeViewColumn(Gtk.TreeViewColumn):
    """ A custom TreeViewColumn for displaying date values. """
    def __init__(self, title, cell_renderer, text=0):
        super().__init__(title, cell_renderer, text=text)
        self.set_cell_data_func(cell_renderer, date_cell_data_func, text)

def calculate_date_range(date_selection):
    """ Calculates start_date and end_date of date_selection range. """
    today = date.today()
    end_date = today.strftime("%Y-%m-%d")

    # Calculate start date
    if date_selection == "This Month":
        start_date = (today+relativedelta(months=-1)).strftime("%Y-%m-%d")
    elif date_selection == "Last 2 Months":
        start_date = (today+relativedelta(months=-2)).strftime("%Y-%m-%d")
    elif date_selection == "Last 3 Months":
        start_date = (today+relativedelta(months=-3)).strftime("%Y-%m-%d")
    elif date_selection == "Last 6 Months":
        start_date = (today+relativedelta(months=-6)).strftime("%Y-%m-%d")
    elif date_selection == "Last 9 Months":
        start_date = (today+relativedelta(months=-9)).strftime("%Y-%m-%d")
    elif date_selection == "Last Year":
        start_date = (today+relativedelta(years=-1)).strftime("%Y-%m-%d")
    elif date_selection == "Last 15 Months":
        start_date = (today+relativedelta(months=-15)).strftime("%Y-%m-%d")
    elif date_selection == "Last 18 Months":
        start_date = (today+relativedelta(months=-18)).strftime("%Y-%m-%d")
    elif date_selection == "Last 2 Years":
        start_date = (today+relativedelta(years=-2)).strftime("%Y-%m-%d")
    else:
        # Set start_date to first date in database table PRICES
        if os.path.isfile(DB_FILE):
            connection = sqlite3.connect(DB_FILE)
            # get datestamp of first entry in database table PRICES
            for row in connection.execute("SELECT DISTINCT DATESTAMP FROM PRICES ORDER BY DATESTAMP ASC LIMIT 1"):
                first_date = row[0]
            connection.close
        start_date = first_date

    date_range = (start_date, end_date)

    return date_range

def plotgraph(materialsearch_str, start_date, end_date):
    """ Plots graph of dates vs prices for specified material
    and date range using matplotlib. """
	# check for existing database file
    if os.path.isfile(DB_FILE):
        connection = sqlite3.connect(DB_FILE)

        # select all dates
        # cursor = connection.execute("SELECT * from PRICES WHERE MATERIAL=?", (materialsearch_str,))
        # select dates between start_date and end_date
        cursor = connection.execute("SELECT * from PRICES WHERE MATERIAL=? AND DATESTAMP BETWEEN ? and ?", (materialsearch_str, start_date, end_date,))

        prices = []
        dates = []
        for row in cursor:
            dates.append(row[4])	# store date in list
            prices.append(row[2])	# store price in list

        connection.close
    else:
        print("Database does not exist.")
        raise SystemExit

    # plot using matplotlib
    # strpdate2num() is depracated in matplotlib 3.1
    #days = [matplotlib.dates.strpdate2num('%Y-%m-%d')(date) for date in dates]
    days = [matplotlib.dates.datestr2num(date) for date in dates]

    daysloc = matplotlib.dates.DayLocator()      # every day
    months = matplotlib.dates.MonthLocator()   # every month
    monthsFmt = matplotlib.dates.DateFormatter('%b\n%Y')

    fig, ax = matplotlib.pyplot.subplots(figsize=(12, 9))
    #matplotlib.pyplot.plot_date will be deprecated in the future.  Do not use.
    #ax.plot_date(days, prices, 'bo-', markersize=4, linewidth=2)
    ax.step(days, prices, 'bo-', markersize=4, linewidth=2, where='post')
    selected_yard = "Zubicks"
    title_str = selected_yard + " Purchase Price for\n" + materialsearch_str
    ax.set(xlabel='Date', ylabel='Price per Pound', title=title_str)
    ax.grid(True)

    # format the date ticks
    ax.xaxis.set_major_locator(months)
    ax.xaxis.set_major_formatter(monthsFmt)
    #ax.xaxis.set_minor_locator(daysloc)

    # Label every nth ticklabel on the date axis when plotting date ranges of 2 years or more
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    delta = end_date_obj - start_date_obj
    n = int((delta.days)/365.0)
    #if delta.days >= 730:
    #    n=2
    if n > 1:
        for index, label in enumerate(ax.xaxis.get_ticklabels()):
            if index % n != 0:
                label.set_visible(False)
    #fig.autofmt_xdate()

    # format the price labels
    fmt = '${x:.2f}'
    tick = matplotlib.ticker.StrMethodFormatter(fmt)
    ax.yaxis.set_major_formatter(tick)

    max_yvalue = max(prices)
    min_yvalue = min(prices)

    if min_yvalue < 0.5:
        ypadding = 0.01
    else:
        ypadding = 0.1

    matplotlib.pyplot.ylim(min_yvalue-ypadding, max_yvalue+ypadding)

    matplotlib.pyplot.show()

def populate_yard_combo():
    """ Populates yard selection combobox by reading data from sql database. """
    if os.path.isfile(DB_FILE):
        # Open database file
        connection = sqlite3.connect(DB_FILE)

        # Get list of distinct scrap yards and put in yard_store
        cursor = connection.execute("SELECT DISTINCT YARD FROM PRICES ORDER BY YARD")

        yard_store = Gtk.ListStore(str)

        yard_store.append(["All Yards"])
        for record in cursor:
            yard_store.append(record)

        connection.close()
    else:
        raise SystemExit

    return yard_store

def populate_material_combo():
    """ Populates material selection combobox by reading data from sql database. """
    if os.path.isfile(DB_FILE):
        # Open database file
        connection = sqlite3.connect(DB_FILE)

        # Get list of distinct materials and put in material_store
        cursor = connection.execute("SELECT DISTINCT MATERIAL FROM PRICES ORDER BY MATERIAL")

        material_store = Gtk.ListStore(str)

        material_store.append(["All Materials"])
        for record in cursor:
            material_store.append(record)

        connection.close()
    else:
        raise SystemExit

    return material_store

class ZeffsScrapWindow(Gtk.ApplicationWindow):
    """ The main application window. """
    def populate_treeview(self):
        """ Populates price liststore by reading data from sql database
        and creates a treeview from the price liststore. """
        if os.path.isfile(DB_FILE):
            # Open database file
            connection = sqlite3.connect(DB_FILE)

            # Get list of column properties
            cursor = connection.execute('''PRAGMA table_info(PRICES)''')

            # Get list of column properties
            cursor = connection.execute('''PRAGMA table_info(PRICES)''')

            # Get names of columns
            column_names = [i[1] for i in cursor.fetchall()]

            # Get list of column properties
            cursor = connection.execute('''PRAGMA table_info(PRICES)''')

            # Get datatypes of columns
            column_types = [i[2] for i in cursor.fetchall()]

            # Set types in ListStore for TreeView
            for index, item in enumerate(column_types):
                if item.startswith('CHAR'):
                    column_types[index] = str
                elif item == 'TEXT':
                    column_types[index] = str
                elif item == 'REAL':
                    column_types[index] = float
                elif item == 'INTEGER':
                    column_types[index] = int

            # Get data from database file
            cursor = connection.execute("SELECT YARD, MATERIAL, PRICE, UNIT, DATESTAMP from PRICES ORDER BY DATESTAMP DESC")

            pricelist = cursor.fetchall()

            # Gtk.ListStore will hold data for the TreeView
            # Put data from file into a ListStore
            # store = Gtk.ListStore(str,str,float,str,str) # works
            # now it works better because the number of fields is not hard coded.
            self.pricestore = Gtk.ListStore(*column_types)
            for record in pricelist:
                self.pricestore.append(record)

            # Close database file
            connection.close

        # Initialize filters
        self.current_yard_filter = None
        self.current_material_filter = None
        self.current_daterange_filter = None

        # Create the yard filter, feeding it with the pricestore model
        self.yard_filter = self.pricestore.filter_new()
        # Create the material filter, feeding it with the yard_filter model
        self.material_filter = self.yard_filter.filter_new()
        # Create the daterange filter, feeding it with the material_filter model
        self.daterange_filter = self.material_filter.filter_new()

        # Setting the filter functions
        self.yard_filter.set_visible_func(self.yard_filter_func)
        self.material_filter.set_visible_func(self.material_filter_func)
        self.daterange_filter.set_visible_func(self.daterange_filter_func)

        # Create the treeview, using the sorted filter as a model
        #self.sortedandfilteredtree = Gtk.TreeModelSort(model=self.material_filter)
        # Create the treeview, using the sorted daterange filter as a model
        self.sortedandfilteredtree = Gtk.TreeModelSort(model=self.daterange_filter)
        self.sortedtreeview = Gtk.TreeView.new_with_model(self.sortedandfilteredtree)

        # Add columns to sorted treeview model
        # Column for YARD field, allow sorting
        renderer = TextCellRenderer()
        column0 = TextTreeViewColumn(column_names[0], renderer, text=0)
        column0.set_sort_column_id(0)
        self.sortedtreeview.append_column(column0)

        # Column for MATERIAL fields, allow sorting
        column1 = TextTreeViewColumn(column_names[1], renderer, text=1)
        column1.set_sort_column_id(1)
        self.sortedtreeview.append_column(column1)

        # Column for PRICE field
        renderer = CurrencyCellRenderer()
        column2 = CurrencyTreeViewColumn(column_names[2], renderer, text=2)
        self.sortedtreeview.append_column(column2)

        # Column for UNIT field
        renderer = TextCellRenderer()
        column3 = TextTreeViewColumn(column_names[3], renderer, text=3)
        self.sortedtreeview.append_column(column3)

        # Column for DATESTAMP field, allow sorting
        renderer = DateCellRenderer()
        renderer.set_alignment(1.0, 1.0)
        column4 = DateTreeViewColumn(column_names[4], renderer, text=4)
        # Display most recent datestamps first
        column4.set_sort_order(Gtk.SortType.ASCENDING)
        column4.set_sort_column_id(4)
        self.sortedtreeview.append_column(column4)

    def yard_filter_func(self, model, row, data):
        """ Tests if the yard in the row is the one in the filter """
        if self.current_yard_filter is None:
            return True
        else:
            return model[row][0] == self.current_yard_filter

    def on_yard_combo_changed(self, combo):
        """ Gets selected yard value from yard selection combobox. """
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            selected_yard = model[tree_iter][0]
            if selected_yard == "All Yards":
                self.current_yard_filter = None
            else:
                self.current_yard_filter = selected_yard
            self.yard_filter.refilter()

    def material_filter_func(self, model, row, data):
        """ Tests if the material in the row is the one in the filter """
        if self.current_material_filter is None:
            return True
        else:
            return model[row][1] == self.current_material_filter

    def on_material_combo_changed(self, combo):
        """ Gets selected material value from material selection combobox. """
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            selected_material = model[tree_iter][0]
            if selected_material == "All Materials":
                self.current_material_filter = None
            else:
                self.current_material_filter = selected_material
            self.material_filter.refilter()

    def daterange_filter_func(self, model, iter, data):
        """ Tests if the date in the row is inside the date range filter. """
        if self.current_daterange_filter is None:
            return True
        else:
            # Test if model[iter][4] is greater than sdate and less than edate of the selected_date_range
            (sdate, edate) = calculate_date_range(self.current_daterange_filter)
            return ((sdate <= model[iter][4]) and (model[iter][4] <= edate))

    def on_date_range_combo_changed(self, combo):
        """ Gets selected date range from date_range combobox. """
        selected_date_range = combo.get_active_text()
        if selected_date_range is not None:
            if selected_date_range == "All Dates":
                self.current_daterange_filter = None
            else:
                self.current_daterange_filter = selected_date_range
        self.daterange_filter.refilter()

    def on_update_prices_clicked(self, button):
        """ Retrieves price updates by checking scrap yard website online
        when the update prices button is clicked. """

        tree_iter = self.yard_combo.get_active_iter()
        if tree_iter is not None:
            model = self.yard_combo.get_model()
            selected_yard = model[tree_iter][0]

        if selected_yard == "All Yards":
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Please select a scrap yard.",
            )
            dialog.run()
            dialog.destroy()
        else:
            #dialog = Gtk.MessageDialog(
            #    transient_for=self,
            #    flags=0,
            #    message_type=Gtk.MessageType.INFO,
            #    text="Checking " + selected_yard + " for price updates."
            #)
            #dialog.run()
            fetch_price_updates(self, selected_yard)
            #dialog.destroy()

    def on_plot_graph_clicked(self, button):
        """ Plots graph of selected_material for the selected_date_range
        when the Plot Graph button is clicked. """
        selected_material = None
        selected_date_range = None

        tree_iter = self.material_combo.get_active_iter()
        if tree_iter is not None:
            model = self.material_combo.get_model()
            selected_material = model[tree_iter][0]

        selected_date_range = self.date_range_combo.get_active_text()

        if (selected_material is None) or (selected_material == "All Materials"):
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Please select a material.",
            )
            dialog.run()
            dialog.destroy()
        else:
            date_range = ("", "")

            date_range = calculate_date_range(selected_date_range)

            start_date = date_range[0]
            end_date = date_range[1]

            plotgraph(selected_material, start_date, end_date)

    def __init__(self, app):
        Gtk.Window.__init__(self, title="Zubick's Scrap App", application=app)
        self.set_border_width(10)

        # Create about_action with no state
        about_action = Gio.SimpleAction.new("about", None)
        # Connect about_action to about_callback function
        about_action.connect("activate", self.about_callback)
        # Add about_action to window
        self.add_action(about_action)

        yard_label = Gtk.Label(label="Choose Scrap Yard")
        yard_label.set_justify(Gtk.Justification.LEFT)
        material_label = Gtk.Label(label="Choose Material")
        date_range_label = Gtk.Label(label="Choose Date Range")
        date_range_label.set_justify(Gtk.Justification.RIGHT)

        hbox_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox_top.set_homogeneous(True)
        hbox_top.pack_start(yard_label, False, False, 0)
        hbox_top.pack_start(material_label, False, False, 0)
        hbox_top.pack_start(date_range_label, False, False, 0)

        hbox_middle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox_middle.set_homogeneous(True)
        yard_store = populate_yard_combo()
        self.yard_combo = Gtk.ComboBox.new_with_model(yard_store)
        self.yard_combo.connect("changed", self.on_yard_combo_changed)
        renderer_text = Gtk.CellRendererText()
        self.yard_combo.pack_start(renderer_text, True)
        self.yard_combo.add_attribute(renderer_text, "text", 0)
        self.yard_combo.set_active(0)
        hbox_middle.pack_start(self.yard_combo, False, False, 0)

        material_store = populate_material_combo()
        self.material_combo = Gtk.ComboBox.new_with_model(material_store)
        self.material_combo.connect("changed", self.on_material_combo_changed)
        renderer_text = Gtk.CellRendererText()
        self.material_combo.pack_start(renderer_text, True)
        self.material_combo.add_attribute(renderer_text, "text", 0)
        self.material_combo.set_wrap_width(3)
        self.material_combo.set_active(0)
        hbox_middle.pack_start(self.material_combo, False, False, 0)

        date_ranges = [
            "All Dates",
            "This Month",
            "Last 2 Months",
            "Last 3 Months",
            "Last 6 Months",
            "Last 9 Months",
            "Last Year",
            "Last 15 Months",
            "Last 18 Months",
            "Last 2 Years",
        ]

        self.date_range_combo = Gtk.ComboBoxText()
        self.date_range_combo.connect("changed", self.on_date_range_combo_changed)

        for date_range in date_ranges:
            self.date_range_combo.append_text(date_range)

        self.date_range_combo.set_active(0)
        hbox_middle.pack_start(self.date_range_combo, False, False, 0)

        hbox_bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox_bottom.set_homogeneous(True)

        update_button = Gtk.Button.new_with_label("Get Price Updates")
        update_button.connect("clicked", self.on_update_prices_clicked)
        hbox_bottom.pack_start(update_button, False, False, 0)

        plot_button = Gtk.Button.new_with_label("Plot Graph")
        plot_button.connect("clicked", self.on_plot_graph_clicked)
        hbox_bottom.pack_start(plot_button, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.pack_start(hbox_top, False, False, 0)
        vbox.pack_start(hbox_middle, False, False, 0)
        vbox.pack_start(hbox_bottom, False, False, 0)

        # Use ScrolledWindow to make the TreeView scrollable
        # Only allow vertical scrollbar
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(400)
        scrolled_window.set_min_content_width(400)
        self.populate_treeview()
        scrolled_window.add(self.sortedtreeview)
        vbox.pack_start(scrolled_window, True, True, 0)

        self.add(vbox)
        self.show_all()

    def about_callback(self, action, parameter):
        aboutdialog = Gtk.AboutDialog()

        # lists of authors and documenters
        authors = ["John Driezen (Zeffran)"]
        mentors = ["Paul Nijjar (KWLUG)",
                   "Andrew Lytle (MindFlare Retro Discord)",
                   "Daniel Beal (MindFlare Retro Discord)",
                   "Matt London (MindFlare Retro Discord)"]
        artists = ["Frances Seeley"]
        testers = ["Simon Pasieka"]
        comments = "An application to track scrap metal pricing for various commodities."
        foss = ["Python 3.8.10",
                "GTK+3.0 version 3.24.20",
                "python3-matplotlib version 3.1.2",
                "python3-bs4 version 4.8.2-1",
                "python3-lxml version 4.5.0-1",
                "sqlite3 v2.8.17"]
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(BASE_DIR+"ZSALogo.png")
        aboutdialog.set_program_name("Zubicks Scrap App")
        aboutdialog.set_logo(pixbuf)
        aboutdialog.set_version("0.04")
        aboutdialog.set_copyright("Copyright \xa9 2021 John Driezen")
        aboutdialog.set_comments(comments)
        aboutdialog.set_authors(authors)
        aboutdialog.add_credit_section("Code Mentors", mentors)
        aboutdialog.add_credit_section("Testers", testers)
        aboutdialog.add_credit_section("Logo Artist", artists)
        aboutdialog.add_credit_section("Written With", foss)
        aboutdialog.set_website("http://www.zubicks.com")
        aboutdialog.set_website_label("Zubicks Scrap Yard")

        aboutdialog.connect("response", self.on_close)
        aboutdialog.show()

    # Callback function to destroy the aboutdialog
    def on_close(self, action, parameter):
        action.destroy()

class ZeffsScrapApplication(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self)

        # Create quit_action with no state
        quit_action = Gio.SimpleAction.new("quit", None)
        # Connect quit_action to quit_callback function
        quit_action.connect("activate", self.quit_callback)
        # Add quit_action to the application
        self.add_action(quit_action)

    def do_activate(self):
        win = ZeffsScrapWindow(self)
        win.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Create builder to add the UI to the grid
        builder = Gtk.Builder()
        # Get menubar.ui file if it exists
        try:
            builder.add_from_file(BASE_DIR+"zsa_menubar.ui")
        except:
            sys.exit()

        # Add menubar to the application
        self.set_menubar(builder.get_object("menubar"))

    def quit_callback(self, action, parameter):
        sys.exit()

app = ZeffsScrapApplication()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
