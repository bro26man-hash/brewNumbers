# Formulas referenced from:
# "Brew by the Numbers - Add up what's in your beer" by Dr. Michael J. Hall, Zymergy, Summer 1995, vol. 18, no. 2
#
# IBU calculation uses the TastyBrew formula (Greg Noonan, 1995):
# Utilization = 1.65 * 0.000125^(SG-1) * (1 - e^(-0.004 * t))
# IBU = utilization * (AA%/100) * hops_oz * 7489 / volume_gal


# Specific Gravity Formulas


def correction_factor(temp_f):
    return 1.00130346 - \
           (1.34722124e-4 * temp_f) + \
           (2.04052596e-6 * (temp_f ** 2)) - \
           (2.32820948e-9 * (temp_f ** 3))


def corrected_sg(measured_gravity, temp_f):
    '''Returns corrected specific gravity when accounting for temperature related correction factor'''
    c_factor = correction_factor(temp_f)
    return measured_gravity + (c_factor - 1)


# Extract Formulas


def extract(specific_gravity):
    '''Returns weight percent of dissolved materials in wort in degress Plato.
    Parameter: specific_gravity is measured gravity (ie 1.065)'''
    return -668.962 + \
           1262.45 * specific_gravity - \
           776.43 * specific_gravity ** 2 + \
           182.94 * specific_gravity ** 3


def attenuation_coefficient(original_gravity):
    '''Returns attenuation coefficient
    Parameter: original_gravity is measured reading before fermentation'''
    return 0.22 + 0.001 * extract(original_gravity)


def real_extract(original_gravity, final_gravity):
    '''Returns real extract in degrees Plato.
    Parameters: original_gravity measured gravity reading before fermentation
                final_gravity measured gravity reading at end of fermentation'''
    q = attenuation_coefficient(original_gravity)
    return (q * extract(original_gravity) + extract(final_gravity)) / (1 + q)


# Attenuation Formulas


def apparent_attenuation(original_gravity, final_gravity):
    '''Returns apparent attenuation in as a percent of sugar converted to alcohol.
    Parameters: original_gravity measured gravity reading before fermentation
                final_gravity measured gravity reading at end of fermentation'''
    return ((extract(original_gravity) - extract(final_gravity)) / extract(original_gravity)) * 100


def real_attenuation(original_gravity, final_gravity):
    '''Returns real attenuation in as a percent of sugar converted to alcohol.
    Parameters: original_gravity measured gravity reading before fermentation
                final_gravity measured gravity reading at end of fermentation'''
    re = real_extract(original_gravity, final_gravity)
    return ((extract(original_gravity) - re) / extract(original_gravity)) * 100


# Alcohol Content Formulas


def alcohol_content(original_gravity, final_gravity):
    '''Returns alcohol percent by weight.
    Parameters: original_gravity measured gravity reading before fermentation
                final_gravity measured gravity reading at end of fermentation'''
    return (extract(original_gravity) - real_extract(original_gravity, final_gravity)) / (2.0665 - 0.010665 * \
                                                                                          extract(original_gravity))


# Calorie Content Formulas


def extract_calories(original_gravity, final_gravity):
    '''Returns calories derived from residual sugars in beer
    Parameters: original_gravity measured gravity reading before fermentation
                final_gravity measured gravity reading at end of fermentation'''
    return 3.55 * final_gravity * 3.8 * real_extract(original_gravity, final_gravity)


def alcohol_calories(original_gravity, final_gravity):
    '''Returns calories derived from converted ethanol alcohol final beer
    Parameters: original_gravity measured gravity reading before fermentation
                final_gravity measured gravity reading at end of fermentation'''
    return 3.55 * final_gravity * 7.1 * alcohol_content(original_gravity, final_gravity)


def protein_calories(original_gravity, final_gravity):
    '''Returns calories derived from proteins produced during fermentation
    Parameters: original_gravity measured gravity reading before fermentation
                final_gravity measured gravity reading at end of fermentation'''
    return 3.55 * final_gravity * 4.0 * 0.07 * real_extract(original_gravity, final_gravity)


def calories(original_gravity, final_gravity):
    '''Returns sum of all caloric elements of beer
    Parameters: original_gravity measured gravity reading before fermentation
                final_gravity measured gravity reading at end of fermentation'''
    return extract_calories(original_gravity, final_gravity) + alcohol_calories(original_gravity, final_gravity) + \
           protein_calories(original_gravity, final_gravity)


# Carbonation Level


def carbon_dioxide_initial(temp_f):
    '''Returns volumes of Carbon Dioxide when at equilibrium at provided temperature
    Parameter: temp_f is temperature of solution in fahrenheit'''
    return 3.0378 - 5.0062e-2 * temp_f + 2.6555e-4 * temp_f ** 2


def carbon_dioxide_generated(priming_sugar_grams, volume_beer_gallons):
    '''Returns volumes of carbon dioxide produced by a given volume of beer and given mass of priming sugar
    Parameters: priming_sugars_grams is mass of priming sugar in grams
                volume_beer_gallons is volume of beer in gallons'''
    return 6.5811e-2 * (priming_sugar_grams / volume_beer_gallons)


def carbon_dioxide(temp_f, priming_sugars_grams, volume_beer_gallons):
    '''Returns volumes of carbon dioxide in solution
    Parameters: temp_f is temperature of solution in fahrenheit
                priming_sugars_grams is mass of priming sugar in grams
                volume_beer_gallons is volume of beer in gallons'''
    return carbon_dioxide_initial(temp_f) + carbon_dioxide_generated(priming_sugars_grams, volume_beer_gallons)


def how_much_sugar(temp_f, desired_co2, volume_beer_gallons):
    '''Returns the mass of priming sugar in grams to provide to a given volume of beer to achieve a desired volume of CO2
    Parameters: temp_f is temperature of solution in fahrenheit
                desired_co2 is the desired volume of CO2 in final solution
                volume_beer_gallons is volume of beer in gallons'''
    return 15.195 * volume_beer_gallons * (desired_co2 - 3.0378 + 5.0062e-2 * temp_f - 2.6555e-4 * temp_f ** 2)


# IBU (International Bitterness Units) Calculation
# Formula: TastyBrew (Greg Noonan, 1995)
# Reference: "Brew by the Numbers" by Dr. Michael J. Hall

import math


def hop_utilization(alpha_acid_pct, boil_minutes, original_gravity=1.050):
    '''Returns hop utilization as a fraction (0.0 to ~1.0) using the TastyBrew formula.

    The utilization accounts for:
    - Wort gravity: Higher OG reduces isomerization efficiency
    - Boil time: Exponential approach to maximum utilization

    Parameters:
        alpha_acid_pct: hops alpha acid percentage (e.g. 10.0 for 10% AA)
        boil_minutes: time in the boil (e.g. 60 for a 60-min addition)
        original_gravity: wort original gravity (default 1.050)

    Returns:
        utilization as a fraction (e.g. 0.30 = 30%)
    '''
    # Gravity correction: 1.65 * 0.000125^(SG-1)
    gravity_factor = 1.65 * (0.000125 ** (original_gravity - 1))
    # Time-dependent isomerization: (1 - e^(-k*t))
    # k=0.004/min gives results matching homebrew reference values
    time_factor = 1 - math.exp(-0.004 * boil_minutes)
    utilization = gravity_factor * time_factor
    return utilization


def calculate_ibu(alpha_acid_pct, hops_oz, boil_minutes, volume_gal, original_gravity=1.050):
    '''Returns IBU (International Bitterness Units) for a single hop addition.

    Formula: IBU = utilization * (AA%/100) * hops_oz * 7489 / volume_gal

    Parameters:
        alpha_acid_pct: hops alpha acid percentage (e.g. 10.0 for 10% AA)
        hops_oz: ounces of hops added
        boil_minutes: minutes in the boil
        volume_gal: batch volume in gallons
        original_gravity: wort original gravity (default 1.050)

    Returns:
        IBU value (float)
    '''
    utilization = hop_utilization(alpha_acid_pct, boil_minutes, original_gravity)
    aa_fraction = alpha_acid_pct / 100.0
    # 7489 = conversion factor: 1 oz/gal ≈ 7489 mg/L
    ibu = utilization * aa_fraction * hops_oz * 7489.0 / volume_gal
    return ibu


def calculate_ibu_multiple_additions(additions, volume_gal, original_gravity=1.050):
    '''Returns total IBU for multiple hop additions.

    Parameters:
        additions: list of dicts with keys:
            - alpha_acid_pct: float (hops alpha acid percentage)
            - hops_oz: float (ounces of hops)
            - boil_minutes: float (minutes in the boil)
        volume_gal: batch volume in gallons
        original_gravity: wort original gravity (default 1.050)

    Returns:
        total IBU (float, sum of all additions)

    Example:
        additions = [
            {'alpha_acid_pct': 12.0, 'hops_oz': 2.0, 'boil_minutes': 60},
            {'alpha_acid_pct': 10.0, 'hops_oz': 1.5, 'boil_minutes': 15},
            {'alpha_acid_pct': 8.0,  'hops_oz': 1.0, 'boil_minutes': 5},
        ]
        total_ibu = calculate_ibu_multiple_additions(additions, 5.0, 1.055)
    '''
    total_ibu = 0.0
    for add in additions:
        ibu = calculate_ibu(
            add['alpha_acid_pct'],
            add['hops_oz'],
            add['boil_minutes'],
            volume_gal,
            original_gravity
        )
        total_ibu += ibu
    return total_ibu
