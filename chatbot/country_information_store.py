import pandas as pd
import spacy
import Levenshtein
from sentence_transformers import CrossEncoder


class CountryInformationStore:
    """Stores country data and answers stat-focused questions."""

    COLUMN_BLUEPRINT = [
        {
            "column": "Region",
            "definition": "Region: the geographic region where the country is located.",
            "template": "{country} is located in the {value} region.",
        },
        {
            "column": "Population",
            "definition": "Population: the total number of people living in the country.",
            "template": "The population of {country} is {value} people.",
        },
        {
            "column": "Area (sq. mi.)",
            "definition": "Area (sq. mi.): total surface area of the country measured in square miles (i.e. how big the country is).",
            "template": "{country} covers {value} square miles.",
        },
        {
            "column": "Pop. Density (per sq. mi.)",
            "definition": "Population Density (per sq. mi.): the average number of people living in each square mile of the country.",
            "template": "{country} has a population density of {value} people per square mile.",
        },
        {
            "column": "Coastline (coast/area ratio)",
            "definition": "Coastline (coast/area ratio): the ratio of coastline length to total land area.",
            "template": "The coastline-to-area ratio for {country} is {value}.",
        },
        {
            "column": "Net migration",
            "definition": "Net migration: the number of people entering minus leaving the country per 1,000 residents.",
            "template": "{country} has a net migration rate of {value} people per 1,000 residents.",
        },
        {
            "column": "Infant mortality (per 1000 births)",
            "definition": "Infant mortality: the number of infant deaths per 1,000 live births.",
            "template": "The infant mortality rate in {country} is {value} deaths per 1,000 births.",
        },
        {
            "column": "GDP ($ per capita)",
            "definition": "GDP ($ per capita): the average economic output per person in the country in US dollars.",
            "template": "The GDP per capita of {country} is ${value}.",
        },
        {
            "column": "Literacy (%)",
            "definition": "Literacy: the percentage of people in the country who can read and write.",
            "template": "{country}'s literacy rate is {value}%.",
        },
        {
            "column": "Phones (per 1000)",
            "definition": "Phones: the average number of cellular mobile phone subscriptions per 1,000 people.",
            "template": "There are {value} cellular subscriptions per 1,000 people in {country}.",
        },
        {
            "column": "Birthrate",
            "definition": "Birthrate: the number of births per 1,000 people each year.",
            "template": "{country} has a birthrate of {value} births per 1,000 people.",
        },
        {
            "column": "Deathrate",
            "definition": "Deathrate: the number of deaths per 1,000 people each year.",
            "template": "{country} has a death rate of {value} deaths per 1,000 people.",
        },
    ]

    def __init__(self, data_path, model_name="cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.data_path = data_path
        self.model_name = model_name
        self.column_order = []
        self.templates = {}
        for entry in self.COLUMN_BLUEPRINT:
            column_name = entry["column"]
            self.column_order.append(column_name)
            self.templates[column_name] = entry["template"]
        self.cross_encoder = CrossEncoder(model_name)
        self.spacy_nlp = self.load_spacy_model()
        self.country_records = []
        self.load_dataset()

    def load_dataset(self):
        dataset_frame = pd.read_csv(self.data_path)
        dataset_frame["Country"] = dataset_frame["Country"].astype(str).str.strip()
        country_records = []
        for unused_index, row in dataset_frame.iterrows():
            country_name = str(row.get("Country", "")).strip()
            if not country_name:
                continue
            record = row.to_dict()
            record["_display_name"] = country_name
            country_records.append(record)
        country_records.sort(key=lambda record: record["_display_name"].lower())
        self.country_records = country_records

    def population_lookup(self, country_query):
        record = self.get_best_country_match(country_query)
        if not record:
            return None
        formatted_population = record.get("Population")
        if not formatted_population:
            return None
        return f"{formatted_population} people"

    def answer_question(self, question):
        record = self.get_country_from_entities(question)
        if not record:
            return None
        column_name = self.infer_column(question)
        if not column_name:
            return None
        value = record.get(column_name)
        if value is None:
            return f"I don't have {column_name.lower()} data for {record['_display_name']}."
        template = self.templates.get(column_name, "{country}: {value}")
        return template.format(country=record["_display_name"], value=value)

    def get_country_from_entities(self, question):
        if not self.spacy_nlp or not question:
            return None
        document = self.spacy_nlp(question)
        for entity in document.ents:
            if entity.label_ in {"GPE", "LOC"}:
                record = self.get_best_country_match(entity.text)
                if record:
                    return record
        return None

    def get_best_country_match(self, text):
        if not text:
            return None
        target = text.strip().lower()
        if not target:
            return None
        best_record = None
        best_distance = None
        for record in self.country_records:
            candidate = record["_display_name"].lower()
            distance = Levenshtein.distance(target, candidate)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_record = record
        return best_record

    def infer_column(self, question):
        if not question:
            return None
        comparison_pairs = []
        for entry in self.COLUMN_BLUEPRINT:
            comparison_pairs.append((question, entry["definition"]))
        scores = self.cross_encoder.predict(comparison_pairs)
        best_index = 0
        best_score = None
        for index, score in enumerate(scores):
            if best_score is None or score > best_score:
                best_score = score
                best_index = index
        return self.column_order[best_index]

    def load_spacy_model(self):
        try:
            return spacy.load("en_core_web_lg")
        except Exception as exc:
            print(f"Failed to load spaCy model: {exc}")
            return None
