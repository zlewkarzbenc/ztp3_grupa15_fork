import pandas as pd

def convert_df(df_pm25):
    # formatowanie i czyszczenie danych, zmiana formatu i typu na liczbowy
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
    # grupowanie danych i liczenie średniego PM25
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
    # wyliczanie średniej miesięcznej dla miejscowości wedłgu wszystkich stacji w danym mieście
    df = monthly_means.copy()
    df["Mean PM25"] = pd.to_numeric(df["Mean PM25"], errors="coerce")

    return (
        df.groupby(["Rok", "Miesiąc", "Miejscowość"])["Mean PM25"]
        .mean()
        .reset_index()
    )


def calc_daily_means(formated):
    # liczenie średniego dziennego PM25
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
    # wybieranie dni, gdzie norma została przekroczona
    # liczenie unikalnych przekroczeń dla danego roku i każdej stacji
    df = daily.copy()
    over = df[df["Daily mean PM25"] > threshold]

    out = (
        over.groupby(["Rok", "Kod stacji"])["Data"]
        .nunique()
        .reset_index(name=f"Liczba dni PM25 > {threshold}")
    )
    return out


def top_bottom_stations(over_counts, year, n=3):
    # wybieranie n (3) stacji z największą i najmniejszą liczbą przekroczeń
    df = over_counts[over_counts["Rok"] == year].copy()
    col = df.columns[-1] # licznik dni
    top = df.nlargest(n, col)
    bottom = df.nsmallest(n, col)
    out = pd.concat([top, bottom], ignore_index=True)
    return out