import shutil
import pandas as pd
import os

def load_dataset(file_path):
    data = pd.read_csv(file_path)
    data.columns = data.columns.str.strip()
    data = data.dropna(subset=['WHO region', 'Country/Region'])
    return data

def safe_create_folder(path):
    if not os.path.exists(path):
        print(f"Creating folder: {path}")  # Debug statement
        os.makedirs(path)

def extract_years(columns):
    return {col.split('/')[-1] for col in columns if '/' in col}

def save_data_to_csv(data, output_file):
    data.to_csv(output_file, index=False)

def prepare_datasets(file_path, base_dir):
    data = load_dataset(file_path)
    safe_create_folder(base_dir)
    unique_regions = data['WHO region'].dropna().unique()

    for region in unique_regions:
        region_dir = os.path.join(base_dir, region)
        safe_create_folder(region_dir)
        region_data = data[data['WHO region'] == region]
        unique_countries = region_data['Country/Region'].unique()

        for country in unique_countries:
            country_dir = os.path.join(region_dir, country)
            safe_create_folder(country_dir)
            country_data = region_data[region_data['Country/Region'] == country]
            years = extract_years(country_data.columns)

            for year in years:
                if year.isdigit():
                    year_dir = os.path.join(country_dir, year)
                    safe_create_folder(year_dir)
                    year_columns = [col for col in country_data.columns if col.endswith(year) or col in ['Province/States', 'Country/Region', 'WHO region']]
                    year_data = country_data[year_columns]
                    output_file = os.path.join(year_dir, f'{country}_{year}.csv')
                    save_data_to_csv(year_data, output_file)

# Usage
file_path = 'who_covid_19_sit_rep_time_series.csv'
base_dir = 'WHO_Region_Data'
prepare_datasets(file_path, base_dir)
