import pandas as pd

def convert_df(df_pm25):
    """
    Przekształca dane PM2.5 z formatu szerokiego na długi i czyści wartości liczbowe.

    Args:
        df_pm25 (pandas.DataFrame): Dane PM2.5 w formacie szerokim z MultiIndex.

    Returns:
        pandas.DataFrame: Dane w formacie długim z kolumnami datetime, Miejscowość, Kod stacji i PM25.
    """

    df = df_pm25.copy()

    formated = (
        df
        .set_index(("datetime", ""))
        .stack(["Miejscowość", "Kod stacji"])
        .reset_index()
    )

    formated.columns = ["datetime", "Miejscowość", "Kod stacji", "PM25"]
    formated["PM25"] = (
        formated["PM25"].astype(str).str.strip()
        .str.replace(",", ".", regex=False)
    )
    formated["PM25"] = pd.to_numeric(formated["PM25"], errors="coerce")

    return formated


def calc_monthly_means(formated):
    """
    Oblicza średnie miesięczne stężenie PM2.5 dla każdej stacji.

    Args:
        formated (pandas.DataFrame): Dane PM2.5 w formacie długim.

    Returns:
        pandas.DataFrame: Średnie miesięczne PM2.5 z podziałem na rok, miesiąc, miejscowość i stację.
    """

    df = formated.copy()

    return (
        df.groupby([
            df["datetime"].dt.year.rename("Rok"),
            df["datetime"].dt.month.rename("Miesiąc"),
            "Miejscowość",
            "Kod stacji"
        ])["PM25"].mean().reset_index(name="Mean PM25")
    )


def calc_monthly_city_means(monthly_means):
    """
    Oblicza średnie miesięczne stężenie PM2.5 dla każdej miejscowości.

    Args:
        monthly_means (pandas.DataFrame): Średnie miesięczne PM2.5 dla stacji.

    Returns:
        pandas.DataFrame: Średnie miesięczne PM2.5 uśrednione po wszystkich stacjach w mieście.
    """
    df = monthly_means.copy()
    df["Mean PM25"] = pd.to_numeric(df["Mean PM25"], errors="coerce")

    return (
        df.groupby(["Rok", "Miesiąc", "Miejscowość"])["Mean PM25"]
        .mean()
        .reset_index()
    )


def calc_daily_means(formated):
    """
    Oblicza dzienne średnie stężenie PM2.5 dla każdej stacji.

    Args:
        formated (pandas.DataFrame): Dane PM2.5 w formacie długim.

    Returns:
        pandas.DataFrame: Dzienne średnie PM2.5 z podziałem na rok, datę, miejscowość i stację.
    """
    df = formated.copy()
    df["PM25"] = pd.to_numeric(df["PM25"], errors="coerce")

    out = (
        df.groupby([
            df["datetime"].dt.year.rename("Rok"),
            df["datetime"].dt.date.rename("Data"),
            "Miejscowość",
            "Kod stacji"
        ])["PM25"]
        .mean()
        .reset_index(name="Daily mean PM25")
    )
    return out


def count_overnorm_days(daily, threshold):
    """
    Liczy dni z przekroczeniem dobowej normy PM2.5 dla każdej stacji.

    Args:
        daily (pandas.DataFrame): Dzienne średnie stężenia PM2.5.
        threshold (float): Wartość graniczna normy PM2.5.

    Returns:
        pandas.DataFrame: Liczba dni z przekroczeniem normy dla każdej stacji i roku.
    """
    df = daily.copy()
    over = df[df["Daily mean PM25"] > threshold]

    out = (
        over.groupby(["Rok", "Kod stacji"])["Data"]
        .nunique()
        .reset_index(name=f"Liczba dni PM25 > {threshold}")
    )
    return out


def top_bottom_stations(over_counts, year, n=3):
    """
    Wybiera stacje z największą i najmniejszą liczbą dni z przekroczeniem normy.

    Args:
        over_counts (pandas.DataFrame): Liczba dni z przekroczeniem normy PM2.5.
        year (int): Rok analizy.
        n (int): Liczba stacji w każdej grupie.

    Returns:
        pandas.DataFrame: Zestawienie n stacji z największą i n z najmniejszą liczbą przekroczeń.
    """
    df = over_counts[over_counts["Rok"] == year].copy()
    col = df.columns[-1] # licznik dni
    top = df.nlargest(n, col)
    bottom = df.nsmallest(n, col)
    out = pd.concat([top, bottom], ignore_index=True)
    return out

def wojew_over_treshold(long: pd.DataFrame, wojew_dict: dict, treshold: int = 15):        
    """
    Zlicza dni z przekroczeniem progu `treshold` przez średnie PM2.5 z rozróżnieniem na województwa

    Args:
        long (pandas.DataFrame): ramka danych w formacie long
        wojew_dict (dict): słownik przypisujący nazwy województw ich dwuliterowym kodom (Kod: Nazwa)
        treshold (int): maksymalne dopuszczalne stężenie PM2.5

    Returns:
        pandas.DataFrame: Zliczenia dni z przekroczeniem normy PM2.5 posortowanej malejąco
    """
    long['date'] = long["datetime"].dt.date
    long["Województwo"] = long["Kod stacji"].str[:2]
    long['Województwo'] = long["Województwo"].apply(lambda code: wojew_dict[code])

    long = long.drop("Miejscowość", axis=1)

    daily  = (
        long
        .groupby(["Województwo", "Kod stacji", "date"], as_index=False)
        .agg(PM25=("PM25", "mean"))
    )
    wojew_means = (
        daily
        .groupby(['date', "Województwo"], as_index=False)
        .agg(PM25=("PM25", "mean"))
    )

    wojew_means['exceeds_treshold'] = wojew_means['PM25'] > treshold
    counts = wojew_means.groupby('Województwo')['exceeds_treshold'].sum()
    return counts.sort_values(ascending=False)