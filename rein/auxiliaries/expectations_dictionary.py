# Dictionary of expectations.
DATASET_EXPECTATIONS = {
    'beers':[

        {'column': 'ounces', 'expectation': 'expect_column_values_to_match_regex',
        'kwargs': {'regex': r'^\d+(\.\d+)?$'}},

        {'column': 'abv', 'expectation': 'expect_column_values_to_match_regex',
        'kwargs':{'regex': r'^\d+(\.\d+)?$' }},

        {'column': 'brewery_id', 'expectation': 'expect_column_values_to_match_regex',
        'kwargs': {'regex': r"^\d+$" }},

        {'column': 'state', 'expectation': 'expect_column_values_to_match_regex',
        'kwargs': {'regex': r"^[A-Z]{2}$" }},

         {'column': 'ibu', 'expectation': 'expect_column_values_to_not_be_null',
        'kwargs': {}},

         {'column': 'id', 'expectation': 'expect_column_values_to_be_unique',
        'kwargs': {}},

        {'column': 'style', 'expectation': 'expect_column_values_to_match_regex',
        'kwargs': {'regex': r'.+'}},

        {'column': 'city', 'expectation': 'expect_column_values_to_not_match_regex',
        'kwargs': {'regex': r' [A-Z]{2}$'}},
                


            ]
        
}