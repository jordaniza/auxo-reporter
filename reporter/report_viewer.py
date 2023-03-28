import dtale
import pandas as pd
import json

# read the data from the json file
with open("reports/test-1/claims-xAUXO.json", "r") as f:
    data = json.load(f)

# create some data
data = pd.DataFrame.from_records(data["recipients"]).T

# start dtale web server
d = dtale.show(
    data, subprocess=False, open_browser=True, allow_edit=False, hide_header_editor=True
)
