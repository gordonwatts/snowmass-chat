# snowmass-chat

Experiments exploring the US Snowmass Process documents using LLM

## Introduction

## Usage

Getting from a list of documents to a working chat-bot follows the below steps:

1. Download locally all the PDF files that are the source material.
    * Use the `chatter -c snowmass/snowmass.yaml cache download` command
1. Chunk the PDF files
1. Upload into an account at XXX
1. Profit (and also pay)

### Snowmass Info

Included is a config file for `snowmass`.

Paper Sources:

* [Snowmass White Paper Archive](https://snowmass21.org/submissions/start)

## Architecture & Development

### virtual-env for development

1. Create a new virtual environment
1. `pip install -e .` from the root directory
