import pandas as pd

def wojew_over_treshold(long: pd.DataFrame, wojew_dict: dict, treshold: int = 15):        
    """
    POPRAWNIE zlicza dni z przekroczeniem progu `treshold` przez średnie PM2.5 z rozróżnieniem na województwa

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
        .groupby(["Województwo", "date"], as_index=False) # to jest dobre grupowanie
        .agg(PM25=("PM25", "mean"))
    )

    daily['exceeds_treshold'] = daily['PM25'] > treshold
    counts = daily.groupby('Województwo')['exceeds_treshold'].sum()
    return counts.sort_values(ascending=False)