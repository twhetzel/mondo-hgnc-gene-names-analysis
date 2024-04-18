#!/usr/bin/env python3
import click
import pandas as pd
import requests
import json
from openai import OpenAI
import re
import os
import time


def get_gene_symbol_info(symbol):
    """
    Search HGNC by gene symbol.
    """
    symbol_url = f"https://rest.genenames.org/search/symbol/{symbol}"
    previous_symbol_url = f"https://rest.genenames.org/search/prev_symbol/{symbol}"
    headers = {
        'Accept': 'application/json',
    }
    response = requests.get(previous_symbol_url, headers=headers)
    if response.status_code == 200:
        response_dict = json.loads(response.content)
        symbol = response_dict['response']['docs'][0]['symbol']
        return symbol
    else:
        response.raise_for_status()


def check_definition_for_gene_symbol(iri, definition):
    """
    Use OpenAI to check if definition contains a gene symbol.
    """
    # Use the API key
    client = OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    
    # User prompt to identify the gene symbol in the text
    # TODO: Fine tune prompt so it does not return example gene symbols
    prompt = f"Identify any gene symbols in the following text: {definition}. \
        Include only the gene symbol found in the prompt text. Do not return example gene symbols."

    chat_completion = client.chat.completions.create(
        # model="gpt-3.5-turbo",
        # model="gpt-3.5-turbo-0125",
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant with knowledge about gene names and symbols."},
            {"role": "user", "content": prompt},
        ],
    )
    print(chat_completion.choices[0].message.content)
    # print(chat_completion.choices[0].message)
    return chat_completion.choices[0].message.content


@click.command()
@click.argument('file_path', type=click.Path(exists=True))
def main(file_path):
    """
    Main steps
    """
    # Read in data file
    df = pd.read_csv(file_path)
    # print(df.head())

    df_results = pd.DataFrame(columns=['?cls', 'old_gene_symbol', 'updated_gene_symbol', 'updated_definition'])
    all_gene_symbol_matches = []

    for index, row in df.iterrows():
        iri = row['?cls']
        gene_label = row['?gene_label']
        definition = row['?definition']

        print(f"\n---\n** Input:\n{iri} -- {gene_label}\n{definition}\n")

        # Check for gene symbol in the ?definition field using prompt
        possible_gene_symbol = check_definition_for_gene_symbol(iri, definition)
        print('** PGS:', possible_gene_symbol)

       # Regular expression pattern to match gene symbols
        pattern = r"\b[A-Z]{2,}[0-9]*\b"

        # Find all matches in the text
        matches = re.findall(pattern, possible_gene_symbol)
        print(matches, type(matches))

        # Check if any matches were found
        if matches:
            for match in matches:
                print("Gene symbols found:", match)
 
            # Check if possible gene symbol in definition is a previous symbol in HGNC (previous is different than alias) 
            if match:
                try:
                    results = get_gene_symbol_info(match)
                    print("Matched Results:", results)

                    # Update definition with new gene symbol
                    updated_definition = definition.replace(match, results)

                    # Append to dictionary to later join back to original dataframe
                    all_gene_symbol_matches.append({"cls": iri, "old_def_gene_symbol": match,
                                                    "updated_gene_symbol": results, "updated_definition": updated_definition})
                    # print(all_gene_symbol_matches)

                    
                    # TODO: If not results as previous symbol, try search for alias and symbol 
                    # when using full data set of all MONDO classes with definitions.
                except Exception as e:
                    print("An error occurred:", e)
            else:
                print('Skip searching...')
        else:
            all_gene_symbol_matches.append({"cls": iri, "old_def_gene_symbol": "No gene symbol found in definition.",
                                            "updated_gene_symbol": "", "updated_definition": ""})

    # Debug
    for d in all_gene_symbol_matches:
        print(d)
                


if __name__ == '__main__':
    main()