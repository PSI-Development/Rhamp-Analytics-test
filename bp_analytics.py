import time
import logging

class BPAnalytics:

    logging.basicConfig(level=logging.ERROR)

    def __init__(self, measurement_list):
        self.measurement_list = measurement_list
        self.sorted_measurement_list = None
        self.analytics_processing_result = False
        self.quality = None
        self.diagnosis = None
        self.avg_sys = None
        self.avg_dia = None
        self.avg_pr = None
        self.avg_diff = None
        self.__sorted_data = None

    # public method for accessing analytics result
    def get_hbpm_analytics(self):
        self.sorted_measurement_list = self.__sort_measurement_list(self.measurement_list)
        if self.sorted_measurement_list is not None:
            self.__sorted_data = self.__restructure_measurement_data(self.sorted_measurement_list)
            if len(self.__sorted_data) > 0:
                self.__calculate_avg_hbpm(self.sorted_measurement_list, self.__sorted_data)
                self.__check_measurement_quality(self.sorted_measurement_list, self.__sorted_data)
                if self.avg_sys is not None and self.avg_dia is not None:
                    self.__categorize_hbpm_diagnosis(self.avg_sys, self.avg_dia)
                hbpm = {'avg_sys':self.avg_sys, 'avg_dia':self.avg_dia}
                analytics_result = {'hbpm':hbpm, 'diagnosis':self.diagnosis.name, 'quality':self.quality.name}
                self.analytics_processing_result = True
                return analytics_result
        else:
            return {'error':'invalid measurement data format'}

    # sort measurement list received from database based on timestamp with ascending order
    def __sort_measurement_list(self, measurement_list):
        if measurement_list is not None:
            temp_measurement_list = []
            #normalize timestamp from ms to second
            for idx, item in enumerate(measurement_list):
                temp_measurement_list.append(item)
                if(self.__countDigit(item['measurementTime']) > 10):
                    temp_measurement_list[idx]['measurementTime'] = int((temp_measurement_list[idx]['measurementTime'] / 1000))
            return sorted(temp_measurement_list, key = lambda i: i['measurementTime'])
        else:
            return None

    # check if in every morning/evening within 7 days, patient takes at least 2 measurements
    # measurement list given is sorted seven days data
    def __restructure_measurement_data(self, measurement_list):
        data_check = {}
        morning_counter = 0
        evening_counter = 0
        prev_day = 0
        prev_year = 0
        day_idx = 0
        day_idx_name = ""
        for idx, measurement in enumerate(measurement_list):
            date = time.localtime(measurement['measurementTime'])
            day = date.tm_yday
            year = date.tm_year
            if (day > prev_day) or (year > prev_year):
                morning_counter = 0
                evening_counter = 0
                day_idx+=1
                day_idx_name = 'day_' + str(day_idx)
                data_check[day_idx_name] = {}
                data_check[day_idx_name]['morning'] = []
                data_check[day_idx_name]['evening'] = []
            prev_day = day
            prev_year = year 
            if self.__is_morning_data(measurement):
                #data_idx = "day_" + str(idx) + "_morning_" + str(morning_counter)
                try:
                    if morning_counter > 0:
                        logging.debug('multiple morning measurement data, measurement list index=' + str(idx))
                        diff = (measurement['measurementTime']) - (measurement_list[idx-1]['measurementTime'])
                    else:
                        diff = 0
                    data_check[day_idx_name]['morning'].append({'timestamp':(measurement['measurementTime']), 'diff':diff})
                    morning_counter+=1
                except KeyError:
                    logging.debug("Invalid measurement list data")
            elif self.__is_evening_data(measurement):
                try:
                    if evening_counter > 0:
                        logging.debug('multiple evening measurement data, measurement list index=' + str(idx))
                        diff = (measurement['measurementTime']) - (measurement_list[idx-1]['measurementTime'])
                    else:
                        diff = 0
                    data_check[day_idx_name]['evening'].append({'timestamp':(measurement['measurementTime']), 'diff':diff})
                    evening_counter+=1
                except KeyError:
                    logging.debug("Invalid measurement list data")
        return data_check

    # filter data with more than enough data points based on measurement interval for each morning/evening
    def __filter_excellent_data(self, sorted_data):
        for day, day_data in sorted_data.items():
            if len(day_data['morning']) > 2 :
                sorted_list = sorted(day_data['morning'], key=day_data['morning'].get)
                while len(sorted_list) > 2:
                    sorted_data['day']['morning'].pop(sorted_list[-1])
            if len(day_data['evening']) > 2 :
                sorted_list = sorted(day_data['evening'], key=day_data['evening'].get)
                while len(sorted_list) > 2:
                    sorted_data['day']['evening'].pop(sorted_list[-1])         
        return sorted_data

    # based on measurement data points categorize measurement quality
    # if measurement comply with hbpm recommended clinical practice
    def __check_measurement_quality(self, measurement_list, sorted_data):
        num_day_sample = len(sorted_data)
        day_complete_list = []
        # check if each day has min of 2 morning and evening reads each
        for idx, day in sorted_data.items():
            if ('morning' in day) and ('evening' in day):
                if (len(day['morning'])>=2) and (len(day['evening'])>=2):
                    day_complete_list.append(idx)
        if len(day_complete_list) >= 7:
            self.quality = AnalyticsQuality.EXCELLENT
        elif len(day_complete_list) >= 3:
            self.quality = AnalyticsQuality.GOOD
        else:
            self.quality = AnalyticsQuality.BAD

    # based on average hbpm data, categorize diagnosis result based on reference
    # unknown might means normal, as hbpm is intended for use of patient with high blood pressure symptoms
    def __categorize_hbpm_diagnosis(self, avg_sys, avg_dia):
        if avg_sys < 120 and avg_sys < 80:
            self.diagnosis = HBPMCategory.OPTIMAL
        elif 120 <= avg_sys <= 129 or 80 <= avg_dia <= 84:
            self.diagnosis = HBPMCategory.NORMAL
        elif 130 <= avg_sys <= 139 or  85 <= avg_dia <= 89:
            self.diagnosis = HBPMCategory.HIGH_NORMAL_BP
        elif 140 <= avg_sys <= 159 or  90 <= avg_dia <= 99:
            self.diagnosis = HBPMCategory.GRADE_1_HYPERTENSION
        elif 160 <= avg_sys <= 179 or  100 <= avg_dia <= 109:
            self.diagnosis = HBPMCategory.GRADE_2_HYPERTENSION
        elif avg_sys >= 180 or  avg_dia >= 110:
            self.diagnosis = HBPMCategory.GRADE_3_HYPERTENSION
        elif avg_sys >= 140 and avg_dia <= 90:
            self.diagnosis = HBPMCategory.ISOLATED_SYSTOLIC_HYPERTENSION
        else:
            self.diagnosis = HBPMCategory.UNKNOWN

    # calculate average hbpm based on all data points
    def __calculate_avg_hbpm(self, measurement_list, sorted_data):
        sum_sys = 0
        sum_dia = 0
        sum_pr = 0
        sum_diff = 0
        num_points = 0
        sorted_data.pop('day_1') # omit 1st measurement
        for day, day_data in sorted_data.items():
            for record in day_data.get('morning'):
                for item in measurement_list:
                    if record['timestamp'] == item['measurementTime']:
                        sum_sys += int(item['telemetry']['measurement'].get('systolicValue'))
                        sum_dia += int(item['telemetry']['measurement'].get('diastolicValue'))
                        sum_pr += int(item['telemetry']['measurement'].get('pulseRate'))
                        sum_diff += record['diff']
                        num_points += 1
            for record in day_data.get('evening'):
                for item in measurement_list:
                    if record['timestamp'] == item['measurementTime']:
                        sum_sys += int(item['telemetry']['measurement'].get('systolicValue'))
                        sum_dia += int(item['telemetry']['measurement'].get('diastolicValue'))
                        sum_pr += int(item['telemetry']['measurement'].get('pulseRate'))
                        sum_diff += record['diff']
                        num_points += 1
        if num_points != 0:
            self.avg_sys = sum_sys / num_points
            self.avg_dia = sum_dia / num_points
            self.avg_pr = sum_pr / num_points
            self.avg_diff = sum_diff / ( num_points - (len(sorted_data)*2) )

    # check if data point is considered as morning measurement
    def __is_morning_data(self, measurement):
        time_data = time.localtime(measurement['measurementTime'])
        if (time_data.tm_hour < 12) & (time_data.tm_hour > 5):
            return True
        else:
            return False

    # check if data point is considered as evening measurement
    def __is_evening_data(self, measurement):
        time_data = time.localtime(measurement['measurementTime'])
        if (time_data.tm_hour > 12) & (time_data.tm_hour < 24):
            return True
        else:
            return False
    
    # count integer digit used for checking if timestamp is in ms 
    def __countDigit(self, n):
        if n == 0:
            return 0
        return 1 + self.__countDigit(n // 10)

from enum import Enum

class AnalyticsQuality(Enum):
    BAD = 0
    OK = 1
    GOOD = 2
    EXCELLENT = 3

class HBPMCategory(Enum):
    OPTIMAL = 0
    NORMAL = 1
    HIGH_NORMAL_BP = 2
    GRADE_1_HYPERTENSION = 3
    GRADE_2_HYPERTENSION = 4
    GRADE_3_HYPERTENSION = 5
    ISOLATED_SYSTOLIC_HYPERTENSION = 6
    UNKNOWN = 5