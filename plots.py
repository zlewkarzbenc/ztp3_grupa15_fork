import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt

def plot_means(monthly_means, cities, years):
    """
    Rysuje wykres liniowy trendu średnich miesięcznych PM2.5 dla wybranych miast i lat.

    Args:
        monthly_means (pandas.DataFrame): Średnie miesięczne PM2.5 dla stacji.
        cities (list[str]): Lista nazw miejscowości.
        years (list[int]): Lista lat do porównania.

    Returns:
        None: Funkcja wyświetla wykres.
    """
    # filtrowanie danych do wybranych miast oraz liczenie średniej miesięcznej dla miasta
    city_monthly = (
        monthly_means[monthly_means["Miejscowość"].isin(cities)]
        .groupby(["Rok", "Miesiąc", "Miejscowość"])["Mean PM25"]
        .mean()
        .reset_index()
    )

    # ;pivot danych tak żeby łatwiej było stworzyć wykres
    df = city_monthly[city_monthly["Rok"].isin(years)]
    df = df.pivot_table(
        values="Mean PM25",
        index="Miesiąc",
        columns=["Miejscowość", "Rok"]
    )

    plt.figure()
    for city in cities:
        for year in years:
            plt.plot(df.index, df[(city, year)], label=f"{city} {year}")

    plt.legend()
    plt.xlabel("Miesiąc")
    plt.ylabel("Średnia miesięczna wartość PM25")
    plt.title(
        f"Trend średnich miesięcznych PM2.5 w Warszawie i Katowicach w latach {years[0]} i {years[1]}"
    )
    plt.grid(True)
    plt.show()


def heatmaps_means(city_monthly, years):
    """
    Tworzy heatmapy średnich miesięcznych stężeń PM2.5 dla każdej miejscowości.

    Args:
        city_monthly (pandas.DataFrame): Średnie miesięczne PM2.5 dla miejscowości.
        years (list[int]): Lista lat uwzględnianych na heatmapach.

    Returns:
        matplotlib.figure.Figure: Obiekt figury z heatmapami.
    """
    
    df = city_monthly.copy()
    # weryfikacja, że kolumny mają poprawne typy (czyli liczbowe)
    df["Mean PM25"] = pd.to_numeric(df["Mean PM25"], errors="coerce")
    df["Rok"] = pd.to_numeric(df["Rok"], errors="coerce").astype("Int64")
    df["Miesiąc"] = pd.to_numeric(df["Miesiąc"], errors="coerce").astype("Int64")
    # filtrowanie wybranych lat
    df = df[df["Rok"].isin(years)]

    cities = df["Miejscowość"].unique()
    vmin, vmax = df["Mean PM25"].min(), df["Mean PM25"].max()

    # siatka wykresów i dla każdego miasta heatmapa
    fig, axes = plt.subplots(6, 3, figsize=(18, 36))
    axes = axes.flatten()

    for ax, city in zip(axes, cities):
        data = df[df["Miejscowość"] == city]
        pivot = data.pivot(index="Rok", columns="Miesiąc", values="Mean PM25")
        pivot = pivot.reindex(years)
        hm = sns.heatmap(pivot, vmin=vmin, vmax=vmax, ax=ax)

        ax.set_title(city, fontsize=16)
        ax.set_xlabel("Miesiąc", fontsize=16)
        ax.set_ylabel("Rok", fontsize=14)

        cbar = hm.collections[0].colorbar
        cbar.set_label("PM2.5 [ug/m3]", fontsize=12)

    for ax in axes[len(cities):]:
        ax.axis("off")

    plt.tight_layout()
    return fig


def plot_overnorm(over_counts, selected, years):
    """
    Rysuje wykres słupkowy liczby dni z przekroczeniem normy PM2.5 dla wybranych stacji.

    Args:
        over_counts (pandas.DataFrame): Liczba dni z przekroczeniem normy PM2.5.
        selected (pandas.DataFrame): Wybrane stacje do wizualizacji.
        years (list[int]): Lista lat uwzględnianych na wykresie.

    Returns:
        None: Funkcja wyświetla wykres.
    """

    df = over_counts.copy()
    stations = selected["Kod stacji"].unique()
    df = df[df["Kod stacji"].isin(stations)]
    df = df[df["Rok"].isin(years)]
    y_col = df.columns[-1]

    plt.figure()
    sns.barplot(data=df, x="Kod stacji", y=y_col, hue="Rok")
    plt.title("Liczba dni z przekroczeniem normy dobowej PM2.5")
    plt.xlabel("Stacja")
    plt.ylabel("Liczba dni z przekroczeniem")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_wojewodztwa(df: pd.DataFrame, year: int = 2024, treshold: int = 15):
    """
    Rysuje wykres słupkowy liczby dni z przekroczeniem normy PM2.5 dla wszystkich województw.
    
    Args:
        df (pandas.DataFrame): Liczba dni z przekroczeniem normy PM2.5.
        year (int): Rok pochodzenia danych uwzględnianych na wykresie.
        treshold (int): maksymalne dopuszczalne stężenie PM2.5

    Returns:
        None: Funkcja wyświetla wykres.
    """

    sns.set_theme(style="whitegrid", context="talk")

    df = df.sort_values(ascending=False)
   
    df = df.reset_index()
    df.columns = ["name", "value"]

    fig, ax = plt.subplots(figsize=(16, 10))

    sns.barplot(
        data=df,
        x="name",
        y="value",
        hue="name",
        palette='magma',
        ax=ax,
    )

    ax.set_title(f"Liczba dni z przekroczeniem normy stężenia PM2.5 w roku {year} w poszczególnych województwach")

    # Rotate long labels
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")

    # Add value labels on top of bars
    for container in ax.containers:
        # ax.bar_label(container, fmt="%.2f", padding=3)
        ax.bar_label(container, padding=3)

    # Labels and legend
    ax.set_xlabel("")
    ax.set_ylabel(f"Liczba dni z przekroczeniem progu {treshold} µg/m³")

    plt.tight_layout()
    plt.show()