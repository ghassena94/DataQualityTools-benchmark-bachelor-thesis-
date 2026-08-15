# Dictionary of expectations.
DATASET_EXPECTATIONS = {
    # 'beers':[

    #     {'column': 'ounces', 'expectation': 'expect_column_values_to_match_regex',
    #     'kwargs': {'regex': r'^\d+(\.\d+)?$'}},

    #     {'column': 'abv', 'expectation': 'expect_column_values_to_match_regex',
    #     'kwargs':{'regex': r'^\d+(\.\d+)?$' }},

    #     {'column': 'brewery_id', 'expectation': 'expect_column_values_to_match_regex',
    #     'kwargs': {'regex': r"^\d+$" }},

    #     {'column': 'state', 'expectation': 'expect_column_values_to_match_regex',
    #     'kwargs': {'regex': r"^[A-Z]{2}$" }},

    #      {'column': 'ibu', 'expectation': 'expect_column_values_to_not_be_null',
    #     'kwargs': {}},

    #      {'column': 'id', 'expectation': 'expect_column_values_to_be_unique',
    #     'kwargs': {}},

    #     {'column': 'style', 'expectation': 'expect_column_values_to_match_regex',
    #     'kwargs': {'regex': r'.+'}},

    #     {'column': 'city', 'expectation': 'expect_column_values_to_not_match_regex',
    #     'kwargs': {'regex': r' [A-Z]{2}$'}},
                
    #         ]


    'beers': [
    {'column': 'index', 'expectation': 'expect_column_values_to_match_regex',     
    'kwargs': {'regex': r'^\d+$'}},
    {'column': 'id', 'expectation': 'expect_column_values_to_be_unique',       
    'kwargs': {}},
    {'column': 'id', 'expectation': 'expect_column_values_to_match_regex',     
    'kwargs': {'regex': r'^\d+$'}},
    {'column': 'style', 'expectation': 'expect_column_values_to_match_regex',     
    'kwargs': {'regex': r'\S'}},
    {'column': 'ounces','expectation': 'expect_column_values_to_match_regex',     
    'kwargs': {'regex': r'^\d+(\.\d+)?$'}},
    {'column': 'abv', 'expectation': 'expect_column_values_to_match_regex',     
    'kwargs': {'regex': r'^0\.\d+$'}},
    {'column': 'ibu', 'expectation': 'expect_column_values_to_not_be_in_set',   
    'kwargs': {'value_set': ['N/A', 'n/a', 'NA', 'null', 'NULL', '?', '-']}},
    {'column': 'brewery_id', 'expectation': 'expect_column_values_to_match_regex',     
    'kwargs': {'regex': r'^\d+$'}},
    {'column': 'city', 'expectation': 'expect_column_values_to_not_match_regex', 
    'kwargs': {'regex': r'\s[A-Z]{2}$'}},
    {'column': 'state', 'expectation': 'expect_column_values_to_match_regex',     
    'kwargs': {'regex': r'^[A-Z]{2}$'}},
]   #these expectations deliveres a 1.00 precision / recall / F1
        
}