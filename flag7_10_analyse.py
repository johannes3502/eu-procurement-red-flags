import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Pfad anpassen
file_path = r"C:\Users\Johannes\uni\sose26\dw\red-flags-procurement-governance\data\raw\ted\2022.csv"

df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)

# ------------------------------
# FLAG 7: Price Deviation > 50%
# ------------------------------
print("=== Analyse Flag 7: Preisabweichung ===")

# Konvertiere VALUE_EURO und AWARD_VALUE_EURO zu numerisch
value_est = pd.to_numeric(df['VALUE_EURO'], errors='coerce')
value_act = pd.to_numeric(df['AWARD_VALUE_EURO'], errors='coerce')

# Basisstatistiken
print(f"VALUE_EURO - Anzahl nicht-NA: {value_est.notna().sum()} / {len(df)}")
print(f"VALUE_EURO - Anzahl <= 0: {(value_est <= 0).sum()} (davon 0: {(value_est == 0).sum()})")
print(f"VALUE_EURO - min / max / mean: {value_est.min():.2f} / {value_est.max():.2f} / {value_est.mean():.2f}")

print(f"\nAWARD_VALUE_EURO - Anzahl nicht-NA: {value_act.notna().sum()} / {len(df)}")
print(f"AWARD_VALUE_EURO - Anzahl <= 0: {(value_act <= 0).sum()} (davon 0: {(value_act == 0).sum()})")
print(f"AWARD_VALUE_EURO - min / max / mean: {value_act.min():.2f} / {value_act.max():.2f} / {value_act.mean():.2f}")

# Gemeinsame nicht-NA und positive Werte
valid = (value_est > 0) & (value_act > 0)
print(f"\nGültige Paare (beide > 0): {valid.sum()}")

if valid.sum() > 0:
    deviation = abs(value_act - value_est) / value_est
    print(f"Abweichung > 50% bei gültigen Paaren: {(deviation > 0.5).sum()} / {valid.sum()} ({(deviation > 0.5).sum()/valid.sum()*100:.1f}%)")
    
    # Zeige einige Beispiele mit sehr hoher Abweichung
    high_dev = deviation[deviation > 10].dropna()
    if len(high_dev) > 0:
        print(f"\nBeispiele für extreme Abweichung (>1000%):")
        for idx in high_dev.head(5).index:
            print(f"  ID {df.loc[idx, 'ID_NOTICE_CAN']}: VALUE_EURO={value_est.loc[idx]:.2f}, AWARD={value_act.loc[idx]:.2f}, Faktor={value_act.loc[idx]/value_est.loc[idx]:.1f}")
else:
    print("Keine gültigen Paare (beide >0).")

# Prüfe die Verteilung der Werte (Histogramme)
plt.figure(figsize=(12,4))
plt.subplot(1,2,1)
value_est[value_est < 1e7].hist(bins=50)
plt.title('VALUE_EURO (bis 10 Mio.)')
plt.subplot(1,2,2)
value_act[value_act < 1e7].hist(bins=50)
plt.title('AWARD_VALUE_EURO (bis 10 Mio.)')
plt.tight_layout()
plt.show()

# ------------------------------
# FLAG 10: High Lot Fragmentation (>5 Lose pro Notice)
# ------------------------------
print("\n=== Analyse Flag 10: Los-Fragmentierung ===")

# Prüfe ID_LOT: Wie viele unique Werte pro Notice?
# Achtung: ID_LOT kann leer oder None sein
lot_per_notice = df.groupby('ID_NOTICE_CAN')['ID_LOT'].nunique()
print(f"Anzahl Notices: {lot_per_notice.shape[0]}")
print(f"Lose pro Notice - min / max / mean / median: {lot_per_notice.min()} / {lot_per_notice.max()} / {lot_per_notice.mean():.2f} / {lot_per_notice.median()}")

# Verteilung der Los-Anzahl
print("\nVerteilung der Lose pro Notice (Top 10):")
print(lot_per_notice.value_counts().head(10))

# Anteil mit >5 Losen
high_lot_notices = lot_per_notice[lot_per_notice > 5]
print(f"\nNotices mit >5 Losen: {len(high_lot_notices)} von {len(lot_per_notice)} ({len(high_lot_notices)/len(lot_per_notice)*100:.1f}%)")

# Zeige ein Beispiel-Notice mit vielen Losen
if len(high_lot_notices) > 0:
    example_notice = high_lot_notices.index[0]
    example_rows = df[df['ID_NOTICE_CAN'] == example_notice]
    print(f"\nBeispiel-Notice {example_notice}: {len(example_rows)} Zeilen, Lose: {example_rows['ID_LOT'].tolist()}")