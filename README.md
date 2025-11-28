# 🚶 Walking Catchment Analyzer

A geospatial web application that visualizes **15-minute city** concepts. This tool allows users to click anywhere on a map to generate a walking isochrone (reachable network) and analyze the amenities, transit, and services available within that walking distance.



## 🌟 Features

* **Interactive Map:** Click anywhere to set a starting point.
* **Isochrone Generation:** Calculates the actual street network reachable within 1-15 minutes of walking (not just a simple radius).
* **Amenity Analysis:** Scans the area for essential services like Healthcare, Transit, Offices, Shops, and Leisure spots.
* **Dynamic Dashboard:**
    * **Bar Chart:** Visual breakdown of amenity categories.
    * **Metrics:** Calculates total street network length (km) and catchment area size (km²).
* **Layer Controls:** Toggle the visibility of the Catchment Polygon and Street Network.
* **Base Maps:** Switch between Light, Dark, and Street view modes.

## 🛠️ Tech Stack

* **Python** (Core Logic)
* **Streamlit** (Web App Framework)
* **OSMnx** (OpenStreetMap Data & Network Analysis)
* **Folium** (Interactive Mapping)
* **GeoPandas** (Spatial Data Handling)
* **Altair** (Data Visualization)

## 🚀 How to Run Locally

If you want to run this app on your own computer:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/walking-catchment-analyzer.git](https://github.com/your-username/walking-catchment-analyzer.git)
    cd walking-catchment-analyzer
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the app:**
    ```bash
    streamlit run app.py
    ```

## 📦 Deployment

This app is designed to be deployed on **Streamlit Cloud**.

1.  Push this code to a GitHub repository.
2.  Go to [share.streamlit.io](https://share.streamlit.io/).
3.  Connect your GitHub account and select this repository.
4.  Click **Deploy**.

## 📊 Data Source

* **OpenStreetMap (OSM):** All street networks and amenity data are fetched in real-time using the Overpass API via the OSMnx library.

## 📄 License

This project is open-source and available under the MIT License.
