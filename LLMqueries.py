import json
import os
import openai
import pandas as pd
from flask import Flask, request, jsonify
from html import escape  # Correct module for escape
from config import API_KEY
from flask_cors import CORS
import matplotlib.pyplot as plt
import io
import base64

# OpenAI API Initialization
os.environ["OPENAI_API_KEY"] = API_KEY
openai.api_key = os.getenv("OPENAI_API_KEY")

# Flask App
app = Flask(__name__)



CORS(app)

# Data directory
DATA_FOLDER = "WHO_Region_Data"

# Function to build the directory tree
def build_directory_tree(folder):
    tree = {}
    for entry in os.listdir(folder):
        path = os.path.join(folder, entry)
        if os.path.isdir(path):
            tree[entry] = build_directory_tree(path)
        elif os.path.isfile(path):
            tree.setdefault("files", []).append(entry)
    return tree

# Build tree and get region-country mappings
directory_tree = build_directory_tree(DATA_FOLDER)


# Function to create a graph based on the dataset and user query
def create_graph(dataset, query):
    """
    Creates a graph based on the dataset and the user's query.
    Handles cases where one dimension is dates and another is numeric.
    Returns a base64-encoded image of the graph.
    """
    try:
        # Check if there's a column with dates
        date_columns = dataset.select_dtypes(include=["datetime64", "object"]).columns
        numeric_columns = dataset.select_dtypes(include=["number"]).columns

        if len(numeric_columns) < 1:
            return "The dataset does not have enough numeric columns to generate a meaningful graph."

        # Handle dates if available
        if len(date_columns) > 0:
            # Assume the first date column is the x-axis
            date_col = date_columns[0]
            dataset[date_col] = pd.to_datetime(dataset[date_col], errors='coerce')
            dataset = dataset.dropna(subset=[date_col])  # Drop rows with invalid dates
            dataset = dataset.sort_values(by=date_col)  # Ensure dates are in order

            # Plot date on x-axis and first numeric column on y-axis
            plt.figure(figsize=(10, 6))
            plt.plot(dataset[date_col], dataset[numeric_columns[0]], marker='o')
            plt.title(f"Graph based on query: {query}")
            plt.xlabel(date_col)
            plt.ylabel(numeric_columns[0])
            plt.grid(True)
            plt.xticks(rotation=45)  # Rotate dates for better readability
        else:
            # Plot the first two numeric columns as a fallback
            plt.figure(figsize=(10, 6))
            plt.plot(dataset[numeric_columns[0]], dataset[numeric_columns[1]], marker='o')
            plt.title(f"Graph based on query: {query}")
            plt.xlabel(numeric_columns[0])
            plt.ylabel(numeric_columns[1])
            plt.grid(True)

        # Save the plot to a BytesIO buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)

        # Encode the image in base64 for transmission
        encoded_image = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        return f"data:image/png;base64,{encoded_image}"

    except Exception as e:
        return f"An error occurred while creating the graph: {e}"

# Function to parse the query with OpenAI (updated for multiple countries)
def parse_request_for_keywords(prompt, regions_and_countries):
    system_prompt = (
        "Extract the region, countries (comma-separated if more than one), year, and month from the user's query. "
        "If the region is missing, infer it based on the countries. "
        "Only use regions from this list: "
        f"{list(regions_and_countries.keys())}. "
        "Respond only with a JSON object in the format: "
        '{"region": "<region>", "countries": ["<country1>", "<country2>"], "year": "<year>"}'
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        result = response["choices"][0]["message"]["content"]
        return eval(result)  # Convert JSON-like string to dictionary
    except Exception as e:
        print(f"Error parsing OpenAI response: {e}")
        return {"region": None, "countries": [], "year": None}



# Function to search dataset in the directory tree (updated for multiple countries)
def search_dataset(tree, region=None, countries=None, year=None):
    def recursive_search(subtree, region, countries, year, path=""):
        matching_files = []
        for key, value in subtree.items():
            if key == "files":
                for file in value:
                    normalized_year = year[-2:] if year else ""
                    if (
                        region and year and any(
                            country.lower() in path.lower() for country in countries
                        ) and normalized_year in file
                    ):
                        matching_files.append(os.path.join(path, file))
            elif isinstance(value, dict):
                result = recursive_search(value, region, countries, year, os.path.join(path, key))
                if result:
                    matching_files.extend(result)
        return matching_files

    return recursive_search(tree, region, countries, year)

def answer_question(user_query, dataset):
    """
    Processes the user's query and uses OpenAI to generate insights based on a single-row dataset.
    """
    # Extract headers and the single row
    headers = dataset.columns.tolist()
    values = dataset.iloc[0].tolist()  # Assuming there's only one row

    # Combine headers and values into a dictionary for clarity
    data_summary = {headers[i]: values[i] for i in range(len(headers))}

    # Construct the OpenAI prompt
    prompt = (
        "You are an AI data analyst. The user has provided a dataset with only one row of data. "
        "Your task is to analyze the headers and the single row of values, then answer the user's query. "
        "Provide a concise, clear response in plain text. "
        "Here are the headers and their corresponding value:\n\n"
        f"{data_summary}\n\n"
        f"User's query: {user_query}"
    )

    try:
        # Send the prompt to OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in data analysis."},
                {"role": "user", "content": prompt},
            ],
        )
        # Extract and return the response content
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"An error occurred while querying OpenAI: {e}"



@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>CSV Search</title></head>
    <body>
        <h1>Search CSV Data</h1>
        <form method="POST" action="/search">
            <label for="query">Enter your query:</label><br>
            <input type="text" id="query" name="query" size="60" required><br><br>
            <input type="submit" value="Search">
        </form>
    </body>
    </html>
    """
@app.route("/search", methods=["POST"])
def search():
    request_data = request.get_json()
    user_query = request_data.get("message", "").strip()
    if not user_query:
        return jsonify({"error": "Query is required."}), 400

    # Parse the query
    parsed_keywords = parse_request_for_keywords(user_query, directory_tree)
    print(parsed_keywords)
    region = parsed_keywords.get("region")
    countries = parsed_keywords.get("countries")
    year = parsed_keywords.get("year")

    if not year:
        return jsonify({"error": "Please specify a valid year in your query."}), 400

    if not countries:
        return jsonify({"error": "Please specify at least one country in your query."}), 400

    dataset_paths = search_dataset(directory_tree, region, countries, year)
    print(dataset_paths)
    if dataset_paths:
        responses = []
        graphs = []
        for dataset_path in dataset_paths:
            full_path = os.path.join(DATA_FOLDER, dataset_path)
            try:
                data = pd.read_csv(full_path)
                if data.empty:
                    responses.append(f"The dataset '{dataset_path}' is available but contains no data.")
                else:
                    responses.append(answer_question(user_query, data))
                    graph = create_graph(data, user_query)
                    graphs.append(graph)
            except Exception as e:
                responses.append(f"An error occurred while processing the dataset '{dataset_path}': {e}")
        response_text = "\n\n".join(responses)
        return jsonify({"message": response_text, "graphs": graphs})
    else:
        return jsonify({"message": "No datasets matching your query were found.", "graphs": []})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
