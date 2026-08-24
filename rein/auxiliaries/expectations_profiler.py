# generates expectations automatically from a dataframe, with no domain knowledge.
# used for two tiers: 
# 'generic' profiles the dirty data 
# 'oracle' profiles the clean data (an upper bound thatis not reachable in practice).

# values that stand for a missing entry
MISSING_TOKENS = ['', 'N/A', 'n/a', 'NA', 'NULL', 'null', '-', '?']

# a plain number, used when a column looks numeric
NUMBER_REGEX = r'^-?\d+(\.\d+)?$'


def looks_numeric(value):
    """
    helper function that checks whether a single value can be read as a number

    Arguments:
    value: the cell value as a string

    Returns:
    True when the value parses as a float
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


def profile_expectations(dataDF, max_set_size=20):
    """
    builds a list of expectations by looking only at the dataframe

    Arguments:
     dataDF: the dataframe to profile
     max_set_size: a column with at most this many distinct values gets a value set rule

    Returns:
    a list of expectations in the same format as DATASET_EXPECTATIONS
    """
    expectations = []

    for column in dataDF.columns:
        values = [str(value) for value in dataDF[column]]
        observed = [value for value in values if value not in MISSING_TOKENS]

        # every column gets a disguised missing value check
        expectations.append({
            'column': column,
            'expectation': 'expect_column_values_to_not_be_in_set',
            'kwargs': {'value_set': MISSING_TOKENS}})

        if not observed:
            continue

        # a column where everything parses as a number should stay numeric
        if all(looks_numeric(value) for value in observed):
            expectations.append({
                'column': column,
                'expectation': 'expect_column_values_to_match_regex',
                'kwargs': {'regex': NUMBER_REGEX}})

        # a column with few distinct values should keep the values it already has
        elif len(set(observed)) <= max_set_size:
            expectations.append({
                'column': column,
                'expectation': 'expect_column_values_to_be_in_set',
                'kwargs': {'value_set': sorted(set(observed))}})

    return expectations