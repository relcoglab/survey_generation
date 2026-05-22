import json
import os
import typer
from typing import List

app = typer.Typer()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_json_file(file_path: str):
    with open(file_path, 'r') as file:
        return json.load(file)

def save_json_file(data, file_path: str):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def find_and_replace_placeholders(template_data, input_data):
    scenario_text = input_data[0]['scenario']
    choice_text = input_data[0]['choice']
    base_entities = [e.strip() for e in input_data[0]['entities'].split(',') if e.strip() != '']

    for element in template_data['SurveyElements']:
        if element['Element'] == 'SQ' and 'Payload' in element:
            payload = element['Payload']
            if payload.get('DataExportTag') == 'entity_q':
                entities = base_entities + ["an old man with a long white beard", "a mouse"]
            else:
                entities = base_entities.copy()

            if 'QuestionText' in payload:
                payload['QuestionText'] = payload['QuestionText'].replace('SCENARIO_TEXT', scenario_text)
                payload['QuestionText'] = payload['QuestionText'].replace('CHOICE_TEXT', choice_text)

            if 'Choices' in payload:
                for entity_index, entity in enumerate(entities, start=1):
                    key = str(entity_index)
                    if key in payload['Choices']:
                        payload['Choices'][key]['Display'] = entity
                    else:
                        payload['Choices'][key] = {'Display': entity}
                current_keys = list(payload['Choices'].keys())
                for key in current_keys:
                    if int(key) > len(entities):
                        del payload['Choices'][key]
    return template_data

def update_looping_options(template_data, input_data):
    outcomes = input_data[0]['outcomes']
    for element in template_data['SurveyElements']:
        if element['Element'] == 'BL':
            payload = element.get('Payload', {})
            for block_id, block in payload.items():
                if block.get('Description') == 'outcome_block':
                    looping_options = block.get('Options', {}).get('LoopingOptions', {}).get('Static', {})
                    for idx, outcome in enumerate(outcomes, start=1):
                        looping_options[str(idx)] = {"1": outcome}
                    block['Options']['LoopingOptions']['Static'] = looping_options
    return template_data

def update_survey_name(template_data, input_file):
    input_filename = os.path.splitext(os.path.basename(input_file))[0]
    survey_name = f"Annotation Validation Study [{input_filename}]"
    if 'SurveyEntry' in template_data:
        template_data['SurveyEntry']['SurveyName'] = survey_name
    return template_data

def update_consent_question(template_data):
    for element in template_data['SurveyElements']:
        if element['Element'] == 'SQ' and element['Payload']['QuestionDescription'].startswith("CONSENT You are being asked"):
            element['Payload']['QuestionDescription'] = "CONSENT You are being asked to take part in a research study. Before you decide to participate in..."
            element['Payload']['Choices'] = {
                "4": {"Display": "I have read the consent form and agree to participate."},
                "5": {"Display": "I do not agree to participate."}
            }
            element['Payload']['ChoiceOrder'] = ["4", "5"]
            break
    return template_data

def update_specific_question(template_data):
    for element in template_data['SurveyElements']:
        if element['Element'] == 'SQ' and element['Payload']['QuestionDescription'].startswith("Given the above scenario and action choice, how likely is this outcome to occur?"):
            element['Payload']['Choices'] = {"1": {"Display": "&nbsp;"}}
            element['Payload']['ChoiceOrder'] = ["1"]
            break
    return template_data

def update_real_world_experience_question(template_data):
    for element in template_data['SurveyElements']:
        if element['Element'] == 'SQ' and element['Payload']['QuestionDescription'].startswith("Your task is to read a piece of text describing one person's real-world experience."):
            element['Payload']['Choices'] = {"1": {"Display": "Mary"}, "2": {"Display": "Lamb"}, "3": {"Display": "Snow"}, "4": {"Display": "School"}}
            element['Payload']['ChoiceOrder'] = ["1", "2", "3", "4"]
            break
    return template_data


def update_outcome_list_question(template_data, input_data):
    outcomes = input_data[0]['outcomes']
    # Formatting each outcome as an HTML list item
    formatted_outcome_list = "<ul>" + "".join(f"<li>{outcome}</li>" for outcome in outcomes) + "</ul>"

    for element in template_data['SurveyElements']:
        if element['Element'] == 'SQ' and 'Payload' in element:
            if element['Payload'].get('DataExportTag') == 'Q18':
                # Replace 'OUTCOME_LIST' with the formatted list of outcomes
                element['Payload']['QuestionText'] = element['Payload']['QuestionText'].replace('OUTCOME_LIST', formatted_outcome_list)
                break
    return template_data


def process_template(template_file: str, input_files: List[str], output_directory: str):
    for input_file in input_files:
        template_data = load_json_file(template_file)  # Move loading here to ensure a fresh template each time
        input_data = load_json_file(input_file)
        updated_data = find_and_replace_placeholders(template_data, input_data)
        updated_data_with_outcomes = update_looping_options(updated_data, input_data)
        updated_data_with_outcome_list = update_outcome_list_question(updated_data_with_outcomes, input_data)
        updated_data_with_name = update_survey_name(updated_data_with_outcome_list, input_file)
        updated_data_consent = update_consent_question(updated_data_with_name)
        updated_data_specific = update_specific_question(updated_data_consent)
        final_updated_data = update_real_world_experience_question(updated_data_specific)
        output_filename = "Formatted_" + os.path.basename(input_file)
        output_file = os.path.join(output_directory, output_filename)
        save_json_file(final_updated_data, output_file)



@app.command()


def main(template: str = typer.Argument(..., help="Path to the template JSON file"),
         input_dir: str = typer.Option("scenarios", "--input_dir", help="Directory containing input JSON files"),
         output_dir: str = typer.Option("surveys", "--output_dir", help="Directory to save output JSON files")):
    template_file = os.path.join(BASE_DIR, template)
    input_dir_path = os.path.join(BASE_DIR, input_dir)
    output_dir_path = os.path.join(BASE_DIR, output_dir)

    input_files = [os.path.join(input_dir_path, f) for f in os.listdir(input_dir_path) if f.endswith('.json')]
    process_template(template_file, input_files, output_dir_path)
    typer.echo("Processing completed.")

if __name__ == "__main__":
    app()

## TO RUN THE SCRIPT: python3.11 utils.py templates/Annotation_Validation_Study_template.json 

