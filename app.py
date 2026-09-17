from flask import Flask, request, render_template
from flask_restful import Resource, Api
from formulas import *

app = Flask(__name__)
api = Api(app)

class AllDataWithCorrectedTemps(Resource):


    def get(self, original_gravity, original_temp, final_gravity, final_temp):
        corrected_original_gravity = round(corrected_sg(original_gravity, original_temp), 3)
        corrected_final_gravity = round(corrected_sg(final_gravity, final_temp), 3)
        response = {
            "provided" : {
                "original_gravity": original_gravity,
                "original_temp": original_temp,
                "final_gravity": final_gravity,
                "final_temp": final_temp
            },
            "corrected_original_gravity": corrected_original_gravity,
            "corrected_final_gravity": corrected_final_gravity,
            "alcohol_content": round(alcohol_content(corrected_original_gravity, corrected_final_gravity), 3),
            "attenuation": round(real_attenuation(original_gravity, final_gravity), 3),
            "calories": round(calories(original_gravity, final_gravity), 3)
        }
        return response


class TemperatureCorrection(Resource):


    def get(self, measured_gravity, temp_f):
        response = {
            "provided" : {
                "measured_gravity": measured_gravity,
                "temperature": temp_f
            },
            "corrected_gravity": round(corrected_sg(measured_gravity, temp_f),3)
        }
        return response


class GravitiesOnly(Resource):


    def get(self, original_gravity, final_gravity):
        response = {
            "provided" : {
                "original_gravity": original_gravity,
                "final_gravity": final_gravity,
            },
            "alcohol_content": round(alcohol_content(original_gravity, final_gravity), 3),
            "attenuation": round(real_attenuation(original_gravity, final_gravity), 3),
            "calories": round(calories(original_gravity, final_gravity), 3)
        }
        return response


class HowMuchSugar(Resource):


    def get(self, temp_f, desired_co2, volume_beer_gallons):
        response = {
            "provided": {
                "temp_in_f": temp_f,
                "desired_co2": desired_co2,
                "volume_beer_gallons": volume_beer_gallons
            },
            "req_grams_priming_sugar": round(how_much_sugar(temp_f, desired_co2, volume_beer_gallons), 2)
        }
        return response


class HowMuchCO2(Resource):


    def get(self, temp_f, priming_sugar_grams, volume_beer_gallons):
        response = {
            "provided": {
                "temp_in_f": temp_f,
                "priming_sugar_grams": priming_sugar_grams,
                "volume_beer_gallons": volume_beer_gallons
            },
            "co2": round(carbon_dioxide(temp_f, priming_sugar_grams, volume_beer_gallons), 2)
        }
        return response


class IBUSingleAddition(Resource):
    """Calculate IBU for a single hop addition"""

    def get(self, alpha_acid_pct, hops_oz, boil_minutes, volume_gal, original_gravity=1.050):
        response = {
            "provided": {
                "alpha_acid_pct": alpha_acid_pct,
                "hops_oz": hops_oz,
                "boil_minutes": boil_minutes,
                "volume_gal": volume_gal,
                "original_gravity": original_gravity
            },
            "utilization": round(hop_utilization(alpha_acid_pct, boil_minutes, original_gravity), 4),
            "ibu": round(calculate_ibu(alpha_acid_pct, hops_oz, boil_minutes, volume_gal, original_gravity), 2)
        }
        return response


class IBUMultipleAdditions(Resource):
    """Calculate total IBU for multiple hop additions.

    Expects JSON body with:
    - volume_gal: float (batch volume in gallons)
    - original_gravity: float (optional, default 1.050)
    - additions: list of {alpha_acid_pct, hops_oz, boil_minutes}
    """

    def get(self, volume_gal, original_gravity=1.050):
        # Parse additions from query params as repeated key-value pairs
        # e.g. /ibu/multiple/5.0/1.050?aa=10&oz=1&min=60&aa=8&oz=0.5&min=5
        aa_list = request.args.getlist('aa')
        oz_list = request.args.getlist('oz')
        min_list = request.args.getlist('min')

        if not (aa_list and oz_list and min_list):
            return {"error": "Missing query parameters. Use ?aa=10&oz=1&min=60&aa=8&oz=0.5&min=5"}, 400

        if not (len(aa_list) == len(oz_list) == len(min_list)):
            return {"error": "Mismatched aa/oz/min parameter counts"}, 400

        additions = []
        for i in range(len(aa_list)):
            additions.append({
                'alpha_acid_pct': float(aa_list[i]),
                'hops_oz': float(oz_list[i]),
                'boil_minutes': float(min_list[i])
            })

        total_ibu = calculate_ibu_multiple_additions(additions, volume_gal, original_gravity)

        detail = []
        for add in additions:
            detail.append({
                "alpha_acid_pct": add['alpha_acid_pct'],
                "hops_oz": add['hops_oz'],
                "boil_minutes": add['boil_minutes'],
                "utilization": round(hop_utilization(add['alpha_acid_pct'], add['boil_minutes'], original_gravity), 4),
                "ibu": round(calculate_ibu(add['alpha_acid_pct'], add['hops_oz'], add['boil_minutes'], volume_gal, original_gravity), 2)
            })

        response = {
            "provided": {
                "volume_gal": volume_gal,
                "original_gravity": original_gravity,
                "additions": detail
            },
            "total_ibu": round(total_ibu, 2)
        }
        return response


api.add_resource(GravitiesOnly, '/all/no_correction/<float:original_gravity>/'
                                '<float:final_gravity>')
api.add_resource(AllDataWithCorrectedTemps, '/all/temp_corrected/<float:original_gravity>/'
                                 '<int:original_temp>/'
                                 '<float:final_gravity>/'
                                 '<int:final_temp>')
api.add_resource(HowMuchSugar, '/carbonation/howmuchsugar/<int:temp_f>/'
                               '<float:desired_co2>/'
                               '<float:volume_beer_gallons>')
api.add_resource(HowMuchCO2, '/carbonation/howmuchco2/<int:temp_f>/'
                             '<float:priming_sugar_grams>/'
                             '<float:volume_beer_gallons>')
api.add_resource(TemperatureCorrection, '/temp_correction/<float:measured_gravity>/'
                             '<int:temp_f>/')
api.add_resource(IBUSingleAddition, '/ibu/single/<float:alpha_acid_pct>/'
                                    '<float:hops_oz>/'
                                    '<int:boil_minutes>/'
                                    '<float:volume_gal>/'
                                    '<float:original_gravity>')
api.add_resource(IBUMultipleAdditions, '/ibu/multiple/<float:volume_gal>/'
                                       '<float:original_gravity>')

@app.route('/')
def home_func():
    return render_template("home.html")



if __name__ == "__main__":
    app.run(port=8080, debug=False)
