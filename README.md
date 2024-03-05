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
    * Use `chatter -c snowmass/snowmass.yaml query ask "What does the MATHUSLA experiment do?`
    * Change `ask` to `find` to see what chunks of text are used by the LLM to answer your question.
    * Use the new gpt 4.5 turbo from the command line: `chatter -c snowmass/snowmass.yaml query ask -q "gpt-4-turbo-preview" "What does the MATHUSLA experiment do?"`, or set it as the default:
1. Generate answers file for comparison
    * Generate a `yaml` file contains the answers to a list of questions
        * `chatter -c snowmass/snowmass.yaml questions --questions_file snowmass/snowmass-questions.yaml ask "Default config, but updated code" snowmass/snowmass-v1.0-update.yaml`
    * You can then generate a markdown file that "compares" the answers in a table
        * `chatter -c snowmass/snowmass.yaml questions --questions_file snowmass/snowmass-questions.yaml compare snowmass/snowmass-v1.0.yaml snowmass/snowmass-v1.0-update.yaml`
        * This will write a table to your output terminal, but you can also generate a markdown file - see command line help for the `compare` sub-command.

### Snowmass Info

Included is a config file for `snowmass`.

Paper Sources:

* [Snowmass White Paper Archive](https://snowmass21.org/submissions/start)

## Architecture & Development

### virtual-env for development

1. Create a new virtual environment
1. `pip install -e .[test]` from the root directory
