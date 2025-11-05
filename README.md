# Toolio Lite - Merchandise Plan Demo

A Streamlit-based demo application that showcases how Toolio Lite handles merchandise planning with attributes, grouping, and filtering functionality.

## Features

This demo application demonstrates:

- **Attributes**: Select and display attribute columns (Category, Brand, Color, Size, Store, Week)
- **Group By**: Aggregate data by selected attributes (similar to SQL GROUP BY)
- **Filters**: Apply filters to narrow down the data view
- **Metrics**: Display four key metrics:
  - Gross Sales Units
  - Receipts Units
  - BOP Units (Beginning of Period)
  - On Order Units

## Data

The app generates sample data for 3 weeks with realistic merchandise attributes and metric values. The data is randomly generated for demonstration purposes.

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the App

Start the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your default web browser at `http://localhost:8501`

## Usage

1. **Select Attributes**: Choose which attribute columns to display in the data table
2. **Group By**: Select attributes to group by - metrics will be aggregated (summed) for each group
3. **Filters**: Apply filters to specific attributes to narrow down the view
4. **View Metrics**: The top row shows aggregated metrics for the current filtered/grouped data

## Example Workflow

1. Select "Category" and "Brand" in Group By
2. Filter by Week to show only one week
3. Add "Color" as a filter to see specific colors
4. Notice how the metrics aggregate at the group level

## Notes

This is a demo application for showcasing Toolio Lite functionality to clients. It does not connect to actual data sources and is intended for visual demonstration purposes.

