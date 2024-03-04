# snowmass-chat

Experiments exploring the US Snowmass Process documents using LLM

## Introduction

## Usage

Getting from a list of documents to a working chat-bot follows the below steps:

1. Download locally all the PDF files that are the source material.
    * Use the `chatter -c snowmass/snowmass.yaml cache download` command
    * Use the `chatter -c snowmass/snowmass.yaml cache set <dir>` to set a custom directory and copy down all the previously downloaded files to avoid having to hit the archive for anything but metadata. Better yet, copy down the `pickle` files.
1. The next steps require accessing OpenAI endpoints.
    * Use `chatter keys set openai <key>` to set the key.
1. Load the files, using their embedding, into the vector store database
    * use `chatter -c snowmass/snowmass.yaml vector populate`
    * This could take some time as it involves sending and receiving all the PDF data to OpenAI for their embedding.
1. Make your query
    * Use `chatter -c snowmass/snowmass.yaml query ask "What does the MATHUSULA experiment do?`
    * Change `ask` to `find` to see what chunks of text are used by the LLM to answer your question.

### Snowmass Info

Included is a config file for `snowmass`.

Paper Sources:

* [Snowmass White Paper Archive](https://snowmass21.org/submissions/start)

## Architecture & Development

### virtual-env for development

1. Create a new virtual environment
1. `pip install -e .[test]` from the root directory
