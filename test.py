import json
from pprint import pprint

with open("metadata-zz0-129.json", "r") as f:
    data = json.load(f)

for building in data:
    if building["name"].startswith("Neo Solar"):
        print(building["name"])
        print(building["asset_id"])
        pprint(building["components"]["SpaceAgeSpaceHub"])
        pprint(
            building["components"]["SpaceAgeSpaceHub"]["lookup"],
            width=100,
            compact=True,
            sort_dicts=False,
            depth=3,
        )

        print("--------------------------------")
