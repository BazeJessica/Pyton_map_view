import requests
import json
import folium
import time
import schedule


UPDATE_INTERVAL = 60

# API key for JCDecaux API
API_KEY = "e0a1bf2c844edb9084efc764c089dd748676cc14"
# Base URL for JCDecaux API
BASE_URL = "https://api.jcdecaux.com/vls/v3/"


def get_all_contracts() -> list:
    # Fetch all contracts
    try:
        url = f"{BASE_URL}/contracts"
        # Send request
        response = requests.get(url, params={"apiKey": API_KEY})
        if response.status_code == 200:
            contracts = response.json()
            return contracts
        else:
            print(f"Failed to fetch contracts. {response.status_code}")
            print(response.json())
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def get_bike_data(city: str, write_to_file: bool=True):
    # Fetch bike data for specified city.
    try:
        # Construct the API request URL
        url = f"{BASE_URL}stations?contract={city}&apiKey={API_KEY}"
        # Send GET request to JCDecaux API
        response = requests.get(url)
        if response.status_code == 200:
            if write_to_file == True:
                # Write json data to disk
                with open(f"json_outputs/{city}_station_data.json", "w") as out_file:
                    json.dump(response.json(), out_file)
            return response.json()
        else:
            # Contract for specified city not available.
            print(f"Failed to fetch data for {city}: {response.status_code}")
            print(response.json())
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def load_bike_data_from_disk(filepath: str) -> dict:
    # For testing purposes (to avoid having to call the API every time)
    # Reads pre-fetched bike data from disk
    try:
        with open(filepath, 'r') as in_file:
            return json.load(in_file)
    except Exception as e:
        print(f"Exception Occurred:", e)
        return None


def extract_bike_type_information(bike_data: dict) -> dict:
    # Extract information about various bike types in city (electrical, mechanical)

    mechanical_bike_identifiers = ["mechanicalBikes"]
    electrical_bike_identifiers = [
        "electricalBikes",
        "electricalInternalBatteryBikes",
        "electricalRemovableBatteryBikes"
    ]

    all_station_info = {}

    for station in bike_data:
        station_name = station['name']
        station_bike_info = {
            "stationMechanicalBikes": 0,
            "stationElectricalBikes": 0
        }
        print(station)
        print("Done!!!!!!!!!!!!!!!!")
        # Get count of all mechanical bikes in station
        for mechanical_bike_id in mechanical_bike_identifiers:
            station_bike_info["stationMechanicalBikes"] += station["totalStands"]["availabilities"][mechanical_bike_id]

        # Get count of all electrical bikes in station
        for electrical_bike_id in electrical_bike_identifiers:
            station_bike_info["stationElectricalBikes"] += station["totalStands"]["availabilities"][electrical_bike_id]

        all_station_info[station_name] = station_bike_info

    return all_station_info


def plot_stations_on_map(contracts_data):
    # Create a map centered around the first contract
    first_contract = contracts_data[0]
    city = first_contract['name']
    bike_data = first_contract['bike_data']
    map_center = (bike_data[0]['position']['latitude'],
                  bike_data[0]['position']['longitude'])
    map_object = folium.Map(location=map_center, zoom_start=13)

    # Add markers for each bike station for all contracts
    for contract_data in contracts_data:
        city = contract_data['name']
        bike_data = contract_data['bike_data']
        for station in bike_data:
            station_name = station['name']
            station_position = (
                station['position']['latitude'], station['position']['longitude'])
            available_bikes = station['mainStands']['availabilities']['bikes']
            total_stands = station['mainStands']['capacity']

            # Construct popup text with station name and bike counts
            # Purpose: Show the number of available banks, total stands,
            # number of mechanical and number of electrical bikes at the station.
            popup_text = f"""
                {station_name}<br>
                Available bikes: {available_bikes}/{total_stands}<br>
                Number of Mechanical Bikes: {contract_data['bike_type_data'][station_name]['stationMechanicalBikes']}<br>
                Number of Electrical Bikes: {contract_data['bike_type_data'][station_name]['stationElectricalBikes']}
            """

            # Add marker with popup to map
            marker = folium.Marker(location=station_position, popup=popup_text)
            marker.add_to(map_object)

    # Display the map
    map_filename = "all_cities_bike_stations_map.html"
    map_object.save(map_filename)
    print(f"Map saved as {map_filename}")


def update_bike_data_and_map(contracts_data):
    for contract_data in contracts_data:
        city_name = contract_data['name']
        bike_data = get_bike_data(city=city_name)
        if bike_data:
            contract_data['bike_data'] = bike_data
    plot_stations_on_map(contracts_data)  # Update the map with new data


def get_data_and_stats_for_all_cities():
    # Get all supported contracts
    supported_contracts = get_all_contracts()
    if not supported_contracts:
        print("Failed to fetch supported contracts.")
        raise RuntimeError(f"Failed to fetch supported contracts.")

    contracts_data = []
    for contract in supported_contracts:
        city_name = contract['name']
        print(f"Fetching data for {city_name}...")
        bike_data = get_bike_data(city=city_name)
        if not bike_data:
            print(f"Failed to fetch bike data for {city_name}. Skipping...")
            continue

        # Extract bike type information for the city
        bike_type_data = extract_bike_type_information(bike_data=bike_data)

        contracts_data.append({
            'name': city_name,
            'bike_data': bike_data,
            'bike_type_data': bike_type_data
        })

    # Plot initial markers on the map
    plot_stations_on_map(contracts_data)

    # Schedule periodic updates
    schedule.every(UPDATE_INTERVAL).seconds.do(update_bike_data_and_map, contracts_data=contracts_data)

    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(2)

# Plot bike data on map
get_data_and_stats_for_all_cities()