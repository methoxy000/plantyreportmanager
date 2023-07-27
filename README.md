

Before running the Plant Report Automation Script, make sure to configure the config.json file in the project directory. This configuration file contains important settings and credentials used by the script. Below is an overview of the sections in the config.json file:
    
json
    
    {
      "db_config": {
        "host": "your_mysql_host",
        "user": "your_mysql_username",
        "password": "your_mysql_password",
        "database": "Plantdb"
      },
      "mqtt_config": {
        "host": "your_mqtt_host",
        "port": 1883,
        "username": "your_mqtt_username",
        "password": "your_mqtt_password"
      },
      "sftp_config": {
        "hostname": "your_sftp_host",
        "port": 22,
        "username": "your_sftp_username",
        "password": "your_sftp_password",
        "remote_directory": "/home/reportmanager/"
      },
      "video_stream_config": {
        "url": "http://your_video_stream_url_here"
      }
    }

  1. db_config: Contains the configuration for connecting to the MySQL database where the strains information is stored.

  2. mqtt_config: Contains the configuration for connecting to the MQTT broker to receive temperature and humidity data (optional).

  3. sftp_config: Contains the configuration for connecting to the SFTP server to upload generated reports (optional).

  4. video_stream_config: Contains the configuration for the video stream URL used by the webcam widget.

Make sure to replace the placeholder values in the configuration file with your actual credentials and server details. The script will use these settings to connect to the respective services and fetch or upload data as required.

Please exercise caution and do not share the config.json file with sensitive information publicly, as it may contain sensitive server details and credentials. Keep it secure and limit access to authorized users only.
How to Use the Plant Report Automation Script:

Clone the repository to your local machine.

Install the required Python libraries by running the following command in the terminal:


    pip install -r requirements.txt

  Configure the config.json file with your server details and credentials. Replace the placeholder values with your actual data.

  Run the Plant Report Automation Script using the following command:

    python plant_report.py

  The script will start running and display the webcam stream along with the Growbox configuration. Use the GUI to select strains and generate reports.

  If the MQTT and SFTP configurations are provided, the script will also subscribe to temperature and humidity data and upload generated reports to the SFTP server.

    Note: Make sure to keep the config.json file secure and do not share it publicly to prevent unauthorized access to your servers and sensitive data.
