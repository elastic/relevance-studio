# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

# Standard packages
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone

# Third-party packages
import click
from beir import util
from dotenv import load_dotenv
from termcolor import colored

# Elastic packages
from elasticsearch import helpers
from elasticsearch.helpers import BulkIndexError
from concurrent.futures import ThreadPoolExecutor

# Local packages
sys.path.insert(0, os.path.abspath("src"))
from server.client import es
from server import api, utils
from server.models import *

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()

CWD = os.path.dirname(os.path.abspath(__file__))
CHUNK_SIZE_ASSETS = 500 # esrs-studio assets
CHUNK_SIZE_DATA = 50 # content
SAMPLE_DATA_DIRECTORY = os.path.join(CWD, "sample-data")
SAMPLE_DATA_INDEX_PREFIX = "esrs-sample-data-"
SAMPLE_DATASETS = [
    {
        "id": "arguana",
        "name": "ArguAna",
        "params": [ "text" ],
        "fields": [ "text", "title" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "climate-fever",
        "name": "Climate-FEVER",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    # TODO: cqadupstack has a different folder structure than the rest
    #{
    #    "id": "cqadupstack",
    #    "name": "CQADupstack",
    #    "params": [ "text" ],
    #    "rating_scale": { "min": 0, "max": 1 },
    #    "display": { "template": { "body": "### {{title}}\n{{text}}" }},
    #    "source": "beir"
    #},
    {
        "id": "dbpedia-entity",
        "name": "DBPedia",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 2 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "fever",
        "name": "FEVER",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "### {{title.text}}\n{{tex.text}}" }},
        "source": "beir"
    },
    {
        "id": "fiqa",
        "name": "FiQA-2018",
        "fields": [ "text" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "hotpotqa",
        "name": "HotpotQA",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "msmarco",
        "name": "MSMARCO",
        "fields": [ "text" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "nfcorpus",
        "name": "NFCorpus",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 2 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "nq",
        "name": "NQ",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "quora",
        "name": "Quora",
        "fields": [ "text" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "scidocs",
        "name": "SCIDOCS",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "scifact",
        "name": "SciFact",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 1 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "trec-covid",
        "name": "TREC-COVID",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 2 },
        "display": { "template": { "body": "### {{title.text}}\n{{text.text}}" }},
        "source": "beir"
    },
    {
        "id": "webis-touche2020",
        "name": "Touche-2020",
        "fields": [ "text", "title" ],
        "params": [ "text" ],
        "rating_scale": { "min": 0, "max": 2 },
        "display": { "template": { "body": "### {{title.text}}\n{{tex.textt}}" }},
        "source": "beir"
    },
]


####  Logger  ##################################################################

class ColoredStreamHandler(logging.StreamHandler):
    
    def format(self, record):
        msg = super().format(record)
        level = record.levelno

        if level >= logging.CRITICAL:
            return colored(msg, "magenta", attrs=["bold"])
        elif level >= logging.ERROR:
            return colored(msg, "red", attrs=["bold"])
        elif level >= logging.WARNING:
            return colored(msg, "yellow", attrs=["bold"])
        elif level >= logging.INFO:
            return colored(msg, "white")
        elif level >= logging.DEBUG:
            return colored(msg, "dark_grey")
        else:
            return msg
        
logger = logging.getLogger("colored")
logger.setLevel(logging.DEBUG)
logger.addHandler(ColoredStreamHandler())
        

####  Bulk indexing functions  #################################################

def count_lines(filepath):
    """
    Count the number of lines in a file.
    """
    num_lines = 0
    with open(filepath) as file:
        for i, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            num_lines += 1
    return num_lines

def read_jsonl_lines(filepath, transformer):
    """
    Lazily read and yield JSON objects from a .jsonl or .ndjson file.
    """
    with open(filepath) as file:
        for i, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            line = json.loads(line)
            _id = line["_id"]
            if transformer:
                line = transformer(line)
            yield line, _id
            
def format_for_bulk(docs_with_ids, index):
    """
    Lazily yield actions for the Elasticsearch Bulk API.
    """
    for doc, _id in docs_with_ids:
        action = {
            "_op_type": "index",
            "_index": index,
            "_id": _id
        }
        doc.pop("_id", None)
        action["_source"] = doc
        yield action
        
def bulk_index_worker(docs_with_ids, index, deployment):
    """
    Perform bulk indexing for a batch of documents.
    """
    actions = format_for_bulk(docs_with_ids, index)
    try:
        success, errors = helpers.bulk(es(deployment), actions, raise_on_error=False)
        return success, errors
    except BulkIndexError as e:
        logger.error("\nBulk indexing errors:")
        for error in e.errors:
            logger.error(json.dumps(error, indent=2))
        raise

def chunked_iterable(iterable, size=CHUNK_SIZE_DATA):
    """
    Split iterable into chunks of given size.
    """
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
        
def parallel_bulk_import(deployment, filepath, index, transformer=None, chunk_size=CHUNK_SIZE_DATA):
    """
    Load and index documents from file in parallel using threads.
    """
    num_lines = count_lines(filepath)
    logger.debug(f"Loading {num_lines:,} docs (in batches of {chunk_size:,}) into index: {index}")
    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count()-1)) as executor:
        futures = []
        num_docs = 0
        num_successes = 0
        num_errors = 0
        num_running_total = 0
        for chunk in chunked_iterable(read_jsonl_lines(filepath, transformer), size=chunk_size):
            num_docs += len(chunk)
            futures.append(executor.submit(bulk_index_worker, chunk, index, deployment))
        for future in futures:
            successes, errors = future.result()
            num_successes += successes
            num_errors += len(errors)
            num_running_total += successes + len(errors)
            logger.debug(f"Bulk loading into {index}: {len(errors):,} errors ({num_errors:,} total), {successes:,} successes ({num_running_total:,} total), {(num_running_total / num_docs * 100):.4f}% done")
            for error in errors:
                print(f"\n{error}")
        logger.debug(f"Done. Indexed {num_successes:,} docs with {num_errors:,} errors.")
        
        
####  Document formatting functions  ###########################################

def dataset_directory(dataset):
    return os.path.join(SAMPLE_DATA_DIRECTORY, dataset["id"])

def staging_directory(dataset):
    return os.path.join(dataset_directory(dataset), "esrs")

def make_timestamp():
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def make_index_name(dataset):
    """
    Generate an index name for a given sample dataset.
    """
    return f"{SAMPLE_DATA_INDEX_PREFIX}{dataset['id']}"

def make_workspace_id(dataset):
    """
    Generate a workspace_id for a given sample dataset.
    """
    return utils.unique_id(f"esrs-sample-data-{dataset['id']}")

def make_strategy_docs(dataset):
    """
    Return a fresh copy of the default strategies to use for sample datasets.
    """
    return [
        {
            "_id": utils.unique_id([
                make_workspace_id(dataset), "query-string-and"
            ]),
            "workspace_id": make_workspace_id(dataset),
            "name": "Query String (AND)",
            "tags": [ "bm25" ],
            "template": {
                "lang": "painless",
                "source": json.dumps({
                    "retriever": {
                        "standard": {
                            "query": {
                                "query_string": {
                                    "query": "{{ text }}",
                                    "default_operator": "AND"
                                }
                            }
                        }
                    }
                }, indent=2)
            }
        },
        {
            "_id": utils.unique_id([
                make_workspace_id(dataset), "query-string-or"
            ]),
            "workspace_id": make_workspace_id(dataset),
            "name": "Query String (OR)",
            "tags": [ "bm25" ],
            "template": {
                "lang": "painless",
                "source": json.dumps({
                    "retriever": {
                        "standard": {
                            "query": {
                                "query_string": {
                                    "query": "{{ text }}",
                                    "default_operator": "OR"
                                }
                            }
                        }
                    }
                }, indent=2)
            }
        }
    ]
    
def make_judgement_doc(dataset, doc_id, scenario_id, rating):
    """
    Create a document that will be indexed in esrs-judgements.
    """
    return {
        "_id": utils.unique_id([
            make_workspace_id(dataset),
            scenario_id,
            make_index_name(dataset),
            doc_id
        ]),
        "workspace_id": make_workspace_id(dataset),
        "scenario_id": scenario_id,
        "index": make_index_name(dataset),
        "doc_id": doc_id,
        "rating": int(rating)
    }
    
def make_scenario_doc(dataset, _id, name, text, tags=[]):
    """
    Create a document that will be indexed in esrs-scenarios.
    """
    return {
        "_id": utils.unique_id([
            make_workspace_id(dataset), { "text": text } 
        ]),
        "workspace_id": make_workspace_id(dataset),
        "name": name,
        "values": { "text": text },
        "tags": tags or []
    }

def make_display_doc(dataset):
    """
    Create a document that will be indexed in esrs-displays.
    """
    return {
        "_id": utils.unique_id([
            make_workspace_id(dataset), make_index_name(dataset)
        ]),
        "workspace_id": make_workspace_id(dataset),
        "index_pattern": make_index_name(dataset),
        "template": dataset.get("display", {}).get("template") or {}
    }
    
def make_workspace_doc(dataset):
    """
    Create a document that will be indexed in esrs-workspaces.
    """
    return {
        "_id": make_workspace_id(dataset),
        "name": dataset["name"],
        "index_pattern": make_index_name(dataset),
        "params": dataset["params"],
        "rating_scale": dataset["rating_scale"],
        "tags": ["beir"],
    }


####  Load workspace assets  #####################################################

def load_evaluations(dataset):
    """
    Load evaluations into Elasticsearch for a given dataset.
    """
    return # Not implemented

def load_benchmarks(dataset):
    """
    Load benchmarks into Elasticsearch for a given dataset.
    """
    return # Not implemented

def load_strategies(dataset):
    """
    Load strategies into Elasticsearch for a given dataset.
    """
    logger.debug(f"Loading strategies for: {dataset['id']}")
    filepath = os.path.join(staging_directory(dataset), "strategies.jsonl")
    def transformer(doc):
        doc.pop("_id", None)
        doc_dict = StrategyCreate.model_validate(doc).serialize()
        doc_dict = utils.copy_fields_to_search("strategies", doc_dict)
        return doc_dict
    parallel_bulk_import("studio", filepath, "esrs-strategies", transformer, chunk_size=CHUNK_SIZE_ASSETS) 

def load_judgements(dataset):
    """
    Load judgements into Elasticsearch for a given dataset.
    """
    logger.debug(f"Loading judgements for: {dataset['id']}")
    filepath = os.path.join(staging_directory(dataset), "judgements.jsonl")
    def transformer(doc):
        doc.pop("_id", None)
        doc_dict = JudgementCreate.model_validate(doc).serialize()
        doc_dict = utils.copy_fields_to_search("judgements", doc_dict)
        return doc_dict
    parallel_bulk_import("studio", filepath, "esrs-judgements", transformer, chunk_size=CHUNK_SIZE_ASSETS)

def load_scenarios(dataset):
    """
    Load scenarios into Elasticsearch for a given dataset.
    """
    logger.debug(f"Loading scenarios for: {dataset['id']}")
    filepath = os.path.join(staging_directory(dataset), "scenarios.jsonl")
    def transformer(doc):
        doc.pop("_id", None)
        doc_dict = ScenarioCreate.model_validate(doc).serialize()
        doc_dict = utils.copy_fields_to_search("scenarios", doc_dict)
        return doc_dict
    parallel_bulk_import("studio", filepath, "esrs-scenarios", transformer, chunk_size=CHUNK_SIZE_ASSETS)

def load_displays(dataset):
    """
    Load displays into Elasticsearch for a given dataset.
    """
    logger.debug(f"Loading displays for: {dataset['id']}")
    filepath = os.path.join(staging_directory(dataset), "displays.jsonl")
    def transformer(doc):
        doc.pop("_id", None)
        doc_dict = DisplayCreate.model_validate(doc).serialize()
        doc_dict = utils.copy_fields_to_search("displays", doc_dict)
        return doc_dict
    parallel_bulk_import("studio", filepath, "esrs-displays", transformer, chunk_size=CHUNK_SIZE_ASSETS)
    
def load_workspace(dataset):
    """
    Load workspace into Elasticsearch for a given dataset.
    """
    logger.debug(f"Loading workspace for: {dataset['id']}")
    #logger.debug(f"Deleting old workspace if it exist for: {make_index_name(dataset)}")
    #api.workspaces.delete(make_workspace_id(dataset))
    filepath = os.path.join(staging_directory(dataset), "workspaces.jsonl")
    def transformer(doc):
        doc.pop("_id", None)
        doc_dict = WorkspaceCreate.model_validate(doc).serialize()
        doc_dict = utils.copy_fields_to_search("workspaces", doc_dict)
        return doc_dict
    parallel_bulk_import("studio", filepath, "esrs-workspaces", transformer, chunk_size=CHUNK_SIZE_ASSETS)

def load_dataset_assets(dataset):
    """
    Load all workspace assets into Elasticsearch for a given dataset.
    """
    logger.info(f"Loading workspace assets for: {dataset['id']}")
    load_workspace(dataset)
    load_displays(dataset)
    load_scenarios(dataset)
    load_judgements(dataset)
    load_strategies(dataset)
    load_benchmarks(dataset)
    load_evaluations(dataset)
    
def load_datasets_assets(datasets):
    """
    Load all workspace assets into Elasticsearch for all given datasets.
    """
    for dataset in datasets:
        load_dataset_assets(dataset)
        
        
####  Stage workspace assets  ####################################################

def stage_evaluations(dataset):
    """
    Create "evauations" assets for a given dataset.
    Save them to the staging directory.
    """
    return # Not implemented
    #logger.debug(f"Staging evaluations for: {dataset['id']}")
    #filepath_output = os.path.join(staging_directory(dataset), "evaluations.jsonl")
    #with open(filepath_output, "w") as output:
    #    pass

def stage_benchmarks(dataset):
    """
    Create "benchmarks" assets for a given dataset.
    Save them to the staging directory.
    """
    return # Not implemented
    #logger.debug(f"Staging benchmarks for: {dataset['id']}")
    #filepath_output = os.path.join(staging_directory(dataset), "benchmarks.jsonl")
    #with open(filepath_output, "w") as output:
    #    pass

def stage_strategies(dataset):
    """
    Create "strategies" assets for a given dataset.
    Save them to the staging directory.
    """
    logger.debug(f"Staging strategys for: {dataset['id']}")
    filepath_output = os.path.join(staging_directory(dataset), "strategies.jsonl")
    with open(filepath_output, "w") as output:
        for asset in make_strategy_docs(dataset):
            print(json.dumps(asset), file=output)

def stage_judgements(dataset):
    """
    Create "judgements" assets for a given dataset.
    Save them to the staging directory.
    """
    logger.debug(f"Loading scenario _ids into memory for: {dataset['id']}")
    scenario_ids = {}
    filepath_input = os.path.join(dataset_directory(dataset), "queries.jsonl")
    with open(filepath_input) as input:
        for line in input:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            scenario_ids[data["_id"]] = utils.unique_id([
                make_workspace_id(dataset), { "text": data["text"] } 
            ])
            
    logger.debug(f"Staging judgements for: {dataset['id']}")
    filepath_output = os.path.join(staging_directory(dataset), "judgements.jsonl")
    for type in ( "dev", "test", "train" ):
        filepath_input = os.path.join(dataset_directory(dataset), "qrels", f"{type}.tsv")
        if not os.path.exists(filepath_input):
            continue
        with open(filepath_input) as input, open(filepath_output, "w") as output:
            for i, line in enumerate(input):
                if i == 0:
                    continue
                line = line.strip()
                if not line:
                    continue
                query_id, corpus_id, score = line.split("\t")
                asset = make_judgement_doc(
                    dataset,
                    doc_id=corpus_id,
                    scenario_id=scenario_ids[query_id],
                    rating=score
                )
                print(json.dumps(asset), file=output)

def stage_scenarios(dataset):
    """
    Create "scenarios" assets for a given dataset.
    Save them to the staging directory.
    """
    logger.debug(f"Staging scenarios for: {dataset['id']}")
    filepath_input = os.path.join(dataset_directory(dataset), "queries.jsonl")
    filepath_output = os.path.join(staging_directory(dataset), "scenarios.jsonl")
    with open(filepath_input) as input, open(filepath_output, "w") as output:
        for line in input:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            asset = make_scenario_doc(
                dataset,
                _id=data["_id"],
                name=data.get("metadata", {}).get("query") or data["_id"],
                text=data["text"]
            )
            print(json.dumps(asset), file=output)

def stage_displays(dataset):
    """
    Create "displays" assets for a given dataset.
    Save them to the staging directory.
    """
    logger.debug(f"Staging displays for: {dataset['id']}")
    filepath_output = os.path.join(staging_directory(dataset), "displays.jsonl")
    with open(filepath_output, "w") as output:
        asset = make_display_doc(dataset)
        print(json.dumps(asset), file=output)

def stage_workspace(dataset):
    """
    Create a "workspace" asset for a given dataset.
    Save it to the staging directory.
    """
    logger.debug(f"Staging workspace for: {dataset['id']}")
    filepath_output = os.path.join(staging_directory(dataset), "workspaces.jsonl")
    with open(filepath_output, "w") as output:
        asset = make_workspace_doc(dataset)
        print(json.dumps(asset), file=output)

def stage_dataset_assets(dataset):
    """
    Transform and stage a given dataset from its original format to
    workspace assets for Elasticsearch Relevance Studio. Save each set of assets
    to its respective sample data directory.
    """
    logger.info(f"Staging workspace assets for dataset: {dataset['id']}")
    try:
        logger.debug(f"Wiping any existing workspace assets in: {staging_directory(dataset)}")
        shutil.rmtree(staging_directory(dataset))
    except FileNotFoundError:
        pass
    logger.debug(f"Staging new workspace assets in: {staging_directory(dataset)}")
    os.mkdir(staging_directory(dataset))
    stage_workspace(dataset)
    stage_displays(dataset)
    stage_scenarios(dataset)
    stage_judgements(dataset)
    stage_strategies(dataset)
    stage_benchmarks(dataset)
    stage_evaluations(dataset)
    
def stage_datasets_assets(datasets):
    """
    Transform and stage all given datasets from their original format to
    workspace assets for Elasticsearch Relevance Studio. Save each set of assets
    to its respective sample data directory.
    """
    for dataset in datasets:
        stage_dataset_assets(dataset)
        
        
####  Load datasets  ###########################################################

def load_dataset(dataset, vectors=False):
    """
    Load a single dataset into Elasticsearch.
    """
    logger.info(f"Loading \"{dataset['id']}\" dataset into index: {make_index_name(dataset)}")
    logger.debug(f"Wiping old index if it exists: {make_index_name(dataset)}")
    # (Re)create index
    es("content").options(ignore_status=404).indices.delete(index=make_index_name(dataset))
    mapping = { "properties": {}}
    for field in dataset["fields"]:
        mapping["properties"][field] = {
            "properties": {
                "text": {
                    "type": "text"
                }
            }
        }
        if vectors:
            mapping["properties"][field]["properties"]["elser"] = {
                "type": "semantic_text",
                "inference_id": "elser"
            }
            mapping["properties"][field]["properties"]["e5"] = {
                "type": "semantic_text",
                "inference_id": "elser"
            }
    es("content").indices.create(index=make_index_name(dataset), mappings=mapping)
    filepath = os.path.join(dataset_directory(dataset), "corpus.jsonl")
    def transformer(doc):
        _doc = {}
        for field in dataset["fields"]:
            _doc[field] = {
                "text": doc[field]
            }
            if vectors:
                _doc[field]["elser"] = doc[field]
                _doc[field]["e5"] = doc[field]
        return _doc
    logger.debug(f"Bulk loading data into index: {make_index_name(dataset)}")
    parallel_bulk_import("content", filepath, make_index_name(dataset), transformer)

def load_datasets(datasets, vectors=False):
    """
    Load all given datasets into Elasticsearch.
    """
    for dataset in datasets:
        load_dataset(dataset, vectors)
    
    
####  Download datasets  #######################################################

def download_dataset(dataset):
    """
    Download a single dataset. Save the dataset in its original format to its
    respective sample data directory.
    """
    logger.info(f"Downloading dataset: {dataset['id']}")
    url = f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{dataset['id']}.zip"
    logger.debug(f"Downloading from: {url}")
    util.download_and_unzip(url, SAMPLE_DATA_DIRECTORY)
    logger.debug(f"Extracted to: {SAMPLE_DATA_DIRECTORY}/{dataset['id']}")

def download_datasets(datasets):
    """
    Download all given datasets. Save the dataset in its original format to its
    respective sample data directory.
    """
    for dataset in datasets:
        download_dataset(dataset)
        
        
####  CLI # ####################################################################

@click.group()
def cli():
    """
    Relevance Studio CLI.
    """
    pass

@cli.command()
def list():
    """
    List available datasets.
    """
    click.echo("Available datasets:")
    for dataset in SAMPLE_DATASETS:
        click.echo(f"  - {dataset['id']}")

def handle_run(run_download, run_load, run_stage, run_import, run_all, datasets, vectors=False):
    datasets = datasets.split(",") if datasets else []
    datasets = [ d.strip() for d in datasets ]
    valid_datasets = {}
    for i, dataset in enumerate(SAMPLE_DATASETS):
        valid_datasets[dataset["id"]] = dataset
    _datasets = []
    for dataset in (datasets or valid_datasets.keys()):
        if dataset not in valid_datasets:
            logger.warning(f"Unknown dataset specified: {dataset}")
            return sys.exit()
        _datasets.append(valid_datasets[dataset])
    if not _datasets:
        logger.warning("No valid datasets specified.")
        return sys.exit()
    if run_all:
        run_download = run_load = run_stage = run_import = True
    if run_download:
        download_datasets(_datasets)
    if run_load:
        load_datasets(_datasets, vectors)
    if run_stage:
        stage_datasets_assets(_datasets)
    if run_import:
        load_datasets_assets(_datasets)

@cli.command()
@click.option("-d", "--download", "run_download", is_flag=True, help="Download datasets from their sources")
@click.option("-l", "--load", "run_load", is_flag=True, help="Load datasets into Elasticsearch")
@click.option("-s", "--stage", "run_stage", is_flag=True, help="Stage workspace assets for datasets")
@click.option("-i", "--import", "run_import", is_flag=True, help="Import staged workspace assets into Elasticsearch")
@click.option("-a", "--all", "run_all", is_flag=True, help="Run all steps (default)")
@click.option("-v", "--vectors", is_flag=True, help="Include ELSER and E5 vectorization")
@click.option("--datasets", "-D", multiple=False, help="Datasets to run (comma separated). Defaults to all.")
def run(run_download, run_load, run_stage, run_import, run_all, datasets, vectors=False):
    """
    Download and ingest sample datasets.
    """
    if not any([run_download, run_load, run_stage, run_import]):
        run_all = True
    handle_run(run_download, run_load, run_stage, run_import, run_all, datasets, vectors)
 
if __name__ == "__main__":
    cli()