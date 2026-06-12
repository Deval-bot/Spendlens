"""
generate_data.py — creates a realistic but synthetic steel-plant procurement dataset.
It deliberately reproduces the real mess: the same supplier under several names,
and parts written as plant shorthand. Output: procurement_steel.csv
"""
import csv
import random

random.seed(42)  # same data every run, so our results are repeatable

# (correct name, [messy recorded variants], category)
SUPPLIERS = [
    ("Bosch Rexroth India Limited", ["Bosch Rexroth India Ltd", "BOSCH REXROTH", "Rexroth India"], "Hydraulics"),
    ("Yuken India Limited", ["Yuken India Ltd", "YUKEN INDIA", "yuken india"], "Hydraulics"),
    ("Festo India Private Limited", ["Festo India", "Festo India Pvt Ltd", "FESTO INDIA"], "Pneumatics"),
    ("SMC Pneumatics India Limited", ["SMC Pneumatics", "SMC India", "SMC PNEUMATICS"], "Pneumatics"),
    ("Elecon Engineering Company", ["Elecon Engineering", "ELECON", "Elecon Engg Co"], "Gears & Drives"),
    ("Shanthi Gears Limited", ["Shanthi Gears Ltd", "SHANTHI GEARS", "shanthi gears"], "Gears & Drives"),
    ("SKF India Limited", ["SKF India Ltd", "SKF INDIA", "S.K.F. India Limited"], "Bearings & Spares"),
    ("Schaeffler India Limited", ["Schaeffler India Ltd", "SCHAEFFLER INDIA", "Schaeffler India"], "Bearings & Spares"),
    ("Fenner Conveyor Belting India", ["Fenner India", "Fenner Conveyor Belting", "FENNER INDIA"], "Conveyor & Handling"),
    ("TRF Limited", ["TRF Ltd", "T R F LIMITED", "trf ltd"], "Conveyor & Handling"),
    ("Vesuvius India Limited", ["Vesuvius India Ltd", "VESUVIUS INDIA", "vesuvius india"], "Refractories"),
    ("TRL Krosaki Refractories Limited", ["TRL Krosaki", "TRL Krosaki Refractories Ltd", "T R L KROSAKI"], "Refractories"),
    ("Maithan Alloys Limited", ["Maithan Alloys Ltd", "MAITHAN ALLOYS", "maithan alloys"], "Ferro Alloys"),
    ("Indian Oil Corporation Limited", ["IOCL", "Indian Oil Corp Ltd", "INDIAN OIL"], "Lubricants"),
    ("Castrol India Limited", ["Castrol India Ltd", "CASTROL INDIA", "castrol india"], "Lubricants"),
    ("Larsen and Toubro Limited", ["L&T", "L and T Ltd", "Larsen & Toubro"], "Electrical & Automation"),
    ("Siemens Limited", ["Siemens Ltd", "SIEMENS", "siemens india"], "Electrical & Automation"),
    ("Kirloskar Brothers Limited", ["KBL", "Kirloskar Bros Ltd", "KIRLOSKAR BROTHERS"], "Pumps & Compressors"),
    ("Atlas Copco India Limited", ["Atlas Copco India Ltd", "ATLAS COPCO", "atlas copco"], "Pumps & Compressors"),
    ("Sandvik Asia Private Limited", ["Sandvik Asia", "Sandvik Asia Pvt Ltd", "SANDVIK ASIA"], "Cutting Tools & Rolls"),
]

ITEMS = {
    "Hydraulics": ["HYD CYLINDER 100/56x800 mill", "hyd power pack 90L 210bar", "proportional valve 4WRE 25", "hydraulic hose R2 1in"],
    "Pneumatics": ["PNEU CYLINDER DSBC 63x200", "solenoid valve 5/2 1/4in", "FRL unit 1/2in air prep", "air filter regulator G3/8"],
    "Gears & Drives": ["WORM GEARBOX 1:40 ratio", "helical geared motor 11KW", "bevel gearbox right angle", "gear coupling GC 250"],
    "Bearings & Spares": ["SPHERICAL ROLLER BRG 22320", "deep groove ball brg 6312", "taper roller bearing 32218", "plummer block SNH 517"],
    "Conveyor & Handling": ["CONVEYOR BELT 1200mm EP500/4", "idler roller 152dia", "belt fastener MS clip 1200", "conv pulley lagged 630dia"],
    "Refractories": ["MAG CARBON BRICK MgO-C 14%", "castable LC 60% alumina 25kg", "ladle slide gate plate", "tundish nozzle SEN 70mm"],
    "Ferro Alloys": ["FERRO MANGANESE HC 70pct", "ferro silicon 70 lumps", "silico manganese 60-14", "ferro chrome HC"],
    "Lubricants": ["EP2 grease lithium 18kg", "gear oil 320 ISO VG", "hydraulic oil HLP 68 210L", "turbine oil 46"],
    "Electrical & Automation": ["HT MOTOR 1000KW 6.6KV", "VFD 132KW 415V drive", "PLC S7 input card", "MCCB 400A 4P"],
    "Pumps & Compressors": ["CENTRIFUGAL PUMP 150x125", "screw compressor 250cfm", "submersible pump 30HP", "vacuum pump RH"],
    "Cutting Tools & Rolls": ["WORK ROLL CI HCr mill", "carbide insert CNMG", "grinding wheel 600mm", "slitter knife circular"],
}

BUSINESS_UNITS = ["Blast Furnace", "Steel Melt Shop", "Hot Strip Mill", "Coke Oven",
                  "Sinter Plant", "Plate Mill", "Power Plant", "Central Maintenance"]

BASE_PRICE = {
    "Hydraulics": 85000, "Pneumatics": 18000, "Gears & Drives": 220000,
    "Bearings & Spares": 15000, "Conveyor & Handling": 60000, "Refractories": 35000,
    "Ferro Alloys": 90000, "Lubricants": 12000, "Electrical & Automation": 70000,
    "Pumps & Compressors": 130000, "Cutting Tools & Rolls": 190000,
}

weights = [random.random() ** 2 for _ in SUPPLIERS]  # a few suppliers dominate spend

rows = []
for i in range(4000):
    canonical, variants, category = random.choices(SUPPLIERS, weights=weights, k=1)[0]
    qty = random.randint(1, 500)
    unit_price = round(BASE_PRICE[category] * random.uniform(0.5, 1.8), 2)
    rows.append({
        "po_id": f"PO{100000 + i}",
        "supplier_name_raw": random.choice(variants),
        "true_supplier": canonical,
        "true_category": category,
        "item_description": random.choice(ITEMS[category]),
        "business_unit": random.choice(BUSINESS_UNITS),
        "order_qty": qty,
        "invoice_value": round(unit_price * qty, 2),
    })

with open("procurement_steel.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

recorded = {r["supplier_name_raw"] for r in rows}
real = {r["true_supplier"] for r in rows}
print(f"Wrote {len(rows)} purchase orders to procurement_steel.csv")
print(f"{len(recorded)} different supplier names were recorded...")
print(f"...but they are really only {len(real)} suppliers.")
print("That gap is the problem we're going to solve.")