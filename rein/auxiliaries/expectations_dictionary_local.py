# Dictionary of Hand Written expectations.
#
# Note: the benchmark reads every value as a string, so number ranges are
# written as regexes (expect_column_values_to_be_between does not work here).


# column groups that are too long to write one rule per line

# soilmoisture: 125 reflectance channels, 454 nm to 950 nm in 4 nm steps
soilmoisture_channels = [str(nm) for nm in range(454, 951, 4)]

# mercedes: binary features X10 to X385 (these 8 numbers are missing in the data)
mercedes_missing = [25, 72, 121, 149, 188, 193, 303, 381]
mercedes_binary = ['X' + str(i) for i in range(10, 386) if i not in mercedes_missing]

# smartfactory: 18 sensor columns
smartfactory_sensors = ['i_w_blo_weg', 'o_w_blo_power', 'o_w_blo_voltage',
                        'i_w_bhl_weg', 'o_w_bhl_power', 'o_w_bhl_voltage',
                        'i_w_bhr_weg', 'o_w_bhr_power', 'o_w_bhr_voltage',
                        'i_w_bru_weg', 'o_w_bru_power', 'o_w_bru_voltage',
                        'i_w_hr_weg', 'o_w_hr_power', 'o_w_hr_voltage',
                        'i_w_hl_weg', 'o_w_hl_power', 'o_w_hl_voltage']


DATASET_EXPECTATIONS = {
    'beers': {
        'hand_written': [

            {'column': 'ounces', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+(\.\d+)?$'}},

            {'column': 'abv', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+(\.\d+)?$'}},

            {'column': 'brewery_id', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'state', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[A-Z]{2}$'}},

            {'column': 'ibu', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(\d+(\.\d+)?)?$'}},

            {'column': 'id', 'expectation': 'expect_column_values_to_be_unique',
            'kwargs': {}},

            {'column': 'style', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'.+'}},

            {'column': 'city', 'expectation': 'expect_column_values_to_not_match_regex',
            'kwargs': {'regex': r' [A-Z]{2}$'}},

        ]
    },

#     'beers': [
#     {'column': 'index', 'expectation': 'expect_column_values_to_match_regex',
#     'kwargs': {'regex': r'^\d+$'}},
#     {'column': 'id', 'expectation': 'expect_column_values_to_be_unique',
#     'kwargs': {}},
#     {'column': 'id', 'expectation': 'expect_column_values_to_match_regex',
#     'kwargs': {'regex': r'^\d+$'}},
#     {'column': 'style', 'expectation': 'expect_column_values_to_match_regex',
#     'kwargs': {'regex': r'\S'}},
#     {'column': 'ounces','expectation': 'expect_column_values_to_match_regex',
#     'kwargs': {'regex': r'^\d+(\.\d+)?$'}},
#     {'column': 'abv', 'expectation': 'expect_column_values_to_match_regex',
#     'kwargs': {'regex': r'^0\.\d+$'}},
#     {'column': 'ibu', 'expectation': 'expect_column_values_to_not_be_in_set',
#     'kwargs': {'value_set': ['N/A', 'n/a', 'NA', 'null', 'NULL', '?', '-']}},
#     {'column': 'brewery_id', 'expectation': 'expect_column_values_to_match_regex',
#     'kwargs': {'regex': r'^\d+$'}},
#     {'column': 'city', 'expectation': 'expect_column_values_to_not_match_regex',
#     'kwargs': {'regex': r'\s[A-Z]{2}$'}},
#     {'column': 'state', 'expectation': 'expect_column_values_to_match_regex',
#     'kwargs': {'regex': r'^[A-Z]{2}$'}},
# ]   #these expectations deliveres a 1.00 precision / recall / F1

    'nasa': {
        'hand_written': [

            # frequency in Hz, 200 to 20000
            {'column': 'frequency', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d{3,5}(\.\d+)?$'}},

            # angle in degrees, 0 to 22
            {'column': 'angle', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([0-9]|1[0-9]|2[0-2])(\.\d+)?$'}},

            # chord length in metres, below 1
            {'column': 'chord_length', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^0\.\d+$'}},

            # velocity in m/s, 31 to 72
            {'column': 'velocity', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(3[1-9]|[4-6][0-9]|7[0-2])(\.\d+)?$'}},

            # thickness in metres, below 1
            {'column': 'thickness', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^0\.\d+$'}},

            # sound pressure level in dB, 2 or 3 digits
            {'column': 'sound_pressure_level', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d{2,3}(\.\d+)?$'}},

        ]
    },

    'breast_cancer': {
        'hand_written': [

            # row number
            {'column': 'Unnamed: 0', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'Unnamed: 0', 'expectation': 'expect_column_values_to_be_unique',
            'kwargs': {}},

            # sample code, 5 to 8 digits (not unique: a patient can appear twice)
            {'column': 'Sample code number', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d{5,8}$'}},

            # 1 to 10, or '?' which is the missing marker of the original data
            {'column': 'Bare Nuclei', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10|\?)$'}},

            # 2 = benign, 4 = malignant
            {'column': 'class', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[24]$'}},

            # the other attributes are graded 1 to 10
            {'column': 'Clump Thickness', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10)$'}},

            {'column': 'Uniformity of Cell Size', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10)$'}},

            {'column': 'Uniformity of Cell Shape', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10)$'}},

            {'column': 'Marginal Adhesion', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10)$'}},

            {'column': 'Single Epithelial Cell Size', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10)$'}},

            {'column': 'Bland Chromatin', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10)$'}},

            {'column': 'Normal Nucleoli', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10)$'}},

            {'column': 'Mitoses', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|10)$'}},

        ]
    },

    # the errors in adult are only 1 -> 0 flips in income, so these rules find nothing
    'adult': {
        'hand_written': [

            # age 17 to 90
            {'column': 'age', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(1[7-9]|[2-8][0-9]|90)$'}},

            {'column': 'fnlwgt', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            # education number 1 to 16
            {'column': 'educational_num', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|1[0-6])$'}},

            {'column': 'capital_gain', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'capital_loss', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            # hours per week 1 to 99
            {'column': 'hours_per_week', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|[1-9][0-9])$'}},

            {'column': 'income', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[01]$'}},

            # text columns: words made of letters, digits, - . & ( ), or '?' for unknown
            {'column': 'workclass', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([A-Za-z0-9][A-Za-z0-9\-\.&()]*( [A-Za-z0-9\-\.&()]+)*|\?)$'}},

            {'column': 'education', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([A-Za-z0-9][A-Za-z0-9\-\.&()]*( [A-Za-z0-9\-\.&()]+)*|\?)$'}},

            {'column': 'marital_status', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([A-Za-z0-9][A-Za-z0-9\-\.&()]*( [A-Za-z0-9\-\.&()]+)*|\?)$'}},

            {'column': 'occupation', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([A-Za-z0-9][A-Za-z0-9\-\.&()]*( [A-Za-z0-9\-\.&()]+)*|\?)$'}},

            {'column': 'relationship', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([A-Za-z0-9][A-Za-z0-9\-\.&()]*( [A-Za-z0-9\-\.&()]+)*|\?)$'}},

            {'column': 'race', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([A-Za-z0-9][A-Za-z0-9\-\.&()]*( [A-Za-z0-9\-\.&()]+)*|\?)$'}},

            {'column': 'gender', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([A-Za-z0-9][A-Za-z0-9\-\.&()]*( [A-Za-z0-9\-\.&()]+)*|\?)$'}},

            {'column': 'native_country', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([A-Za-z0-9][A-Za-z0-9\-\.&()]*( [A-Za-z0-9\-\.&()]+)*|\?)$'}},

        ]
    },

    'bike': {
        'hand_written': [

            {'column': 'instant', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'instant', 'expectation': 'expect_column_values_to_be_unique',
            'kwargs': {}},

            # date as a 6 digit number
            {'column': 'dteday', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d{6}(\.\d+)?$'}},

            # season 1 to 4
            {'column': 'season', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[1-4]$'}},

            # year: 0 = 2011, 1 = 2012
            {'column': 'yr', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[01]$'}},

            # month 1 to 12
            {'column': 'mnth', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([1-9]|1[0-2])$'}},

            # hour 0 to 23
            {'column': 'hr', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([0-9]|1[0-9]|2[0-3])$'}},

            {'column': 'holiday', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[01]$'}},

            # weekday 0 to 6
            {'column': 'weekday', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[0-6]$'}},

            {'column': 'workingday', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[01]$'}},

            # weather 1 to 4
            {'column': 'weathersit', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[1-4]$'}},

            # normalised values between 0 and 1
            {'column': 'temp', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(0(\.\d+)?|1(\.0+)?)$'}},

            {'column': 'atemp', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(0(\.\d+)?|1(\.0+)?)$'}},

            {'column': 'hum', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(0(\.\d+)?|1(\.0+)?)$'}},

            {'column': 'windspeed', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(0(\.\d+)?|1(\.0+)?)$'}},

            # ride counts
            {'column': 'casual', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'registered', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'cnt', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

        ]
    },

    'har': {
        'hand_written': [

            {'column': 'Index', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'Index', 'expectation': 'expect_column_values_to_be_unique',
            'kwargs': {}},

            # activity label ('null' is a real label here)
            {'column': 'gt', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(null|sit|stand)$'}},

            # acceleration in m/s^2, -20 to 20
            {'column': 'x', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^-?([0-9]|1[0-9]|20)(\.\d+)?$'}},

            {'column': 'y', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^-?([0-9]|1[0-9]|20)(\.\d+)?$'}},

            {'column': 'z', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^-?([0-9]|1[0-9]|20)(\.\d+)?$'}},

        ]
    },

    'smartfactory': {
        'hand_written': [

            # every sensor value is a whole number, possibly negative
            {'column': column, 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^-?\d+$'}}
            for column in smartfactory_sensors

        ] + [

            # 0 = normal, 1 = fault
            {'column': 'labels', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[01]$'}},

        ]
    },

    'soilmoisture': {
        'hand_written': [

            {'column': 'index', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'index', 'expectation': 'expect_column_values_to_be_unique',
            'kwargs': {}},

            # unix timestamp, 10 digits
            {'column': 'datetime', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d{10}$'}},

            # soil moisture in %, 0 to 100
            {'column': 'soil_moisture', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([0-9]|[1-9][0-9]|100)(\.\d+)?$'}},

            # soil temperature in C, 0 to 60
            {'column': 'soil_temperature', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^([0-9]|[1-5][0-9]|60)(\.\d+)?$'}},

        ] + [

            # reflectance of soil, 0 to 0.40
            {'column': column, 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^(0|0\.[0-3]\d*|0\.40*)$'}}
            for column in soilmoisture_channels

        ]
    },

    'mercedes': {
        'hand_written': [

            {'column': 'ID', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+$'}},

            {'column': 'ID', 'expectation': 'expect_column_values_to_be_unique',
            'kwargs': {}},

            # seconds on the test bench
            {'column': 'y', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^\d+(\.\d+)?$'}},

            # categorical codes: 1 or 2 lowercase letters
            {'column': 'X0', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[a-z]{1,2}$'}},

            {'column': 'X1', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[a-z]{1,2}$'}},

            {'column': 'X2', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[a-z]{1,2}$'}},

            {'column': 'X3', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[a-z]{1,2}$'}},

            {'column': 'X4', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[a-z]{1,2}$'}},

            {'column': 'X5', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[a-z]{1,2}$'}},

            {'column': 'X6', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[a-z]{1,2}$'}},

            {'column': 'X8', 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[a-z]{1,2}$'}},

        ] + [

            # all the other features are 0 or 1
            {'column': column, 'expectation': 'expect_column_values_to_match_regex',
            'kwargs': {'regex': r'^[01]$'}}
            for column in mercedes_binary

        ]
    },

}
