import pandas as pd
import requests
import zipfile
import io

gios_archive_url = "https://powietrze.gios.gov.pl/pjp/archives/downloadFile/"

def download_gios_archive(year, gios_id, filename):
    # Pobranie archiwum ZIP do pamięci
    url = f"{gios_archive_url}{gios_id}"
    response = requests.get(url)
    response.raise_for_status()  # jeśli błąd HTTP, zatrzymaj

    # Otwórz zip w pamięci
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # znajdź właściwy plik z PM2.5
        if not filename:
            print(f"Błąd: nie znaleziono {filename}.")
        else:
            # wczytaj plik do pandas
            with z.open(filename) as f:
                try:
                    df = pd.read_excel(f, header=None)
                except Exception as e:
                    print(f"Błąd przy wczytywaniu {year}: {e}")
    return df


def download_gios_meta(gios_id):
    # Pobranie metadanych do pamięci
    url = f"{gios_archive_url}{gios_id}"
    response = requests.get(url)
    response.raise_for_status()  # jeśli błąd HTTP, zatrzymaj

    # wczytaj plik do pandas
    df = pd.read_excel(io.BytesIO(response.content))
    return df


def clean_pm25(df, header_row, drop_rows):
    df = df.copy()
    df.columns = df.iloc[header_row]
    df = df.drop(drop_rows).reset_index(drop=True)

    first = df.columns[0]
    df = df.rename(columns={first: "datetime"})
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def midnight(df):
    df = df.copy()
    # checking if hrs, mins, secs = 0 (True/False, where True means midnight)
    midn = (df["datetime"].dt.hour.eq(0)) & (df["datetime"].dt.minute.eq(0)) & (df["datetime"].dt.second.eq(0))
    # if True (midnight) -> taking back 1 second in "datetime" column 
    df.loc[midn, "datetime"] = df.loc[midn, "datetime"] - pd.Timedelta(seconds=1) 
    return df


def update_stations(df, meta):
    df = df.copy()
    old_code = 'Stary Kod stacji \n(o ile inny od aktualnego)'
    new_code = 'Kod stacji'

    # creating a dictionary with code mapping (old: new)
    mapping_codes = {}
    for old, new in zip(meta[old_code], meta[new_code]):
        if pd.isna(old):
            continue

        # handling examples with multiple old station codes    
        multiple_codes = [codes.strip() for codes in str(old).split(",") if codes.strip()] 
        
        for old in multiple_codes:
            mapping_codes[old] = new
    df = df.rename(columns=mapping_codes)
    return df


def add_city(df, meta):
    df = df.copy()
    city = (
        meta[["Kod stacji", "Miejscowość"]]
        .dropna(subset=["Kod stacji"])
        .drop_duplicates(subset=["Kod stacji"])
        .set_index("Kod stacji")["Miejscowość"]
    )
    station_codes = [x for x in df.columns if x != "datetime"]
    cities = city.reindex(station_codes).fillna("Unknown")

    df.columns = pd.MultiIndex.from_tuples(
        [("datetime", "")] + list(zip(cities, station_codes)),
        names=["Miejscowość", "Kod stacji"]
    )
    return df


def make_pm25_data(years, gios_url_ids, gios_pm25_file, clean_info, outfile):
    # downloading
    data = {y: download_gios_archive(y, gios_url_ids[y], gios_pm25_file[y]) for y in years}
    meta = download_gios_meta(gios_url_ids["meta"])

    # cleaning 
    cleaned = {
    y: clean_pm25(data[y], **clean_info[y])
    for y in years
    }

    # midnight fix
    cleaned = {y: midnight(df) for y, df in cleaned.items()}
    
    # making sure that after midnight fix cleaned data contains only chosen years
    cleaned = {
    y: df[df["datetime"].dt.year.isin(years)]
    for y, df in cleaned.items()
    }

    # station code updates
    cleaned = {y: update_stations(df, meta) for y, df in cleaned.items()}

    # merging years by shared stations
    df_pm25 = pd.concat([cleaned[y] for y in years], axis=0, join="inner", ignore_index=True)

    # adding cities (MultiIndex)
    df_pm25 = add_city(df_pm25, meta)

    df_pm25.to_csv(outfile, index=None)
    return df_pm25, meta