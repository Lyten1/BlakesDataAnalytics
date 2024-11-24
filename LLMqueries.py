import json
import os
import openai
import pandas as pd
from flask import Flask, request, jsonify
from html import escape  # Correct module for escape
from config import API_KEY
from flask_cors import CORS

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

# Function to parse the query with OpenAI
def parse_request_for_keywords(prompt, regions_and_countries):
    system_prompt = (
        "Extract the region, country, year, and month from the user's query. "
        "If the region is missing, infer it based on the country. "
        "Only use regions from this list: "
        f"{list(regions_and_countries.keys())}. "
        "Respond only with a JSON object in the format: "
        '{"region": "<region>", "country": "<country>", "year": "<year>"}'
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
        return {"region": None, "country": None, "year": None}



# Function to search dataset in the directory tree
def search_dataset(tree, region=None, country=None, year=None):
    def recursive_search(subtree, region, country, year, path=""):
        for key, value in subtree.items():
            if key == "files":
                for file in value:
                    normalized_year = year[-2:] if year else ""
                    if (
                        region and country and year and
                        region.lower() in path.lower() and
                        country.lower() in path.lower() and
                        normalized_year in file
                    ):
                        return os.path.join(path, file)
            elif isinstance(value, dict):
                result = recursive_search(value, region, country, year, os.path.join(path, key))
                if result:
                    return result
        return None

    return recursive_search(tree, region, country, year)


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

    # Example logic for parsing query and searching dataset
    # Replace with your actual logic
    parsed_keywords = parse_request_for_keywords(user_query, directory_tree)
    region = parsed_keywords.get("region")
    country = parsed_keywords.get("country")
    year = parsed_keywords.get("year")

    if not year:
        return jsonify({"error": "Please specify a valid year in your query."}), 400

    dataset_path = search_dataset(directory_tree, region, country, year)
    print(dataset_path)
    if dataset_path:
        full_path = os.path.join(DATA_FOLDER, dataset_path)
        try:
            data = pd.read_csv(full_path)
            if data.empty:
                response_text = "The dataset is available but contains no data."
            else:
                response_text = answer_question(user_query, data)
        except Exception as e:
            response_text = f"An error occurred while processing the dataset: {e}"
    else:
        response_text = "No dataset matching your query was found."

    return jsonify({"message": response_text})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
