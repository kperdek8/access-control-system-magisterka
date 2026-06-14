import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import pandas as pd

# 1. Wczytanie danych
df = pd.read_csv("pomiary.csv", decimal=",")

fazy = ["request_preparation", "attribute_fetching", "evaluation"]

# 2. Obliczenie średniej i zachowanie logicznej kolejności
df_srednia = df.groupby("Case")[fazy].mean()
df_srednia = df_srednia.reindex(["best_case", "average_case", "worst_case"])

# 3. Dobór kolorów
kolory = ["#1f4e79", "#2e75b6", "#bdd7ee"]

# Tłumaczenie etykiet legendy na język polski
etykiety_pl = {
    "request_preparation": "Przygotowanie zapytania",
    "attribute_fetching": "Pobranie atrybutów",
    "evaluation": "Ewaluacja decyzji"
}
df_srednia = df_srednia.rename(columns=etykiety_pl)

# 4. Wykres
ax = df_srednia.plot(kind="bar", stacked=True, figsize=(9, 6), color=kolory, edgecolor="black", linewidth=0.7)

# 5. Dodanie wartości całkowitych nad słupkami
# Obliczamy sumę wierszy (całkowity czas), aby wiedzieć, na jakiej wysokości postawić napis
for i, (idx, row) in enumerate(df_srednia.iterrows()):
    calkowity_czas = row.sum()
    ax.text(
        i,
        calkowity_czas + 0.5,                  # Pozycja Y (lekko nad czubkiem słupka)
        f"{calkowity_czas:.2f} ms",            # Sformatowany tekst
        ha="center",                           # Wyrównanie do środka w poziomie
        va="bottom",                           # Wyrównanie od dołu w pionie
        fontsize=10,
        fontweight="bold"                      # Pogrubienie dla czytelności
    )

# 6. Podpisy
plt.title("Średni czas podejmowania decyzji z podziałem na etapy", fontsize=13, fontweight="bold", pad=15)
plt.ylabel("Średni czas wykonania [ms]", fontsize=11)
plt.xlabel("Przypadek testowy", fontsize=11)

# Estetyczne etykiety osi X
etykiety_osi_x = ["Optymistyczny\n(best_case)", "Średni\n(average_case)", "Pesymistyczny\n(worst_case)"]
ax.set_xticklabels(etykiety_osi_x, rotation=0, fontsize=10)

# Dostosowanie siatki (tylko linie poziome, pod słupkami)
plt.grid(axis="y", linestyle="--", alpha=0.5)
ax.set_axisbelow(True)

# Przesunięcie i poprawa legendy
plt.legend(title="Etapy procesu decyzyjnego", loc="upper left", frameon=True, shadow=False, facecolor="white")

# Zwiększenie limitu osi Y, aby napisy nad słupkami nie dotykały krawędzi wykresu
plt.ylim(0, df_srednia.sum(axis=1).max() * 1.15)

# 7. Zapis do pliku (wysoka rozdzielczość 300 DPI idealna do druku)
plt.tight_layout()
plt.savefig("wykres_wydajnosci.png", dpi=300, bbox_inches="tight")

# 8. Wyświetlenie wykresu
plt.show()