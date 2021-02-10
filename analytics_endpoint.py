from bp_analytics import BPAnalytics
from flask import Flask, request
import requests
import json
import logging
import os

app = Flask(__name__)
config = None
logging.basicConfig(level=logging.ERROR)

def load_configuration():
    filename = os.getenv('CONFIG_ANALYTICS')
    if filename is None:
        filename = 'config_analytics.json'
    try:
        with open(filename) as f:
            global config
            config = json.loads(f.read())
            if 'hbpm' not in config:
                logging.error('Invalid configuration file')
    except IOError as e:
        logging.error(e)

def get_user_bp_telemetry(phone_number, duration=196, measurement_status=True):

    url = config['hbpm'].get('bp_db_url')
    query_url = url + str(phone_number) + "/" + str(duration)
    logging.debug(query_url)

    if measurement_status:
        json_payload = {"bodyMovementDetection": 0, "cuffFit": 0, "irregularPulse": 0, "measurementPosition": 0}
        r = requests.get(query_url, json=json_payload)
        if r.ok:
            return r.json()
    else:
        # not implemented yet: in case payload is different or empty
        return f'HBPM Analytics: Request is not complete'
    
    if r.ok:
        return r.json

# flask endpoint /hbpmanalytics/phn/<phone_number>
# hbpm analytics request based on phone number and DEFAULT DURATION
@app.route('/hbpmanalytics/phn/<phone_number>', methods=['GET'])
def api_analytic_request_phn_only(phone_number = None):
    if phone_number is not None:
        measurement_list = get_user_bp_telemetry(phone_number)
        logging.debug(measurement_list)
        if (measurement_list is not None) and (len(measurement_list)>0):
            analytics = BPAnalytics(measurement_list)
            result = analytics.get_hbpm_analytics()
            if len(result) > 0:
                return result
        else:
            f'HBPM Analytics: Measurement Data is not Available'
    else:
        return f'HBPM Analytics: Invalid Request'

# flask endpoint /hbpmanalytics/phn/<phone_number>/<duration>
# hbpm analytics request based on phone number and duration
@app.route('/hbpmanalytics/phn/<phone_number>/<duration>', methods=['GET'])
def api_analytic_request(phone_number = None, duration = None):
    if phone_number is not None:
        measurement_list = get_user_bp_telemetry(phone_number, duration)
        logging.debug(measurement_list)
        if (measurement_list is not None) and (len(measurement_list)>0):
            analytics = BPAnalytics(measurement_list)
            result = analytics.get_hbpm_analytics()
            if len(result) > 0:
                return result
        else:
            f'HBPM Analytics: Measurement Data is not Available'
    else:
        return f'HBPM Analytics: Invalid Request'


# run web server if this py is called as main
if __name__ == '__main__':
    load_configuration()
    app.run(host='0.0.0.0', port=5000, debug=True)