import pygame
import pysftp
import cv2
import os
import json
import datetime
import paramiko
import numpy as np
import mysql.connector
from mysql.connector import Error
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput 
from kivy.uix.video import Video
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
import paho.mqtt.client as mqtt
from kivy.uix.popup import Popup

with open("config.json", "r") as config_file:
    config_data = json.load(config_file)

db_config = config_data["db_config"]
mqtt_config = config_data["mqtt_config"]
sftp_config = config_data["sftp_config"]
strains = []



def upload_to_sftp(local_file_path):
    try:
        with open('config.json') as config_file:
            config = json.load(config_file)
            
        sftp_config = config["sftp"]
        
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # Deactivate Host Key Verification (can be insecure in production)
        with pysftp.Connection(
            sftp_config["host"],
            port=sftp_config["port"],
            username=sftp_config["username"],
            password=sftp_config["password"],
            cnopts=cnopts
        ) as sftp:
            # Generate the timestamp for the file name
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            remote_filename = f"report_{timestamp}.pdf"

            # Upload the local report to the server
            sftp.put(local_file_path, f"{sftp_config['remote_directory']}/{remote_filename}")

            print(f"The report has been successfully uploaded to the server as '{remote_filename}' in the directory '{sftp_config['remote_directory']}'.")
    except Exception as e:
        print(f"Error uploading the report: {e}")



def fetch_strains_from_database():
    strains = []

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Use Plantdb database
        cursor.execute("USE Plantdb")

        # Fetch all the strains from the database and store them in the local list
        cursor.execute("SELECT * FROM strains")
        fetched_strains = cursor.fetchall()
        for strain in fetched_strains:
            strains.append({
                "Strain Name": strain[1],
                "Crossing": strain[2],
                "Breeder": strain[3]
            })

    except Error as e:
        print("Error: ", e)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return strains

def create_pdf(data):
    filename = "plant_report.pdf"

    # Create PDF
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont("Helvetica", 12)

    # Add content to PDF
    y_position = 750  # Initial y position
    for key, value in data.items():
        if key != "Selected Strain":
            c.drawString(100, y_position, f"{key}: {value}")
            y_position -= 20  # Move the cursor upwards by 20 units for each line

    # Save PDF
    c.save()
    print(f"The plant report has been saved as '{filename}'.")
    # Lade den generierten Report auf den Server hoch
    upload_to_sftp(filename)


def create_database():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Check if Plantdb database exists
        cursor.execute("SHOW DATABASES LIKE 'Plantdb'")
        db_exists = cursor.fetchone()

        if not db_exists:
            # Create Plantdb database if not exists
            cursor.execute("CREATE DATABASE Plantdb")
            print("Database 'Plantdb' created successfully.")

        # Use Plantdb database
        cursor.execute("USE Plantdb")

        # Check if 'strains' table exists
        cursor.execute("SHOW TABLES LIKE 'strains'")
        table_exists = cursor.fetchone()

        if not table_exists:
            # Create 'strains' table if not exists
            create_table_query = """
            CREATE TABLE strains (
                id INT AUTO_INCREMENT PRIMARY KEY,
                strain_name VARCHAR(255) NOT NULL,
                crossing VARCHAR(255),
                breeder VARCHAR(255)
            )
            """
            cursor.execute(create_table_query)
            print("Table 'strains' created successfully.")

        # Fetch all the strains from the database and store them in the local list
        cursor.execute("SELECT * FROM strains")
        fetched_strains = cursor.fetchall()
        for strain in fetched_strains:
            strains.append({
                "Strain Name": strain[1],
                "Crossing": strain[2],
                "Breeder": strain[3]
            })

        return strains

    except Error as e:
        print("Error: ", e)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def add_strain(strain_data):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Use Plantdb database
        cursor.execute("USE Plantdb")

        # Insert the strain data into the 'strains' table
        insert_query = "INSERT INTO strains (strain_name, crossing, breeder) VALUES (%s, %s, %s)"
        values = (strain_data["Strain Name"], strain_data["Crossing"], strain_data["Breeder"])
        cursor.execute(insert_query, values)
        connection.commit()

        print("Strain added successfully!")

    except Error as e:
        print("Error: ", e)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

class AddStrainForm(Popup):
    def __init__(self, **kwargs):
        super(AddStrainForm, self).__init__(**kwargs)
        self.title = "Add Strain"
        self.size_hint = (0.8, 0.8)
        self.content = BoxLayout(orientation='vertical', spacing=10)

        self.strain_name_entry = TextInput(multiline=False, hint_text="Strain Name")
        self.crossing_entry = TextInput(multiline=False, hint_text="Crossing")
        self.breeder_entry = TextInput(multiline=False, hint_text="Breeder")

        add_button = Button(text="Add Strain", on_release=self.add_strain)

        self.content.add_widget(self.strain_name_entry)
        self.content.add_widget(self.crossing_entry)
        self.content.add_widget(self.breeder_entry)
        self.content.add_widget(add_button)

    def add_strain(self, instance):
        strain_data = {
            "Strain Name": self.strain_name_entry.text,
            "Crossing": self.crossing_entry.text,
            "Breeder": self.breeder_entry.text
        }
        add_strain(strain_data)
        self.dismiss()


class GenerateReportForm(Popup):
    def __init__(self, strains, selected_strain="", **kwargs):
        super(GenerateReportForm, self).__init__(**kwargs)
        self.title = "Generate Grow Report"
        self.size_hint = (0.8, 0.8)
        self.content = BoxLayout(orientation='vertical', spacing=10)

        self.strain_combo = Spinner(text="Select a Strain", values=["Select a Strain"] + [strain["Strain Name"] for strain in strains])
        self.stage_entry = TextInput(multiline=False, hint_text="Stage (Germination, Growth, Flowering, Harvest)")
        self.start_date_entry = TextInput(multiline=False, hint_text="Start Date (YYYY-MM-DD)")
        self.fertilizer_entry = TextInput(multiline=False, hint_text="Fertilizer")
        self.humidity_entry = TextInput(multiline=False, hint_text="Humidity (%)")
        self.temperature_entry = TextInput(multiline=False, hint_text="Temperature (°C)")
        self.water_consumption_entry = TextInput(multiline=False, hint_text="Water Consumption (ml/day)")
        self.lamp_setting_entry = TextInput(multiline=False, hint_text="Lamp Setting (%)")

        generate_button = Button(text="Generate Grow Report", on_release=self.generate_grow_report)

        self.content.add_widget(self.strain_combo)
        self.content.add_widget(self.stage_entry)
        self.content.add_widget(self.start_date_entry)
        self.content.add_widget(self.fertilizer_entry)
        self.content.add_widget(self.humidity_entry)
        self.content.add_widget(self.temperature_entry)
        self.content.add_widget(self.water_consumption_entry)
        self.content.add_widget(self.lamp_setting_entry)
        self.content.add_widget(generate_button)

        self.selected_strain = selected_strain
        self.strain_combo.text = selected_strain

    def generate_grow_report(self, instance):
        strain_name = self.strain_combo.text
        stage = self.stage_entry.text
        start_date = self.start_date_entry.text
        fertilizer = self.fertilizer_entry.text
        humidity = self.humidity_entry.text
        temperature = self.temperature_entry.text
        water_consumption = self.water_consumption_entry.text
        lamp_setting = self.lamp_setting_entry.text

        report_data = {
            "Selected Strain": strain_name,
            "Stage": stage,
            "Start Date": start_date,
            "Fertilizer": fertilizer,
            "Humidity": humidity,
            "Temperature": temperature,
            "Water Consumption": water_consumption,
            "Lamp Setting": lamp_setting
        }

        create_pdf(report_data)
        self.dismiss()

class StrainInfoPopup(Popup):
    def __init__(self, strain_data, **kwargs):
        super(StrainInfoPopup, self).__init__(**kwargs)
        self.title = strain_data["Strain Name"]
        self.size_hint = (0.8, 0.8)

        # Create a BoxLayout to display the strain information
        content_layout = BoxLayout(orientation="vertical", spacing=10)
        
        # Display the strain information using labels
        for key, value in strain_data.items():
            label = Label(text=f"{key}: {value}", font_size=18)
            content_layout.add_widget(label)

        # Add the content layout to the popup
        self.content = content_layout

class GrowBoxConfig(GridLayout):
    def __init__(self, strains, **kwargs):
        super(GrowBoxConfig, self).__init__(**kwargs)
        self.cols = 3
        self.spacing = 5
        self.padding = 5
        self.strains = strains

        self.grow_box = {}

        for i in range(3):
            for j in range(3):
                key = (i, j)
                box_layout = BoxLayout(orientation='vertical', spacing=5)

                strain_label = Label(text="Strain:")
                strain_button = Button(text="Choose Strain", on_release=self.choose_strain)
                report_button = Button(text="Report", on_release=self.show_report_popup)

                box_layout.add_widget(strain_label)
                box_layout.add_widget(strain_button)
                box_layout.add_widget(report_button)

                self.grow_box[key] = {
                    "strain_label": strain_label,
                    "strain_button": strain_button,
                    "report_button": report_button,
                    "selected_strain": None
                }

                self.add_widget(box_layout)

    def capture_image(self, instance):
        _, frame = self.video_stream.read()

        # Get the current timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        # Save the captured frame as an image file
        image_filename = f"captured_image_{timestamp}.jpg"
        cv2.imwrite(image_filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        print(f"Image '{image_filename}' saved successfully!")

    def build_controls(self):
        # Create a button to capture images
        capture_button = Button(text="Capture Image", size_hint=(0.5, None), height=50)
        capture_button.bind(on_release=self.capture_image)

        # Add the button to the controls layout
        self.controls_layout.add_widget(capture_button)

    def show_strain_info_popup(self, instance, position):
        strain_data = self.selected_strains[position]
        if strain_data["name"]:
            strain_info_popup = StrainInfoPopup(strain_data)
            strain_info_popup.open()

    def choose_strain(self, instance):
        row, col = self.get_grow_box_index(instance)
        if row is not None and col is not None:
            dropdown = DropDown()

            # Add available strains to the dropdown
            for strain in self.strains:
                btn = Button(text=strain["Strain Name"], size_hint_y=None, height=44)
                btn.bind(on_release=lambda btn: self.set_strain(row, col, btn.text, instance))
                dropdown.add_widget(btn)

            # Show the dropdown near the button
            dropdown.open(instance)

    def set_strain(self, row, col, strain_name, instance):
        self.grow_box[(row, col)]["selected_strain"] = strain_name
        self.grow_box[(row, col)]["strain_label"].text = f"Strain: {strain_name}"
        instance.text = strain_name  # Change the "Choose Strain" button text to the selected strain

    def show_report_popup(self, instance):
        row, col = self.get_grow_box_index(instance)
        if row is not None and col is not None:
            strain_name = self.grow_box[(row, col)]["selected_strain"]
            if strain_name is not None:
                popup_layout = BoxLayout(orientation='vertical', spacing=10)
                popup = Popup(title="Report Data", content=popup_layout, size_hint=(0.6, 0.6))

                stage_entry = TextInput(multiline=False, hint_text="Stage (Germination, Growth, Flowering, Harvest)")
                start_date_entry = TextInput(multiline=False, hint_text="Start Date (YYYY-MM-DD)")
                fertilizer_entry = TextInput(multiline=False, hint_text="Fertilizer")
                humidity_entry = TextInput(multiline=False, hint_text="Humidity (%)")
                temperature_entry = TextInput(multiline=False, hint_text="Temperature (°C)")
                water_consumption_entry = TextInput(multiline=False, hint_text="Water Consumption (ml/day)")
                lamp_setting_entry = TextInput(multiline=False, hint_text="Lamp Setting (%)")

                generate_button = Button(text="Generate Report", on_release=lambda x: self.generate_report(strain_name, stage_entry.text, start_date_entry.text, fertilizer_entry.text, humidity_entry.text, temperature_entry.text, water_consumption_entry.text, lamp_setting_entry.text, popup))

                popup_layout.add_widget(Label(text=f"Strain: {strain_name}"))
                popup_layout.add_widget(stage_entry)
                popup_layout.add_widget(start_date_entry)
                popup_layout.add_widget(fertilizer_entry)
                popup_layout.add_widget(humidity_entry)
                popup_layout.add_widget(temperature_entry)
                popup_layout.add_widget(water_consumption_entry)
                popup_layout.add_widget(lamp_setting_entry)
                popup_layout.add_widget(generate_button)

                popup.open()

    def generate_report(self, strain_name, stage, start_date, fertilizer, humidity, temperature, water_consumption, lamp_setting, popup):
        report_data = {
            "Selected Strain": strain_name,
            "Stage": stage,
            "Start Date": start_date,
            "Fertilizer": fertilizer,
            "Humidity": humidity,
            "Temperature": temperature,
            "Water Consumption": water_consumption,
            "Lamp Setting": lamp_setting
        }

        create_pdf(report_data)
        popup.dismiss()
        
    def get_grow_box_index(self, button_instance):
        for key, value in self.grow_box.items():
            if value["strain_button"] == button_instance or value["report_button"] == button_instance:
                return key
        return None, None

class WebcamWidget(BoxLayout):
    def __init__(self, selected_strains, video_stream_config, **kwargs):
        super(WebcamWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.video_stream = cv2.VideoCapture(video_stream_config["url"])
        Clock.schedule_interval(self.update, 1.0 / 30.0)  # Update the stream at 30 frames per second

        # Create an Image widget to display the webcam stream
        self.image_widget = Image(allow_stretch=True)  # Allow the image to stretch to fill the available space

        # Add the Image widget to the layout
        self.add_widget(self.image_widget)

        # Store the selected_strains as an instance variable
        self.selected_strains = selected_strains

    def update(self, dt):
        _, frame = self.video_stream.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Draw labels on the frame
        frame = self.draw_labels(frame)

        # Convert the frame to a texture
        height, width, _ = frame.shape
        texture = Texture.create(size=(width, height))
        texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')

        # Set the texture to the Image widget
        self.image_widget.texture = texture

    def draw_labels(self, frame):
        # Iterate through selected strains and their labels
        for position, strain_data in self.selected_strains.items():
            if strain_data["name"]:
                # Get the position of the box on the stream
                x, y = self.get_box_position(position)

                # Get the color of the label and strain
                label_color = strain_data["label_color"]
                strain_color = strain_data["color"]

                # Draw the label background rectangle
                label_height = 40
                cv2.rectangle(frame, (x, y), (x + 180, y + label_height), label_color, -1)

                # Draw the label text
                cv2.putText(frame, strain_data["name"], (x + 10, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, strain_color, 2)

        return frame

    def get_box_position(self, position):
        # Calculate the position of the box on the stream based on its grid position
        row, col = position
        box_width = self.video_stream.get(cv2.CAP_PROP_FRAME_WIDTH) / 3
        box_height = self.video_stream.get(cv2.CAP_PROP_FRAME_HEIGHT) / 3
        x = int(box_width * col)
        y = int(box_height * row)
        return x, y
    
class WebcamWidget(BoxLayout):
    def __init__(self, selected_strains, **kwargs):
        super(WebcamWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'

        # Load configuration from the config file
        with open('config.json') as config_file:
            config = json.load(config_file)

        # Get the video stream configuration from the config
        video_stream_config = config["video_stream_config"]
        video_url = video_stream_config["url"]

        # Create the video stream using the URL from the config
        self.video_stream = cv2.VideoCapture(video_url)
        Clock.schedule_interval(self.update, 1.0 / 30.0)  # Update the stream at 30 frames per second

        # Create an Image widget to display the webcam stream
        self.image_widget = Image(allow_stretch=True)  # Allow the image to stretch to fill the available space

        # Add the Image widget to the layout
        self.add_widget(self.image_widget)

        # Store the selected_strains as an instance variable
        self.selected_strains = selected_strains

    def update(self, dt):
        _, frame = self.video_stream.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Draw labels on the frame
        frame = self.draw_labels(frame)

        # Convert the frame to a texture
        height, width, _ = frame.shape
        texture = Texture.create(size=(width, height))
        texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')

        # Set the texture to the Image widget
        self.image_widget.texture = texture

    def draw_labels(self, frame):
        # Iterate through selected strains and their labels
        for position, strain_data in self.selected_strains.items():
            if strain_data["name"]:
                # Get the position of the box on the stream
                x, y = self.get_box_position(position)

                # Get the color of the label and strain
                label_color = strain_data["label_color"]
                strain_color = strain_data["color"]

                # Draw the label background rectangle
                label_height = 40
                cv2.rectangle(frame, (x, y), (x + 180, y + label_height), label_color, -1)

                # Draw the label text
                cv2.putText(frame, strain_data["name"], (x + 10, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, strain_color, 2)

        return frame

    def get_box_position(self, position):
        # Calculate the position of the box on the stream based on its grid position
        row, col = position
        box_width = self.video_stream.get(cv2.CAP_PROP_FRAME_WIDTH) / 3
        box_height = self.video_stream.get(cv2.CAP_PROP_FRAME_HEIGHT) / 3
        x = int(box_width * col)
        y = int(box_height * row)
        return x, y




class PlantReportApp(App):
    def __init__(self):
        super(PlantReportApp, self).__init__()
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message

        # Load config from the file
        with open("config.json", "r") as file:
            config_data = json.load(file)
        
        # MQTT configuration
        mqtt_config = config_data.get("mqtt_config", {})
        self.mqtt_server_ip = mqtt_config.get("mqtt_server_ip", "YOUR_MQTT_SERVER_IP")
        self.mqtt_topics = mqtt_config.get("mqtt_topics", [])

        # Temperatur- und Luftfeuchtigkeitswerte (initialisiert mit Dummy-Daten)
        self.temperature = "N/A"
        self.humidity = "N/A"

        # Dictionary to store selected strains and their labels
        self.selected_strains = {}

        # Load selected strains from the config file (if exists)
        self.load_selected_strains()


    def on_mqtt_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT Broker")
        # Nach dem Verbinden die gewünschten Topics abonnieren
        for topic, qos in self.mqtt_topics:
            self.mqtt_client.subscribe(topic, qos)

    def on_mqtt_message(self, client, userdata, msg):
        # Die Funktion, die bei empfangenen MQTT-Nachrichten aufgerufen wird
        topic = msg.topic
        message = msg.payload.decode("utf-8")

        if topic == "/report/hum":
            self.humidity = message
        elif topic == "/report/temp":
            self.temperature = message

    def load_selected_strains(self):
        if os.path.exists("selected_strains.json"):
            with open("selected_strains.json", "r") as file:
                self.selected_strains = json.load(file)

    def save_selected_strains(self):
        with open("selected_strains.json", "w") as file:
            json.dump(self.selected_strains, file)

    def build(self):
        create_database()
        strains = fetch_strains_from_database()

        main_layout = BoxLayout(orientation='vertical', spacing=10)

        # Add Growbox configuration
        grow_box_config = GrowBoxConfig(strains)
        main_layout.add_widget(grow_box_config)

        # Add the WebcamWidget to the main layout
        webcam_widget = WebcamWidget(self.selected_strains)
        main_layout.add_widget(webcam_widget)

        # Add buttons for "Add Strain" and "Generate Report" below the Growbox
        button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.1))

        add_strain_button = Button(text="Add Strain", size_hint=(0.5, 1), on_release=self.show_add_strain_form)
        generate_report_button = Button(text="Generate Report", size_hint=(0.5, 1), on_release=lambda x: self.show_generate_report_form(strains))

        button_layout.add_widget(add_strain_button)
        button_layout.add_widget(generate_report_button)

        main_layout.add_widget(button_layout)

        # Verbindung zum MQTT-Broker herstellen und auf eingehende Nachrichten lauschen
        self.mqtt_client.connect(self.mqtt_server_ip)
        self.mqtt_client.loop_start()

        return main_layout

    def on_stop(self):
        # Aufgerufen, wenn die App beendet wird
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    def show_add_strain_form(self, instance):
        add_strain_form = AddStrainForm()
        add_strain_form.open()

    def show_strain_info_popup(self, position):
        # Get the strain data from the selected_strains dictionary based on the position
        strain_data = self.root.grow_box_config.selected_strains[position]
        if strain_data["name"]:
            strain_info_popup = StrainInfoPopup(strain_data)
            strain_info_popup.open()
            
    def show_generate_report_form(self, strains):
        generate_report_form = GenerateReportForm(strains)
        generate_report_form.open()


if __name__ == "__main__":
    strains = create_database()  # Fetch strains from the database
    PlantReportApp().run()

