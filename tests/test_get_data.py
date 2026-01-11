import io
import os
import zipfile
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
import get_data


def test_download_gios_archive():
    # Checks whether ZIP download is handled in memory and returns a DataFrame
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2015_PM25_1g.xlsx", b"fake")

    with patch("get_data.requests.get") as mock_get, patch(
        "get_data.pd.read_excel"
    ) as mock_xl:
        mock_get.return_value = MagicMock()
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.content = buf.getvalue()
        mock_xl.return_value = pd.DataFrame(
            {
                0: ["2015-01-01 01:00:00", "2015-01-01 02:00:00"],
                1: [151.112, 262.566],
                2: [78, 42],
            }
        )
        out = get_data.download_gios_archive(2015, "236", "2015_PM25_1g.xlsx")
        assert isinstance(out, pd.DataFrame)
        assert not out.empty
        assert out.shape[0] == 2
        assert out.iloc[0, 1] == 151.112


def test_download_gios_meta():
    # Checks whether metadata download returns a DataFrame
    with patch("get_data.requests.get") as mock_get, patch(
        "get_data.pd.read_excel"
    ) as mock_xl:
        mock_get.return_value = MagicMock()
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.content = b"fake"
        mock_xl.return_value = pd.DataFrame(
            {   "Stary Kod stacji \n(o ile inny od aktualnego)": [None, "DsWrocWisA"],
                "Kod stacji": ["DsJelGorOgin", "DsWrocAlWisn"],
                "Miejscowość": ["Jelenia Góra", "Wrocław"],
            }
        )
        out = get_data.download_gios_meta("622")
        assert isinstance(out, pd.DataFrame)
        assert "Kod stacji" in out.columns



@pytest.fixture
def df_raw():
    # data frame with raw data before cleaning
    return pd.DataFrame(
        [
            ["0", "1", "2", "3"],
            ["Kod stacji", "DsWrocWisA", "KpAirpWiktorowo", "KpBydgPlPozn"],
            ["Wskaźnik", "PM2.5", "PM2.5", "PM2.5"],
            ["Czas uśredniania", "1g", "1g", "1g"],
            ["2014-01-01 01:00:00", 152, 104, "116.214424"],
            ["2014-01-01 02:00:00", 137, 94.3, "NaN"],
        ]
    )


@pytest.fixture
def df_clean():
    # data after cleaning but before combining station codes with towns
    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                [
                    "2015-01-01 01:00:00",
                    "2015-01-01 02:00:00",
                ]
            ),
            "DsJelGorOgin": [151.112, 262.566],
            "DsWrocAlWisn": [78, 42],
        }
    )
    meta = pd.DataFrame(
        {
            "Kod stacji": ["DsJelGorOgin", "DsWrocAlWisn"],
            "Miejscowość": ["Jelenia Góra", "Wrocław"],
        }
    )
    return df, meta


def test_clean_pm25(df_raw):
    # Checks that cleaning creates a datetime column and preserves data columns
    out = get_data.clean_pm25(df_raw, header_row=1, drop_rows=[0, 1, 2, 3])
    assert "datetime" in out.columns
    assert pd.api.types.is_datetime64_any_dtype(out["datetime"])
    assert "DsWrocWisA" in out.columns
    assert out.shape[0] == 2


@pytest.mark.parametrize(
    "input, output",
    [
        ("2015-01-01 00:00:01", "2015-01-01 00:00:01"),
        ("2015-01-02 00:00:00", "2015-01-01 23:59:59"),
    ],
)
def test_midnight(input, output):
    # Checks whether midnight measurements are shifted to the previous day
    df = pd.DataFrame({"datetime": pd.to_datetime([input])})
    out = get_data.midnight(df)
    assert out.loc[0, "datetime"] == pd.Timestamp(output)


def test_update_stations():
    # Checks whether old station codes are replaced with current ones
    meta = pd.DataFrame(
        {
            "Stary Kod stacji \n(o ile inny od aktualnego)": ["DsWrocWisA"],
            "Kod stacji": ["DsWrocAlWisn"],
        }
    )
    df = pd.DataFrame({"datetime": pd.to_datetime(["2015-01-01"]), "DsWrocWisA": [78]})
    out = get_data.update_stations(df, meta)
    assert "DsWrocAlWisn" in out.columns
    assert "DsWrocWisA" not in out.columns


def test_add_city(df_clean):
    # Checks whether station codes are correctly mapped to city names
    df, meta = df_clean
    out = get_data.add_city(df, meta)
    assert isinstance(out.columns, pd.MultiIndex)
    assert ("datetime", "") in out.columns
    assert ("Jelenia Góra", "DsJelGorOgin") in out.columns
    assert out.loc[0, ("Jelenia Góra", "DsJelGorOgin")] == 151.112


def test_make_pm25_data():
    # Checks whether the full PM2.5 data pipeline runs and returns DataFrames
    years = [2015]
    gios_url_ids = {2015: "236", "meta": "622"}
    gios_pm25_file = {2015: "2015_PM25_1g.xlsx"}
    clean_info = {2015: {"header_row": 0, "drop_rows": []}}

    fake_df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2015-01-01 01:00:00", "2015-01-01 02:00:00"]),
            "DsJelGorOgin": [151.112, 262.566],
            "DsWrocAlWisn": [78, 42],
        }
    )
    fake_meta = pd.DataFrame(
        {   "Stary Kod stacji \n(o ile inny od aktualnego)": ["DsJelGorOgin", "DsWrocAlWisn"],
            "Kod stacji": ["DsJelGorOgin", "DsWrocAlWisn"],
            "Miejscowość": ["Jelenia Góra", "Wrocław"],
        }
    )

    with patch("get_data.download_gios_archive", return_value=fake_df), patch(
        "get_data.download_gios_meta", return_value=fake_meta
    ):
        out_df, out_meta = get_data.make_pm25_data(
            years, gios_url_ids, gios_pm25_file, clean_info, "PM25_test.csv"
        )
        assert isinstance(out_df, pd.DataFrame)
        assert isinstance(out_meta, pd.DataFrame)
    
    # Clean up the output file after the test
    if os.path.exists("PM25_test.csv"):
        os.remove("PM25_test.csv")
