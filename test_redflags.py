import pandas as pd

file_path = r"C:\Users\Johannes\uni\sose26\dw\red-flags-procurement-governance\data\raw\ted\2022.csv"
df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)

print("Geladene Zeilen:", len(df))
print()

# -------------------- KERN-RED FLAGS (1-3) --------------------
mask1 = df['NUMBER_OFFERS'] == 1
mask2 = df['TOP_TYPE'] != "OPE"
mask3 = df['TOP_TYPE'].isin(['NIC', 'AWP'])

# -------------------- EXPLORATIVE RED FLAGS (4-7) --------------------
mask4 = df['B_ACCELERATED'] == "Y"
mask5 = df['B_AWARDED_TO_A_GROUP'] == "Y"

high_value_threshold = df['AWARD_VALUE_EURO'].quantile(0.75)
mask6 = (df['AWARD_VALUE_EURO'] >= high_value_threshold) & (df['NUMBER_OFFERS'] <= 2)

tax_havens = ['KY', 'BM', 'VG', 'BS', 'BB', 'SC', 'MU', 'CH']
mask7 = df['WIN_COUNTRY_CODE'].isin(tax_havens)

# -------------------- FLAG 8: Los-Fragmentierung (Notice-Ebene) --------------------
lot_counts = df.groupby('ID_NOTICE_CAN')['ID_LOT'].nunique()
high_lot_notices = lot_counts[lot_counts > 5].index
notices_total = df['ID_NOTICE_CAN'].nunique()
notices_high = len(high_lot_notices)

# -------------------- Hilfsfunktion für zeilenbasierte Ausgabe --------------------
def count_and_example(mask, flag_name, id_col='ID_NOTICE_CAN'):
    count = mask.sum()
    examples = df.loc[mask, id_col].head(3).tolist()
    print(f"{flag_name:30} {count:6} Treffer  (Beispiele: {examples})")
    return count

# -------------------- Ausgabe --------------------
print("=== KERN-RED FLAGS (1-3) – zeilenbasiert ===")
count1 = count_and_example(mask1, "1. Single-Bidder")
count2 = count_and_example(mask2, "2. Non-Open Procedure")
count3 = count_and_example(mask3, "3. No Prior Call")
print()

print("=== EXPLORATIVE RED FLAGS (4-7) – zeilenbasiert ===")
count4 = count_and_example(mask4, "4. Accelerated Procedure")
count5 = count_and_example(mask5, "5. Award to Group")
count6 = count_and_example(mask6, "6. High Value/Low Bidders")
count7 = count_and_example(mask7, "7. Tax Haven Winner")
print()

print("=== FLAG 8: LOS-FRAGMENTIERUNG (Notice-Ebene) ===")
print(f"8. High Lot Fragmentation (>5 Lose): {notices_high} von {notices_total} Notices ({notices_high/notices_total*100:.1f}%)")
print()

# Optional: Vorgänge mit mindestens einer der Flags 1-7 (ohne Flag 8, da andere Ebene)
any_flag = (mask1 | mask2 | mask3 | mask4 | mask5 | mask6 | mask7)
print(f"Vorgänge mit mindestens einer Red Flag (1-7): {any_flag.sum()} von {len(df)}")