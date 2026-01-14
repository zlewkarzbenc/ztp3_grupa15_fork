from unittest.mock import MagicMock, patch, call
import pandas as pd
import zipfile
import pytest
import io

import get_data


@pytest.fixture
def df_pm25():
    """Fragment surowych danych PM2.5 z GIOŚ (2015)"""
    return pd.DataFrame(
        [
            ["Kod stacji", "DsJelGorOgin", "DsWrocAlWisn", "DsWrocWybCon"],
            ["Wskaźnik", "PM2.5", "PM2.5", "PM2.5"],
            ["Czas uśredniania", "1g", "1g", "1g"],
            ["2015-01-01 01:00:00", 151.112, 78.0, 50.0],
            ["2015-01-01 02:00:00", 262.566, 42.0, 33.8244],
            ["2015-01-01 03:00:00", 222.83, 27.0, 28.7215],
        ]
    )


@pytest.fixture
def zip_pm25_bytes():
    """Archiwum ZIP z plikiem PM2.5 zapisane w obiekcie BytesIO"""
    filename = "2015_PM25_1g.xlsx"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(filename, b"fake-xlsx-content")
    return filename, buf.getvalue()


def test_download_gios_archive(zip_pm25_bytes, df_pm25):
    """
    Sprawdza, czy funkcja download_gios_archive:
    - pobiera ZIP z właściwego URL,
    - otwiera plik wewnątrz archiwum,
    - wywołuje pd.read_excel z header=None i zwraca DataFrame
    """

    year = 2015
    gios_id = "236"
    filename, zip_bytes = zip_pm25_bytes
    expected = df_pm25

    with patch("get_data.requests.get") as mock_get, patch(
        "get_data.pd.read_excel"
    ) as mock_xl:
        mock_get.return_value = MagicMock()
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.content = zip_bytes
        mock_xl.return_value = expected

        out = get_data.download_gios_archive(year, gios_id, filename)
        mock_get.assert_called_once_with(f"{get_data.gios_archive_url}{gios_id}")

        mock_xl.assert_called_once()
        (arg0,), kwargs = mock_xl.call_args
        assert hasattr(arg0, "read")
        assert kwargs.get("header") is None

        pd.testing.assert_frame_equal(out, expected)


def test_download_gios_meta():
    """
    Sprawdza, czy funkcja download_gios_meta:
    - pobiera plik z właściwego adresu URL,
    - przekazuje dane do pd.read_excel przez io.BytesIO,
    - zwraca wynik wywołania pd.read_excel
    """

    gios_id = "622"

    expected = pd.DataFrame(
        {
            "Nr": [1, 2, 3],
            "Kod stacji": ["DsBialka", "DsBielGrot", "DsBogatFrancMOB"],
            "Kod międzynarodowy": [None, None, "PL0602A"],
            "Nazwa stacji": [
                "Białka",
                "Bielawa - ul. Grota Roweckiego",
                "Bogatynia Mobil",
            ],
            "Stary Kod stacji \n(o ile inny od aktualnego)": [None, None, "DsBogatMob"],
        }
    )

    fake_bytes = b"fake"

    with patch("get_data.requests.get") as mock_get, patch(
        "get_data.pd.read_excel"
    ) as mock_xl:
        mock_get.return_value = MagicMock()
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.content = fake_bytes
        mock_xl.return_value = expected

        out = get_data.download_gios_meta(gios_id)
        mock_get.assert_called_once_with(f"{get_data.gios_archive_url}{gios_id}")

        mock_xl.assert_called_once()
        (arg0,), _ = mock_xl.call_args
        assert isinstance(arg0, io.BytesIO)
        assert arg0.getvalue() == fake_bytes

        pd.testing.assert_frame_equal(out, expected)


def test_clean_pm25(df_pm25):
    """
    Sprawdza, czy funkcja clean_pm25:
    - ustawia nagłówki z wybranego wiersza,
    - usuwa wskazane wiersze,
    - zwraca kolumnę datetime oraz dane stacji,
    - nie modyfikuje wejściowego DataFrame
    """
    df_raw = df_pm25.copy(deep=True)
    df_raw_copy = df_raw.copy(deep=True)

    out = get_data.clean_pm25(df_raw, header_row=0, drop_rows=[0, 1, 2])

    expected = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                ["2015-01-01 01:00:00", "2015-01-01 02:00:00", "2015-01-01 03:00:00"]
            ),
            "DsJelGorOgin": [151.112, 262.566, 222.83],
            "DsWrocAlWisn": [78.0, 42.0, 27.0],
            "DsWrocWybCon": [50.0, 33.8244, 28.7215],
        }
    )

    pd.testing.assert_frame_equal(out, expected, check_dtype=False, check_names=False)
    pd.testing.assert_frame_equal(
        df_raw, df_raw_copy, check_dtype=False, check_names=False
    )


def test_midnight():
    """
    Sprawdza, czy funkcja midnight:
    - zamienia zapis z godziny 00:00:00 o jedną sekundę,
    - nie modyfikuje pozostałych danych w wejściowym DataFrame
    """
    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
               [
                    "2015-01-01 23:00:00.105",
                    "2015-01-02 00:00:00.110",
                    "2015-01-02 01:00:00.115",
                ]
            ),
            "DsJelGorOgin": [151.112, 262.566, 222.83],
            "DsWrocAlWisn": [78.0, 42.0, 27.0],
            "DsWrocWybCon": [50.0, 33.8244, 28.7215],
        }
    )
    df_copy = df.copy(deep=True)

    out = get_data.midnight(df)

    expected = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
               [
                    "2015-01-01 23:00:00.105",
                    "2015-01-01 23:59:59.110",
                    "2015-01-02 01:00:00.115",
                ]
            ),
            "DsJelGorOgin": [151.112, 262.566, 222.83],
            "DsWrocAlWisn": [78.0, 42.0, 27.0],
            "DsWrocWybCon": [50.0, 33.8244, 28.7215],
        }
    )

    pd.testing.assert_frame_equal(out, expected)
    pd.testing.assert_frame_equal(df, df_copy)


def test_update_stations():
    """
    Sprawdza, czy funkcja update_stations:
    - zmienia stare kody stacji na aktualne na podstawie metadanych,
    - nie modyfikuje pozostałych danych w wejściowym DataFrame
    """
    old_col = "Stary Kod stacji \n(o ile inny od aktualnego)"
    new_col = "Kod stacji"

    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2015-01-01 01:00:00"]),
            "PdBialWaszyn": [67.0],
            "ZpSzczPils02": [None],
        }
    )
    df_copy = df.copy(deep=True)

    meta = pd.DataFrame(
        {
            new_col: ["ZpSzczPilsud", "PdBialUpalna"],
            old_col: ["ZpSzczecin002, ZpSzczPils02", "PdBialWaszyn"],
        }
    )

    out = get_data.update_stations(df, meta)

    expected = df.rename(
        columns={
            "PdBialWaszyn": "PdBialUpalna",
            "ZpSzczPils02": "ZpSzczPilsud",
        }
    )

    pd.testing.assert_frame_equal(out, expected)
    pd.testing.assert_frame_equal(df, df_copy)


def test_add_city():
    """
    Sprawdza, czy add_city:
    - zamienia kolumny stacji na MultiIndex (Miejscowość, Kod stacji),
    - przypisuje stacjom miejscowość na podstawie metadanych,
    - nie modyfikuje pozostałych danych w wejściowym DataFrame
    """
    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2015-01-01 01:00:00", "2015-01-01 02:00:00"]),
            "DsJelGorOgin": [151.112, 262.566],
            "DsWrocAlWisn": [78.0, 42.0],
            "DsWrocWybCon": [50.0, 33.8244],
        }
    )
    df_copy = df.copy(deep=True)

    meta = pd.DataFrame(
        {
            "Kod stacji": ["DsJelGorOgin", "DsWrocAlWisn", "DsWrocWybCon"],
            "Miejscowość": ["Jelenia Góra", "Wrocław", "Wrocław"],
        }
    )

    out = get_data.add_city(df, meta)

    expected = df.copy()
    expected.columns = pd.MultiIndex.from_tuples(
        [
            ("datetime", ""),
            ("Jelenia Góra", "DsJelGorOgin"),
            ("Wrocław", "DsWrocAlWisn"),
            ("Wrocław", "DsWrocWybCon"),
        ],
        names=["Miejscowość", "Kod stacji"],
    )

    pd.testing.assert_frame_equal(out, expected)
    pd.testing.assert_frame_equal(df, df_copy)


def test_make_pm25_data(mocker):
    """
    Sprawdza, czy make_pm25_data:
    - wykonuje cały pipeline (download, clean, midnight, update, add_city),
    - zwraca końcowy DataFrame i metadane,
    - zapisuje wynik do pliku CSV z podaną nazwą pliku.
    """

    years = [2015]
    gios_url_ids = {2015: "236", "meta": "622"}
    gios_pm25_file = {2015: "2015_PM25_1g.xlsx"}
    clean_info = {2015: {"header_row": 0, "drop_rows": [0, 1, 2]}}
    outfile = "PM25_test.csv"

    raw_df = pd.DataFrame(
        [
            ["Kod stacji", "DsJelGorOgin", "DsWrocAlWisn", "DsWrocWybCon"],
            ["Wskaźnik", "PM2.5", "PM2.5", "PM2.5"],
            ["Czas uśredniania", "1g", "1g", "1g"],
            ["2015-01-01 01:00:00", 151.112, 78.0, 50.0],
            ["2015-01-02 00:00:00.110", 262.566, 42.0, 33.8244],
            ["2015-01-01 03:00:00", 222.83, 27.0, 28.7215],
        ]
    )

    meta_df = pd.DataFrame(
        {
            "Kod stacji": ["DsJelGorOgin", "DsWrocAlWisnNew", "DsWrocWybCon"],
            "Miejscowość": ["Jelenia Góra", "Wrocław", "Wrocław"],
            "Stary Kod stacji \n(o ile inny od aktualnego)": [
                None,
                "DsWrocAlWisn",
                None,
            ],
        }
    )

    cleaned_df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                [
                    "2015-01-01 23:00:00.105",
                    "2015-01-02 00:00:00.110",
                    "2015-01-02 01:00:00.115",
                ]
            ),
            "DsJelGorOgin": [151.112, 262.566, 222.83],
            "DsWrocAlWisn": [78.0, 42.0, 27.0],
            "DsWrocWybCon": [50.0, 33.8244, 28.7215],
        }
    )

    midnight_df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                [
                    "2015-01-01 23:00:00.105",
                    "2015-01-01 23:59:59.110",
                    "2015-01-02 01:00:00.115",
                ]
            ),
            "DsJelGorOgin": [151.112, 262.566, 222.83],
            "DsWrocAlWisn": [78.0, 42.0, 27.0],
            "DsWrocWybCon": [50.0, 33.8244, 28.7215],
        }
    )

    updated_df = pd.DataFrame(
        {
            "datetime": midnight_df["datetime"],
            "DsJelGorOgin": midnight_df["DsJelGorOgin"],
            "DsWrocAlWisnNew": midnight_df["DsWrocAlWisn"],
            "DsWrocWybCon": midnight_df["DsWrocWybCon"],
        }
    )

    final_df = updated_df.copy()
    final_df.columns = pd.MultiIndex.from_tuples(
        [
            ("datetime", ""),
            ("Jelenia Góra", "DsJelGorOgin"),
            ("Wrocław", "DsWrocAlWisnNew"),
            ("Wrocław", "DsWrocWybCon"),
        ],
        names=["Miejscowość", "Kod stacji"],
    )

    mock_download_archive = mocker.patch(
        "get_data.download_gios_archive", return_value=raw_df
    )
    mock_download_meta = mocker.patch(
        "get_data.download_gios_meta", return_value=meta_df
    )
    mock_clean = mocker.patch("get_data.clean_pm25", return_value=cleaned_df)
    mock_midnight = mocker.patch("get_data.midnight", return_value=midnight_df)
    mock_update = mocker.patch("get_data.update_stations", return_value=updated_df)
    mock_add_city = mocker.patch("get_data.add_city", return_value=final_df)

    mock_to_csv = mocker.patch("pandas.DataFrame.to_csv", autospec=True)

    out_df, out_meta = get_data.make_pm25_data(
        years, gios_url_ids, gios_pm25_file, clean_info, outfile
    )

    pd.testing.assert_frame_equal(out_df, final_df)
    pd.testing.assert_frame_equal(out_meta, meta_df)

    mock_download_archive.assert_called_once_with(
        2015, gios_url_ids[2015], gios_pm25_file[2015]
    )
    mock_download_meta.assert_called_once_with(gios_url_ids["meta"])
    mock_clean.assert_called_once_with(raw_df, header_row=0, drop_rows=[0, 1, 2])

    # Sprawdzenie czy wynik funkcji clean_pm25 jest wejściem funkcji midnight
    mock_midnight.assert_called_once()
    (args,), _ = mock_midnight.call_args
    pd.testing.assert_frame_equal(args, cleaned_df)

    mock_update.assert_called_once()
    (args0, args1), _ = mock_update.call_args
    pd.testing.assert_frame_equal(args0, midnight_df)
    pd.testing.assert_frame_equal(args1, meta_df)

    mock_add_city.assert_called_once()
    (args0, args1), _ = mock_add_city.call_args
    pd.testing.assert_frame_equal(args0, updated_df)
    pd.testing.assert_frame_equal(args1, meta_df)

    mock_to_csv.assert_called_once()
    assert mock_to_csv.call_args.args[0] is final_df
    assert mock_to_csv.call_args.args[1] == outfile
    assert mock_to_csv.call_args.kwargs.get("index") is None
