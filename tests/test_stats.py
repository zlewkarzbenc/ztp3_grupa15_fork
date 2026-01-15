import pandas as pd
import pytest

from stats import (
    convert_df,
    calc_monthly_means,
    calc_monthly_city_means,
    calc_daily_means,
    count_overnorm_days,
    top_bottom_stations,
)


@pytest.fixture
def df_pm25():
    """
    Uporządkowane dane PM2.5
    """
    cols = pd.MultiIndex.from_tuples(
        [
            ("datetime", ""),
            ("Jelenia Góra", "DsJelGorOgin"),
            ("Wrocław", "DsWrocAlWisn"),
            ("Wrocław", "DsWrocWybCon"),
        ],
        names=["Miejscowość", "Kod stacji"],
    )

    df_in = pd.DataFrame(
        [
            ["2015-01-01 01:00:00.000", 151.112, 78.00, 50.00],
        ],
        columns=cols,
    )
    df_in[("datetime", "")] = pd.to_datetime(df_in[("datetime", "")])
    return df_in


@pytest.fixture
def df_pm25_formated():
    """
    Uporządkowane dane PM2.5, ale w innym formacie
    """
    df = pd.DataFrame(
        [
            {
                "datetime": "2015-01-01 01:00:00",
                "Miejscowość": "Jelenia Góra",
                "Kod stacji": "DsJelGorOgin",
                "PM25": 151.112,
            },
            {
                "datetime": "2015-01-01 01:00:00",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "PM25": 78.0,
            },
            {
                "datetime": "2015-01-01 01:00:00",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocWybCon",
                "PM25": 50.0,
            },
            {
                "datetime": "2015-01-01 02:00:00",
                "Miejscowość": "Jelenia Góra",
                "Kod stacji": "DsJelGorOgin",
                "PM25": 262.566,
            },
            {
                "datetime": "2015-01-01 02:00:00",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "PM25": 42.0,
            },
            {
                "datetime": "2015-01-01 02:00:00",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocWybCon",
                "PM25": 33.8244,
            },
        ]
    )
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


@pytest.fixture
def df_monthly_means():
    """
    Średnie miesięczne wartości PM2.5 dla stacji
    """
    return pd.DataFrame(
        [
            {
                "Rok": 2015,
                "Miesiąc": 1,
                "Miejscowość": "Jelenia Góra",
                "Kod stacji": "DsJelGorOgin",
                "Mean PM25": (151.112 + 262.566) / 2,
            },
            {
                "Rok": 2015,
                "Miesiąc": 1,
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "Mean PM25": (78.0 + 42.0) / 2,
            },
            {
                "Rok": 2015,
                "Miesiąc": 1,
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocWybCon",
                "Mean PM25": (50.0 + 33.8244) / 2,
            },
        ]
    )



def test_convert_df(df_pm25):
    """
    Sprawdza, czy funkcja convert_df:
    - zamienia format danych,
    - zachowuje poprawne wartości PM25,
    - tworzy kolumny datetime, Miejscowość i Kod stacji
    """
    out = convert_df(df_pm25)

    expected = pd.DataFrame(
        [
            {
                "datetime": "2015-01-01 01:00:00",
                "Miejscowość": "Jelenia Góra",
                "Kod stacji": "DsJelGorOgin",
                "PM25": 151.112000,
            },
            {
                "datetime": "2015-01-01 01:00:00",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "PM25": 78.000000,
            },
            {
                "datetime": "2015-01-01 01:00:00",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocWybCon",
                "PM25": 50.000000,
            },
        ]
    )
    expected["datetime"] = pd.to_datetime(expected["datetime"])

    # sortowanie usuwa zależność od kolejności po stack()
    out = out.sort_values(["Miejscowość", "Kod stacji"]).reset_index(drop=True)
    expected = expected.sort_values(["Miejscowość", "Kod stacji"]).reset_index(
        drop=True
    )

    pd.testing.assert_frame_equal(out, expected)


def test_convert_df_cleans_strings(df_pm25):
    """
    Sprawdza, czy funkcja convert_df:
    - usuwa spacje z wartości PM25,
    - zamienia przecinek na kropkę,
    - konwertuje string na liczbę
    """
    df = df_pm25.copy()
    df[("Jelenia Góra", "DsJelGorOgin")] = " 151,112 "

    out = convert_df(df)

    val = out.loc[out["Kod stacji"] == "DsJelGorOgin", "PM25"].iloc[0]
    assert val == pytest.approx(151.112)


def test_calc_monthly_means(df_pm25_formated):
    """
    Sprawdza, czy funkcja calc_monthly_means:
    - poprawnie grupuje dane po roku i miesiącu,
    - liczy średnią PM25 dla każdej stacji,
    - zwraca poprawne wartości liczbowe
    """

    out = calc_monthly_means(df_pm25_formated)

    expected = pd.DataFrame(
        [
            {
                "Rok": 2015,
                "Miesiąc": 1,
                "Miejscowość": "Jelenia Góra",
                "Kod stacji": "DsJelGorOgin",
                "Mean PM25": (151.112 + 262.566) / 2,
            },
            {
                "Rok": 2015,
                "Miesiąc": 1,
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "Mean PM25": (78.0 + 42.0) / 2,
            },
            {
                "Rok": 2015,
                "Miesiąc": 1,
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocWybCon",
                "Mean PM25": (50.0 + 33.8244) / 2,
            },
        ]
    )

    out = out.sort_values(["Miejscowość", "Kod stacji"]).reset_index(drop=True)
    expected = expected.sort_values(["Miejscowość", "Kod stacji"]).reset_index(
        drop=True
    )

    # dtype roku/miesiąca może być int32 lub int64, dlatego check_dtype=False
    pd.testing.assert_frame_equal(
        out, expected, check_exact=False, atol=1e-4, check_dtype=False
    )


def test_calc_monthly_city_means(df_monthly_means):
    """
    Sprawdza, czy calc_monthly_city_means:
    - liczy miesięczną średnią wartość PM25 dla każdej miejscowości,
    - uwzględnia wszystkie stacje w danym mieście,
    - zwraca poprawne wartości liczbowe
    """

    out = calc_monthly_city_means(df_monthly_means)

    expected = pd.DataFrame(
        [
            {
                "Rok": 2015,
                "Miesiąc": 1,
                "Miejscowość": "Jelenia Góra",
                "Mean PM25": (151.112 + 262.566) / 2,
            },
            {
                "Rok": 2015,
                "Miesiąc": 1,
                "Miejscowość": "Wrocław",
                "Mean PM25": (((78.0 + 42.0) / 2) + ((50.0 + 33.8244) / 2)) / 2,
            },
        ]
    )

    out = out.sort_values(["Rok", "Miesiąc", "Miejscowość"]).reset_index(drop=True)
    expected = expected.sort_values(["Rok", "Miesiąc", "Miejscowość"]).reset_index(
        drop=True
    )

    pd.testing.assert_frame_equal(
        out, expected, check_exact=False, atol=1e-4, check_dtype=False
    )


def test_calc_daily_means(df_pm25_formated):
    """
    Sprawdza, czy funkcja calc_daily_means:
    - poprawnie liczy dzienne średnie wartości PM25,
    - grupuje dane po dacie i stacji,
    - zwraca poprawne wartości liczbowe
    """

    out = calc_daily_means(df_pm25_formated)

    expected = pd.DataFrame(
        [
            {
                "Rok": 2015,
                "Data": pd.to_datetime("2015-01-01").date(),
                "Miejscowość": "Jelenia Góra",
                "Kod stacji": "DsJelGorOgin",
                "Daily mean PM25": (151.112 + 262.566) / 2,
            },
            {
                "Rok": 2015,
                "Data": pd.to_datetime("2015-01-01").date(),
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "Daily mean PM25": (78.0 + 42.0) / 2,
            },
            {
                "Rok": 2015,
                "Data": pd.to_datetime("2015-01-01").date(),
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocWybCon",
                "Daily mean PM25": (50.0 + 33.8244) / 2,
            },
        ]
    )

    out = out.sort_values(["Rok", "Data", "Miejscowość", "Kod stacji"]).reset_index(
        drop=True
    )
    expected = expected.sort_values(
        ["Rok", "Data", "Miejscowość", "Kod stacji"]
    ).reset_index(drop=True)

    pd.testing.assert_frame_equal(
        out, expected, check_exact=False, atol=1e-4, check_dtype=False
    )


def test_count_overnorm_days():
    """
    Sprawdza, czy funkcja count_overnorm_days:
    - identyfikuje dni z przekroczeniem normy,
    - liczy dni przekroczeń normy dla każdej stacji,
    - zwraca poprawne wyniki
    """
    daily = pd.DataFrame(
        [
            {
                "Rok": 2015,
                "Data": "2015-01-01",
                "Miejscowość": "Jelenia Góra",
                "Kod stacji": "DsJelGorOgin",
                "Daily mean PM25": 82.286400,
            },
            {
                "Rok": 2015,
                "Data": "2015-01-02",
                "Miejscowość": "Jelenia Góra",
                "Kod stacji": "DsJelGorOgin",
                "Daily mean PM25": 20.026298,
            },
            {
                "Rok": 2015,
                "Data": "2015-01-01",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "Daily mean PM25": 44.958333,
            },
            {
                "Rok": 2015,
                "Data": "2015-01-02",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "Daily mean PM25": 9.739130,
            },
            {
                "Rok": 2015,
                "Data": "2015-01-01",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocWybCon",
                "Daily mean PM25": 6.594062,
            },
            {
                "Rok": 2015,
                "Data": "2015-01-02",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocWybCon",
                "Daily mean PM25": 5.240792,
            },
        ]
    )
    daily["Data"] = pd.to_datetime(daily["Data"]).dt.date

    threshold = 15

    expected = pd.DataFrame(
        [
            {
                "Rok": 2015,
                "Kod stacji": "DsJelGorOgin",
                f"Liczba dni PM25 > {threshold}": 2,
            },
            {
                "Rok": 2015,
                "Kod stacji": "DsWrocAlWisn",
                f"Liczba dni PM25 > {threshold}": 1,
            },
        ]
    )

    out = count_overnorm_days(daily, threshold)

    out = out.sort_values(["Rok", "Kod stacji"]).reset_index(drop=True)
    expected = expected.sort_values(["Rok", "Kod stacji"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(out, expected)


def test_count_overnorm_empty():
    """
    Sprawdza, czy funkcja count_overnorm_days:
    - zwraca pusty DataFrame, gdy nie występują przekroczenia normy
    """
    daily = pd.DataFrame(
        [
            {
                "Rok": 2015,
                "Data": "2015-01-01",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "Daily mean PM25": 10.0,
            },
            {
                "Rok": 2015,
                "Data": "2015-01-02",
                "Miejscowość": "Wrocław",
                "Kod stacji": "DsWrocAlWisn",
                "Daily mean PM25": 14.99,
            },
        ]
    )
    daily["Data"] = pd.to_datetime(daily["Data"]).dt.date

    out = count_overnorm_days(daily, threshold=15)

    assert out.empty
    assert list(out.columns) == ["Rok", "Kod stacji", "Liczba dni PM25 > 15"]


def test_top_bottom_stations():
    """
    Sprawdza, czy top_bottom_stations:
    - filtruje dane po roku,
    - wybiera n stacji z największą liczbą przekroczeń,
    - wybiera n stacji z najmniejszą liczbą przekroczeń
    """
    over_counts = pd.DataFrame(
        [
            {"Rok": 2015, "Kod stacji": "DsJelGorOgin", "Liczba dni PM25 > 15": 100},
            {"Rok": 2015, "Kod stacji": "DsWrocAlWisn", "Liczba dni PM25 > 15": 80},
            {"Rok": 2015, "Kod stacji": "DsWrocWybCon", "Liczba dni PM25 > 15": 10},
            {"Rok": 2015, "Kod stacji": "KpBydPlPozna", "Liczba dni PM25 > 15": 20},
            {"Rok": 2018, "Kod stacji": "DsJelGorOgin", "Liczba dni PM25 > 15": 999},
        ]
    )

    expected = pd.DataFrame(
        [
            # TOP 2
            {"Rok": 2015, "Kod stacji": "DsJelGorOgin", "Liczba dni PM25 > 15": 100},
            {"Rok": 2015, "Kod stacji": "DsWrocAlWisn", "Liczba dni PM25 > 15": 80},
            # BOTTOM 2
            {"Rok": 2015, "Kod stacji": "DsWrocWybCon", "Liczba dni PM25 > 15": 10},
            {"Rok": 2015, "Kod stacji": "KpBydPlPozna", "Liczba dni PM25 > 15": 20},
        ]
    )

    out = top_bottom_stations(over_counts, year=2015, n=2)

    out = out.sort_values("Kod stacji").reset_index(drop=True)
    expected = expected.sort_values("Kod stacji").reset_index(drop=True)

    pd.testing.assert_frame_equal(out, expected)
